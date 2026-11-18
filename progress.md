# Progress

## 2026-11-17 - Task: Write the Python RTSP-to-WebRTC application locally

### What was done

- Implemented a single-camera, single-viewer video gateway using Python/aiohttp and native GStreamer, with a receive-only browser player.
- Added a synthetic test source, H.264 passthrough and an MPP H.265-to-H.264 path without assuming the camera's login, RTSP path or codec.
- Added token-gated signaling, origin checks, explicit ICE configuration, session cleanup and dependency diagnostics.
- Supplied locked Python dependencies, an explicit Ubuntu prerequisite installer and a release-isolated upload script. Neither script embeds credentials; upload does not install or start services.
- Documented setup, camera/network prerequisites, public-access boundaries and the implementation decision. No camera network configuration was changed in this task.

### Testing

- PASS: `.venv/bin/python -m unittest discover -s tests -v`, 11 tests on local Python 3.15.2. Coverage includes configuration, authentication before media creation, origin rejection, single-viewer release, malformed signaling and shutdown. Media is a test double.
- PASS: `.venv/bin/ruff check carstream tests`, `node --check carstream/static/player.js`, `bash -n scripts/install-ubuntu-deps.sh scripts/sync-board.sh`, and `uv lock --check`.
- PASS: architecture note tree/format/archive validators with `AGENT_NOTE_ROOT=docs/decisions`; one active note. Git append-only archive checking is inapplicable because the workspace is not a Git repository.
- PASS: SSH connectivity to the board and the `/home/cat` release parent were checked. A finite board test of `videotestsrc num-buffers=10 is-live=true ! video/x-raw,format=NV12,width=640,height=360,framerate=15/1 ! mpph264enc bps=1500000 gop=30 ! video/x-h264,profile=baseline ! h264parse ! fakesink sync=false` exited 0 under a 15-second limit.
- BLOCKED: local `.venv/bin/python -m tests.smoke_media` exits with `Missing GStreamer elements: nicesrc, nicesink`. Native WebRTC loopback has not passed.
- NOT VERIFIED: actual camera media, browser decoding, H.265 camera compatibility, TURN relay, public-network viewing and sustained performance. Earlier board inspection also found missing GstWebRTC GI, ICE packages and aiohttp. Code synchronization is not runtime deployment.
- IDE ReadLints was not available in the exposed tool catalog; command-line Ruff was used successfully instead.

### Notes

Changed files:

- `.gitignore`: excludes local secrets, environments and generated caches.
- `.env.example`: provides non-secret configuration names and safe defaults.
- `pyproject.toml`: declares Python/aiohttp and lint tooling requirements.
- `uv.lock`: locks development and runtime dependency resolution.
- `requirements.txt`: exports runtime-only, Python-version-aware pinned dependencies.
- `carstream/__init__.py`: defines the application package.
- `carstream/__main__.py`: adds server startup and native dependency inspection.
- `carstream/config.py`: validates environment configuration and converts ICE URI settings for browsers.
- `carstream/errors.py`: separates safe media errors from native diagnostic output.
- `carstream/media.py`: implements native source pipelines, WebRTC negotiation and resource cleanup.
- `carstream/server.py`: implements protected signaling, static routes and viewer lifecycle limits.
- `carstream/static/index.html`: provides the receive-only video player page.
- `carstream/static/player.js`: implements ordered browser SDP/ICE handling and disconnection.
- `carstream/static/style.css`: styles the player.
- `tests/__init__.py`: defines the test package.
- `tests/test_config.py`: checks secret representation, required settings and ICE conversion.
- `tests/test_server.py`: checks access boundaries, signaling errors and session cleanup.
- `tests/smoke_media.py`: adds an opt-in native WebRTC decoded-frame loopback check.
- `scripts/install-ubuntu-deps.sh`: provides explicit Ubuntu prerequisite installation without network reconfiguration.
- `scripts/sync-board.sh`: uploads an allowlist into a new private release directory without secrets or automatic execution.
- `README.md`: provides scope, configuration, startup and verification instructions.
- `docs/deployment.md`: records board prerequisites, camera/public-access acceptance and rollback boundaries.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: records the Python/GStreamer boundary, alternatives and outstanding validation.
- `progress.md`: records implementation evidence and limitations.

Local `.venv` and tool caches are generated development artifacts, excluded from upload. No real `.env` or credentials were created.

Rollback: this workspace started empty and no service is installed by this task. To preserve all local work while disabling this project path, from its parent run `mv /Users/jiangdk/code/company/CarStream /Users/jiangdk/code/company/CarStream.disabled-20261117` after checking that the destination does not exist. This does not uninstall any host-level tools. Board uploads use separate release paths and have their own rollback record below when completed.

## 2026-11-17 - Task: Attempt synchronization to the RK3588 board

### What was done

- Attempted to upload the completed local project to private, timestamped release directories on `cat@100.94.108.3`, without changing existing releases or starting services.
- Increased the SSH connection allowance from 10 to 30 seconds after an observed timeout. Replaced the initial tar stream with rsync for visible file-transfer progress and to avoid macOS extended-attribute archive warnings.
- Stopped failed local transfer children. No further automatic retries are running. No board packages were installed and no camera routes or addresses were changed.
- Synchronization is BLOCKED/INCOMPLETE, not successful: remote content integrity and board-side application checks could not be confirmed.

### Testing

- PASS: `bash -n scripts/sync-board.sh` after the transport change.
- OBSERVED: initial SSH connection timed out. `tailscale ping --c=2 --timeout=10s 100.94.108.3` saw one timeout and one response through DERP(hkg) at 1.638 seconds; no direct connection was established by that probe.
- FAILED: the tar upload to `/home/cat/carstream-20261117T043318Z` exceeded its observation timeout and left an unverified partial directory. Its remaining local SSH child was stopped.
- FAILED: rsync to `/home/cat/carstream-20261117T043556Z` listed all 24 allowlisted files and 8 directory entries, then reported `poll: timeout` / `rsync_sender`. This is not evidence of a completed upload. Failed transfer children were stopped; the wrapper exited 20.
- BLOCKED: a fresh SSH connection for remote file inspection, Python 3.10 configuration tests and `--check` timed out connecting to port 22. Those remote checks did not run.
- NOT VERIFIED: either partial release's completeness. The final local documentation/log changes were not synchronized after the connection failure. Do not start either partial release.

### Notes

Changed files and directories:

- `scripts/sync-board.sh`: uses rsync with visible progress, a 30-second SSH connect timeout and a 60-second I/O timeout, preserving allowlist and new-directory safety.
- `README.md`: documents the SSH/rsync prerequisite and explicitly rejects incomplete uploads as runnable releases.
- `docs/deployment.md`: documents sync timeouts, required tools and the installer's noninteractive apt behavior.
- `progress.md`: appends the actual synchronization failure and verification gap without changing earlier history.
- Board `/home/cat/carstream-20261117T043318Z/`: contains an unverified partial tar upload; inactive and not a release to run.
- Board `/home/cat/carstream-20261117T043556Z/`: contains an unverified partial rsync upload of the allowlisted project files; inactive and not a release to run.

The authoritative complete source remains this local workspace. Minimal next action: restore stable SSH reachability, rerun `bash scripts/sync-board.sh`, and verify remote content before dependency installation or startup.

Rollback after SSH is reachable: preserve the partial copies but mark them unusable with `ssh cat@100.94.108.3 'test ! -e /home/cat/carstream-20261117T043318Z.disabled && mv /home/cat/carstream-20261117T043318Z /home/cat/carstream-20261117T043318Z.disabled'` and `ssh cat@100.94.108.3 'test ! -e /home/cat/carstream-20261117T043556Z.disabled && mv /home/cat/carstream-20261117T043556Z /home/cat/carstream-20261117T043556Z.disabled'`. These commands were not executed because the link is unavailable. There is no deployed service or package change to roll back.

## 2026-11-17 - Task: Reconnect and resume synchronization after reported network recovery

### What was done

- Successfully authenticated as `cat` on `lubancat`, then resumed the previously requested project upload into a new isolated directory.
- The connection failed again during transfer. Stopped the timed-out upload and performed bounded read-only connectivity checks, including SSH through `tailscale nc` without changing routes or proxy settings.
- Did not install packages, start CarStream, change Clash/Tailscale configuration, or touch the user's existing SSH process. No automatic upload retry remains running.

### Testing

