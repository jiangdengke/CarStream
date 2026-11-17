"""Optional native WebRTC loopback: python -m tests.smoke_media.

Requires the full GStreamer runtime, including an H.264 decoder. This is not
a browser compatibility test and never connects to the real camera.
"""

import asyncio
import secrets

from carstream.config import Settings
from carstream.media import (
    CameraSession,
    Gst,
    GstWebRTC,
    call_with_promise,
    parse_description,
)


async def run():
    loop = asyncio.get_running_loop()
    settings = Settings(access_token=secrets.token_urlsafe(32))
    sender = CameraSession(settings)
    packet_sizes = []

    def record_packet_sizes(_pad, information):
        if information.type & Gst.PadProbeType.BUFFER_LIST:
            buffer_list = information.get_buffer_list()
            for buffer_index in range(buffer_list.length()):
                packet_sizes.append(buffer_list.get(buffer_index).get_size())
        elif information.type & Gst.PadProbeType.BUFFER:
            packet_sizes.append(information.get_buffer().get_size())
        return Gst.PadProbeReturn.OK

    sender.payloader.get_static_pad("src").add_probe(
        Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST, record_packet_sizes
    )
    receiver_pipeline = Gst.Pipeline.new("test-receiver")
    receiver = Gst.ElementFactory.make("webrtcbin", "receiver")
    receiver.set_property("bundle-policy", GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE)
    receiver_pipeline.add(receiver)
    decoder_name = "mppvideodec" if Gst.ElementFactory.find("mppvideodec") else "avdec_h264"
    receiver_bin = Gst.parse_bin_from_description(
        "queue ! rtph264depay ! h264parse ! "
        + decoder_name
        + " ! fakesink name=decoded sync=false signal-handoffs=true",
        True,
    )
    receiver_pipeline.add(receiver_bin)
    frames_received = asyncio.Event()
    frame_count = 0
    candidates = asyncio.Queue()
    tasks = []

    def record_frame():
        nonlocal frame_count
        frame_count += 1
        if frame_count >= 10:
            frames_received.set()

    receiver_bin.get_by_name("decoded").connect(
        "handoff", lambda *_unused: loop.call_soon_threadsafe(record_frame)
    )

    def link_received_pad(_element, pad):
        if pad.get_direction() == Gst.PadDirection.SRC:
            sink_pad = receiver_bin.get_static_pad("sink")
            if not sink_pad.is_linked():
                pad.link(sink_pad)

    receiver.connect("pad-added", link_received_pad)
    receiver.connect(
        "on-ice-candidate",
        lambda _element, index, candidate: loop.call_soon_threadsafe(
            candidates.put_nowait, (index, candidate)
        ),
    )

    async def exchange_signaling():
        remote_ready = False
        pending_candidates = []
        while True:
            event = await sender.events.get()
            if event["type"] == "error":
                raise RuntimeError(event["message"])
            if event["type"] == "offer":
                offer = parse_description(GstWebRTC.WebRTCSDPType.OFFER, event["sdp"])
                await call_with_promise(receiver, "set-remote-description", offer)
                remote_ready = True
                for index, candidate in pending_candidates:
                    receiver.emit("add-ice-candidate", index, candidate)
                reply = await call_with_promise(receiver, "create-answer", None)
                answer = reply.get_value("answer")
                await call_with_promise(receiver, "set-local-description", answer)
                await sender.accept_answer(answer.sdp.as_text())
            elif event["type"] == "ice":
                pair = (event["sdpMLineIndex"], event["candidate"])
                if remote_ready:
                    receiver.emit("add-ice-candidate", *pair)
                else:
                    pending_candidates.append(pair)

    async def send_receiver_candidates():
        while True:
            index, candidate = await candidates.get()
            sender.add_candidate(index, candidate)

    async def start_sender():
        await sender.create_offer()
        await sender.watch_bus()

    try:
        receiver_pipeline.set_state(Gst.State.PLAYING)
        tasks = [
            asyncio.create_task(coroutine)
            for coroutine in (
                exchange_signaling(),
                send_receiver_candidates(),
                start_sender(),
                frames_received.wait(),
            )
        ]
        completed, _pending = await asyncio.wait(
            tasks, timeout=40, return_when=asyncio.FIRST_COMPLETED
        )
        for task in completed:
            task.result()
        if not frames_received.is_set():
            raise RuntimeError("WebRTC loopback did not deliver 10 decoded frames")
        if not packet_sizes or max(packet_sizes) > 1200:
            raise RuntimeError("RTP packets must stay within the 1200-byte path budget")
        print("PASS: WebRTC loopback received at least 10 decoded test-pattern frames")
        print("PASS: largest outgoing RTP packet:", max(packet_sizes), "bytes")
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await sender.close()
        await asyncio.to_thread(receiver_pipeline.set_state, Gst.State.NULL)


if __name__ == "__main__":
    asyncio.run(run())
