# Deployment and acceptance boundaries

## Board baseline

Inspected on 2026-11-17: RK3588, Ubuntu 22.04.5 LTS, Python 3.10.12,
GStreamer 1.20.3. Rockchip `mppvideodec`, `mpph264enc` and `mpph265enc` exist.
Finite synthetic MPP encoding and H.265-to-H.264 tests reached EOS in the earlier
inspection. The application-specific baseline H.264 caps also passed a finite
hardware test. These are not camera or browser tests, and not resolution/load benchmarks.

Missing at inspection: `gstreamer1.0-nice` (`nicesrc` / `nicesink`), the
`GstWebRTC` GI namespace (`gir1.2-gst-plugins-bad-1.0`), `python3-gst-1.0`, and
`aiohttp`. Synchronization does not install them. The install script uses Ubuntu
packages and accepts apt installation non-interactively. Review the script and
simulate its package transaction before running it on a vendor image.

The trial deployment subsequently installed only the three missing system packages
above, with no upgrades or removals, and put the pinned Python dependencies in a
system-site-packages virtualenv. Native dependency inspection now passes on the
board. The existing MPP plugin defaults to High profile and emits capitalized
profile caps; the application explicitly selects Baseline and places the profile
filter after `h264parse` so the parser can normalize the vendor caps. H.264
passthrough remains unchanged and is not forced to a new profile.

`python -m carstream --check` inspects shared WebRTC requirements and lists optional
source/encoder elements. Success does not prove camera-specific plugins, network
access, a stream, or browser decoding. Startup of an actual session checks its
source-specific elements. With a missing GI namespace the check exits early with
installation guidance rather than pretending the media runtime is ready.

## Current test-pattern trial

