import asyncio
import unittest
from dataclasses import replace
from html.parser import HTMLParser
from unittest.mock import patch

from aiohttp import ClientSession, WSServerHandshakeError
from aiohttp.test_utils import TestClient, TestServer, unused_port
from aiohttp.web_ws import WebSocketResponse

from carstream.config import Settings
from carstream.server import create_app

TOKEN = "test-token-that-is-not-a-real-secret"


class FakeSession:
    def __init__(self, _settings):
        self.events = asyncio.Queue()
        self.closed = asyncio.Event()
        self.answers = []
        self.candidates = []

    async def create_offer(self):
        await self.events.put({"type": "offer", "sdp": "test-sdp"})

    async def accept_answer(self, text):
        self.answers.append(text)

    def add_candidate(self, line_index, candidate):
        self.candidates.append((line_index, candidate))

    async def watch_bus(self):
        await asyncio.Future()

    async def wait_connected(self, timeout):
        await asyncio.Future()

    async def watch_connection(self):
        await asyncio.Future()

    async def close(self):
        self.closed.set()


class SignalingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sessions = []

        def factory(settings):
            session = FakeSession(settings)
            self.sessions.append(session)
            return session

        self.client = TestClient(TestServer(create_app(Settings(access_token=TOKEN), factory)))
        await self.client.start_server()
        self.origin = str(self.client.make_url("/")).rstrip("/")

    async def asyncTearDown(self):
        await self.client.close()

    async def connect(self, token=TOKEN):
        websocket = await self.client.ws_connect("/ws", headers={"Origin": self.origin})
        await websocket.send_json({"type": "auth", "token": token})
        return websocket

    async def test_authentication_precedes_camera_and_ice_credentials(self):
        websocket = await self.connect("wrong-token")
        self.assertEqual((await websocket.receive_json())["message"], "Invalid access token")
        self.assertEqual(self.sessions, [])
        await websocket.close()

    async def test_rejects_foreign_origin(self):
        with self.assertRaises(WSServerHandshakeError) as failure:
            await self.client.ws_connect("/ws", headers={"Origin": "https://attacker.invalid"})
        self.assertEqual(failure.exception.status, 403)
        self.assertEqual(self.sessions, [])

    async def test_multiple_viewers_have_independent_media_lifetimes(self):
        viewers = []
        for _viewer_number in range(9):
            websocket = await self.connect()
            self.assertEqual((await websocket.receive_json())["type"], "ready")
            self.assertEqual((await websocket.receive_json())["type"], "offer")
            viewers.append(websocket)
        self.assertEqual(len(self.sessions), 9)
        await viewers[0].close()
        await asyncio.wait_for(self.sessions[0].closed.wait(), 2)
        self.assertTrue(all(not session.closed.is_set() for session in self.sessions[1:]))
        for viewer_index in (1, 8):
            await viewers[viewer_index].send_json(
                {"type": "ice", "candidate": "test-candidate", "sdpMLineIndex": 0}
            )
            await viewers[viewer_index].send_json({"type": "invalid"})
            self.assertEqual((await viewers[viewer_index].receive_json())["type"], "error")
            await asyncio.wait_for(self.sessions[viewer_index].closed.wait(), 2)
            self.assertEqual(self.sessions[viewer_index].candidates, [(0, "test-candidate")])
        self.assertFalse(self.sessions[2].closed.is_set())
        for websocket in viewers[1:]:
            await websocket.close()

    async def test_malformed_candidate_closes_media_without_leaking_payload(self):
        websocket = await self.connect()
        await websocket.receive_json()
        await websocket.receive_json()
        await websocket.send_json({"type": "ice", "candidate": "private-url", "sdpMLineIndex": -1})
        failure = await websocket.receive_json()
        self.assertEqual(failure["type"], "error")
        self.assertNotIn("private-url", failure["message"])
        await asyncio.wait_for(self.sessions[0].closed.wait(), 2)
        await websocket.close()

    async def test_liveness_and_static_files_do_not_expose_configuration(self):
        response = await self.client.get("/healthz")
        self.assertEqual(await response.json(), {"status": "alive"})
        response = await self.client.get("/")
        self.assertEqual(response.status, 200)
        self.assertNotIn(TOKEN, await response.text())
        response = await self.client.get("/.env")
        self.assertEqual(response.status, 404)

    async def test_player_form_leaves_token_length_policy_to_server(self):
        class TokenInputParser(HTMLParser):
            token_attributes = None

            def handle_starttag(self, tag, attributes):
                attribute_values = dict(attributes)
                if tag == "input" and attribute_values.get("id") == "token":
                    self.token_attributes = attribute_values

        response = await self.client.get("/")
        parser = TokenInputParser()
        parser.feed(await response.text())
        self.assertIsNotNone(parser.token_attributes)
        self.assertEqual(parser.token_attributes.get("type"), "password")
        self.assertIn("required", parser.token_attributes)
        self.assertNotIn("minlength", parser.token_attributes)

    async def test_server_shutdown_closes_active_media(self):
        viewers = [await self.connect() for _viewer_number in range(2)]
        for websocket in viewers:
            self.assertEqual((await websocket.receive_json())["type"], "ready")
        await self.client.server.close()
        self.assertTrue(all(session.closed.is_set() for session in self.sessions))
        for websocket in viewers:
            await websocket.close()

    async def test_client_close_records_code_without_logging_private_payloads(self):
        websocket = await self.connect()
        await websocket.receive_json()
        await websocket.receive_json()
        with self.assertLogs("carstream.server", level="INFO") as captured:
            await websocket.close()
            await asyncio.wait_for(self.sessions[0].closed.wait(), 2)
        output = "\n".join(captured.output)
        self.assertIn("close_code=1000", output)
        self.assertIn("socket_error=none", output)
        self.assertNotIn(TOKEN, output)

    async def test_missing_pong_records_timeout_without_logging_private_payloads(self):
        def short_heartbeat_websocket(**arguments):
            arguments["heartbeat"] = 0.04
            return WebSocketResponse(**arguments)

        with patch("carstream.server.web.WebSocketResponse", short_heartbeat_websocket):
            with self.assertLogs("carstream.server", level="INFO") as captured:
                websocket = await self.client.ws_connect(
                    "/ws", headers={"Origin": self.origin}, autoping=False
                )
                await websocket.send_json({"type": "auth", "token": TOKEN})
                self.assertEqual((await websocket.receive_json())["type"], "ready")
                self.assertEqual((await websocket.receive_json())["type"], "offer")
                await asyncio.wait_for(self.sessions[0].closed.wait(), 2)
                await websocket.close()
        output = "\n".join(captured.output)
        # Python 3.10 formats aiohttp's IntEnum as its name; newer Python uses its value.
        self.assertRegex(output, r"close_code=(?:1006|WSCloseCode\.ABNORMAL_CLOSURE)")
        self.assertIn("socket_error=TimeoutError", output)
        self.assertNotIn(TOKEN, output)


class LocalFeedTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sessions = []
        self.session_settings = []
        self.local_port = unused_port()
        self.settings = Settings(
            access_token=TOKEN,
            local_port=self.local_port,
            public_origin="https://public.example.com",
            stun_url="stun://relay.example.com:3478",
            turn_url="turn://viewer:private-turn-secret@relay.example.com:3478?transport=tcp",
            ice_policy="relay",
        )

        def factory(settings):
            session = FakeSession(settings)
            self.sessions.append(session)
            self.session_settings.append(settings)
            return session

        self.client = TestClient(TestServer(create_app(self.settings, factory)))
        await self.client.start_server()
        self.local_client = ClientSession()
        self.local_url = f"http://127.0.0.1:{self.local_port}"

    async def asyncTearDown(self):
        await self.local_client.close()
        await self.client.close()

    async def connect_local(self, token=TOKEN):
        websocket = await self.local_client.ws_connect(self.local_url + "/ws")
        await websocket.send_json({"type": "auth", "token": token})
        return websocket

    async def test_local_feed_authenticates_before_media_and_omits_cloud_ice(self):
        for token in ("", "wrong-token"):
            websocket = await self.connect_local(token)
            self.assertEqual((await websocket.receive_json())["message"], "Invalid access token")
            await websocket.close()
        self.assertEqual(self.sessions, [])
        websocket = await self.connect_local()
        ready = await websocket.receive_json()
        self.assertEqual(ready["type"], "ready")
        self.assertEqual(ready["iceServers"], [])
        self.assertEqual(ready["iceTransportPolicy"], "all")
        self.assertEqual((await websocket.receive_json())["type"], "offer")
        self.assertEqual(
            self.session_settings[0],
            replace(self.settings, host="127.0.0.1", local_port=0, public_origin="",
                    stun_url="", turn_url="", ice_policy="all"),
        )
        await websocket.send_json({"type": "answer", "sdp": "local-answer"})
        await websocket.send_json({"type": "ice", "candidate": "local-host-candidate", "sdpMLineIndex": 0})
        await websocket.send_json({"type": "invalid"})
        self.assertEqual((await websocket.receive_json())["type"], "error")
        await asyncio.wait_for(self.sessions[0].closed.wait(), 2)
        self.assertEqual(self.sessions[0].answers, ["local-answer"])
        self.assertEqual(self.sessions[0].candidates, [(0, "local-host-candidate")])
        await websocket.close()

    async def test_local_feed_rejects_browser_origins_and_serves_no_player(self):
        for origin in ("https://attacker.invalid", self.settings.public_origin, "null", ""):
            with self.subTest(origin=origin):
                with self.assertRaises(WSServerHandshakeError) as failure:
                    await self.local_client.ws_connect(
                        self.local_url + "/ws", headers={"Origin": origin}
                    )
                self.assertEqual(failure.exception.status, 403)
        self.assertEqual(self.sessions, [])
        for path in ("/", "/player.js", "/.env"):
            response = await self.local_client.get(self.local_url + path)
            self.assertEqual(response.status, 404)
        response = await self.local_client.get(self.local_url + "/healthz")
        self.assertEqual(await response.json(), {"status": "alive"})

    async def test_public_feed_keeps_origin_and_relay_policy_with_local_enabled(self):
        for headers in ({}, {"Origin": "https://attacker.invalid"},
                        {"X-Forwarded-For": "127.0.0.1"}):
            with self.assertRaises(WSServerHandshakeError) as failure:
                await self.client.ws_connect("/ws", headers=headers)
            self.assertEqual(failure.exception.status, 403)
        websocket = await self.client.ws_connect(
            "/ws", headers={"Origin": self.settings.public_origin}
        )
        await websocket.send_json({"type": "auth", "token": TOKEN})
        ready = await websocket.receive_json()
        self.assertEqual(ready["iceTransportPolicy"], "relay")
        self.assertEqual(ready["iceServers"], self.settings.browser_ice_servers())
        self.assertEqual(self.session_settings[0], self.settings)
        await websocket.close()

    async def test_stopping_main_app_releases_local_media_and_listener(self):
        websocket = await self.connect_local()
        await websocket.receive_json()
        await self.client.close()
        self.assertTrue(self.sessions[0].closed.is_set())
        server = await asyncio.start_server(lambda _reader, writer: writer.close(), "127.0.0.1", self.local_port)
        server.close()
        await server.wait_closed()
        await websocket.close()