- PASS: SSH returned `SSH_CONNECTED`, hostname `lubancat`, username `cat`, Python 3.10.12, the existing `/home/cat` directory and `/usr/bin/rsync`; SSH exited 0.
- PASS: `bash -n scripts/sync-board.sh` before running the unchanged upload script.
- FAILED: the upload to `/home/cat/carstream-20261117T052346Z` listed 32 file/directory entries but exceeded the 120-second overall deadline. The wrapper terminated its transfer process group and exited 1. No successful completion or content-integrity result was obtained.
- BLOCKED: a subsequent SSH command intended to compute remote SHA-256 hashes and run Python configuration/dependency checks timed out connecting to port 22. Those checks did not run.
- OBSERVED: `route -n get 100.94.108.3` selected `utun6`, MTU 1280. This does not identify which application owns the interface or prove a Clash conflict. A Tailscale ping received no reply.
- FAILED: an independent SSH attempt using `ProxyCommand=tailscale nc %h %p` timed out during banner exchange. Neither this result nor the ping establishes whether the failure is local, remote or in the overlay relay.
- PASS: process inspection found no remaining agent upload, rsync, or `tailscale nc` process; the pre-existing user SSH process was left intact.
- NOT VERIFIED: latest uploaded files, application startup, camera media or browser playback. The source remains complete locally; the board copy is not approved for use.

### Notes

Changed files and directories:

- `progress.md`: appends the confirmed successful login, subsequent transfer interruption and bounded diagnostic evidence.
- Board `/home/cat/carstream-20261117T052346Z/`: contains an unverified upload attempt of the existing 24-file project allowlist; no runtime configuration or service was started.

Rollback after stable SSH returns: `ssh cat@100.94.108.3 'test ! -e /home/cat/carstream-20261117T052346Z.disabled && mv /home/cat/carstream-20261117T052346Z /home/cat/carstream-20261117T052346Z.disabled'`. This non-destructive rename has not been executed. Keep this append-only log as the verification record; no application source changed in this task.

## 2026-11-17 - Task: Complete source synchronization over the phone hotspot

### What was done

- Confirmed that switching the Mac to a phone hotspot restored Tailscale to `Running`, with a local address and the board online. The same control-server IPv4 address that previously timed out returned HTTP 200 over the hotspot; IPv6 also returned HTTP 200. This points to the original network path, not a necessary client reinstall; the router versus upstream cause remains unconfirmed.
- Successfully uploaded the 24-file project allowlist to `/home/cat/carstream-20261117T060914Z`, preserving older incomplete directories and excluding secrets and virtual environments.

### Testing

- PASS: board Tailscale ping through DERP(hkg), 683 ms, and authenticated SSH identity `cat` on `lubancat`.
- PASS: upload script exited 0, transferring 24 files / 370165 bytes. A separate checksum-based `rsync -rcn --itemize-changes` comparison exited 0 with no differences for the allowlisted files at upload time.
- PASS: 5 configuration tests on board Python 3.10.12; 11 local configuration/signaling tests; Ruff and JavaScript syntax checks.
- EXPECTED BLOCKER: board `python3 -B -m carstream --check` reports missing GStreamer GI. Apt simulation proposes only three new packages (`python3-gst-1.0`, `gir1.2-gst-plugins-bad-1.0`, `gstreamer1.0-nice`), with no upgrades or removals. Installation and startup are the next stage, not part of this synchronization success.

### Notes

- Board `/home/cat/carstream-20261117T060914Z/`: complete, checksum-verified source upload of the existing 24 allowlisted project files. No application source changed locally.
- `progress.md`: appends successful synchronization and hotspot comparison evidence. This appended entry postdates the first upload and is synchronized with subsequent deployment records.

Rollback: before running a service from this path, `ssh cat@100.94.108.3 'test ! -e /home/cat/carstream-20261117T060914Z.disabled && mv /home/cat/carstream-20261117T060914Z /home/cat/carstream-20261117T060914Z.disabled'` preserves the uploaded files but disables their original path. No network settings were changed.

## 2026-11-17 - Task: Install prerequisites and start the board test-pattern trial

### What was done

- Installed exactly three missing Ubuntu packages after a no-upgrades/no-removals simulation: `gstreamer1.0-nice` 0.1.18-2, `python3-gst-1.0` 1.20.1-1, and `gir1.2-gst-plugins-bad-1.0` 1.20.3-0ubuntu1.1. Apt reported 0 upgrades, 3 new packages and 0 removals; existing Rockchip MPP packages were retained.
- Created the release's `.venv` using board Python 3.10.12 with system site packages, and installed the pinned runtime requirements into that environment without replacing distribution packages.
- Fixed the native test-source failure locally before uploading the correction: explicitly select MPP Baseline profile and put its caps filter after `h264parse` to normalize the vendor's capitalized profile caps. The H.264 passthrough branch remains unchanged. No new wire/configuration contract or architecture choice was introduced; the existing architecture note was updated in place.
- Started the test-pattern service as a detached `cat` process, PID 116564 at startup, from `/home/cat/carstream-20261117T060914Z`, listening only on board `127.0.0.1:8080`. Created `.env`, `server.pid` and `server.log` with private mode 0600. No camera credentials were configured; the access token is absent from project source and notes.
- Established an SSH forward on Mac `127.0.0.1:18080` to board `127.0.0.1:8080`; its listener PID was 52195. No public HTTP port, boot service or network configuration was added.

### Testing

- PASS: board `.venv/bin/python -B -m carstream --check` now finds all shared WebRTC, RTSP and MPP elements. Optional `x264enc` remains absent; the hardware encoder is used.
- PASS: all 11 configuration and signaling unit tests on the board after installation and after the media correction. The same 11 tests, Ruff, JavaScript syntax and shell syntax checks also pass locally.
- REPRODUCED/FIXED: the first native smoke test timed out waiting for video. Inspection showed the MPP encoder's default High profile and capitalized vendor caps blocked the pre-parser Baseline filter. A finite `mpph264enc profile=baseline ! h264parse ! video/x-h264,profile=baseline` hardware check exited 0. After the local correction was uploaded, `timeout 50 .venv/bin/python -B -u -m tests.smoke_media` passed with at least ten decoded test-pattern frames.
- PASS: HTTP startup returned `{'status': 'alive'}` with PID 116564. A native client then used the actual running service's private access token, `/ws` authentication, SDP offer/answer and ICE signaling and received at least ten MPP-decoded frames (`LIVE_HTTP_WEBSOCKET_DECODED_VIDEO_PASS`, exit 0). This is a native receiver test, not a browser test.
- PASS at initial tunnel verification: `curl http://127.0.0.1:18080/healthz` returned HTTP 200 and `{"status": "alive"}`. The local tunnel listener was confirmed separately.
- WARNING: the system-site-packages virtualenv's `pip check` exits 1 because `pynacl 1.5.0 requires cffi, which is not installed`. PyNaCl is not a CarStream dependency. This separate inconsistency was not repaired; system-Python comparison could not be reconfirmed after the link interruption.
- PASS: updated decision-note tree, format and archive checks. This workspace is not a Git repository, so Git append-only archive checking is inapplicable. IDE diagnostics for the media correction returned no diagnostics earlier; the final tool catalog no longer exposed ReadLints, and final CLI Ruff passed.
- FINAL ACCESS BLOCKER: a later Mac tunnel health request timed out. Read-only checks show the default gateway changed from hotspot `172.20.10.1` back to original-network `192.168.50.1`; Tailscale still reports `Running`, illustrating that cached/connected status alone is insufficient. Fresh SSH for runtime inspection timed out as well. Service startup and decoded-frame test results remain valid historical evidence, but current remote service availability cannot be reconfirmed.
- NOT VERIFIED: browser playback from the Mac, real-camera RTSP media, actual H.265 camera behavior, public HTTPS/TURN playback or sustained load. The SSH forward carries signaling, not the WebRTC media path. Camera credentials and a verified RTSP URL remain needed.

### Notes

Changed files and runtime artifacts:

- `carstream/media.py`: explicitly configures MPP Baseline and normalizes encoded caps before applying the profile constraint; synchronized to the board before the passing native/live tests.
- `README.md`: updates verified trial status while preserving browser/camera/public acceptance gaps.
- `docs/deployment.md`: records the tested deployment path, private access and stop instructions, the caps compatibility fix, the pip warning and latest connectivity limitation.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: updates the existing rationale with the vendor compatibility constraint and actual native validation evidence.
- `progress.md`: appends package, runtime, verification and rollback evidence.
- Board `/home/cat/carstream-20261117T060914Z/.venv/`: contains the isolated pinned Python runtime.
- Board `/home/cat/carstream-20261117T060914Z/.env`: private test-source configuration and random access token, never uploaded back into this project.
- Board `/home/cat/carstream-20261117T060914Z/server.pid` and `server.log`: private trial process record and output.
- Mac local SSH forward `127.0.0.1:18080`: created for this trial; last listener PID 52195, but latest end-to-end request failed after the network change.

The corrected application source is on the board. The final README, deployment note, architecture-note and this log updates are currently local only because SSH is unavailable; synchronize these documentation files after the working network is restored. No application changes remain waiting to be deployed.

