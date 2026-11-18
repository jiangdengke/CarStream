"""Optional native resource regression: python -m tests.smoke_cleanup.

Uses only synthetic video. Environment TURN settings are reused privately when
present so closing a session also exercises native ICE allocation cleanup.
"""

import asyncio
import gc
import os
import secrets
import unittest
import weakref
from dataclasses import replace
from pathlib import Path

from gi.repository import GLib

from carstream.config import Settings
from carstream.errors import MediaError
from carstream.media import CameraSession, Gst


class NativeCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_closed_native_sessions_release_callbacks_and_descriptors(self):
        settings = (
            replace(Settings.from_environment(), source="test")
            if os.environ.get("CARSTREAM_ACCESS_TOKEN")
            else Settings(access_token=secrets.token_urlsafe(32))
        )
        descriptor_directory = Path("/proc/self/fd")
        warmed_descriptor_count = None
        session_references = []
        for attempt_number in range(10):
            session = CameraSession(settings)
            session_references.append(weakref.ref(session))
            native_finalizations = []
            native_references = [
                session.pipeline.weak_ref(native_finalizations.append, "pipeline"),
                session.webrtc.weak_ref(native_finalizations.append, "webrtcbin"),
            ]
            try:
                await session.create_offer()
                if settings.turn_url:
                    async def wait_for_relay_candidate(events):
                        while True:
                            event = await events.get()
                            if event["type"] == "ice" and " typ relay" in event["candidate"]:
                                return

                    await asyncio.wait_for(wait_for_relay_candidate(session.events), timeout=15)
            finally:
                await session.close()
            await session.close()
            del session
            gc.collect()
            await asyncio.sleep(1)
            surviving_sessions = sum(reference() is not None for reference in session_references)
            self.assertEqual(surviving_sessions, 0, "Native signal callbacks retained a closed session")
            self.assertCountEqual(native_finalizations, ["pipeline", "webrtcbin"])
            self.assertTrue(all(reference() is None for reference in native_references))
            if descriptor_directory.exists():
                descriptor_count = len(list(descriptor_directory.iterdir()))
                if warmed_descriptor_count is None:
                    warmed_descriptor_count = descriptor_count
                self.assertLessEqual(
                    descriptor_count, warmed_descriptor_count + 1,
                    "Repeated close accumulated native sockets or descriptors",
                )
                print("Closed session", attempt_number + 1, "open descriptors", descriptor_count)

    async def test_pipeline_build_failure_releases_registered_callbacks(self):
        session_references = []

        class FailingSession(CameraSession):
            def _build_pipeline(self):
                session_references.append(weakref.ref(self))
                super()._build_pipeline()
                raise RuntimeError("Synthetic failure after signal registration")

        with self.assertRaisesRegex(RuntimeError, "Synthetic failure"):
            FailingSession(Settings(access_token=secrets.token_urlsafe(32)))
        gc.collect()
        await asyncio.sleep(0.1)
        self.assertIsNone(session_references[0](), "Failed construction retained native callbacks")

    async def test_native_error_metadata_never_includes_raw_message_or_debug(self):
        session = CameraSession(Settings(access_token=secrets.token_urlsafe(32)))
        try:
            source = session.pipeline.get_by_name("peer")
            native_error = GLib.Error.new_literal(
                Gst.ResourceError.quark(), "private-camera-url-must-not-be-exposed",
                int(Gst.ResourceError.READ),
            )
            session.pipeline.get_bus().post(
                Gst.Message.new_error(source, native_error, "private-native-debug")
            )
            with self.assertRaises(MediaError) as failure:
                await session.watch_bus()
            safe_message = str(failure.exception)
            self.assertIn("component=webrtcbin", safe_message)
            self.assertIn("domain=resource", safe_message)
            self.assertIn("code=9", safe_message)
            self.assertNotIn("private-", safe_message)
        finally:
            await session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
