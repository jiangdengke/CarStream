"""Authenticated WebSocket signaling and a same-origin, receive-only player."""

import asyncio
import hmac
import json
import logging
from pathlib import Path

from aiohttp import WSMsgType, web

from .errors import MediaError

STATIC_DIRECTORY = Path(__file__).with_name("static")
LOGGER = logging.getLogger(__name__)


def decode_message(message):
    if message.type != WSMsgType.TEXT:
        raise ValueError("Expected a JSON text message")
    payload = json.loads(message.data)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    return payload


def create_app(settings, session_factory=None):
    settings.validate()
    if session_factory is None:
        from .media import CameraSession

        session_factory = CameraSession

    app = web.Application(client_max_size=131072)
    active_sockets = set()
    viewing_tasks = set()

    async def index(_request):
        return web.FileResponse(STATIC_DIRECTORY / "index.html")

    async def javascript(_request):
        return web.FileResponse(STATIC_DIRECTORY / "player.js")

    async def stylesheet(_request):
        return web.FileResponse(STATIC_DIRECTORY / "style.css")

    async def health(_request):
        # Liveness only; does not claim that camera or WebRTC are ready.
        return web.json_response({"status": "alive"})

    async def signaling(request):
        expected_origin = settings.public_origin or request.scheme + "://" + request.host
        if request.headers.get("Origin") != expected_origin:
            raise web.HTTPForbidden(text="Origin not allowed")
        websocket = web.WebSocketResponse(heartbeat=20, max_msg_size=131072)
        active_sockets.add(websocket)
        handler_task = asyncio.current_task()
        viewing_tasks.add(handler_task)
        session = None
        tasks = []
        try:
            await websocket.prepare(request)
            payload = decode_message(await asyncio.wait_for(websocket.receive(), timeout=10))
            supplied_token = payload.get("token")
            if (
                payload.get("type") != "auth"
                or not isinstance(supplied_token, str)
                or not hmac.compare_digest(supplied_token.encode(), settings.access_token.encode())
            ):
                await websocket.send_json({"type": "error", "message": "Invalid access token"})
                return websocket
            session = session_factory(settings)
            await websocket.send_json(
                {
                    "type": "ready",
                    "source": settings.source,
                    "iceServers": settings.browser_ice_servers(),
                    "iceTransportPolicy": settings.ice_policy,
                }
            )

            async def send_events():
                while True:
                    event = await session.events.get()
                    await asyncio.wait_for(websocket.send_json(event), timeout=10)
                    if event.get("type") == "error":
                        return

            async def receive_events():
                async for message in websocket:
                    payload = decode_message(message)
                    if payload.get("type") == "answer":
                        description = payload.get("sdp")
                        if not isinstance(description, str) or not 1 <= len(description) <= 120000:
                            raise ValueError("Invalid SDP answer")
                        await session.accept_answer(description)
                    elif payload.get("type") == "ice":
                        candidate = payload.get("candidate")
                        line_index = payload.get("sdpMLineIndex")
                        if (
                            not isinstance(candidate, str)
                            or len(candidate) > 4096
                            or type(line_index) is not int
                            or not 0 <= line_index <= 16
                        ):
                            raise ValueError("Invalid ICE candidate")
                        session.add_candidate(line_index, candidate)
                    else:
                        raise ValueError("Unexpected signaling message")

            async def establish_connection():
                await session.create_offer()
                # Bound abandoned negotiation even if WebSocket heartbeat still succeeds.
                await session.wait_connected(timeout=30)
                await session.watch_connection()

            tasks = [
                asyncio.create_task(coroutine)
                for coroutine in (
                    send_events(),
                    receive_events(),
                    establish_connection(),
                    session.watch_bus(),
                )
            ]
            completed, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in completed:
                task.result()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            # Never log raw exceptions: native libraries may include camera credentials.
            safe_message = (
                str(error)
                if isinstance(error, MediaError)
                else "Session failed; check configuration or reconnect"
            )
            LOGGER.warning("Viewing session failed (%s): %s", type(error).__name__, safe_message)
            if websocket.prepared and not websocket.closed:
                try:
                    await asyncio.wait_for(
                        websocket.send_json({"type": "error", "message": safe_message}), 3
                    )
                except (ConnectionError, asyncio.TimeoutError, RuntimeError):
                    pass
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                if session is not None:
                    await session.close()
            finally:
                active_sockets.discard(websocket)
                viewing_tasks.discard(handler_task)
                await websocket.close()
        return websocket

    async def secure_headers(_request, response):
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'",
            }
        )

    async def shutdown(_app):
        await asyncio.gather(
            *(
                socket.close(code=1001, message=b"Server shutting down")
                for socket in list(active_sockets)
            )
        )
        if viewing_tasks:
            await asyncio.gather(*list(viewing_tasks), return_exceptions=True)

    app.router.add_get("/", index)
    app.router.add_get("/player.js", javascript)
    app.router.add_get("/style.css", stylesheet)
    app.router.add_get("/healthz", health)
    app.router.add_get("/ws", signaling)
    app.on_response_prepare.append(secure_headers)
    app.on_shutdown.append(shutdown)
    return app