Rollback: after restoring SSH, inspect `ps -p 116564 -o pid,args` and `/proc/116564/cwd`; only if both identify this release's CarStream process, send `kill -TERM 116564`. Inspect `lsof -nP -iTCP:18080 -sTCP:LISTEN` locally and stop only the SSH process for this trial (last observed PID 52195). Then rename the release to `/home/cat/carstream-20261117T060914Z.disabled`, checking the destination does not exist. Keep runtime configuration private. The three newly installed system packages may be removed only after reviewing `sudo apt-get -s --no-auto-remove remove python3-gst-1.0 gir1.2-gst-plugins-bad-1.0 gstreamer1.0-nice`; do not remove other vendor components or use autoremove. No rollback action was executed.

## 2026-11-17 - Task: Set the user's requested private debugging access token

### What was done

- Added explicit `CARSTREAM_ALLOW_WEAK_TOKEN` configuration, defaulting to false. Short tokens require this opt-in, a literal loopback bind address, and no public origin. Blank tokens remain invalid; the normal 24-character minimum is unchanged.
- Updated the source locally first, then synchronized the configuration implementation and focused tests to the existing board release. Kept the requested token only in the board's private runtime configuration, not project examples, tests or documentation.
- Confirmed PID 116564 belonged to this release before stopping it. Backed up the previous runtime configuration, changed the access token as requested, enabled the private-debugging opt-in, and restarted only this CarStream process. Updated `server.pid`; do not reuse the historical PID above for future stop commands.
- Preserved the test-pattern source and board `127.0.0.1:8080` binding. No network settings, public ports, packages, camera credentials or media behavior were changed.

### Testing

- PASS: all 15 configuration/signaling tests locally and on board Python 3.10, including short-token opt-in, blank-token rejection and loopback/public-origin restrictions. Local Ruff passed.
- PASS: board restart health check and real WebSocket authentication; the previous token was rejected and the replacement was accepted.
- PASS: a separate Mac check through `http://127.0.0.1:18080` returned healthy status, rejected an invalid token and accepted the requested replacement token.
- NOT FIXED: the user-reported browser video stall at `WebRTC: connecting`. Token authentication success is not browser playback acceptance; this request did not authorize browser automation.

### Notes

- `carstream/config.py`, `tests/test_config.py`, `.env.example`, `README.md` and `docs/deployment.md`: document and constrain the explicit private-debugging exception without changing secure defaults.
- Board `/home/cat/carstream-20261117T060914Z/.env`: updated privately with mode 0600; `server.pid` records the replacement service PID.
- Board `.token-change-backup-20261117/` within the release: preserves the original uploaded files and previous `.env`. The backup directory is mode 0700 and its `.env` is mode 0600.

Rollback: verify the current PID from `server.pid` and its command/working directory before stopping it. Restore the private `.env` from `.token-change-backup-20261117/.env`, retain mode 0600, reload that environment and restart the same release. The new validation code still accepts the original strong token with its default opt-in disabled. Never copy private configuration into project documentation or print it during rollback. No rollback was needed.

## 2026-11-17 - Task: Fix browser black screen caused by oversized RTP packets

### What was done

- Used the explicitly authorized Cursor browser to reproduce the black screen. ICE and DTLS connected, but the browser decoded zero frames despite receiving some RTP packets. A sample showed 1829 packets received and 12393 lost, with repeated keyframe requests.
- Inspected actual packet sizes, including GStreamer buffer lists: the default payloader MTU was 1400 bytes, and 163 of 190 sample packets exceeded 1200 bytes. The board's Tailscale interface MTU is 1280; the selected browser media path was direct IPv6, not the SSH forward. The exact network hop dropping large packets was not traced.
- Obtained a separate user confirmation for the packet-handling change and service restart. Limited application RTP packets to 1200 bytes to reserve room for SRTP/UDP/IPv6, without modifying host MTUs, routes, firewall rules, ports, codec, bitrate or ICE policy.
- Wrote the change locally first, backed up and synchronized the two changed Python files, then restarted only the identity-verified trial service. Replacement PID is 119205 at restart; `server.pid` is authoritative. The access token and loopback HTTP binding are unchanged.
- Verified browser playback and a fresh-page reconnect, then disconnected the test viewer and unlocked the browser so the single-viewer slot is available to the user.

### Testing

- REPRODUCED: the original implementation failed the new native packet-size regression with `RTP packets must stay within the 1200-byte path budget`, even though its local native receiver could decode frames.
- PASS: after the fix, board native WebRTC loopback decoded at least ten frames and measured a largest outgoing RTP packet of exactly 1200 bytes.
- PASS: all 15 configuration/signaling tests locally and on the board; local Ruff and IDE ReadLints returned no diagnostics for the edited Python files.
- PASS: restarted service health check. The browser selected the same direct IPv6 address pair before and after the fix, but now showed visible 640x360 color bars. Browser decoded-frame samples grew from 110 to 308, with playback time growing from 11.030 to 28.181 seconds.
- PASS: a clean page reload removed all temporary diagnostic wrappers; reconnect then decoded 203 frames over 20.315 seconds, with 3163 packets received and 27 lost in that sample. The user also supplied a screenshot showing the color bars and `WebRTC: connected`.
- NOT VERIFIED: true camera video, original-Wi-Fi stability, other browser engines, public HTTPS/TURN and long-duration operation. The change fixes this reproduced hotspot browser black screen, not every possible network problem.

### Notes

- `carstream/media.py`: sets the H.264 payloader RTP MTU to 1200 bytes with a transport-header budget comment.
- `tests/smoke_media.py`: inspects actual outgoing buffers and buffer lists and rejects packets larger than 1200 bytes in the existing decoded-frame smoke test.
- `README.md`: updates browser verification status and the native smoke-test packet-size contract.
- `docs/deployment.md`: records the failed/successful browser evidence, packet-size fix and unchanged network boundaries.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: updates the existing media-boundary decision with the packet budget, default-size trade-off and actual browser acceptance limits.
- `progress.md`: appends reproduction, explicit approval, repair, validation and rollback evidence.
- Board `.rtp-mtu-backup-20261117/` within `/home/cat/carstream-20261117T060914Z`: preserves the original `carstream/media.py` and `tests/smoke_media.py`. Runtime `server.pid` and append-only `server.log` reflect the controlled restart; `.env` is unchanged.

Rollback point: `/home/cat/carstream-20261117T060914Z/.rtp-mtu-backup-20261117/`. After checking the PID from `server.pid` with `ps` and verifying its `/proc/<PID>/cwd`, stop only that CarStream process and wait until port 8080 is released. From the release directory run `cp .rtp-mtu-backup-20261117/carstream/media.py carstream/media.py` and `cp .rtp-mtu-backup-20261117/tests/smoke_media.py tests/smoke_media.py`, then `set -a; . ./.env; set +a; .venv/bin/python -B -m carstream` to restart in the foreground with the unchanged private configuration. This intentionally restores the old packet-size behavior and may reproduce the black screen. No rollback was executed.

## 2026-11-17 - Task: Remove stale browser minimum length blocking the configured short token

### What was done

- Corrected the overlooked HTML `minlength="24"` constraint that prevented the user's short token from being submitted. The password input remains required; token strength and authentication stay enforced by the existing server settings and comparison.
- Added a focused regression against the served HTML, uploaded the static page and test with backups, and verified the running service serves the corrected form without a restart. Runtime token, network and media configuration are unchanged.
- The previous authentication/video checks did not cover the user's native browser length-validation path. This task closes that verification gap rather than treating the user's screenshot as an incorrect token.

### Testing

- REPRODUCED: the new served-form regression failed on the original HTML because `minlength="24"` was still present, matching the user's browser screenshot.
- PASS: all 16 configuration/signaling tests locally and on the board after the correction. Ruff and IDE ReadLints reported no new diagnostics.
- PASS: after reloading the deployed page and entering the seven-character token through the browser typing tool, the input has no minimum-length attribute, the form reports valid and the validation message is empty.
- PASS: clicking Connect authenticated and decoded/rendered 269 frames at 640x360 over 23.38 seconds in the sampled browser session. Disconnected afterward and unlocked the browser to release the single-viewer slot.

### Notes

- `carstream/static/index.html`: removes only the obsolete hard-coded minimum token length while preserving required password entry.
- `tests/test_server.py`: verifies that the served password input remains required and does not override server token-length policy.
- `README.md`: updates the verified unit-test count to 16.
- `docs/deployment.md`: documents server-owned token policy and the need to refresh existing pages after the static update.
- `progress.md`: appends the missed frontend constraint, regression and browser verification evidence.
- Board `.token-form-backup-20261117/` within `/home/cat/carstream-20261117T060914Z`: preserves the original HTML and test before deployment.

Rollback: from the board release directory run `cp .token-form-backup-20261117/carstream/static/index.html carstream/static/index.html` and `cp .token-form-backup-20261117/tests/test_server.py tests/test_server.py`, then reload the browser. No service restart is needed for these static/test files. Restoring the old HTML deliberately restores the short-token submission problem. No rollback was needed.

