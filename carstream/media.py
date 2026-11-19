"""GStreamer owns RTP, codecs and WebRTC; asyncio owns each viewing session."""

import asyncio

import gi

from .errors import MediaError

gi.require_version("Gst", "1.0")
gi.require_version("GstSdp", "1.0")
gi.require_version("GstWebRTC", "1.0")
from gi.repository import Gst, GstSdp, GstWebRTC  # noqa: E402

Gst.init(None)

REQUIRED_ELEMENTS = (
    "webrtcbin",
    "nicesrc",
    "nicesink",
    "dtlssrtpenc",
    "dtlssrtpdec",
    "h264parse",
    "rtph264pay",
    "queue",
    "funnel",
    "capsfilter",
)
RTX_CACHE_PACKETS = 1000


def inspect_runtime():
    names = REQUIRED_ELEMENTS + (
        "rtspsrc",
        "rtph264depay",
        "rtph265depay",
        "h265parse",
        "mppvideodec",
        "mpph264enc",
        "x264enc",
        "videotestsrc",
        "videoconvert",
    )
    return {
        "gstreamer": Gst.version_string(),
        "elements": {name: Gst.ElementFactory.find(name) is not None for name in names},
    }


async def call_with_promise(element, signal_name, *arguments):
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def finish(reply, failed):
        if future.done():
            return
        if failed:
            future.set_exception(MediaError("WebRTC negotiation failed: " + signal_name))
        else:
            future.set_result(reply)

    def changed(promise, *_unused):
        replied = promise.wait() == Gst.PromiseResult.REPLIED
        reply = promise.get_reply() if replied else None
        failed = not replied or (reply is not None and reply.has_field("error"))
        loop.call_soon_threadsafe(finish, reply, failed)

    promise = Gst.Promise.new_with_change_func(changed, None, None)
    element.emit(signal_name, *arguments, promise)
    try:
        return await asyncio.wait_for(future, timeout=10)
    finally:
        if not future.done() or future.cancelled():
            promise.interrupt()


def parse_description(description_type, text):
    result, message = GstSdp.SDPMessage.new_from_text(text)
    if result != GstSdp.SDPResult.OK or message is None:
        raise MediaError("Invalid SDP description")
    return GstWebRTC.WebRTCSessionDescription.new(description_type, message)