The following test-pattern results are the earlier baseline. The runtime is now
configured for the real RTSP camera, but continuous browser playback has not
passed; see [the camera-source trial](#current-camera-source-trial). The last
browser reload of the Mac's forwarded page failed after new SSH timeouts, so
historical HTTP 200 results below are not a claim of current reachability.

Started on 2026-11-17 from `/home/cat/carstream-20261117T060914Z`, with the service
listening only at board `127.0.0.1:8080`. A local SSH forward on this Mac provides
`http://127.0.0.1:18080`. Enter the access token from the private board `.env`; it
is deliberately absent from project documentation and synchronized files.
Returning to the phone hotspot restored the SSH forward and HTTP 200 responses.
The latest token-change check also authenticated through the Mac's forward.
The browser black-screen fix now passes in Cursor's Chromium browser: 640x360
test-pattern video decodes continuously, including after a fresh-page reconnect.
Recheck `/healthz` after network changes, and do not treat HTTP liveness or
successful authentication alone as evidence of video delivery.

The failed browser session reached ICE/DTLS `connected` but decoded zero frames,
with 1829 packets received and 12393 lost in one sample. The H.264 payloader's
default RTP MTU was 1400 bytes; the board's Tailscale interface MTU is 1280.
After explicit approval, outgoing RTP packets are limited to 1200 bytes, leaving
room for SRTP, UDP and IPv6 headers. Both failed and successful browser sessions
selected the same direct IPv6 address pair; the exact dropping hop was not traced.
The fix does not change interface MTUs, routes, firewall rules, codec, bitrate,
HTTP binding or ICE policy. The native smoke test checks actual outgoing packet
sizes as well as decoded frames; the old implementation fails that regression.

At the user's request, the private trial uses a short access token with
`CARSTREAM_ALLOW_WEAK_TOKEN='true'`. This exception requires a literal loopback
bind address and no public origin. Empty tokens remain invalid, and the default
still requires at least 24 characters. Disable this flag and rotate to a random
token before exposing the service through a public proxy. Changing the token
requires restarting the service and reconnecting the browser.
The player requires a nonempty token but does not duplicate the server's minimum
length policy. An old page containing `minlength="24"` must be refreshed after
updating the static HTML; otherwise the browser can block submission of the
explicitly permitted short token before any authentication request is sent.
Server-side token validation and constant-time comparison remain authoritative.

The server was started as a detached user process, not a systemd or boot service.
`server.pid` records its PID, `server.log` holds output, and `.env` holds the test
configuration; all three are private runtime files in the release directory.
Do not run a second copy on the same port. The tunnel runs only while its SSH
process and the Mac's Tailscale connection remain healthy. To recreate it if absent:

```bash
ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 cat@100.94.108.3
```

The phone hotspot restored access to the Tailscale control server and authenticated
board SSH, while the original network could not connect even to the same pinned
control-server IPv4 address. No Clash or Tailscale settings were changed. This
comparison points to the original network path but does not distinguish a router
problem from an upstream restriction. Keep the working network for this trial.

Verification now includes all 16 board unit tests, a native WebRTC loopback with
at least ten decoded frames, and a native receiver using the live server's actual
token authentication, WebSocket SDP/ICE and MPP decode to receive ten frames.
HTTP liveness also passes through the Mac's SSH forward. These checks are **not**
real-camera acceptance or public/TURN acceptance. Separate browser acceptance
now includes visible color bars, decoded-frame growth from 110 to 308 over two
samples, and 203 decoded frames after a clean reload without diagnostic wrappers.

The application no longer rejects additional viewers using a fixed count:
both the single-viewer gate and the eight-WebSocket cap are removed. Each
authenticated viewer owns an independent media pipeline. Two browser pages
simultaneously decoded 790 and 214 frames in one sample; after disconnecting
the first page, the second continued to 676 frames. Nine fake media sessions
are covered by unit tests, but nine real video viewers and sustained capacity
have not been tested. Encoder resources, camera session limits and uplink
bandwidth still bound actual capacity; RTSP mode opens a camera connection per
viewer. See the [multi-viewer decision](decisions/implemented/feature/2026-11-17-multiple-viewers.md).

To stop the trial, SSH into the release directory and inspect the recorded PID
with `ps -p "$(<server.pid)" -o pid,args`. Only if it is this release's Python
CarStream process, run `kill -TERM "$(<server.pid)"`. On the Mac, identify the
SSH listener using `lsof -nP -iTCP:18080 -sTCP:LISTEN` and stop only that tunnel.
The release can then be renamed to `.disabled` without deleting its files.

The system-site-packages virtualenv's `pip check` reports `pynacl 1.5.0 requires
cffi, which is not installed`. CarStream does not use or declare PyNaCl. This
separate dependency inconsistency was not repaired; the attempted comparison with
system Python could not be reconfirmed after the connection interruption.

## Camera setup

The confirmed camera address is `192.168.11.83`. In the authorized temporary
network test, TCP 554 answered RTSP OPTIONS and TCP 80 served `Web Viewer`.
Neither observation proves the stream path, password or codec. No login was attempted.

The temporary `192.168.11.82/32` address and camera-only host route were removed.
The application's network behavior is passive with respect to host configuration:
it does not add addresses/routes or change the default gateway.

The user subsequently approved a permanent camera-side setup. NetworkManager
1.36.6 now saves `Wired connection 1` (UUID
`eeb55747-033d-3ed0-87b3-d5641bc753a7`, interface `eth0`) with static
`192.168.11.82/24`, automatic connection, no IPv4 gateway or DNS, and
`ipv4.never-default=yes`. Its native IPv4 duplicate-address detection is enabled
with `ipv4.dad-timeout=3000` milliseconds; activation completed without detecting
a conflict. The persistent profile is
`/etc/NetworkManager/system-connections/Wired connection 1.nmconnection`;
NetworkManager reports `Unsaved=false`. No application code, `.env`, network
service restart or board reboot was involved.

After activation, `ip -4 route get 192.168.11.83` selects `eth0` with source
`192.168.11.82`, and TCP 554 and 80 both connect from that address. The default
route remains `via 192.168.0.1 dev eth1`, with eth1 `192.168.0.100/24` and
Tailscale `100.94.108.3/32` unchanged. A fresh SSH login and HTTP 200 from both
the board service and the Mac SSH forward pass. Persistence is verified by the
saved profile and automatic-connection setting, not by a reboot test. This is
network acceptance only: no camera login, video decode or source switch was
performed. See the [camera-network decision](decisions/implemented/architecture/2026-11-17-camera-network.md).

To undo only this network change, run on the board:

```bash
sudo nmcli connection down uuid eeb55747-033d-3ed0-87b3-d5641bc753a7
sudo nmcli connection modify uuid eeb55747-033d-3ed0-87b3-d5641bc753a7 \
  ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns "" \
  ipv4.never-default no ipv4.dad-timeout -1 connection.autoconnect yes
```

This restores the inspected DHCP profile and leaves eth0 disconnected, as it was
before the change. It does not modify eth1, Tailscale or the streaming service.

After independently verifying a full RTSP URL and the camera codec:

1. Set `CARSTREAM_SOURCE='rtsp'` and `CARSTREAM_RTSP_URL` in the private `.env`.
2. Set camera credentials separately where the camera supports RTSP authentication.
   If the verified vendor URL embeds credentials in its query, treat the whole URL as a secret.
3. Set `CARSTREAM_CAMERA_CODEC='h264'` or `'h265'` from actual stream information.
4. Restart the service after loading the environment, then connect one browser.

The source uses RTSP over TCP and ignores audio. H.264 passthrough preserves the
camera's profile and level: a browser-incompatible profile cannot be repaired by
repacketization. Prefer a compatible H.264 camera substream when available.
H.265 is decoded by MPP and re-encoded to baseline H.264; continuous real-camera
browser delivery and throughput must still be verified. A failed session closes
its server-side resources. The previously deployed player requires Connect to
retry; the local player now supports [automatic recovery](#player-recovery-local-change-not-yet-deployed),
but that update has not yet reached the board.

## Current camera-source trial

After the permanent camera-network configuration, the user approved switching
the running service from the test pattern to the camera and verifying playback.
The URL supplied in the user's existing script opens successfully with ffprobe
over TCP. It reports HEVC/H.265 Main, 2304x1296, 20 fps and `yuvj420p`.
The running release's private `.env` now sets `CARSTREAM_SOURCE='rtsp'`,
`CARSTREAM_RTSP_URL='rtsp://192.168.11.83:554'`, `CARSTREAM_CAMERA_CODEC='h265'`
and separate camera credential fields. No credentials were added to this
repository or public examples; the private `.env` remains mode 0600.

Before changing the source, the previous process PID 120365 and its release
directory were verified. Its environment was backed up to the private directory
`.source-switch-backup-20261117T075338Z/` within the release. The new environment
passed settings validation, and only that CarStream process was restarted.
The replacement PID was 122431 at startup; always recheck `server.pid` rather
than relying on this historical PID. The access token, loopback bind, network
settings, RTP budget and application source were unchanged.

Initial board HTTP health returned 200 and the process environment confirmed
the RTSP/H.265 settings. The browser selected direct IPv6 UDP and decoded a
2304x1296 camera image; the user supplied a screenshot of the physical scene
with `RTSP camera` and `WebRTC: connected`. However, decoded frames grew from
1 to 13 and then remained at 13, with playback time fixed at 12.737 seconds
while received bytes and packet loss continued increasing. One later sample
reported 11499 received packets and 951 lost, with repeated keyframe requests.
The session subsequently ended with the application's media-pipeline error.

A diagnostic pipeline with an extra native H.264 receiver failed with an
internal-stream error, so it is not a passing decoded-video test. A separate
H.265 MPP decode/H.264 MPP encode pipeline did reach at least 120 encoded buffers
and exited 0; that isolates some transcode capability but does not prove stable
browser delivery. Concurrent diagnostic camera connections may affect results;
neither camera session capacity nor the exact failing component was established.

A single browser reconnect failed to restore video. Two subsequent fresh SSH
attempts timed out, even though the already-open forwarding tunnel still briefly
returned HTTP 200; the final browser reload also failed. No additional retries,
network changes, loss-recovery changes or bitrate changes were attempted.
The diagnostic browser was released and no test viewer was left active. The
requested RTSP source remains configured; the latest process health cannot be
reconfirmed after the management-path interruption. Real-camera live playback
is **not accepted** on the evidence above, and the root cause is not yet proven.

To return to the known test-pattern configuration after SSH access is restored,
verify the PID in `server.pid`, its command line and `/proc/<PID>/cwd`, then stop
only that release's CarStream process. From the release directory run:

```bash
cp .source-switch-backup-20261117T075338Z/.env .env
chmod 600 .env
set -a
. ./.env
set +a
.venv/bin/python -B -u -m carstream
```

This starts the restored configuration in the foreground; do not start it while
another service still owns port 8080. No rollback was executed.

## Player recovery: local change, not yet deployed

The local player treats Connect as a continuing request to watch. WebSocket
closure/error, failed WebRTC, media errors and the initial 65-second connection
timeout release the old session and schedule a fresh authenticated connection.
Retry delays increase through 1, 2, 4, 8, 16 and 30 seconds and stay capped at
30 seconds. Ten seconds of advancing playback resets that backoff; merely
reaching WebRTC `connected` or receiving a single frame does not reset it.

While WebRTC is connected, the player checks presented/dropped frame counts
every two seconds using `getVideoPlaybackQuality()`, or playback time where that
API is absent. About 15 seconds with no progress triggers session recovery.
User pause and browser-blocked autoplay do not cause a reconnect loop; when
autoplay is blocked, press the video's Play control. Normal uninterrupted video
has no duration limit. The backend still closes disconnected/failed sessions;
the player opens a new one rather than preserving an unusable media pipeline.

Disconnect or leaving the page cancels both the current attempt and any pending
retry. An invalid access token stops retries until the user corrects it and
presses Connect again. Token transport, server authentication, Origin checks,
SDP/ICE messages, media packet handling, bitrate and network settings are unchanged.
Callbacks from an obsolete session cannot schedule duplicate retries or replace
the current status with a late video-play rejection.

Verification: `node --test tests/player.test.cjs` passes eight recovery tests;
the original player failed five of the first seven regression cases. The
healthy-playback check advances a simulated clock through five minutes, not
five minutes of real camera footage. All 16 existing Python tests, Python Ruff
and JavaScript syntax checks pass locally. A fresh board SSH attempt still
times out, so no upload, live browser recovery, long-running camera test or
new root-cause diagnosis has been completed. The camera stall remains unresolved;
reconnect support is a recovery mechanism, not a claimed cure for its cause.

Once SSH is restored, back up and upload only `carstream/static/player.js` in
the running release, then reload the browser. Static JavaScript needs no server
restart; keep private `.env` and the camera network unchanged. The original local
script is preserved in ignored `.tmp/player-before-reconnect.js`. To reverse
the local behavior, from the project root run
`cp .tmp/player-before-reconnect.js carstream/static/player.js`; for any later
board deployment, preserve its original script first and restore that copy.
See the [recovery decision](decisions/implemented/feature/2026-11-17-player-recovery.md).

## Public access through Alibaba Cloud

This section describes required deployment work; it is not already deployed.

- **HTTPS and signaling:** use a real hostname/certificate at the cloud reverse
  proxy. Proxy `/`, `/player.js`, `/style.css`, `/healthz` and WebSocket `/ws` to
  the board through a private route. Preserve WebSocket upgrades and permit
  long-lived signaling. Set `CARSTREAM_PUBLIC_ORIGIN` to the exact external origin.
- **Reachable backend:** loopback binding is intentionally not reachable from the
  cloud. For a Tailscale-based proxy, explicitly bind the board service to its
  Tailscale address and restrict access to the trusted cloud proxy using ACLs or
  firewall rules. Do not expose the application HTTP port or camera RTSP publicly.
- **Media connectivity:** a reverse proxy or SSH tunnel does not relay WebRTC
  UDP media. Supply a working STUN/TURN deployment and allow its configured
  listening/relay ports in the cloud security group and host firewall. TURN
  credentials must be restricted and rotated; authorized viewers receive them.
- **Acceptance:** use `CARSTREAM_ICE_POLICY='relay'` with TURN and a browser outside
  Tailscale. Verify decoded video and that the selected ICE candidate pair is
  relay-based. Change the policy only after this check. Direct/STUN-only success
  on a LAN is not public-network acceptance.

The implementation supports a single TURN URI, not a TURN service or credential
issuer. It provides a shared access token, not user accounts, per-user permissions
or a production abuse-protection system. Add proxy-level rate limits and trusted
network restrictions before public use. No public ports are opened by this project.

## Security and troubleshooting

- Default bind address is loopback. Plain HTTP is for local development only.
- Short-token opt-in is for private loopback debugging only; a loopback bind does
  not prevent a reverse proxy or SSH forward from exposing it to other users.
- The token is sent as the first WebSocket message, not in a URL, and not stored
  in browser localStorage. The browser never receives camera credentials.
- Python error messages omit native debug strings because they can include RTSP
  secrets. Do not publish verbose `GST_DEBUG` logs or share a private `.env`.
- `/healthz` only means HTTP liveness. A green response is not a camera-health check.
- Missing plugins: run `--check` using the same Python environment as the service.
- No video: first distinguish missing camera networking/authentication, codec
  mismatch, and ICE connectivity. A test pattern isolates the camera from the check.
- Color bars labeled `TEST PATTERN` are an intentional live synthetic source,
  not camera corruption. They remain until verified RTSP configuration replaces
  `CARSTREAM_SOURCE='test'`; changing the viewer count does not select the camera.
- Stop using Ctrl-C; active media pipelines are released. No background/systemd
  service is installed by the synchronization script.

## Release safety and rollback

`bash scripts/sync-board.sh` uploads an allowlisted set of files into a new private
timestamped directory using SSH and rsync, which must exist on both machines.
It excludes `.env`, virtual environments, caches and local
credentials. It does not use rsync `--delete`, replace a running release or modify
networking. A failed upload may leave a partial, inactive directory; do not run it.
The SSH connect timeout is 30 seconds and rsync's I/O timeout is 60 seconds.

The script prints a command to rename its newly created directory to `.disabled`.
That disables use of the uploaded path without deleting data. If you later start
a service manually, stop it first. Package installation and network changes are
separate operations and are not undone by renaming a source directory.
