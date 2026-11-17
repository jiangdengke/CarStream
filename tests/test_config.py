import unittest

from carstream.config import Settings

TOKEN = "test-token-that-is-not-a-real-secret"


class ConfigurationTests(unittest.TestCase):
    def test_turn_uri_converts_credentials_for_browser(self):
        settings = Settings.from_environment(
            {
                "CARSTREAM_ACCESS_TOKEN": TOKEN,
                "CARSTREAM_TURN_URL": "turns://viewer:secret%3Avalue@[::1]:5349",
                "CARSTREAM_ICE_POLICY": "relay",
            }
        )
        self.assertEqual(
            settings.browser_ice_servers(),
            [{"urls": "turns:[::1]:5349", "username": "viewer", "credential": "secret:value"}],
        )
        self.assertNotIn("secret", repr(settings))
        self.assertNotIn(TOKEN, repr(settings))

    def test_rtsp_mode_requires_an_explicit_url(self):
        with self.assertRaisesRegex(ValueError, "RTSP_URL"):
            Settings.from_environment({"CARSTREAM_ACCESS_TOKEN": TOKEN, "CARSTREAM_SOURCE": "rtsp"})

    def test_relay_requires_turn(self):
        with self.assertRaisesRegex(ValueError, "requires"):
            Settings(access_token=TOKEN, ice_policy="relay").validate()

    def test_refuses_insecure_default_token(self):
        with self.assertRaisesRegex(ValueError, "ACCESS_TOKEN"):
            Settings.from_environment({})

    def test_short_token_requires_explicit_opt_in(self):
        for flag_value in (None, "false"):
            with self.subTest(flag_value=flag_value):
                environment = {"CARSTREAM_ACCESS_TOKEN": "short-test"}
                if flag_value is not None:
                    environment["CARSTREAM_ALLOW_WEAK_TOKEN"] = flag_value
                with self.assertRaisesRegex(ValueError, "24 characters"):
                    Settings.from_environment(environment)

    def test_short_token_opt_in_allows_only_loopback_without_public_origin(self):
        for hostname in ("127.0.0.1", "::1"):
            with self.subTest(hostname=hostname):
                settings = Settings.from_environment(
                    {
                        "CARSTREAM_ACCESS_TOKEN": "short-test",
                        "CARSTREAM_ALLOW_WEAK_TOKEN": "true",
                        "CARSTREAM_HOST": hostname,
                    }
                )
                self.assertTrue(settings.allow_weak_token)
                self.assertEqual(settings.access_token, "short-test")

        for overrides in (
            {"host": "0.0.0.0"},
            {"host": "192.168.0.100"},
            {"host": "100.94.108.3"},
            {"public_origin": "https://video.example.com"},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, "requires loopback"):
                    Settings(
                        access_token="short-test", allow_weak_token=True, **overrides
                    ).validate()

    def test_short_token_opt_in_still_rejects_blank_tokens(self):
        for access_token in ("", "   "):
            with self.subTest(access_token=access_token):
                with self.assertRaisesRegex(ValueError, "must not be empty"):
                    Settings(access_token=access_token, allow_weak_token=True).validate()

    def test_rejects_invalid_weak_token_flag(self):
        with self.assertRaisesRegex(ValueError, "ALLOW_WEAK_TOKEN"):
            Settings.from_environment(
                {"CARSTREAM_ACCESS_TOKEN": TOKEN, "CARSTREAM_ALLOW_WEAK_TOKEN": "invalid"}
            )

    def test_public_origin_is_not_a_url_path(self):
        with self.assertRaisesRegex(ValueError, "PUBLIC_ORIGIN"):
            Settings(
                access_token=TOKEN, public_origin="https://video.example.com/player"
            ).validate()
