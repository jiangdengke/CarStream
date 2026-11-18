import argparse
import json
import logging

from .config import Settings


def main():
    parser = argparse.ArgumentParser(description="RK3588 RTSP / WebRTC gateway")
    parser.add_argument("--check", action="store_true", help="Check native media dependencies only")
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        from .media import REQUIRED_ELEMENTS, inspect_runtime
    except (ImportError, ValueError):
        parser.exit(1, "GStreamer GI is unavailable. See README Ubuntu prerequisites.\n")
    if arguments.check:
        report = inspect_runtime()
        print(json.dumps(report, indent=2))
        missing = [name for name in REQUIRED_ELEMENTS if not report["elements"][name]]
        parser.exit(1 if missing else 0)
    try:
        settings = Settings.from_environment()
    except ValueError as error:
        parser.exit(1, "Configuration error: " + str(error) + "\n")
    from aiohttp import web

    from .server import create_app

    web.run_app(create_app(settings), host=settings.host, port=settings.port, access_log=None)


if __name__ == "__main__":
    main()