## 2026-11-17 - Task: Remove fixed viewer limits and verify simultaneous browser playback

### What was done

- Implemented the user's explicit request not to impose a viewer count: removed the single-viewer occupancy gate and eight-WebSocket cap. Retained token authentication, Origin checks, authentication timeout, message validation and independent media cleanup.
- Kept the existing per-viewer media pipeline rather than introducing a shared-source redesign. Updated the page and deployment guidance to distinguish no fixed application cap from finite hardware, camera and bandwidth capacity.
- Synchronized the locally tested server, page and tests into the existing board release with original-file backups. Restarted only the identity-verified CarStream process, retaining its private token, test source, 1200-byte RTP budget and loopback binding. No packages or network settings changed.
- Verified two actual browser viewers at the same time, then disconnected both test sessions and unlocked both tabs. Documented that the displayed color bars are the intentional synthetic source, not damaged camera video.

### Testing

- REPRODUCED: the new concurrent-lifecycle test failed on the original server when the second authenticated viewer received an error instead of ready.
- PASS: all 16 tests locally and on board Python 3.10. The changed test admits nine fake media sessions, verifies independent candidate delivery and failure cleanup, and confirms that disconnecting one viewer leaves others alive. Service shutdown closes multiple sessions.
- PASS: local Ruff and IDE ReadLints for the edited server, page and test. Decision-note tree, format and archive validation passed for two notes; Git append-only checking is inapplicable in this non-Git workspace.
- PASS: board restart and HTTP liveness. Two Cursor Chromium pages simultaneously connected and decoded 640x360 test frames: 790 and 214 in the paired samples. After disconnecting the first page, the second remained connected and grew by 462 frames to 676.
- NOT VERIFIED: higher real-video viewer counts, sustained capacity, camera RTSP or public HTTPS/TURN. Nine fake sessions are not a nine-video capacity claim. No camera login or source switch was performed as part of removing the viewer restriction.

### Notes

- `carstream/server.py`: removes the global viewer slot and connection-count rejection while preserving per-session authentication and cleanup.
- `carstream/static/index.html`: replaces the single-viewer notice with an explicit resource/bandwidth capacity statement.
- `tests/test_server.py`: replaces single-viewer rejection coverage with multi-viewer lifecycle isolation and multi-session shutdown checks.
- `README.md`: records multiple viewers, separate pipelines and the verified two-browser scope.
- `docs/deployment.md`: records actual simultaneous decoding, resource boundaries and the meaning of the synthetic color bars.
- `docs/decisions/implemented/feature/2026-11-17-multiple-viewers.md`: records the changed admission decision, alternatives, actual verification and capacity costs.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: preserves the original single-viewer rationale with an explicit partial-supersession link rather than silently reversing it.
- `progress.md`: appends this task's implementation, verification and rollback evidence.
- Board `.multi-viewer-backup-20261117/` within `/home/cat/carstream-20261117T060914Z`: preserves original `carstream/server.py`, `carstream/static/index.html` and `tests/test_server.py`; runtime `server.pid` and append-only `server.log` reflect the controlled restart.

Rollback point: `/home/cat/carstream-20261117T060914Z/.multi-viewer-backup-20261117/`. Verify the current PID from `server.pid`, its command and `/proc/<PID>/cwd`, then stop only that CarStream service and wait for port 8080 to be released. From the release directory restore with `cp .multi-viewer-backup-20261117/carstream/server.py carstream/server.py`, `cp .multi-viewer-backup-20261117/carstream/static/index.html carstream/static/index.html` and `cp .multi-viewer-backup-20261117/tests/test_server.py tests/test_server.py`. Restart in the foreground with `set -a; . ./.env; set +a; .venv/bin/python -B -m carstream`. This restores the old single-viewer policy; no runtime secrets or network rollback is needed. No rollback was executed.

## 2026-11-17 - Task: Persist the approved camera Ethernet configuration

### What was done

- Executed the user's explicit approval to configure the camera-side network permanently. Confirmed the existing NetworkManager profile was bound to eth0 and still had its inspected DHCP settings before modifying it.
- Saved `192.168.11.82/24` in `Wired connection 1`, UUID `eeb55747-033d-3ed0-87b3-d5641bc753a7`, with automatic connection, no IPv4 gateway or DNS, and `ipv4.never-default=yes`. Enabled NetworkManager's native duplicate-address detection with `ipv4.dad-timeout=3000` milliseconds; activation succeeded. The operation included restoration of the original settings if activation or the default-route check failed; no rollback was required.
- Preserved eth1, the default uplink gateway, Tailscale, the running CarStream service, private `.env` and test-pattern source. Did not install packages, reboot the board, restart the network service, log into the camera or change the video source.
- Updated local deployment instructions and decision records with persistence evidence, acceptance boundaries and exact reversal commands.

### Testing

- PASS: pre-change eth0 had no IPv4 address, and the inspected profile used DHCP with blank IPv4 address/gateway/DNS, `ipv4.never-default=no`, `ipv4.dad-timeout=-1` and automatic connection enabled.
- PASS: after activation, eth0 reports `192.168.11.82/24`; `ip -4 route get 192.168.11.83` selects `dev eth0 src 192.168.11.82`.
- PASS: camera TCP 554 and TCP 80 both connect from `192.168.11.82`, replacing the previously reproduced timeouts. This is port reachability, not RTSP authentication or decoded-video acceptance.
- PASS: NetworkManager reports `Unsaved=false` on `/org/freedesktop/NetworkManager/Settings/1`, and the profile filename is `/etc/NetworkManager/system-connections/Wired connection 1.nmconnection`. Saved automatic connection is enabled; this is persistent configuration rather than a temporary `ip addr` change.
- PASS: the default route is byte-for-byte unchanged by the operation: `default via 192.168.0.1 dev eth1 proto dhcp metric 100`. eth1 remains `192.168.0.100/24`; Tailscale remains `100.94.108.3/32`. A fresh SSH login succeeds after activation.
- PASS: board `http://127.0.0.1:8080/healthz` and Mac SSH-forwarded `http://127.0.0.1:18080/healthz` both return HTTP 200; the latter returns `{"status": "alive"}`.
- PASS: decision-note tree/link and format checks validate all three notes; archive verification passes. Git append-only checking is skipped because the workspace is not a Git repository.
- NOT VERIFIED: actual reboot recovery, camera credentials, video codec or real-camera playback. No application source or test changed, so application unit tests were not rerun for this host-network-only task.

### Notes

Changed files and runtime configuration:

- Board `/etc/NetworkManager/system-connections/Wired connection 1.nmconnection`: saves the approved static camera-network address, automatic connection, no default IPv4 route and native address-conflict detection.
- `docs/deployment.md`: records the permanent profile, observed port/management checks and exact rollback commands.
- `docs/decisions/implemented/architecture/2026-11-17-camera-network.md`: records the network choice, temporary/DHCP alternatives, acceptance evidence and separation from application behavior.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: links the separately approved deployment configuration without changing the application's passive network boundary.
- `progress.md`: appends this task's approval, completed work, actual verification and reversal instructions.

Rollback: run the following on the board. This restores the inspected saved DHCP profile and leaves eth0 disconnected, matching the pre-change state; do not modify eth1 or restart NetworkManager.

```bash
sudo nmcli connection down uuid eeb55747-033d-3ed0-87b3-d5641bc753a7
sudo nmcli connection modify uuid eeb55747-033d-3ed0-87b3-d5641bc753a7 \
  ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns "" \
  ipv4.never-default no ipv4.dad-timeout -1 connection.autoconnect yes
```

No rollback was executed. Documentation changes are local; the board network profile is already applied and saved.

## 2026-11-17 - Task: Initialize the local Git repository

### What was done

- Initialized Git in the existing project directory at the user's request, without staging files, creating a commit, changing Git configuration or adding a remote.
- Preserved all project files and the existing ignore rules for private environment files and generated runtime artifacts.

### Testing

- PASS: `/usr/bin/git rev-parse --show-toplevel` returns `/Users/jiangdk/code/company/CarStream`.
- PASS: `/usr/bin/git --no-pager status --short --branch --untracked-files=all` reports `No commits yet on main` and only the expected project files as untracked; no staged files.

### Notes

- `.git/`: stores the newly initialized local repository metadata, with no commits or remote.
- `progress.md`: appends initialization scope and verification before beginning the separately requested video-source task.

Rollback: to disable this new repository without deleting any source, first confirm `.git.disabled-20261117` does not exist, then from the project directory run `mv .git .git.disabled-20261117`. No rollback was executed; no source-file restoration is required.

## 2026-11-17 - Task: Restore watching automatically after player interruptions

### What was done

