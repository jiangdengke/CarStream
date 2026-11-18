"""Native RTSP pad regression: python -m tests.smoke_rtsp.

Constructs a stopped camera pipeline and simulates its observed SSRC pads.
Never opens a camera connection or processes private camera data.
"""

import secrets
import unittest

from carstream.config import Settings
from carstream.media import CameraSession, Gst


class NativeRtspPadTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_camera_ssrc_pads_connect_to_the_video_path(self):
        session = CameraSession(
            Settings(
                access_token=secrets.token_urlsafe(32),
                source="rtsp",
                rtsp_url="rtsp://127.0.0.1:1/test-only",
                camera_codec="h265",
            )
        )
        try:
            source = next(
                element for element, _handler_identifier in session.signal_handlers
                if element.get_factory().get_name() == "rtspsrc"
            )
            video_pads = []
            for synchronization_source in (0, 1):
                pad = Gst.Pad.new(
                    f"recv_rtp_src_0_{synchronization_source}_98", Gst.PadDirection.SRC
                )
                pad.set_active(True)
                caps = Gst.Caps.from_string(
                    "application/x-rtp,media=video,encoding-name=H265,"
                    f"clock-rate=90000,payload=98,ssrc=(uint){synchronization_source}"
                )
                pad.store_sticky_event(Gst.Event.new_caps(caps))
                self.assertTrue(source.add_pad(pad))
                self.assertTrue(pad.is_linked(), "A new camera SSRC must not remain unlinked")
                video_pads.append(pad)
            first_input = video_pads[0].get_peer()
            second_input = video_pads[1].get_peer()
            self.assertNotEqual(first_input, second_input)
            funnel = first_input.get_parent_element()
            self.assertEqual(funnel, second_input.get_parent_element())
            self.assertEqual(funnel.get_factory().get_name(), "funnel")
            self.assertTrue(funnel.get_static_pad("src").is_linked())
            self.assertTrue(session.events.empty())
        finally:
            await session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
