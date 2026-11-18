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
passed; see [the camera-source trial](#current-camera-source-trial). The earlier
SSH outage has since cleared. Current reachability and browser recovery checks
are recorded in [the player deployment](#player-recovery-deployed); the historical
HTTP 200 results below alone are not proof of current reachability.

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

## Start/stop scripts

The local project now provides executable root entrypoints `./start.sh` and `./stop.sh`
for Ubuntu/Linux releases. They resolve the release directory from the script
location and require the existing `ss` and `flock` commands. These additions
were deployed into the current release on 2026-11-18 during public-access setup.
All eight updated Linux lifecycle tests passed first in an isolated directory;
the real application was then gracefully restarted to activate public settings.

Start loads the trusted `.env`, validates the application configuration with
the release virtualenv, rejects occupied ports, and uses nohup to detach the
service. Success requires the new PID to own a listening socket on the configured
port, not merely for some service to answer HTTP. Startup errors return nonzero;
if the process remains alive without listening after approximately ten seconds,
its PID is retained for inspection and an explicit stop before retrying.
Repeated start recognizes the recorded service instead of replacing its PID.
Running `./start.sh` backgrounds the service without a caller-supplied `&` or
nohup command. Each actual launch writes stdout and stderr to a separate
`log/carstream-YYYYMMDDTHHMMSS.NNNNNNNNNZ.log` using UTC launch time.
The script prints the exact path on startup success or failure. Restart creates
a new file; a repeated start of an already-running service creates no extra log.
There is no midnight rotation, automatic deletion or migration of the old
`server.log`. Monitor disk usage and preserve historical logs as needed.

Stop does not source `.env`. It verifies a positive PID, the exact release Python
command and `/proc/PID/cwd` before sending SIGTERM. It waits approximately
30 seconds, removes the PID after exit, and returns an error without SIGKILL
on timeout. An absent PID is a no-op; an exited PID is cleared; a live unrelated
process is refused. Manually started foreground services still use Ctrl-C.
`server.lock` serializes script operations and is not inherited by the service.
The log directory is mode 0700; PID and log files are mode 0600. Runtime logs,
PID and lock files are ignored by Git; `log/.gitkeep` retains the empty directory
in source checkouts. Synchronization includes the root scripts with executable
permissions preserved, but does not upload runtime logs or the log directory;
the start script creates it on the board if absent.

Restart is `./stop.sh && ./start.sh`. No systemd unit,
boot autostart, package installation, SSH-forward management, camera settings or
host networking are added. Stopping the service affects all viewers, whereas
Disconnect only releases one browser session. These scripts do not repair the
separate camera-stall problem. See the [lifecycle decision](decisions/implemented/process/2026-11-17-service-scripts.md).

`python3 -B -m unittest discover -s tests -p test_scripts.py -v` checks the scripts
on Linux using temporary releases and a standard-library HTTP fixture on private
temporary ports. It never uses camera credentials or a production PID. These
checks are skipped on macOS or when `ss`/`flock` is unavailable.

To roll back the tooling, stop a script-managed service first if one is running,
then remove only `start.sh` and `stop.sh` and use the documented
manual startup process. Do not remove PID metadata while a service is active.
The current application uses these entrypoints. Its first timestamped log is
`log/carstream-20261118T020735.368277373Z.log`; historical `server.log` is untouched.

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
its server-side resources. The deployed player now supports
[automatic recovery](#player-recovery-deployed), with a live-browser check of
recovery after signaling closure; other fault branches have logic-test coverage.

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

## Player recovery: deployed

The deployed player treats Connect as a continuing request to watch. WebSocket
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
five minutes of real camera footage. All 16 existing Python tests and Python Ruff
passed during implementation. JavaScript syntax and all eight recovery tests
passed again immediately before deployment.

On 2026-11-17 at 08:53 UTC, board SSH was reachable again. Only
`carstream/static/player.js` was uploaded and atomically replaced in the running
release `/home/cat/carstream-20261117T060914Z`. The original file is preserved at
`.player-recovery-backup-20261117T085316Z/player.js` in that release, inside a
mode-0700 directory. Its SHA-256 is
`008dbd3f4c8e8707d38703fd53e37a1bf7e048b130b59b53b707dccf7cf35d45`.
The uploaded file, board HTTP response and Mac-forwarded HTTP response all match
the local SHA-256
`a529f7cc30083246aea911d6294f8f7ca42401e020c1703a5f30db9eff14a567`.
`/healthz` returns HTTP 200. Service PID 122431 and its verified release directory
are unchanged; no service restart, private `.env`, native-media or network change
was needed. The Mac's private `127.0.0.1:18080` SSH forward was recreated.

The refreshed Chromium page loaded the recovery functions and received 2304x1296
camera video. Connect was clicked only once. Closing only that browser session's
WebSocket produced `Reconnecting in 1s...`; a new authenticated session connected
about two seconds after closure without another click. Its decoded-frame count
advanced from 193 to 446 in successive samples. The supplied screenshot also
shows the actual camera scene, not the test pattern.

Longer observation in the same check reproduced the stall. At elapsed second
124, the page reported `Video stopped advancing. Reconnecting in 1s...`.
Further stalled attempts triggered 2, 4, 8 and 16 second backoffs. New WebRTC
connections were established, but sustained video did not recover; the sample
at elapsed second 234 had no active inbound video while waiting to retry.
Packet loss was already visible before the stall (267 lost and 11532 received
packets at elapsed second 96). These observations verify automatic signaling
recovery and real stall detection, not a cure for the camera/media failure.
Continuous real-camera playback still fails acceptance; the loss location and
stall cause remain unproven. The diagnostic viewer was explicitly disconnected
to stop its retries, without stopping the service or other viewers.

To undo only this board deployment, run on the board:

```bash
cd /home/cat/carstream-20261117T060914Z
cp -p .player-recovery-backup-20261117T085316Z/player.js carstream/static/.player-rollback.js
mv carstream/static/.player-rollback.js carstream/static/player.js
```

Then refresh the browser; no service restart is needed. No rollback was executed.
The original local script remains in ignored `.tmp/player-before-reconnect.js`;
`cp .tmp/player-before-reconnect.js carstream/static/player.js` restores it locally.
See the [recovery decision](decisions/implemented/feature/2026-11-17-player-recovery.md).

## Public access through Alibaba Cloud

### Deployed endpoint and acceptance

On 2026-11-18, the user approved `ssh company` (cloud `8.130.208.68`), public port
7777, an independent reverse proxy, necessary TURN and a strong access token.
The endpoint is **https://8.130.208.68:7777**. Use HTTPS, not HTTP.

An external native Python client authenticated over public WSS, selected a
relay/relay ICE pair, completed fingerprint-verified DTLS/SRTP and decoded
992 real-camera frames at 2304x1296 during one 60-second trial. Its connection
was closed cleanly afterward; no camera images were recorded. This is **not**
browser, long-term, concurrent-viewer or automatic-recovery acceptance, and does
not establish that the earlier camera-stall root cause is fixed.

The test client's default ECDSA-only DTLS suites failed against the board's RSA
certificate even after ICE succeeded. Adding browser-like ECDHE-RSA AES-GCM to
that temporary client's cipher list resolved the test. Production media code,
certificate fingerprint verification and DTLS security were not relaxed.

### TLS and token

No domain was supplied. The independent proxy uses an IP-SAN self-signed
certificate, expiring **2027-02-16 02:10:20 UTC**, with SHA-256 fingerprint:

```text
2B:09:45:74:F4:BD:7B:01:08:B3:30:4D:0A:50:1E:22:19:2F:B7:28:F6:38:27:04:1F:ED:50:A2:EB:EC:CE:E2
```

Verify this fingerprint before trusting the certificate. There is no automatic
renewal. Use a domain and trusted certificate before wider distribution. The
certificate configuration is tracked in `deploy/cloud/certificate.cnf`; an
explicit OpenSSL config avoids duplicate extensions produced by this host's
old `openssl req -addext` plus system defaults. Strict Python TLS verification
and certificate-extension inspection pass with the corrected certificate.

Get the token privately in your own terminal; do not publish its output:

```bash
ssh company 'set -a; . /opt/carstream/private/public-access.env; printf "%s\n" "$CARSTREAM_ACCESS_TOKEN"'
```

Enter it in Access token and click Connect. The previous short token is rejected.
The access token and TURN password are independent 32-byte random values, never
written to tracked files. Board `.env` and cloud private environment are mode
0600. TURN stores its derived long-term key in a root-owned, group-readable
configuration for the unprivileged container; that key is also sensitive.

### Topology and operational boundaries

| Component | Current configuration |
| --- | --- |
| Public website/signaling | Independent `carstream-proxy` Nginx container, TLS TCP 7777 |
| Private backend | Cloud `127.0.0.1:17777` over reverse SSH to board `127.0.0.1:8080` |
| Media | Independent `carstream-turn` Coturn 4.19.0 container, explicit TURN/TCP 3478, forced relay on both peers |
| Relay endpoints | UDP 49160-49259, cloud private/public address mapping; not an application viewer-count limit |
| Board application | Same release, PID 132745 at activation; always reread `server.pid` before lifecycle operations |
| Tunnel | User service `carstream-tunnel.service`, automatic restart, enabled with `Linger=yes` |

The board's SSH directories contained no usable existing cloud identity, so a
dedicated Ed25519 key was generated on the board. Its private key never left the
board. Cloud account `carstream-tunnel` has a nologin shell; its authorized key
forces `/bin/false`, disallows PTY/agent/X11 forwarding, and allows forwarding.
The client pins the cloud host key retrieved over the authenticated Mac-to-cloud
connection and requests only a loopback listener. The cloud's old OpenSSH lacks
per-key `permitlisten`; because existing `GatewayPorts clientspecified` is left
unchanged, the key is not a server-enforced single-listener sandbox. Protect it;
stricter account-specific forwarding limits require a separate SSH-server change.

The application binds only loopback, disables weak-token opt-in and uses exact
`CARSTREAM_PUBLIC_ORIGIN='https://8.130.208.68:7777'`. Old localhost/SSH-forward
pages can load but cannot authenticate signaling with their different Origin.
Do not disable Origin validation to work around this; use the public URL.

Public UDP 3478 probes timed out despite a working private listener. Public TCP
3478 answered STUN from both Mac and board, authenticated public relay-to-relay
payload transfer passed, and the real media test used TCP to TURN. Config now
accepts and preserves only `?transport=tcp` or `?transport=udp`; `turns` rejects
UDP. Only video between TURN relay endpoints uses UDP internally. This is not
an all-traffic-on-7777 setup, nor TURN-over-TLS; media remains DTLS/SRTP encrypted.

Cloud Firewalld already allowed all TCP. Only `3478/udp` and `49160-49259/udp`
were added to its public zone, runtime and permanent, without reload. Existing
rules, default route, SSH-server config, security groups, camera networking and
the two original Nginx masters were not changed. There is no Alibaba security
group API available here; its rules were neither inspected nor modified.

Containers use host networking, readonly filesystems, nobody UID, no-new-privileges,
memory/PID limits, temporary writable `/tmp`, and Docker log limits of 3x10 MB.
The proxy drops all capabilities; Coturn adds only NET_BIND_SERVICE because its
upstream executable has a file capability and otherwise fails `exec` under a
fully dropped capability bounding set. Images are pinned to these digests:

```text
public.ecr.aws/docker/library/nginx@sha256:901e593c95dc85f5a729f5765516321366ef4ac401821431d408897e95287d0a
ghcr.io/coturn/coturn@sha256:4e3e84aea0ed53ff2cb059ff5c8f48725c03646a6eec5ff2771c3fc12c46c8f5
```

Docker Hub timed out, so official AWS Docker-library and upstream Coturn GitHub
registries were used. Existing Docker settings were untouched. Cloud Ubuntu
18.04, kernel 4.15, Docker 24.0.2 and existing broad TCP firewall policy remain
security-maintenance risks; containers do not fix an obsolete host. The TURN
credential is shared/static and must be rotated with the board config when
revoked. Private, loopback and multicast TURN peers are denied; this is not a
full account system, billing control or bandwidth-abuse protection.

### Management and logs

On the board as `cat`:

```bash
systemctl --user status carstream-tunnel
journalctl --user -u carstream-tunnel -n 100 -f
cd /home/cat/carstream-20261117T060914Z
./stop.sh && ./start.sh
tail -n 100 -f "$(ls -1t log/carstream-*.log | head -n 1)"
```

Repeat the tail command after application restart to select the new filename.
The tunnel reconnect was explicitly tested using `systemctl --user restart`;
cloud loopback health recovered. Reboot acceptance is pending: only the tunnel
is boot-enabled, **not the Python application**. Start it with `./start.sh`
after a board reboot. Cloud containers have `unless-stopped` restart policy.

On the cloud:

```bash
ssh company 'docker ps --filter name=carstream'
ssh company 'docker logs --tail 100 -f carstream-proxy'
ssh company 'docker logs --tail 100 -f carstream-turn'
```

Proxy access logs are disabled; signaling requests are rate-limited per client
IP, not by fixed viewer count. TURN verbose diagnostics are disabled after the
trial. Native application logs may contain sensitive details; do not publish
them or turn on raw GStreamer debug output without redaction.

### Fail-closed gate and rollback

`/opt/carstream/config/backend-ready` enables routing. It was created only after
the live new process rejected the old token/wrong Origin and accepted the strong
token with native TURN configuration. The proxy returns 503 while it is absent.
To close public routing immediately without touching existing unrelated services:

```bash
ssh company 'rm -f /opt/carstream/config/backend-ready'
```

To stop this project's cloud services as well:

```bash
ssh company 'docker stop carstream-proxy carstream-turn'
```

On the board, `systemctl --user disable --now carstream-tunnel` disables the
dedicated tunnel only. Linger was previously off; `sudo loginctl disable-linger cat`
restores it if no other user services now depend on it. Keep backups and logs.

The private board backup is
`.public-access-backup-20261118T020800Z/{.env,config.py,server.pid}` inside the
release. **Close public routing and disable the tunnel before restoring it:**
it contains the previous weak-token configuration. Then stop the current
identity-checked process with `./stop.sh`, restore only `.env` and
`carstream/config.py` from the backup, and run `./start.sh`. Never restore the
historical PID file or expose the old config via the public proxy.

The cloud `/opt/carstream/private/deployment.json` records exactly the four
runtime/permanent Firewalld additions. Remove only those recorded additions if
fully undoing this deployment; do not reload/replace all firewall rules. Dedicated
account/key removal is optional after disabling the tunnel. No rollback has been
executed. See the [public-access decision](decisions/implemented/architecture/2026-11-18-public-access.md).

## RTSP stability repair

On 2026-11-18, isolated board probes reproduced two separate defects:

- Native GObject signal callbacks retained closed Python sessions and their
  elements. Three close cycles increased descriptors from 7 to 96. Explicit
  handler disconnection and element-reference release also cover construction
  failure and repeated close.
- This camera emits successive H.265 RTP pads with SSRC 0, 1 and 2. Linking only
  the first pad leaves later pads unlinked and stops `rtspsrc` with a stream
  error. A native `funnel` now connects each matching video pad to the existing
  queue/depayloader/MPP path. An `rtpfunnel` trial failed caps negotiation and
  was not deployed. Audio selection, encoder, bitrate and RTP MTU are unchanged.

The application now timestamps safe error logs and includes element factory,
fixed error-domain category and numeric code, never raw native message/debug
strings. Do not enable unredacted native debugging in production.

The native dual-SSRC regression fails against the old input code and passes
against the correction, without opening a camera. Ten synthetic sessions each
gathered an actual TURN relay candidate, then closed twice; Python weakrefs and
native pipeline/webrtcbin finalizers cleared, and settled descriptors remained
17. A separate synthetic WebRTC loopback decoded ten frames with maximum RTP
packet size 1200 bytes. These are not long-term real-camera acceptance tests.

One corrected-camera probe kept progressing for 90 seconds, but earlier probes
still stalled after roughly 37-61 seconds. A stalled process had queued RTSP TCP
input and paused native source tasks, with downstream stages waiting for input.
Disabling RTCP in an isolated comparison did not solve it; production RTCP,
buffering and timeouts remain unchanged. The earlier probe that printed PASS
after output stopped was not a valid continuous-playback pass; later probes
require ongoing progress and fail after eight seconds without outgoing RTP.

### Extended acceptance: not passed

The post-deployment public test targeted 300 seconds of real-camera decoding
through verified HTTPS/WSS and forced relay/relay TURN/TCP. Its last periodic
sample showed 2352 decoded frames at 163 seconds, with 21762 received RTP packets
and 4604 reported lost packets. It subsequently failed after 20 seconds without
a decoded frame; the test process exited 1 after 233 seconds overall. That total
includes setup and cleanup and is not a continuous-playback duration. The initial
15.78-second frame-gap metric includes startup, not just steady playback.

During that trial the application recorded `rtspsrc`, resource-domain code 9
(read error), followed by two safely summarized `ValueError` failures. There is
no per-viewer correlation identifier, so these server errors cannot conclusively
be assigned to that particular test client. The tunnel stayed active with
`NRestarts=0`. Receiver loss counters do not identify where packets were lost.

A subsequent isolated camera-to-fakesink probe, using the same source settings
and fixed input code but without the public WebRTC path, kept progressing for
180 seconds and produced 3600 encoded frames. Both successive SSRC pads linked.
It logged only fixed diagnostic categories, never raw native messages or RTSP
credentials, and closed at the end. This one passing source-path trial does not
negate the earlier intermittent stalls or the failed public acceptance.

The final read-only check found the deployed hash unchanged, one active camera
TCP connection, application HTTP health alive and the tunnel active without
restarts. Live descriptor counts vary with active viewers and are not comparable
to the isolated cleanup-test baseline. All diagnostic viewers have exited;
production remains running. No further RTCP, buffering, timeout or bitrate
adjustment was deployed. Remaining work is to correlate source progress and
receiver progress in the same failing viewing session before choosing a fix;
browser and long-term stability are not accepted.

After identity-checked graceful restarts, the current release has the cleanup
and input fixes; activation PID was 137473. Always reread `server.pid` rather
than using that historical PID. Latest activation log:

```text
log/carstream-20261118T032426.290965088Z.log
```

Deployed `carstream/media.py` SHA-256:

```text
cafbaa81d43ea537ef220788645144a96c2c0254738891cd2079c2a5772a55c8
```

The input-only rollback retains the cleanup fix and does not restore secrets:

```bash
cd /home/cat/carstream-20261117T060914Z
./stop.sh
cp -p .rtsp-input-backup-20261118T032425Z/media.py carstream/.media-rollback.py
mv carstream/.media-rollback.py carstream/media.py
./start.sh
```

Stop if any command fails; do not overwrite code while the app is running.
This rollback deliberately reintroduces the unlinked-SSRC defect. The earlier
`.stability-backup-20261118T024200Z` holds pre-cleanup `media.py`, `server.py`
and `__main__.py`; restoring them would also reintroduce the callback leak.
Neither rollback was executed. Public token, exact Origin, SSH tunnel, camera
network and existing cloud services were not changed by these application fixes.
See the [repair decision](decisions/implemented/bug-fix/2026-11-18-rtsp-session-lifetime.md).

### Future trusted-domain deployment

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

The Python application supports a single TURN URI and does not issue temporary
TURN credentials. Coturn is deployed separately above. Shared tokens are not
user accounts, per-user permissions or a production abuse-protection system.
The passive synchronization script does not open ports; the separately approved
public deployment above does.

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