- Implemented the user's requested once-per-viewing Connect behavior locally. Separated the user's intent to keep watching from an individual WebSocket/WebRTC attempt, releasing failed sessions before reconnecting with delays of 1, 2, 4, 8, 16 and then at most 30 seconds.
- Added a two-second video-progress check. A connected session with approximately 15 seconds of no new video frames is rebuilt; playback time is the fallback if frame-quality statistics are unavailable. At least ten seconds of advancing playback resets the failure backoff, rather than simply resetting when ICE connects.
- Made Disconnect and page exit cancel active sessions and pending retries. Invalid access tokens stop retrying until the user corrects the input and starts again. User pause and blocked autoplay do not cause recovery loops.
- Fixed the reproduced obsolete video-play callback that changed the status back to connected after the session had already been stopped. Kept token storage/transport, server authentication, Origin checks, signaling messages, native media handling and host networking unchanged.
- Added focused JavaScript regression tests without installing npm dependencies, and documented behavior, acceptance limits and local rollback. Preserved the pre-existing README line split rather than cleaning it up. No Git commit or push was created.

### Testing

- REPRODUCED: against the original player, five of the initial seven JavaScript tests failed: signaling retry, media-error retry, frozen-picture recovery, stale play-status overwrite and initial-timeout recovery.
- PASS: `node --test --test-reporter=tap tests/player.test.cjs`, eight tests after the correction. Coverage includes capped retry/backoff reset, duplicate callback suppression, invalid-token stop, active/pending Disconnect, frame-counter freezes despite advancing playback time, pause/autoplay handling, obsolete play rejection, initial timeout and page-exit cancellation.
- PASS: the continuous-playback regression advances a fake clock and frame counter through five minutes without reconnecting, then freezes frames and observes recovery. This is a deterministic logic test, not five minutes of camera or browser acceptance.
- PASS: `.venv/bin/python -B -m unittest discover -s tests -v`, all 16 existing Python tests; `.venv/bin/ruff check carstream tests`; `node --check carstream/static/player.js`. IDE ReadLints returned no diagnostics for the edited player, tests and documentation.
- PASS: decision-note tree/link and format validators check four notes; archive validation passes with no archived notes.
- BLOCKED: the task's fresh SSH attempt to `100.94.108.3:22` timed out, so no upload or live-board repair was attempted. No runtime service, camera source, private environment or network configuration was changed in this task.
- NOT VERIFIED: actual browser auto-recovery, sustained real-camera playback and the underlying camera/media-pipeline failure. The earlier real-camera session decoded 13 frames before stalling; this change provides recovery, not evidence that the root cause is repaired.

### Notes

Changed files and rollback artifacts:

- `carstream/static/player.js`: retains watching intent, retries failed sessions with capped backoff, detects stalled video, honors explicit stop and guards obsolete playback callbacks.
- `tests/player.test.cjs`: exercises the actual player script with fake DOM, sockets, peers and timers using Node's built-in test runner.
- `README.md`: describes local recovery support and the new verification command while explicitly stating that the board update is pending; preserves the existing unrelated text edit.
- `docs/deployment.md`: distinguishes deployed/manual behavior from the local repair and records recovery timing, testing boundaries and static-file deployment/rollback steps.
- `docs/decisions/implemented/feature/2026-11-17-player-recovery.md`: records the recovery choice, alternatives, native-media boundary, tests and deployment gap.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: links browser recovery without changing backend media lifetime rules.
- `progress.md`: appends completed local work, exact verification and the SSH blocker.
- `.tmp/player-before-reconnect.js`: ignored, local copy of the original player for reversing this task's behavior; contains no runtime credentials.

Rollback: from the local project root run `cp .tmp/player-before-reconnect.js carstream/static/player.js` to restore the pre-task behavior. No board rollback is needed because the repair has not been deployed. When board access returns, back up its current `carstream/static/player.js` before uploading the corrected static file; refresh the browser afterward, without restarting the service or changing `.env`. Restore that board backup if the later live verification fails. No rollback was executed.

## 2026-11-17 - Task: Prepare the requested GitHub remote and Chinese README

### What was done

- Renamed the unborn local branch from `main` to `master` and added `origin` as `git@github.com:jiangdengke/CarStream.git`, as requested. GitHub CLI confirms the destination is a public repository with no default branch yet.
- Rewrote README in Chinese, including prerequisites, private configuration, startup, viewing, camera setup, recovery behavior, tests, synchronization and public-access boundaries. Kept the distinction between local recovery implementation, pending board deployment and unresolved real-camera stability.
- The user explicitly confirmed creating and pushing the first commit with the current source, tests and documentation, including historical operational addresses and paths. Staged the 28 allowlisted project files, excluding private environments, generated artifacts and local backups; publication follows this preparation record.

### Testing

- PASS: Git reports branch `master` and the exact requested `origin` URL.
- PASS: all 16 Python tests and all eight JavaScript player tests pass locally.
- PASS: staged whitespace validation, Ruff, JavaScript syntax and shell syntax checks; SSH access to the empty origin repository succeeds.
- CHECKED: searched project source and documentation for the known runtime passwords, requested access token and common private-key/GitHub-token markers; no credential values were found. Existing ignore rules exclude `.env`, `.venv/` and `.tmp/`. The public project documentation still includes historical operational addresses and local paths.
- IDE ReadLints is unavailable in the current tool catalog; no application code changed in this documentation task.

### Notes

- `README.md`: complete Chinese usage and status guide.
- `.git/HEAD` and repository remote metadata: requested `master` branch and GitHub SSH origin.
- `progress.md`: records completed preparation, explicit publication approval and checks before the initial commit.

No board deployment, credentials, camera settings or network settings changed. To reverse only the new Git metadata setup before publication, remove the added origin with `git remote remove origin` and rename the branch with `git branch -m main`; these commands were not executed. The Chinese README can be edited independently without changing application behavior.

## 2026-11-17 - Task: Deploy the player recovery repair to the running board

### What was done

- Reached the authorized board by password-authenticated SSH and verified hostname, service command, PID and release directory before changing its static player. Saved the original script in a private timestamped backup, uploaded the already-tested local repair, verified its checksum and atomically replaced only the running release's `carstream/static/player.js`.
- Kept service PID 122431 running without restart. Did not change private `.env`, camera configuration, Python/GStreamer code, encoding, authentication, routing, interfaces or firewall settings. Recreated the absent Mac loopback-only SSH forward at `127.0.0.1:18080`.
- Refreshed Chromium, clicked Connect once and received the actual 2304x1296 camera stream. Closed only that diagnostic browser session's WebSocket and verified that it automatically created a fresh session and resumed decoded video without another Connect.
- Continued the same acceptance check and reproduced a later video stall. Verified that real stalled video triggers automatic retries, but those retries did not restore sustained playback. Explicitly disconnected the diagnostic viewer, confirmed its active session and retry timer were cleared, and unlocked the browser. The deployment remains installed; camera/media stability is not declared fixed.
- Updated the current deployment status, live evidence and rollback instructions in the existing documentation and decisions. No Git commit or push was requested or performed in this task.

### Testing

- PASS: `node --check carstream/static/player.js` and `node --test --test-reporter=tap tests/player.test.cjs`, all eight recovery regression tests immediately before upload. Application code was not changed locally in this task; Python tests were not rerun.
- PASS: board file, board HTTP `/player.js` and Mac-forwarded HTTP `/player.js` match local SHA-256 `a529f7cc30083246aea911d6294f8f7ca42401e020c1703a5f30db9eff14a567`. The preserved original matches SHA-256 `008dbd3f4c8e8707d38703fd53e37a1bf7e048b130b59b53b707dccf7cf35d45`.
- PASS: board `/healthz` and the Mac-forwarded endpoint returned HTTP 200; recorded PID 122431 and `/proc/122431/cwd` still identify `/home/cat/carstream-20261117T060914Z`. After browser cleanup the forwarded health endpoint still returned `{"status": "alive"}`, and SSH PID 95546 listened only at Mac `127.0.0.1:18080`.
- PASS: Chromium loaded `checkVideoProgress`. Relative to the observation start, the forced signaling closure at second 23 displayed a one-second retry, and the replacement WebRTC session connected at second 25. Its decoded frames advanced from 193 to 446 across later samples; camera dimensions were 2304x1296. The user-supplied screenshot shows the real camera scene.
- PASS: natural stall detection fired at observation second 124, followed by automatic backoffs of 1, 2, 4, 8 and 16 seconds during repeated failed-to-sustain-video attempts. This proves retry triggering, not successful camera recovery. Explicit Disconnect at second 256 left `watchingRequested=false`, no active session, no retry timer and Connect enabled when rechecked afterward.
- FAIL, separate acceptance boundary: continuous camera playback still stalls. At second 96 the browser had decoded 446 frames and reported 11532 received packets and 267 lost packets. At second 234 it was waiting to retry with no active inbound video. No transport-loss location or camera/encoder failure cause was established, and no speculative media/network fix was applied.
- PASS: decision-note tree/link and format checks validate four notes; archive verification validates zero archived notes. `git diff --check` passes for the updated deployment documentation.

### Notes

