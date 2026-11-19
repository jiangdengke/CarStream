"""Optional board-only local feed check: python -m tests.smoke_local_feed.

Load the private environment first and enable CARSTREAM_LOCAL_PORT. Connects to
the running service, decodes without saving images and checks host-only ICE.
"""

import asyncio
import json

from aiohttp import ClientSession

from carstream.config import Settings
from carstream.media import Gst, GstWebRTC, call_with_promise, parse_description


async def run():
    settings = Settings.from_environment()
    if not settings.local_port:
        raise RuntimeError("Enable CARSTREAM_LOCAL_PORT before testing the local feed")
    loop = asyncio.get_running_loop()
    pipeline = Gst.Pipeline.new("local-feed-receiver")
    peer = Gst.ElementFactory.make("webrtcbin", "receiver")
    peer.set_property("bundle-policy", GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE)
    pipeline.add(peer)
    decoder = "avdec_h264" if Gst.ElementFactory.find("avdec_h264") else "mppvideodec"
    decoded_video = Gst.parse_bin_from_description(
        "queue ! rtph264depay ! h264parse ! " + decoder
        + " ! fakesink name=decoded sync=false signal-handoffs=true", True,
    )
    pipeline.add(decoded_video)
    candidate_queue = asyncio.Queue()
    candidate_types = {"sender": set(), "receiver": set()}
    decoded_frames = 0
    frame_sizes = set()
    frames_ready = asyncio.Event()
    tasks = []
    handlers = []

    def count_frame(width, height):
        nonlocal decoded_frames
        decoded_frames += 1
        frame_sizes.add((width, height))
        if decoded_frames >= 100:
            frames_ready.set()

    def observe_frame(sink, _buffer, _pad):
        structure = sink.get_static_pad("sink").get_current_caps().get_structure(0)
        loop.call_soon_threadsafe(count_frame, structure.get_value("width"), structure.get_value("height"))

    def link_video(_peer, pad):
        if pad.get_direction() == Gst.PadDirection.SRC:
            pad.link(decoded_video.get_static_pad("sink"))

    def observe_candidate(_peer, line_index, candidate):
        loop.call_soon_threadsafe(candidate_queue.put_nowait, (line_index, candidate))

    handlers.append((peer, peer.connect("pad-added", link_video)))
    handlers.append((peer, peer.connect("on-ice-candidate", observe_candidate)))
    sink = decoded_video.get_by_name("decoded")
    handlers.append((sink, sink.connect("handoff", observe_frame)))

    def check_candidate(direction, candidate):
        fields = candidate.split()
        if len(fields) < 8 or fields[6] != "typ" or fields[7] != "host":
            raise RuntimeError("Local feed exchanged a non-host ICE candidate")
        candidate_types[direction].add(fields[7])

    try:
        async with ClientSession() as client:
            async with client.ws_connect(
                f"http://127.0.0.1:{settings.local_port}/ws", heartbeat=20,
            ) as websocket:
                await websocket.send_json({"type": "auth", "token": settings.access_token})
                ready = await websocket.receive_json(timeout=10)
                if ready.get("type") != "ready" or ready.get("iceServers") != [] or ready.get("iceTransportPolicy") != "all":
                    raise RuntimeError("Local feed did not provide authenticated direct-only settings")
                pipeline.set_state(Gst.State.PLAYING)

                async def receive_signaling():
                    remote_ready = False
                    pending_candidates = []
                    async for message in websocket:
                        event = json.loads(message.data)
                        if event["type"] == "error":
                            raise RuntimeError("Local sender reported a media failure")
                        if event["type"] == "offer":
                            for line in event["sdp"].splitlines():
                                if line.startswith("a=candidate:"):
                                    check_candidate("sender", line[2:])
                            description = parse_description(GstWebRTC.WebRTCSDPType.OFFER, event["sdp"])
                            await call_with_promise(peer, "set-remote-description", description)
                            remote_ready = True
                            for line_index, candidate in pending_candidates:
                                peer.emit("add-ice-candidate", line_index, candidate)
                            response = await call_with_promise(peer, "create-answer", None)
                            answer = response.get_value("answer")
                            await call_with_promise(peer, "set-local-description", answer)
                            await websocket.send_json({"type": "answer", "sdp": answer.sdp.as_text()})
                        elif event["type"] == "ice":
                            check_candidate("sender", event["candidate"])
                            pair = (event["sdpMLineIndex"], event["candidate"])
                            if remote_ready:
                                peer.emit("add-ice-candidate", *pair)
                            else:
                                pending_candidates.append(pair)
                    raise RuntimeError("Local feed closed before decode verification")

                async def send_candidates():
                    while True:
                        line_index, candidate = await candidate_queue.get()
                        check_candidate("receiver", candidate)
                        await websocket.send_json({"type": "ice", "candidate": candidate, "sdpMLineIndex": line_index})

                tasks = [asyncio.create_task(coroutine) for coroutine in (
                    receive_signaling(), send_candidates(), frames_ready.wait(),
                )]
                completed, _pending = await asyncio.wait(tasks, timeout=45, return_when=asyncio.FIRST_COMPLETED)
                for task in completed:
                    task.result()
                if not frames_ready.is_set() or any(types != {"host"} for types in candidate_types.values()):
                    raise RuntimeError("Local feed did not deliver 100 decoded frames with host-only ICE")
                print(json.dumps({"local_feed": "passed", "decoded_frames": decoded_frames,
                                  "frame_sizes": sorted(frame_sizes), "ice_candidates": "host/host",
                                  "cloud_ice_servers": 0}), flush=True)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for element, handler in handlers:
            element.disconnect(handler)
        await asyncio.to_thread(pipeline.set_state, Gst.State.NULL)


if __name__ == "__main__":
    asyncio.run(run())