class CameraSession:
    def __init__(self, settings):
        self.settings = settings
        self.loop = asyncio.get_running_loop()
        self.events = asyncio.Queue(maxsize=128)
        self.closed = False
        self.remote_description_set = False
        self.pending_candidates = []
        self.signal_handlers = []
        self.webrtc = None
        self.payloader = None
        self.pipeline = Gst.Pipeline.new("camera-session")
        try:
            self._build_pipeline()
        except Exception:
            self.closed = True
            self._release_pipeline()
            raise

    def _connect_signal(self, element, signal_name, callback):
        handler_identifier = element.connect(signal_name, callback)
        self.signal_handlers.append((element, handler_identifier))

    def _release_pipeline(self):
        try:
            # Release cached RTP buffers before stopping their hardware encoder.
            if self.webrtc is not None:
                self.webrtc.set_state(Gst.State.NULL)
            if self.pipeline is not None:
                self.pipeline.set_state(Gst.State.NULL)
        finally:
            # Native signal closures retain Python callbacks, bypassing Python's GC.
            for element, handler_identifier in self.signal_handlers:
                element.disconnect(handler_identifier)
            self.signal_handlers.clear()
            self.webrtc = None
            self.payloader = None
            self.pipeline = None
            self.pending_candidates.clear()

    def _element(self, factory, name=None):
        element = Gst.ElementFactory.make(factory, name)
        if element is None:
            raise MediaError("Missing GStreamer element: " + factory)
        self.pipeline.add(element)
        return element

    def _link(self, *elements):
        for source, destination in zip(elements, elements[1:]):
            if not source.link(destination):
                raise MediaError("Cannot link media pipeline at " + destination.get_name())

    def _encoder(self):
        factory = self.settings.encoder
        if factory == "auto":
            factory = "mpph264enc" if Gst.ElementFactory.find("mpph264enc") else "x264enc"
        encoder = self._element(factory)
        if factory == "x264enc":
            encoder.set_property("tune", "zerolatency")
            encoder.set_property("speed-preset", "ultrafast")
            encoder.set_property("bitrate", 1500)
            encoder.set_property("key-int-max", 30)
            encoder.set_property("bframes", 0)
        else:
            encoder.set_property("bps", 1_500_000)
            encoder.set_property("gop", 30)
            encoder.set_property("profile", "baseline")
        return encoder

    def _build_pipeline(self):
        missing = [name for name in REQUIRED_ELEMENTS if not Gst.ElementFactory.find(name)]
        if missing:
            raise MediaError("Missing GStreamer elements: " + ", ".join(missing))
        self.webrtc = self._element("webrtcbin", "peer")
        self.webrtc.set_property("bundle-policy", GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE)
        if self.settings.stun_url:
            self.webrtc.set_property("stun-server", self.settings.stun_url)
        if self.settings.turn_url and not self.webrtc.emit(
            "add-turn-server", self.settings.turn_url
        ):
            raise MediaError("TURN configuration was rejected")
        if self.settings.ice_policy == "relay":
            self.webrtc.set_property(
                "ice-transport-policy", GstWebRTC.WebRTCICETransportPolicy.RELAY
            )
        self._connect_signal(self.webrtc, "on-ice-candidate", self._on_ice_candidate)
        self._connect_signal(self.webrtc, "notify::connection-state", self._on_connection_state)
        self._connect_signal(self.webrtc, "deep-element-added", self._configure_webrtc_element)

        parser = self._element("h264parse")
        self.payloader = self._element("rtph264pay")
        self.payloader.set_property("pt", 96)
        # Leave room for SRTP, UDP and IPv6 headers on 1280-byte paths.
        self.payloader.set_property("mtu", 1200)
        self.payloader.set_property("config-interval", -1)
        self.payloader.set_property("aggregate-mode", "zero-latency")
        rtp_filter = self._element("capsfilter")
        rtp_filter.set_property(
            "caps",
            Gst.Caps.from_string(
                "application/x-rtp,media=video,encoding-name=H264,clock-rate=90000,payload=96"
            ),
        )
        if self.settings.source == "test" or self.settings.camera_codec == "h265":
            baseline_filter = self._element("capsfilter")
            baseline_filter.set_property(
                "caps", Gst.Caps.from_string("video/x-h264,profile=baseline")
            )
            # Vendor MPP caps use capitalized profile names; h264parse normalizes them.
            self._link(parser, baseline_filter, self.payloader)
        else:
            self._link(parser, self.payloader)
        self._link(self.payloader, rtp_filter, self.webrtc)
        transceiver = self.webrtc.get_static_pad("sink_0").get_property("transceiver")
        transceiver.set_property("direction", GstWebRTC.WebRTCRTPTransceiverDirection.SENDONLY)
        # Negotiate native NACK/RTX so a lost video packet can be recovered.
        transceiver.set_property("do-nack", True)

        if self.settings.source == "test":
            source = self._element("videotestsrc")
            source.set_property("is-live", True)
            converter = self._element("videoconvert")
            raw_filter = self._element("capsfilter")
            raw_filter.set_property(
                "caps",
                Gst.Caps.from_string("video/x-raw,format=NV12,width=640,height=360,framerate=15/1"),
            )
            encoder = self._encoder()
            self._link(source, converter, raw_filter, encoder, parser)
            return

        source = self._element("rtspsrc")
        # Set properties rather than interpolating a URL into gst_parse_launch syntax.
        source.set_property("location", self.settings.rtsp_url)
        source.set_property("protocols", 4)  # GstRTSPLowerTrans.TCP, no UDP camera ports needed.
        source.set_property("latency", 150)
        source.set_property("tcp-timeout", 10_000_000)
        if self.settings.camera_username:
            source.set_property("user-id", self.settings.camera_username)
        if self.settings.camera_password:
            source.set_property("user-pw", self.settings.camera_password)
        video_inputs = self._element("funnel")
        queue = self._element("queue")
        queue.set_property("max-size-time", 1_000_000_000)
        self._link(video_inputs, queue)
        codec = self.settings.camera_codec
        depayloader = self._element("rtp" + codec + "depay")
        if codec == "h264":
            self._link(queue, depayloader, parser)
        else:
            hevc_parser = self._element("h265parse")
            decoder = self._element("mppvideodec")
            encoder = self._encoder()
            self._link(queue, depayloader, hevc_parser, decoder, encoder, parser)

        def select_video(_source, _stream_number, caps):
            return caps.get_structure(0).get_string("media") == "video"

        def link_video(_source, pad):
            caps = pad.get_current_caps()
            if caps is None:
                return
            structure = caps.get_structure(0)
            if structure.get_string("media") != "video":
                return
            if structure.get_string("encoding-name") != codec.upper():
                self._emit(
                    {"type": "error", "message": "Camera codec differs from CARSTREAM_CAMERA_CODEC"}
                )
                return
            # The camera emits multiple SSRC pads; leaving a later one unlinked stops RTSP.
            sink_pad = video_inputs.request_pad_simple("sink_%u")
            if pad.link(sink_pad) != Gst.PadLinkReturn.OK:
                video_inputs.release_request_pad(sink_pad)
                self._emit({"type": "error", "message": "Cannot link camera video stream"})

        self._connect_signal(source, "select-stream", select_video)
        self._connect_signal(source, "pad-added", link_video)

    def _configure_webrtc_element(self, _webrtc, _sub_bin, element):
        factory = element.get_factory()
        if factory is not None and factory.get_name() == "rtprtxsend":
            # The GStreamer default keeps only 100 packets. At this stream's
            # measured rate that is shorter than a brief relay interruption.
            element.set_property("max-size-packets", RTX_CACHE_PACKETS)

    def _emit(self, event):
        def deliver():
            if self.closed:
                return
            if self.events.full():
                self.events.get_nowait()
                self.events.put_nowait({"type": "error", "message": "Signaling queue overflow"})
            else:
                self.events.put_nowait(event)

        self.loop.call_soon_threadsafe(deliver)

    def _on_ice_candidate(self, _element, line_index, candidate):
        self._emit({"type": "ice", "candidate": candidate, "sdpMLineIndex": line_index})

    def _on_connection_state(self, element, _property):
        state = element.get_property("connection-state").value_nick
        self._emit({"type": "state", "state": state})
        if state == "failed":
            self._emit({"type": "error", "message": "WebRTC connection failed; check ICE/TURN"})

    async def create_offer(self):
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            raise MediaError("Cannot start media pipeline")
        # Wait for codec caps, especially SPS/PPS from a real RTSP camera.
        deadline = self.loop.time() + 20
        while self.payloader.get_static_pad("src").get_current_caps() is None:
            if self.loop.time() > deadline:
                raise MediaError(
                    "No camera video received; check network, RTSP path and credentials"
                )
            await asyncio.sleep(0.05)
        reply = await call_with_promise(self.webrtc, "create-offer", None)
        if reply is None or not reply.has_field("offer"):
            raise MediaError("WebRTC did not produce an offer")
        offer = reply.get_value("offer")
        await call_with_promise(self.webrtc, "set-local-description", offer)
        await self.events.put({"type": "offer", "sdp": offer.sdp.as_text()})

    async def accept_answer(self, text):
        if self.remote_description_set:
            raise MediaError("Renegotiation is not supported; reconnect the player")
        answer = parse_description(GstWebRTC.WebRTCSDPType.ANSWER, text)
        await call_with_promise(self.webrtc, "set-remote-description", answer)
        self.remote_description_set = True
        for line_index, candidate in self.pending_candidates:
            self.webrtc.emit("add-ice-candidate", line_index, candidate)
        self.pending_candidates.clear()

    def add_candidate(self, line_index, candidate):
        if not self.remote_description_set:
            if len(self.pending_candidates) >= 64:
                raise MediaError("Too many pending ICE candidates")
            self.pending_candidates.append((line_index, candidate))
        else:
            self.webrtc.emit("add-ice-candidate", line_index, candidate)

    async def watch_bus(self):
        bus = self.pipeline.get_bus()
        while not self.closed:
            message = bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS)
            if message is not None:
                # Native errors can embed camera passwords and URLs; do not forward them.
                if message.type == Gst.MessageType.ERROR:
                    native_error, _native_debug = message.parse_error()
                    factory = (
                        message.src.get_factory() if isinstance(message.src, Gst.Element) else None
                    )
                    component = factory.get_name() if factory is not None else "unknown"
                    domain = {
                        "gst-resource-error-quark": "resource",
                        "gst-stream-error-quark": "stream",
                        "gst-core-error-quark": "core",
                        "gst-library-error-quark": "library",
                    }.get(native_error.domain, "other")
                    raise MediaError(
                        f"Media pipeline failed (component={component}, "
                        f"domain={domain}, code={native_error.code}); "
                        "check credentials, codec and installed plugins"
                    )
                raise MediaError("Camera stream ended; reconnect the player")
            await asyncio.sleep(0.1)

    async def wait_connected(self, timeout):
        deadline = self.loop.time() + timeout
        while self.webrtc.get_property("connection-state").value_nick != "connected":
            if self.loop.time() > deadline:
                raise MediaError("WebRTC connection timed out; check ICE/TURN and browser access")
            await asyncio.sleep(0.1)

    async def watch_connection(self):
        disconnected_since = None
        while not self.closed:
            state = self.webrtc.get_property("connection-state").value_nick
            if state in {"closed", "failed"}:
                raise MediaError("WebRTC connection ended; reconnect the player")
            if state == "disconnected":
                disconnected_since = disconnected_since or self.loop.time()
                if self.loop.time() - disconnected_since > 15:
                    raise MediaError("WebRTC remained disconnected; reconnect the player")
            else:
                disconnected_since = None
            await asyncio.sleep(0.5)

    async def close(self):
        if self.closed:
            return
        self.closed = True
        await asyncio.to_thread(self._release_pipeline)