Changed files and runtime artifacts:

- Board `/home/cat/carstream-20261117T060914Z/carstream/static/player.js`: deployed the existing local recovery implementation with checksum verification and atomic replacement.
- Board `/home/cat/carstream-20261117T060914Z/.player-recovery-backup-20261117T085316Z/player.js`: preserved the original player inside a mode-0700 directory; the uploaded staging file was consumed by the atomic replacement.
- `README.md`: marks the repair deployed and distinguishes successful signaling recovery from still-failing continuous camera playback.
- `docs/deployment.md`: records hashes, unchanged service identity, restored forwarding, browser evidence, reproduced stalls and exact static-file rollback commands.
- `docs/decisions/implemented/feature/2026-11-17-player-recovery.md`: updates deployment and live recovery/stall evidence without changing the recovery decision.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: replaces the outdated not-yet-deployed statement while preserving native-media boundaries.
- `progress.md`: appends this deployment, verification evidence, remaining failure and rollback point without changing earlier history.

Board rollback, if requested: run `cd /home/cat/carstream-20261117T060914Z && cp -p .player-recovery-backup-20261117T085316Z/player.js carstream/static/.player-rollback.js && mv carstream/static/.player-rollback.js carstream/static/player.js`, then refresh the browser. No service restart or environment restoration is required. Local documentation has rollback point commit `8faed70`; preserve the append-only progress history. To remove only the recreated tunnel, first recheck `lsof -nP -iTCP:18080 -sTCP:LISTEN` and verify the SSH forwarding command before stopping its PID; do not rely on the historical PID above. No rollback was executed.

## 2026-11-17 - Task: Document starting and stopping the deployed service in README

### What was done

- Added a dedicated Chinese startup, shutdown and restart section for the existing board release, including SSH login, the release directory and reuse of its private environment and virtualenv.
- Distinguished foreground debugging from nohup background operation, with configuration loading, private PID/log creation, port checks, health checks and log inspection.
- Required checking both the recorded process command and working directory before sending SIGTERM. Explained the effects on all viewers, restart order, the difference between Disconnect and service shutdown, and stopping a foreground SSH forward. Clarified that CarStream has no configured systemd unit or boot autostart.
- Preserved the pre-existing local deployment-documentation changes. Did not execute service lifecycle commands, synchronize files to the board, alter application behavior or create a Git commit.

### Testing

- PASS: `bash -n` parsed the newly documented shell snippets without executing them, including environment loading, nohup redirections, PID capture, process inspection and SIGTERM syntax.
- PASS: compared the documented entry point and graceful shutdown usage with `carstream/__main__.py`, the server shutdown hook and the existing deployment instructions.
- PASS: `git diff --check`; IDE ReadLints returned no diagnostics for README.
- NOT RUN: a live start/stop/restart cycle. This is a documentation-only request, so the running board service and viewers were left untouched. No application tests were rerun because no application code changed.

### Notes

- `README.md`: adds actionable board startup, status, stop and restart instructions, with process-identity checks and forwarding/lifecycle boundaries.
- `progress.md`: appends the documentation scope, verification limits and rollback without rewriting history.

Rollback only this README addition from the project root with `python3 -c 'from pathlib import Path; path = Path("README.md"); content = path.read_text(); start = content.index("## 启动、停止与重启\n"); end = content.index("## 配置项\n", start); path.write_text(content[:start] + content[end:])'`. Keep this append-only progress record and all earlier deployment edits. No rollback was executed; there is no board runtime change to reverse.

## 2026-11-17 - Task: Add separate service start and stop shell scripts

### What was done

- Added executable Ubuntu/Linux scripts that find their release directory without relying on the caller's working directory. Start loads the private environment, validates configuration, refuses occupied ports, detaches the service and reports success only after its PID owns the configured listening socket.
- Kept the existing PID and command convention. Repeated start recognizes the current release instead of overwriting its PID; both scripts refuse invalid or unrelated live PIDs. Stop verifies the command and working directory, uses SIGTERM, waits for exit and never escalates to SIGKILL. Stop does not need a valid `.env`.
- Serialized lifecycle operations with a release-local file lock that the service does not inherit. Kept PID/log permissions at 0600 and excluded PID, log and lock files from Git. Added focused tests of real subprocess handling using temporary releases and a standard-library HTTP fixture, without GStreamer or camera access.
- Replaced the manual background start/stop README steps with the two script commands, documented restart and failure behavior, and recorded the lifecycle decision and deployment boundary. Did not install systemd units, add boot autostart, change application/media/network behavior or commit/push changes.
- Used an isolated board temporary directory solely for Linux checks because the Mac lacks Linux `/proc`/`ss` and its Docker daemon is not running. Removed the copied test directory afterward. The scripts have not been installed in the current running release, and its service was not restarted.

### Testing

- PASS: `bash -n scripts/start.sh scripts/stop.sh`; `.venv/bin/ruff check carstream tests`; IDE ReadLints returned no diagnostics for the new scripts, test and updated documentation. ShellCheck is not installed and was not run.
- PASS: local Python discovery ran 23 checks: all 16 existing configuration/signaling tests passed, and the seven Linux-specific lifecycle tests were explicitly skipped on macOS, not counted as passed there.
- PASS: final Linux run of `python3 -B -m unittest discover -s /tmp/carstream-script-check-20261117T094722Z/tests -p test_scripts.py -v`, all seven lifecycle tests. Coverage includes background survival, repeated start/stop, a release path containing spaces, custom port use, private file permissions, stop without `.env`, invalid/stale PIDs, refusal to signal an unrelated process in the same directory, occupied ports, startup failure and a held lifecycle lock.
- OBSERVED AND ADDRESSED IN TEST SETUP: the initial Linux run passed six checks but the startup-exit fixture encountered an already-listening temporary port instead of its expected exit path. An unchanged rerun passed all seven. Tightened the fixture's port reservation so it remains held until launching the start script; the final updated test run passed all seven without relaxing the production port guard.
- PASS: after the isolated tests, the live service still had PID 122431 and release cwd `/home/cat/carstream-20261117T060914Z`, and `/healthz` returned HTTP 200. Verified the running release contains neither new script, then removed only `/tmp/carstream-script-check-20261117T094722Z` created by this task.
- PASS: decision tree/link and format validators check five notes; archive verification passes with zero archived notes. No live GStreamer start/stop cycle, camera-stability acceptance, script timeout-path acceptance or boot-start acceptance is claimed.

### Notes

- `scripts/start.sh`: provides guarded background startup, config validation, PID ownership/readiness checks and duplicate-start handling.
- `scripts/stop.sh`: verifies release identity and performs bounded graceful shutdown without sourcing configuration or killing unrelated processes.
- `tests/test_scripts.py`: adds seven Linux subprocess integration checks with private temporary releases, fixture-only credentials and ephemeral ports.
- `.gitignore`: excludes root `server.pid`, `server.log` and `server.lock` runtime artifacts.
- `README.md`: changes routine service management to the two scripts, documents restart, states the pending live-release deployment and adds the Linux test boundary.
- `docs/deployment.md`: records script behavior, prerequisites, verification limits and rollback without changing the live deployment history.
- `docs/decisions/implemented/process/2026-11-17-service-scripts.md`: records the script-versus-manual/systemd choice and safety/deployment boundaries.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: links lifecycle tooling while preserving passive synchronization and native-media/network boundaries.
- `progress.md`: appends this implementation and its exact local/isolated-Linux evidence without changing earlier entries.

Rollback the new local entry points without deleting source: from the project root, after confirming the `.disabled` destinations are absent, run `mv scripts/start.sh scripts/start.sh.disabled && mv scripts/stop.sh scripts/stop.sh.disabled && mv tests/test_scripts.py tests/test_scripts.py.disabled`, then use the previously documented manual lifecycle commands. Keep all earlier deployment edits and this append-only log. No live-release rollback is required because its files and service were not changed. If these scripts are deployed later, stop their service before removing PID metadata. No rollback was executed.

## 2026-11-18 - Task: Add timestamped log files and root background startup entrypoints

### What was done

- Moved the two newly added, not-yet-deployed lifecycle scripts from `scripts/` to executable root `start.sh` and `stop.sh`. The documented commands are now `./start.sh`, `./stop.sh` and `./stop.sh && ./start.sh`; background startup is internal and needs no caller-supplied ampersand or nohup.
- Added a source-controlled empty `log/` directory. Each actual service launch writes stdout and stderr to its own `log/carstream-<UTC launch timestamp>.log`, including nanoseconds, and reports the exact path. Repeated start of an existing service creates no new file; restart preserves prior output. Kept directory mode 0700 and log mode 0600 at runtime.
- Kept the existing bounded lifecycle and process-identity checks. Do not rotate at midnight, delete old logs, migrate historical `server.log`, install boot services, or change application/media/network behavior.
- Added root scripts to the synchronization allowlist and preserved executable permissions during rsync. Runtime log files and the log directory are not part of that upload; startup creates the board directory when absent. Git ignores runtime log content while retaining `log/.gitkeep`.
- Updated the existing README, deployment guide, lifecycle decision and targeted tests for direct execution, per-start log naming, stdout/stderr capture, unchanged historical logs and restart behavior. Preserved all earlier worktree edits; no commit or push was made.

