"""Configuration contains secrets; never log its full representation."""

import os
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class Settings:
    access_token: str = field(repr=False)
    allow_weak_token: bool = False
    host: str = "127.0.0.1"
    port: int = 8080
    source: str = "test"
    rtsp_url: str = field(default="", repr=False)
    camera_username: str = field(default="", repr=False)
    camera_password: str = field(default="", repr=False)
    camera_codec: str = "h264"
    encoder: str = "auto"
    public_origin: str = ""
    stun_url: str = ""
    turn_url: str = field(default="", repr=False)
    ice_policy: str = "all"

    @classmethod
    def from_environment(cls, environment=None):
        environment = os.environ if environment is None else environment
        values = {
            name: environment["CARSTREAM_" + name.upper()]
            for name in cls.__dataclass_fields__
            if "CARSTREAM_" + name.upper() in environment
        }
        values.setdefault("access_token", "")
        if "port" in values:
            values["port"] = int(values["port"])
        if "allow_weak_token" in values:
            flag_value = values["allow_weak_token"].lower()
            if flag_value not in {"true", "false"}:
                raise ValueError("CARSTREAM_ALLOW_WEAK_TOKEN must be true or false")
            values["allow_weak_token"] = flag_value == "true"
        settings = cls(**values)
        settings.validate()
        return settings

    def validate(self):
        if not self.access_token.strip():
            raise ValueError("CARSTREAM_ACCESS_TOKEN must not be empty")
        if self.allow_weak_token and (
            self.host not in {"127.0.0.1", "::1"} or self.public_origin
        ):
            raise ValueError(
                "CARSTREAM_ALLOW_WEAK_TOKEN requires loopback HOST and no PUBLIC_ORIGIN"
            )
        if len(self.access_token) < 24 and not self.allow_weak_token:
            raise ValueError("CARSTREAM_ACCESS_TOKEN must contain at least 24 characters")
        if not 1 <= self.port <= 65535:
            raise ValueError("CARSTREAM_PORT must be between 1 and 65535")
        for name, allowed in {
            "source": {"test", "rtsp"},
            "camera_codec": {"h264", "h265"},
            "encoder": {"auto", "mpph264enc", "x264enc"},
            "ice_policy": {"all", "relay"},
        }.items():
            if getattr(self, name) not in allowed:
                raise ValueError("Invalid CARSTREAM_" + name.upper())
        if self.source == "rtsp":
            parsed = urlsplit(self.rtsp_url)
            if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.hostname:
                raise ValueError("Set a verified CARSTREAM_RTSP_URL for the camera")
        if self.public_origin:
            parsed = urlsplit(self.public_origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
            ):
                raise ValueError("CARSTREAM_PUBLIC_ORIGIN must be an HTTP(S) origin without a path")
        if self.stun_url:
            parsed = urlsplit(self.stun_url)
            if parsed.scheme != "stun" or not parsed.hostname or parsed.username or parsed.path:
                raise ValueError("CARSTREAM_STUN_URL must use stun://host:port")
            _ = parsed.port
        if self.turn_url:
            parsed = urlsplit(self.turn_url)
            if (
                parsed.scheme not in {"turn", "turns"}
                or not parsed.hostname
                or not parsed.username
                or not parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "CARSTREAM_TURN_URL must use turn[s]://username:password@host:port"
                )
            _ = parsed.port
        if self.ice_policy == "relay" and not self.turn_url:
            raise ValueError("Relay policy requires CARSTREAM_TURN_URL")

    def browser_ice_servers(self):
        servers = []
        for address in [self.stun_url, self.turn_url]:
            if not address:
                continue
            parsed = urlsplit(address)
            hostname = parsed.hostname
            if ":" in hostname:
                hostname = "[" + hostname + "]"
            authority = hostname + (":" + str(parsed.port) if parsed.port else "")
            server = {"urls": parsed.scheme + ":" + authority}
            if parsed.scheme in {"turn", "turns"}:
                server.update(
                    username=unquote(parsed.username), credential=unquote(parsed.password)
                )
            servers.append(server)
        return servers