### Testing

- PASS: `bash -n start.sh stop.sh scripts/sync-board.sh`; `.venv/bin/ruff check carstream tests`; executable permission checks for both root scripts; `git diff --check`. IDE ReadLints returned no diagnostics for edited scripts, tests and documentation.
- PASS: local Python discovery ran 24 checks: the original 16 configuration/signaling tests passed, and eight Linux-specific lifecycle tests were skipped on macOS. The new restart-log test and updated log assertions exist but were not counted as executed locally.
- PASS: Git ignore checks exclude `log/example.log`, `server.pid` and `server.lock`, while explicitly retaining `log/.gitkeep`. The synchronization file list includes the two root entrypoints and excludes runtime logs by allowlist.
- PASS: decision-note tree/link and format validators check five notes; archive validation passes with zero archived notes.
- BLOCKED: one bounded SSH attempt to `100.94.108.3:22` timed out before authentication. The intended isolated Linux checks never started, no remote temporary directory or upload was made, and no live service was signaled. Current board health was not reverified in this task.
- NOT VERIFIED: direct execution and timestamped logging on Linux for this updated version, rsync execution against the board, or a live media-service restart. The previous task's seven passing Linux tests apply to the old script paths and fixed-log behavior only; they are not evidence for these updated log assertions.

### Notes

- `start.sh` (replaces this agent's local `scripts/start.sh`): uses the project root as its location and writes a separate UTC timestamped log for each actual background launch.
- `stop.sh` (replaces this agent's local `scripts/stop.sh`): retains graceful process-verified stop behavior from the new root entrypoint and points timeout diagnostics to `log/`.
- `log/.gitkeep`: retains the requested empty log directory in source checkouts without committing log content.
- `.gitignore`: ignores runtime log-directory content except its empty-directory placeholder, retaining the historical `server.log` exclusion.
- `scripts/sync-board.sh`: allowlists the root scripts and preserves executable permissions without uploading runtime logs or starting services.
- `tests/test_scripts.py`: directly executes the copied executable scripts and checks log naming, permissions, stdout/stderr, repeated-start behavior and preservation across restart; now eight Linux checks.
- `README.md`: documents direct root commands, per-start UTC log files, viewing logs, retention boundaries and pending board synchronization.
- `docs/deployment.md`: records root entrypoints, timestamped log storage, permission-preserving synchronization and unchanged live-release boundaries.
- `docs/decisions/implemented/process/2026-11-17-service-scripts.md`: updates the existing lifecycle decision with root paths, log format, runtime exclusions and the Linux verification gap.
- `progress.md`: appends this task, its SSH blocker and exact verification limits without changing earlier history.

Rollback/disable the new local entrypoints without discarding source: after confirming disabled destinations are absent, run `mv start.sh start.sh.disabled && mv stop.sh stop.sh.disabled` from the project root and use the previously documented foreground command after loading `.env`. Keep historical logs, all prior edits and this append-only record. Do not remove PID metadata while a service is running. No board rollback is necessary because this task did not reach the board or deploy the scripts; no rollback was executed.

## 2026-11-18 - Task: Deploy public port 7777, independent proxy, TURN and strong credentials

### What was done

- User authorized cloud alias `company` (8.130.208.68), public port 7777, independent reverse proxy, necessary TURN and strong token. Inspected listeners, original Nginx processes, SSH forwarding settings, firewall, available packages and board access before deployment. Mac Tailscale was initially stopped, then became running; no agent-side Tailscale/network change was made.
- Installed independent `carstream-proxy` and `carstream-turn` containers under `/opt/carstream`, using official/upstream registries and pinned image digests after Docker Hub timed out. Existing Nginx masters (18457 and 19719 at inspection), Docker daemon configuration, SSH daemon configuration and unrelated services were preserved. Cloud host is Ubuntu 18.04/kernel 4.15/Docker 24.0.2; obsolete-host maintenance remains outstanding.
- Configured HTTPS at `https://8.130.208.68:7777`, IP-SAN self-signed certificate, exact application Origin, fail-closed backend marker and per-IP request limiting. Certificate expires 2027-02-16 02:10:20 UTC and is not automatically renewed. Its SHA-256 fingerprint is recorded in deployment documentation; no private key is tracked. Fixed duplicate certificate extensions from legacy OpenSSL defaults by using an explicit config; strict TLS then passed.
- Generated independent random 32-byte access-token and TURN-password values. Cloud credentials reside in mode-0600 `/opt/carstream/private/public-access.env`; board config stays mode 0600. TURN stores its sensitive derived key, not the raw password, in restricted container configuration. Secrets were not printed or written to tracked files. The old short token is now invalid.
- Board cat/root default SSH directories had no usable existing cloud identity. Generated a dedicated board-local Ed25519 key (private key never copied off-board), pinned the cloud host key via authenticated SSH, and authorized a dedicated nologin cloud account. Installed the `carstream-tunnel` user service, automatic reconnect, and enabled linger (previously off). Cloud backend listener is only `127.0.0.1:17777`, forwarding to board `127.0.0.1:8080`. Old OpenSSH lacks per-key permitlisten; client loopback binding is verified, but server-side single-listener key confinement is not claimed.
- Configured TURN TCP/UDP 3478 and relay UDP 49160-49259 with private/public NAT address mapping, long-term auth, private/loopback/multicast peer denial and container/log/resource restrictions. Added only the two UDP Firewalld port specifications, runtime and permanent, without reload; existing all-TCP policy remains. No cloud security group API was available; no security-group inspection/change is claimed.
- Public UDP probes timed out but TCP 3478 worked from Mac and board. Added narrow validated TURN transport-query support in config.py and preserved it in browser ICE URIs, allowing explicit TCP relay. Production media code and RTP MTU/bitrate/codec/camera networking were not changed.
- Passed latest eight Linux lifecycle tests in an isolated board release, then backed up current `.env`, config.py and historical PID under `.public-access-backup-20261118T020800Z`. Deployed config.py and root start/stop scripts, gracefully stopped identity-verified PID 122431, and started PID 132745 with strong-token/exact-Origin/forced-relay settings. New log is `log/carstream-20261118T020735.368277373Z.log`; historical server.log is untouched. Python application remains manual, not boot-enabled.
- Opened the proxy gate only after live wrong-Origin/old-token rejection and strong-token/native-pipeline checks. Temporary TURN verbose diagnostics were disabled afterward. No browser automation, Git commit or push was performed. Updated local README/deployment/decision records; this is not a full documentation/tests synchronization to the live release.

### Testing

- PASS: local Python discovery, 26 total checks: 18 configuration/signaling tests passed, eight Linux lifecycle tests skipped on macOS. The new explicit-transport test first failed against old config and passes after the change; ambiguous/unsupported queries are rejected. Ruff and JavaScript recovery checks passed.
- PASS: all eight updated lifecycle checks on Linux in `/tmp/carstream-public-check-20261118`, including direct root execution and timestamp log assertions, without using camera or production PID. Live deployment subsequently demonstrated real app stop/start and private timestamp logging.
- PASS: public verified TLS HTTP 503 while gated, then HTTP 200 health through cloud-to-board tunnel after activation. Live wrong Origin returns 403, previous token returns Invalid access token, strong token receives authenticated ready with real RTSP and relay/TCP configuration.
- PASS: public TCP STUN from Mac and board; authenticated public TURN/TCP relay-to-relay payload transfer with both candidate types relay. Public UDP timeout is recorded, not treated as success.
- PASS: native public WSS/SDP/ICE/DTLS/SRTP trial using an isolated aiortc client: forced relay/relay selected, real 2304x1296 frame decoded, 992 frames decoded over 60 seconds; terminal 438871 ended exit 0 after 61.3 seconds. Cleaned up its peer and signaling connection; no frame recording or production dependency addition.
- DIAGNOSED TEST-CLIENT INTEROP: aiortc default ECDSA-only suites initially failed DTLS after ICE succeeded against the board RSA certificate. Added browser-like ECDHE-RSA AES-GCM only in the temporary acceptance client; fingerprint verification remained enabled. No server crypto downgrade or media patch was used.
- PASS: manually restarted the managed tunnel; new tunnel PID 133174 was active and cloud loopback health returned alive. Linger=yes verified. No full board/cloud reboot, automatic outage-recovery test, browser acceptance, multi-viewer public capacity or long-term playback acceptance is claimed. The previous camera-stall root cause remains unresolved.

### Notes and rollback

- `carstream/config.py`, `tests/test_config.py`, `.env.example`: explicit validated TURN TCP/UDP transport and regression coverage, no embedded secrets.
- `deploy/cloud/nginx.conf`, `deploy/cloud/turnserver.conf.template`, `deploy/cloud/certificate.cnf`: nonsecret deployment-specific proxy/TURN/certificate configuration; actual derived TURN key and TLS private key remain remote/private.
- `deploy/board/carstream-tunnel.service`: dedicated pinned-host reverse tunnel and automatic reconnect, independent from manual Python lifecycle.
- `README.md`, `docs/deployment.md`: current public endpoint, private token retrieval, self-signed trust/expiry, logs, exact runtime boundaries and rollback. Existing local edits are preserved.
- `docs/decisions/implemented/architecture/2026-11-18-public-access.md`: public topology, rejected alternatives, trust/transport/host-risk boundaries and acceptance limitations; existing architecture/lifecycle notes are cross-linked and current facts updated.
- `progress.md`: appends this work without rewriting prior history. Private temporary operational files are ignored, not source dependencies.

Rollback must first remove `/opt/carstream/config/backend-ready` (public requests become 503) and disable the board tunnel before restoring the old weak-token environment. Stop only the identity-checked current application using `./stop.sh`, restore backup `.env` and config.py, never the historical PID file, then use `./start.sh` for private operation. Stop only `carstream-proxy`/`carstream-turn` if disabling cloud services. `/opt/carstream/private/deployment.json` lists the exact four firewall additions to undo; preserve pre-existing rules, account-independent access and all backups/logs. Linger was previously off and may be disabled if no other user service depends on it. No rollback executed.

Final checks: six active notes pass tree/link and format gates; archive validation passes with zero archived notes. Ruff, shell syntax, Git diff whitespace and all eight Node player tests pass. IDE ReadLints could not be invoked because its dynamic runtime tool was unavailable despite schema discovery; command-line lint is the verification evidence. After turning off temporary TURN diagnostics and restarting the tunnel, public authenticated relay-to-relay payload transfer and verified-TLS HTTP 200 still pass. Board PID remains 132745, tunnel active, timestamp log mode 0600; config.py/start.sh/stop.sh SHA-256 match local files. Removed only the task-created board test directory and credential staging file, and deleted the local ignored plaintext credential copy after acceptance. Private production environment and backups remain remote; no new viewer process remains from this task.

## 2026-11-18 - Task: Repair reproduced native session and RTSP input defects; verify remaining public stalls

### What was done

- Reproduced two independent defects behind the instability investigation: native signal closures retained closed Python sessions and native resources; the camera's successive H.265 SSRC pads were not all connected, stopping RTSP with not-linked. Added explicit handler/reference cleanup for close and construction failure, and a native funnel accepting each matching video pad before the existing media path.
- Added focused native regressions for the observed pad handover, repeated close with real TURN candidate allocation, Python/native finalization, construction failure and safe native error summaries. Added timestamped, sanitized application errors without publishing raw RTSP messages, debug strings or credentials.
- Backed up and gracefully deployed cleanup/logging first at 02:42 UTC, then the input-only correction at 03:24 UTC, verifying process identity and prior file hash before replacement. Current activation PID is historical 137473; reread server.pid before any operation. Deployed media.py SHA-256 is cafbaa81d43ea537ef220788645144a96c2c0254738891cd2079c2a5772a55c8; active log is log/carstream-20261118T032426.290965088Z.log.
- Preserved private configuration, exact Origin, strong token, camera settings, routes, existing cloud services, bitrate, MTU, production RTCP and timeout values. No speculative workaround was deployed. Updated usage/decision/deployment records to state that these local fixes do not complete stability acceptance. No commit or push was made; all prior worktree edits remain.

### Testing

- PASS, reproduced before fixing: the old implementation retained all three closed-session weakrefs and increased descriptors from 7 to 96; the dual-SSRC regression failed on its unlinked later pad. The corrected native SSRC test passes without opening a camera.
- PASS on the board: all three native cleanup tests, including ten sessions each gathering an actual TURN relay candidate and closing twice. After asynchronous settlement, descriptors remained 17 each round, Python sessions disappeared and pipeline/webrtcbin native weakref finalizers fired. The first half-second wait failed; a separate ten-round diagnostic established one-second settlement without raising the allowed growth limit.
- PASS on the board: existing synthetic native WebRTC loopback decoded at least ten frames and checked actual RTP packet sizes at or below 1200 bytes. These synthetic tests do not prove long-running camera playback.
- MIXED source-path evidence: generic funnel accepted successive camera pads; rtpfunnel failed with not-negotiated and was rejected. Earlier isolated source probes stalled after roughly 37-61 seconds with queued TCP input and downstream stages waiting; disabling RTCP also stalled. Later default-setting source probes kept progressing for 90 and 180 seconds; the latter encoded 3600 frames. An earlier script's PASS after output had frozen was invalid and is not counted; revised probes require ongoing progress and fail after eight seconds without outgoing RTP.
- FAIL, public continuous-playback acceptance: the 300-second target used verified HTTPS/WSS and forced relay/relay TURN/TCP. Last periodic sample: 2352 decoded real-camera frames at 163 seconds, 21762 RTP packets received and 4604 reported lost. It then timed out after 20 seconds without a decoded frame; process exit 1 after 233 seconds overall, including setup/cleanup. The 15.78-second maximum gap includes startup and is not a steady-playback gap measurement. No five-minute pass is claimed.
- OBSERVED during the public trial: rtspsrc resource/read code 9, then two safely summarized ValueError failures, while tunnel NRestarts stayed 0. There is no per-viewer log correlation, so these errors cannot conclusively be assigned to the acceptance client; receive-side loss counters also do not identify the dropping hop. The remaining stall root cause is unresolved.
- PASS final read-only live check: recorded application command/cwd match the current release, media hash unchanged, HTTP health alive, one camera TCP connection and tunnel active with zero restarts. The live descriptor snapshot was 86 with an active viewer; it is not comparable to the isolated test's 17-descriptor baseline and is not a leak verdict. Temporary acceptance/probe processes exited; production remains running.
- PASS final local checks: Ruff carstream/tests; Python discovery ran 26 checks with 18 passing and eight Linux lifecycle checks explicitly skipped on macOS; all eight Node player tests; git diff --check. Seven active decision notes pass tree/link/format gates and zero archived notes pass archive validation. IDE ReadLints discovery returned no available tool; no IDE lint coverage is claimed. Browser, long-term stability and public capacity remain unverified.

### Notes

- `carstream/media.py`: tracks signal ownership, releases pipeline references, handles successive camera SSRC pads through funnel, and exposes only safe native error metadata.
- `carstream/server.py`: includes the already-sanitized failure summary in warning logs.
- `carstream/__main__.py`: timestamps application log records for failure correlation.
- `tests/smoke_cleanup.py`: adds native cleanup, construction-failure and error-redaction regressions using synthetic video.
- `tests/smoke_rtsp.py`: simulates the two observed camera SSRC pads and verifies both connect to the same video path.
- `README.md`: documents optional regressions and accurately marks the latest public stability acceptance as failed.
- `docs/deployment.md`: records both deployed fixes, mixed source-probe evidence, failed extended public trial, current hash/log and layered rollback.
- `docs/decisions/implemented/bug-fix/2026-11-18-rtsp-session-lifetime.md`: records the native lifecycle/input decisions, real alternatives, verification and remaining evidence gaps.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: links the repair while retaining the native-media boundary.
- `docs/decisions/implemented/feature/2026-11-17-multiple-viewers.md`: links per-viewer input and cleanup responsibilities.
- `docs/decisions/implemented/feature/2026-11-17-player-recovery.md`: distinguishes automatic reconnection from the native defects and unresolved sustained playback.
- `progress.md`: appends this task and its exact pass/fail boundaries without rewriting history.
- Ignored `.tmp/probe-camera.py` and `.tmp/verify-public-media.py`: task-local diagnostic clients with ongoing-progress checks and bounded durations, not application dependencies or source deliverables. The private board fixture `/tmp/carstream-stability-20261118` remains for reproducible investigation; its processes are stopped and it is not a service.

Input-only board rollback, retaining the cleanup fix and strong configuration: run each command only if the previous one succeeded: `cd /home/cat/carstream-20261117T060914Z`, `./stop.sh`, `cp -p .rtsp-input-backup-20261118T032425Z/media.py carstream/.media-rollback.py`, `mv carstream/.media-rollback.py carstream/media.py`, `./start.sh`. This deliberately restores the unlinked-SSRC defect. The earlier `.stability-backup-20261118T024200Z/{media.py,server.py,__main__.py}` is the pre-cleanup rollback point and would also restore the resource leak; never restore the unrelated weak-token public-deployment environment as part of stability rollback. Preserve backup/log/history files. No rollback was executed. Next diagnostic action is to correlate source and receiver progress in the same failing viewing session, not to change network/RTCP/bitrate by guesswork.
