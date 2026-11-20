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

## 2026-11-18 - Task: Push reviewed checkpoint, then correlate one viewer's source and receiver progress

### What was done

- Followed the requested order: reviewed and committed existing lifecycle, public-deployment and media-fix work as three separate commits, then pushed master to origin before beginning the next diagnostic. Commits: 57b1751 (guarded lifecycle/logs), c0cd41d (public deployment/TURN transport), 65301be (native media fixes and acceptance records). Remote master was verified to equal 65301be923699b44113474057f0130de0887abb5; the worktree was clean at that checkpoint. No private .env, key, credential staging file or runtime log was included.
- Ran one bounded isolated authenticated viewer against the unchanged production package and settings, on board loopback 18081. Added diagnostic-only per-stage counts before/after camera jitter buffering, MPP encoding and RTP packaging, plus receiver statistics and UTC progress samples for the same viewing session. Signaling traveled through a temporary private SSH forward with the configured public Origin; media selected relay/relay through existing public TURN/TCP. This does not reproduce the public HTTPS/WSS proxy path or a browser.
- The 300-second observation window completed, but captured a 6.61-second decoded-frame gap while source/encoder/payloader counters kept advancing. This narrows that particular event to after RTP packaging, not a source/MPP stop. It does not distinguish WebRTC sending, TURN/network transport or receiver/decode recovery, and does not explain all earlier RTSP read failures.
- Shut down the diagnostic processes and canceled only the temporary SSH forward. Kept production running without restart, replacement, credential/config changes or speculative media-parameter changes. Recorded the new evidence locally after the pushed checkpoint; these post-push documentation updates have not been committed or pushed.

### Testing

- PASS: each commit's staged diff whitespace checks; normal git push origin master; post-push branch tracking showed no ahead/behind delta, and git ls-remote matched local HEAD. No force push, Git configuration change, amend or hook bypass was used.
- PASS: application Ruff checks; Python discovery ran 26 checks, 18 passed and eight Linux lifecycle tests skipped on macOS; Node player test command exited 0 (existing suite has eight tests). Seven decision notes passed tree/link/format gates and zero archived notes passed archive validation before the diagnostic.
- PASS diagnostic execution, NOT smooth playback: client exit 0 after about 304 seconds overall, with 5765 decoded 2304x1296 frames in the 300-second target observation window. The server emitted source_closing and diagnostic_stopped and exited 0. The client's PASS only asserts completion without a 20-second no-frame timeout; the measured 6.61-second post-startup gap fails any claim of uninterrupted viewing. Initial frame wait was 4.87 seconds.
- CORRELATED EVIDENCE: at 03:57:09/03:57:14 UTC the same source's encoded-frame counter rose 4795 to 4895 and packaged RTP rose 38969 to 39739, with active stage inactivity near 0.02 seconds. Receiver frame age was 3.37 then 1.70 seconds and its reported lost-packet count rose 617 to 1553. It later resumed decoding without a reconnect. Final totals: source 6020 encoded frames / 48978 packaged RTP packets, receiver 47378 received / 1596 reported lost. Counters include startup and do not locate the dropping hop. No native source bus warning/error was recorded for this session.
- PASS cleanup/live checks: production PID 137473, release cwd and media hash cafbaa81d43ea537ef220788645144a96c2c0254738891cd2079c2a5772a55c8 unchanged. Camera TCP connections returned from two during diagnosis to one; board diagnostic listener absent, temporary local listener absent after targeted forwarding cancellation. Managed tunnel active, NRestarts=0; verified-TLS public /healthz returned alive. HTTP liveness is not video health.
- PASS: Ruff explicitly included both ignored diagnostic scripts after fixing import-order findings. IDE ReadLints returned totalFiles=0, so it provides no meaningful coverage. No media data or private native message/debug text was saved; only counters, fixed diagnostic categories and public/loopback connection metadata were logged. Browser, production public-endpoint sustained playback and capacity remain unaccepted.

### Notes

- Ignored `.tmp/observe-session.py`: adds the single-session, 400-second-bounded diagnostic server and native stage counters without modifying production code.
- Ignored `.tmp/verify-public-media.py`: permits the explicit isolated signaling endpoint and adds receiver progress/final counters, keeping the actual public TURN media route.
- Remote `/tmp/carstream-stability-20261118/observe-session.py`: task-created diagnostic copy; inactive after the bounded trial, not installed as a service.
- `docs/deployment.md`: records same-session observations, exact proxy-bypass boundary, cleanup and remaining diagnostic scope.
- `docs/decisions/implemented/bug-fix/2026-11-18-rtsp-session-lifetime.md`: updates verification facts without changing the implemented media decision or overstating the new result.
- `progress.md`: appends the requested commit/push checkpoint and post-push diagnostic evidence without changing earlier records.

No production rollback is needed for this diagnostic: both temporary listeners/processes are already gone and production bytes/settings are unchanged. To roll back only the two new explanatory documentation edits, first ensure no later edits need preserving, then run `git restore --source=65301be -- docs/deployment.md docs/decisions/implemented/bug-fix/2026-11-18-rtsp-session-lifetime.md`; keep this append-only progress entry. The pushed three-commit checkpoint remains the code rollback/reference point. No rollback was executed. The next minimum diagnostic is same-session native WebRTC sender transport statistics alongside receiver progress, not a speculative codec/network change.

## 2026-11-18 - Task: Repair native retransmission, abandoned tunnel and constrained video throughput

### Changes and evidence

- Preserved the pre-existing post-push diagnostic documents. No commit or push was made in this task; published checkpoint remains 65301be. Changes below are local unless specifically identified as deployed.
- Installed GStreamer sender default was do-nack=false, and its actual offer lacked generic NACK/RTX. Enabled native retransmission and a bounded 1000-packet history via a tracked deep-element-added handler. The new regression failed the old offer, then passed by dropping a known synthetic RTP sequence after the native cache, observing that same original sequence as RTX and decoding ten more frames. Actual cache size and 1200-byte packet checks passed.
- RTX alone caused the unchanged strict cleanup regression to fail (18 to 20 descriptors). Classification found stable sockets and finalized native RTX objects but retained DMA buffers. Stopping webrtcbin before the MPP pipeline corrected the observed shutdown regression without loosening limits. Repeated independent cleanup runs passed; final original/low-bandwidth ten-round runs remained at 17 descriptors, with Python/native finalization, construction failure and safe-error checks passing.
- Original-profile isolated 300-second trials are NOT smoothness passes: default 100-packet history decoded 5796 frames with maximum gap 2.70 seconds (last sender sample 3346 requests/3205 RTX); 1000-packet history decoded 5881 frames with maximum gap 3.06 seconds (2338 requests/2338 RTX). Both failed the new two-second continuity limit. The improved diagnostic measures startup separately, begins its 300-second window at first frame, requires at least ten decoded frames/second and fails after 20 seconds without a frame.
- With user approval, deployed RTX-only media at 04:29:52 UTC, historical PID 140662, log/carstream-20261118T042952.784877111Z.log, SHA-256 5ad30f97b4e694b5319165f034bce9844528cf68d25a6ae885eeda5aca8a9cb3. Backup .rtx-backup-20261118T042836Z/media.py retains the prior cleanup/SSRC build.
- Public testing exposed an independent tunnel defect: old board SSH timed out at 04:29:56 UTC, but its cloud sshd listener still occupied 17777; automatic reconnects repeatedly failed. Board HTTP and proxy/TURN containers were alive, but cloud loopback HTTP timed out. After separate user approval, configured ONLY carstream-tunnel's ClientAliveInterval=15/ClientAliveCountMax=3, validated candidate/install with sshd -t and complete sshd -T comparisons proving root/unrelated users unchanged, then reloaded SSH. Sent SIGTERM only to verified stale dedicated child 13988 (parent 13949). Board reconnected automatically; cloud/public verified-TLS health recovered, new root SSH worked. Historical NRestarts reached 86; no blackhole recovery-time test was performed.
- Cloud SSH backup /opt/carstream/private/sshd_config-before-heartbeat-20261118T043841Z; original hash 939a89a19b7147d7ab07b4e3e8aaa208cfe0b0aaa9ac367c88788852d7e31333, installed hash 658fb4ea3339779c5ecf5792586efab734e0d63a7df6eda208494c7fd87bdc96. Other user authentication/forwarding settings, routes, firewall and unrelated services were not changed. The new nonsecret deploy/cloud/sshd-carstream-tunnel.conf records the account-scoped block, not a whole-server replacement.
- After tunnel recovery, two public relay/relay ICE/DTLS sessions still decoded zero frames within 20 seconds. Further same-session isolation likewise failed: 263 encoded frames, 3623 original RTP packets, 5013 native transport-input buffers; client counted 919 original and 494 RTX packets, zero decoded frames. Entry to native transport is not wire-delivery proof. Added separate original/RTX diagnostic counters because this aiortc version's inbound report can represent the RTX SSRC instead of total video traffic.
- Private Tailscale SSH temporarily timed out while public reverse HTTP stayed healthy; authorized password reauthentication restored access without network edits. Installed libnice/gstreamer1.0-nice confirmed 0.1.18-2. Old upstream nicesink source inspection alone is not proof of the root cause; no native system library was replaced.
- Independent synthetic relay transport, no camera/GStreamer: Mac-to-TURN-to-Mac delivered both 1600-packet burst/paced trials fully (1200 bytes, 160 packets/sec). Board-to-TURN-to-Mac received 745/1600 within the first bounded window; the next window was affected by prior backlog and teardown exceeded its original bound. Do not interpret these as permanent loss or independent pacing comparisons. Concurrent board TURN TCP showed about 63 KB queued, delivery_rate 547016 bps and about 210 KB retransmitted, below original 1.5 Mbps video demand. Probe-only aioice dependencies were installed in /tmp/carstream-stability-20261118/transport-venv, not production.
- User explicitly approved prioritizing stability over quality after isolated acceptance. Added VIDEO_PROFILE=original|low-bandwidth, default original. H.265 low-bandwidth uses existing MPP hardware 1280x720 scaling, 350 kbps target and CBR bounds 300-400 kbps; H.264 camera passthrough rejects this combination. Synthetic source stays 640x360. No automatic adaptation is claimed; camera settings, credentials, routes, GOP and MTU remain unchanged.
- PASS isolated low-bandwidth real camera: actual 1280x720, 300 seconds after first frame, 6031 decoded frames, maximum steady gap 1.556 seconds, startup 1.13 seconds, relay/relay, no reconnect. Original packet arrivals 13163, RTX arrivals 92; the latter is not total-video traffic. All three native cleanup tests, SSRC and exact-sequence loss recovery pass.
- Following the approval gate, deployed the low-bandwidth profile at 05:21:04 UTC, historical PID 148815, log/carstream-20261118T052104.459906832Z.log. Backup .profile-backup-20261118T051818Z contains the prior RTX build's media.py/config.py and private .env (0700 parent, 0600 environment). Installed media hash 16f1eadeec0d466672f73f3fdcb352aaeb9175f0eeb08e32736af7515ada8b5f, config hash 42887e03107a48910856f69da108623f5808e24911f25c3fed0c9ca334ccf7ba. Private environment append changes only VIDEO_PROFILE. Full public HTTPS/WSS/TURN acceptance is now running and must be judged separately.

### Checks and records

- Local Python discovery: 27 checks, 19 passed and eight Linux lifecycle checks skipped on macOS. All eight Node player tests and Ruff pass. IDE diagnostic queries have returned totalFiles=0, so CLI checks are the meaningful lint coverage.
- Ten active decision notes pass tree/relative-link and format checks; zero archives pass immutability validation. New notes cover native retransmission, server heartbeat and explicit low-bandwidth profile. Related older decisions are preserved and cross-linked, including the narrowly superseded initial no-SSH-server-edit boundary.
- README/.env.example document the explicit profile and focused native test. Deployment records distinguish native correctness, isolated media, full public media, operational backups and account-scoped SSH safety. Ignored diagnostics save no camera frames and print no application/TURN/camera credentials.
- Final public results and cleanup will be appended below. The isolated pass does not complete public, browser, long-term or multi-viewer capacity acceptance. No rollback was executed; preserve all history and private backups. Do not restore an unrelated old weak-token environment for stability rollback.

## 2026-11-18 - Task: Record public acceptance failure and stop at board connectivity blocker

### What was done

- Completed the full production HTTPS/WSS and TURN/TCP observation after the approved 720p / 350 kbps activation. Kept the two-second continuity threshold: five minutes without reconnecting is not by itself a smoothness pass. Updated current status instead of leaving the README on earlier test results.
- A subsequent isolated 200 kbps experiment was interrupted by simultaneous media and SSH loss. This is not a valid bitrate comparison and was not deployed. Removed only this task's experimental bitrate setting, implementation and test locally; media/config hashes again exactly match the previously deployed 350 kbps build. Production was not restarted or changed during this finalization.
- Confirmed a new operational blocker: cloud SSH is reachable, but public health returned 502, cloud reverse listener 17777 is absent, and fresh board SSH times out. At 05:36:27 UTC the listener was still absent. This differs from the previously fixed stale listener that remained bound. Stopped further remote changes; power, board network and board system state require local confirmation before another acceptance trial.
- Preserved all unrelated settings, camera configuration, credentials, user sessions and historical records. No additional commit or push was made; published checkpoint remains 65301be. Empty Git status/diff output is not used as evidence that these new repairs have been committed or that the worktree is clean.

### Testing

- FAIL strict public continuity, completed 05:26:18 UTC: actual 1280x720, 4846 decoded frames during 300 seconds after the first frame, startup wait 1.41 seconds, relay/relay, no reconnect or 20-second frame timeout. Maximum steady frame gap 2.183 seconds exceeds the unchanged two-second limit; the assertion failed and the receiver exited 1. Counted 13522 original PT96 and 153 RTX PT97 arrivals. Neither RTX SSRC statistics nor HTTP liveness are total video-delivery proof.
- PASS isolated gate retained separately: 6031 decoded frames during 300 seconds, maximum steady gap 1.556 seconds at 350 kbps. Full public, browser, long-term and multi-viewer capacity acceptance remain incomplete. Two camera TCP connections were observed during the public test; this is not proof that the additional connection caused its frame gap.
- FAIL interrupted lower-bitrate experiment: 439 decoded frames before media stopped; receiver hit its no-frame timeout. Diagnostic SSH exited 255 at 05:30:23 UTC. Public 502, absent cloud reverse listener and board SSH timeout were observed afterward. The cloud remained accessible; the exact board-side failure is unconfirmed. Do not continue reducing bitrate based on this interrupted trial.
- PASS final local checks: Ruff carstream/tests; Python discovery 27 checks, 19 passed and eight Linux lifecycle checks skipped on macOS; all eight player tests using tests/player.test.cjs; player JavaScript syntax, shell syntax and git diff --check. An initial Node invocation used the nonexistent .mjs filename; the actual .cjs entry then passed. IDE ReadLints returned totalFiles=0 and provides no additional coverage.
- PASS note gates after the final result update: ten active notes pass tree/relative-link and format checks; zero archived notes pass archive verification. Local media SHA-256 is 16f1eadeec0d466672f73f3fdcb352aaeb9175f0eeb08e32736af7515ada8b5f and config SHA-256 is 42887e03107a48910856f69da108623f5808e24911f25c3fed0c9ca334ccf7ba, matching activation records. Current remote bytes/process identity cannot be rechecked while the board is unreachable.
- CLEANUP BOUNDARY: local receiver and diagnostic SSH have exited. The board observer declares a 400-second lifetime, but its final remote process/listener cleanup is not confirmed. Its private /tmp fixture may retain the 200 kbps experimental copy and is not production. After access returns, inspect and clean up only this task's diagnostic process/listener if still present; do not terminate other viewers or delete production secrets.

### Notes

The complete pending repair scope, including the immediately preceding repair entry, is:

- `carstream/media.py`: enables native NACK/RTX, bounds retransmission history, releases WebRTC before MPP teardown, and implements the explicit 720p / 350 kbps profile; no experimental bitrate override remains.
- `carstream/config.py`: validates the explicit profile and rejects low-bandwidth H.264 passthrough; no arbitrary bitrate setting remains.
- `tests/smoke_media.py`: adds optional exact-sequence controlled-loss verification to the native synthetic loopback.
- `tests/smoke_retransmission.py`: provides the dedicated controlled-loss regression entrypoint.
- `tests/test_config.py`: checks profile defaults, explicit selection and unsupported combinations.
- `.env.example`: documents the two fixed video profiles without production credentials.
- `deploy/cloud/sshd-carstream-tunnel.conf`: records the separately approved dedicated-account heartbeat block.
- `README.md`: documents the repairs and records the isolated pass, strict public failure and latest connectivity blocker.
- `docs/deployment.md`: preserves implementation/deployment hashes and rollback boundaries, and adds the final public result, interrupted experiment and cleanup limitation.
- `docs/decisions/implemented/bug-fix/2026-11-18-native-video-retransmission.md`: records native retransmission, bounded cache, teardown ordering and verification limits.
- `docs/decisions/implemented/bug-fix/2026-11-18-tunnel-server-heartbeat.md`: records the dedicated-account-only SSH change, validation and operational rollback.
- `docs/decisions/implemented/bug-fix/2026-11-18-low-bandwidth-video-profile.md`: records the fixed quality tradeoff, strict failed public result and rejection of the interrupted lower-bitrate experiment.
- `docs/decisions/implemented/bug-fix/2026-11-18-rtsp-session-lifetime.md`: links the RTX-specific shutdown responsibility while preserving earlier session/source decisions.
- `docs/decisions/implemented/architecture/2026-11-18-public-access.md`: cross-links the separately approved narrow SSH-server exception without discarding its original deployment boundaries.
- `progress.md`: appends results, exact verification gaps, file scope and rollback points without editing prior entries.

Rollback points are unchanged and were not executed. After board access returns and the current release/process/private configuration are identity-checked, restoring only quality uses private VIDEO_PROFILE='original' followed by ./stop.sh && ./start.sh; this can restore congestion and interrupts viewers. The private .profile-backup-20261118T051818Z contains the pre-profile media.py/config.py/.env with RTX already enabled. The .rtx-backup-20261118T042836Z/media.py is the pre-RTX point. Cloud SSH rollback uses /opt/carstream/private/sshd_config-before-heartbeat-20261118T043841Z only after comparing for newer edits, validating a candidate with sshd -t -f, and reloading rather than restarting SSH. Never restore an unrelated historical weak-token environment. The minimum next action is local board power/network confirmation and restored SSH, then identity/diagnostic cleanup checks before public playback acceptance.

## 2026-11-19 - Task: Install on the replacement board and place the project directly in cam

### What was done

- Paused latency work as requested and authenticated to linaro@192.168.50.84. Inspected Ubuntu 22.04.5, Python 3.10.12, GStreamer 1.20.3 and Rockchip RK3588 ZYSJ 2288A V10 hardware before installation. No route, interface, firewall, old-board service or cloud endpoint was changed.
- Uploaded allowlisted current project artifacts without local secrets, Git metadata, runtime logs or development environments. The initial /home/linaro/CarStream directory was empty. After the user's path correction, copied the project directly into /home/linaro/magnet_car_project/cam, with no nested CarStream directory. Checked for conflicts first and preserved the existing cam/__init__.py byte-for-byte.
- Simulated the minimal APT transaction, then installed 49 new packages with no upgrades/removals and no recommended packages. Explicit additions: python3-venv, python3-gst-1.0, gir1.2-gst-plugins-bad-1.0, gstreamer1.0-plugins-bad, gstreamer1.0-nice and gstreamer1.0-plugins-ugly. The software encoder is for synthetic validation; no vendor codec stack was substituted.
- Created a system-site-packages virtualenv, installed the existing locked requirements, then rebuilt the virtualenv at the final cam path instead of relocating absolute interpreter paths. The initial /home/linaro/CarStream copy remains inactive as a fallback.
- Generated a new strong private application token and mode-0600 .env using test source, loopback 127.0.0.1:8080, original video profile and no camera credentials, public Origin, STUN or TURN. Old board secrets and its low-bandwidth active configuration were not copied. An initial Python 3.10 Path.open(opener=...) attempt failed before creating .env; corrected exclusive os.open/os.fdopen creation succeeded.
- Temporarily started the application only to validate entrypoints, then gracefully stopped it. No application or boot service is left running by this installation. Updated local usage/deployment records and synchronized them to the final directory. No application-code edits, commits or pushes were made.

### Testing

- PASS from the final cam root: all 27 configuration/signaling/Linux lifecycle tests, pip check and common native --check. Native --check is not H.265 capability acceptance; MPP entries remain false.
- PASS from the final root: synthetic native WebRTC received at least ten decoded frames with maximum RTP size 1200 bytes; the controlled-loss regression recovered exact original sequence 28269 as RTX and decoding advanced another ten frames. All three cleanup tests pass; ten closes each settled at eight descriptors, without TURN configuration or relay allocation.
- PASS final-path lifecycle: ./start.sh launched historical PID 15680, loopback health returned HTTP 200 with status alive, a repeated start recognized the same service, and ./stop.sh stopped it. Test log: log/carstream-20261119T015316.686333810Z.log. A final check found no server.pid and no listener on 8080; no private page forward was created.
- PASS preservation/environment: cam/__init__.py SHA-256 remains 4d0e4b367c19703a7fad65e42e86e3571f88cd41f1ccbc4dbe23b91f8ba560a5; .env is 0600, log directory 0700, start/stop scripts 0755, and sys.prefix points to /home/linaro/magnet_car_project/cam/.venv. Checksum-based rsync dry run found no differences in the allowlisted project artifacts, including updated README/deployment records, excluding private/generated runtime content and this final progress append.
- BLOCKED H.265 hardware path: the image lacks mppvideodec/mpph264enc, and inspected package candidates did not provide the vendor stack. The staging-directory H.265 SSRC smoke test failed with Missing GStreamer element: mppvideodec. No threshold was weakened and no pass is claimed for it. Tests after that failed command were run independently; final-path synthetic cleanup passed. Real camera connectivity/credentials, browser display, public deployment, long-running stability and end-to-end latency remain unverified on the replacement board.
- PASS local documentation whitespace check. IDE ReadLints returned totalFiles=0, so no IDE coverage is claimed. No decision was reversed and no decision note was added or modified for the destination correction.

### Notes

- `README.md`: adds the replacement-board cam root, verified installation state, missing H.265 support and warning against the old /home/cat-specific uploader.
- `docs/deployment.md`: records the new hardware, final directory, preserved initializer, dependencies, private test configuration, exact checks, inactive service and rollback boundary while retaining old-board history.
- `progress.md`: appends installation and path-correction results without editing previous entries; the final append is synchronized after writing.
- Remote `/home/linaro/magnet_car_project/cam/`: receives the allowlisted source/docs/tests/deployment templates, rebuilt .venv, private .env and test-created log/server.lock; the user's existing __init__.py is unchanged.
- Remote `/home/linaro/CarStream/`: preserves this task's initial installation as an inactive fallback, not the final project root.
- Remote system packages and APT index/cache: contain the reviewed dependency additions; project Python dependencies are in its virtualenv, not installed into system Python.

Rollback/disable: on the replacement board run `cd /home/linaro/magnet_car_project/cam && ./stop.sh` to stop only this deployment; it is already stopped. The intact initial /home/linaro/CarStream copy is the installation fallback point. Preserve cam/__init__.py, private .env and logs; do not rename or remove the user's whole cam package to undo this installation. Any future removal/move must select only this task's added artifacts after checking for later edits. Package removal is a separate reviewed action, not automatic autoremove. No rollback, old-board shutdown, cloud cutover or network change was executed.

## 2026-11-19 - Task: Install replacement-board hardware plugins and check camera startup prerequisites

### What was done

- Confirmed camera 192.168.11.83 accepts TCP 554/80 via existing enP2p33s0 source 192.168.11.84. No interface, route, firewall, kernel, camera setting or cloud service was changed. The private configuration still has no RTSP URL or camera credentials; the previous board's SSH timed out. Requested the missing private settings rather than guessing or reporting test video as camera playback.
- Found existing MPP 1.3.9 and RGA 2.1.0 development metadata/libraries. Current Rockchip plugin branch bff0659 failed because installed headers lack MppSysCfg. Built pinned compatible commit 0fc75d3710fede7ca2dfb4687362fb6979100d9e into /home/linaro/.local/opt/carstream-rockchip-0fc75d3 without replacing vendor libraries. An initial option gpu was unsupported on this older revision; removed that option and compilation passed.
- Reviewed and installed 43 development packages, with only two GStreamer packages patched from 1.20.3-0ubuntu1.1 to 1.20.3-0ubuntu1.2 and no removals. Pinned GLib development packages to the existing runtime version. An unrelated libffi doc-base warning appeared; package installation and dpkg audit succeeded.
- Added named-user read/write ACLs to eight required media device nodes, with a dedicated udev rule and original ACL snapshot. No world-writable permissions or application root execution. Added private GST_PLUGIN_PATH/GST_REGISTRY variables to the existing mode-0600 .env after backing it up; camera, token, host and quality settings are unchanged. A separate registry avoids the initial root-only scan's decoder-only cache.
- Temporarily started the existing loopback test configuration to verify service lifecycle, then stopped it. Real camera startup is blocked by missing configuration, not by missing hardware plugins. Updated and synchronized operational documentation; no application-code edit, commit or push.

### Testing

- PASS hardware factory/property inspection: mppvideodec, mpph264enc and mpph265enc load from the pinned user prefix; all application-required bitrate/profile/GOP/scale properties are present. Native --check reports all listed elements true.
- PASS finite 60-buffer synthetic pipeline: 640x360 NV12 at 20 fps -> MPP H.265 encode -> H.265 parse -> MPP decode -> MPP Baseline H.264 encode -> parse -> actual H.264 decode, reaching EOS within the 20-second bound. This does not connect to the camera.
- PASS all 27 Linux unit/lifecycle tests, native WebRTC >=10 decoded synthetic frames and RTP <=1200 bytes, exact dropped sequence 26081 recovered via RTX followed by ten frames, the H.265 SSRC regression, and all three cleanup tests. Ten hardware-enabled closes each settle at 17 descriptors; no TURN configured or public-media acceptance claimed.
- PASS temporary lifecycle: historical PID 22366, HTTP 200 alive, repeat start recognized the same process, graceful stop removed server.pid. Final 8080 listener is absent. Log: log/carstream-20261119T021428.142988314Z.log. Existing cam/__init__.py SHA-256 is unchanged at 4d0e4b367c19703a7fad65e42e86e3571f88cd41f1ccbc4dbe23b91f8ba560a5.
- PASS linaro read/write access to required media devices; udevadm test matches the dedicated dma_heap rule, exit 0. dpkg --audit exits 0 with no output. Reboot persistence, real camera authentication/decoding, browser display, public access, latency and long-term acceptance are not verified.
- PASS local documentation whitespace check and ten-note tree/relative-link and format gates. The one-off installer Ruff check exits 0. IDE ReadLints returns totalFiles=0, so no IDE lint coverage is claimed. Final documentation files are synchronized and compared by SHA-256 before handoff.

### Notes

- `README.md`: replaces the missing-plugin status with installed/tested hardware support and the remaining private camera-configuration blocker.
- `docs/deployment.md`: records pinned sources, dependency changes, device access, verification evidence and precise rollback commands while preserving historical board results.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: synchronizes the existing native-media decision with replacement-board dependency isolation and its verification boundary; no architecture decision is reversed.
- `progress.md`: appends this installation/check result without changing history.
- Ignored local `.tmp/gstreamer-rockchip/` and `.tmp/install-camera-device-access.py`: contain pinned vendor source and the one-off backed-up device-access installer; no camera or application secrets.
- Remote `cam/.env`: adds only native plugin path and registry; original preserved in `.hardware-config-backup-20261119T020844Z/.env`. Remote `cam/log/`: adds the temporary startup log; service is stopped.
- Remote `/etc/udev/rules.d/99-carstream-media-access.rules`: adds only linaro device ACLs; original access saved in `cam/.camera-hardware-backup-20261119T020758Z/device-access-before.acl`.
- Remote `.cache/carstream-rockchip-0fc75d3/`, inactive `.cache/carstream-rockchip-bff0659/` and `.local/opt/carstream-rockchip-0fc75d3/`: preserve source/build/registry and isolated installed plugin. Remote APT state contains the reviewed developer dependencies and two patch upgrades.

Rollback point, not executed: stop this cam deployment; after comparing for later changes, restore .env from `.hardware-config-backup-20261119T020844Z/.env`. Run `sudo setfacl --restore=.camera-hardware-backup-20261119T020758Z/device-access-before.acl`, remove only `/etc/udev/rules.d/99-carstream-media-access.rules`, then `sudo udevadm control --reload-rules`. Full commands are in docs/deployment.md. Keep private backups and user files; no broad deletion, package autoremove or automatic downgrade.

## 2026-11-19 - Task: Use the latest plugin and matching MPP, recover the existing camera settings and start cam

### What was done

- Honored the user's request for the new plugin rather than retaining only the compatibility-pinned 2024 plugin. Resolved current upstream MPP develop 9b56348cc61393c84662e6d6dd78feae67773a36 and Rockchip plugin bff0659a51c13585b3c9c9a68aa8c435beeb3fe1, then built both in /home/linaro/.local/opt/carstream-media-latest-20261119. The new MPP supplies the previously missing API. System MPP/RGA libraries, kernel and the previous tested prefix remain intact; no additional APT or global ldconfig change.
- Corrected the earlier incomplete credential search: located the user's original ~/Desktop/voice_project/voice_project/video_stream/inter_video.py on the Mac. Parsed its literal configuration without importing/running OpenCV, reused the same camera credentials, and transmitted them via SSH stdin into private mode-0600 .env. No password guessed, reset or copied to project source/docs; the original script is unchanged. Earlier transcript inspection exposed only completion markers, not previous message text, and the previous board remained unavailable; that is not evidence the user never supplied credentials.
- Backed up the prior test-source/compatible-plugin .env in .latest-runtime-backup-20261119T022813Z. Active settings now use real RTSP/H.265 and the latest private plugin/MPP/registry paths. Kept the existing strong application token, loopback host/port, original video profile, camera-side settings, network and device ACL rule unchanged.
- Started the real-source application in the final cam root, historical/currently verified PID 25947, log/carstream-20261119T022841.824589954Z.log. Created a private Mac loopback-only page forward at 127.0.0.1:18080 using the task-created linaro-latest-ssh.sock master. The service and forward are deliberately left available for the user, not configured as boot services. No public cutover or cloud modification.
- Verified actual real-camera WebRTC decoding through the running application's authenticated WebSocket path. The bounded continuity test failed after initial playback; kept that failure visible rather than treating startup, health or initial frames as stable delivery. Closed only the diagnostic receiver. Did not restart latency/root-cause investigation, change encoding quality or perform unrequested fixes.

### Testing

- PASS latest source/build provenance: local Git resolves the exact two commits above; plugin builds against private MPP pkg-config 1.3.10. Factories load and the running app's /proc/25947/maps shows both libgstrockchipmpp and librockchip_mpp from the new prefix, not the vendor system path. Embedded plugin version 1.14.4 is not the source date; MPP logs say unknown version because the uploaded source excludes Git metadata.
- PASS new pair: finite 60-buffer NV12 640x360/20 fps hardware H.265 encoding -> MPP decode -> Baseline H.264 encode -> actual H.264 decode reaches EOS within 25 seconds. Native synthetic WebRTC delivers >=10 frames with maximum RTP 1200 bytes; controlled loss recovers original sequence 13650 via RTX and continues ten frames.
- PASS all 27 Linux unit/lifecycle tests, H.265 SSRC pad regression and all three cleanup tests. Ten closes each return to 17 descriptors, without configured TURN. Local diagnostic Ruff initially reported two import-spacing issues; fixed only those issues, and final Ruff passes. IDE ReadLints returns totalFiles=0 and supplies no additional lint coverage. Eleven active notes pass tree/relative-link and format gates; git diff --check passes.
- PASS camera identity/authentication and initial service media: confirmed the known URL returns 401 without credentials, then recovered original settings authenticate the app and produce decoded 2304x1296 camera frames via real WebRTC. No frames or screenshots saved.
- FAIL intended 60-second real-camera continuity: last progress sample records 546 decoded frames at 44.13 seconds, with observed maximum frame gap already 4.244 seconds. Receiver exits 1 with MediaStreamError after 52.49 seconds overall, before completing the window. The beginning overlapped independent regression tests; this does not establish their causality. Threshold was not relaxed and no smoothness, browser/public delivery, end-to-end latency or long-term pass is claimed.
- PASS final application preservation/state after receiver exit: verified PID 25947 cwd and runtime SOURCE=rtsp, CAMERA_CODEC=h265, VIDEO_PROFILE=original, HOST=127.0.0.1, PORT=8080. Board and Mac-forwarded health return HTTP 200 alive; repeated ./start.sh recognizes the same process. Original cam/__init__.py hash remains 4d0e4b367c19703a7fad65e42e86e3571f88cd41f1ccbc4dbe23b91f8ba560a5, media.py remains 16f1eadeec0d466672f73f3fdcb352aaeb9175f0eeb08e32736af7515ada8b5f and config.py remains 42887e03107a48910856f69da108623f5808e24911f25c3fed0c9ca334ccf7ba.

### Notes

- `README.md`: records running real camera on the latest pair, private viewing address and failed continuous-playback boundary.
- `docs/deployment.md`: records current source/library versions, credential recovery location, private environment, live service/forward, verification failure, token retrieval and rollback without exposing credentials.
- `docs/decisions/implemented/process/2026-11-19-isolated-latest-media-runtime.md`: records the user-requested latest pair, rejection of global replacement, independent prefix, verification limits and existing-decision audit.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: cross-links the new version-selection decision while preserving original media boundaries and initial compatibility rationale.
- `progress.md`: appends this task's work, evidence, failure and file/rollback inventory without rewriting previous records.
- Ignored local `.tmp/rockchip-mpp-latest/`, `.tmp/gstreamer-rockchip/`, `.tmp/activate-latest-camera.py` and `.tmp/verify-latest-camera.py`: contain source checkouts and one-off secret-free activation/receiver programs; credentials are read only from the user's existing script or private board configuration at runtime.
- Remote `.cache/carstream-mpp-9b56348/`, `.cache/carstream-rockchip-bff0659/build-latest` and its new registry, `.local/opt/carstream-media-latest-20261119/`: contain the isolated source/build/installed latest runtime; older prefixes/builds remain available.
- Remote `cam/.env`, `.latest-runtime-backup-20261119T022813Z/.env`, `server.pid` and startup log: select/start the recovered camera and newest runtime, preserving the original private environment. Application source and user initializer are unchanged.
- Local `.tmp/linaro-latest-ssh.sock` and its private 18080 forward: provide user access without a new public/LAN listener. ControlPersist is 1800; it can expire after idle disconnect. Remote service does not depend on that forward.

Rollback/disable, not executed: `cd ~/magnet_car_project/cam && ./stop.sh` stops this real-source deployment only. To restore the exact pre-task private configuration after checking for later edits, run `cp -p .latest-runtime-backup-20261119T022813Z/.env .env` from cam after stopping; that restores test source and the older compatible plugin, not a working-camera baseline. New libraries need not be deleted or system packages changed. Cancel only the task-created page forward with `ssh -S /Users/jiangdk/code/company/CarStream/.tmp/linaro-latest-ssh.sock -O cancel -L 127.0.0.1:18080:127.0.0.1:8080 linaro@192.168.50.84` after verifying its identity. Preserve user files, camera credentials and historical logs. No commit or push requested/performed.

## 2026-11-19 - Task: Migrate the replacement board to the existing Alibaba Cloud public entrypoint

### What was done

- Followed the user's authorization to reuse yesterday's `ssh company` deployment at https://8.130.208.68:7777. Inspected the existing proxy/TURN containers, certificate and dedicated SSH account; the old reverse listener was absent and public health returned 502. Reused the existing infrastructure without changing container configuration/images, firewall, SSH server configuration, routing, camera networking or other cloud workloads.
- Generated a fresh Ed25519 identity on the new board, pinned the cloud host key obtained through authenticated SSH, and replaced only the verified old board's authorized key. Preserved the saved entry's exact forced-command/restrict/port-forwarding/permitopen options; the old key is no longer authorized and cannot reclaim port 17777. The private key never left the board.
- Installed the existing tunnel template as linaro's enabled user service, with automatic restart and loopback-only reverse forwarding to the existing application. `loginctl --no-ask-password enable-linger linaro` succeeded, Linger=yes. No sudo permission, password guess, root application, global SSH change or application boot service was required.
- Backed up private configuration on both hosts and held the public backend-ready gate closed until access checks passed. Added exact public Origin, existing TURN/TCP credentials, relay-only ICE and explicit weak-token false to the board environment. Preserved its current strong token, real camera credentials, original resolution/quality and latest isolated codec runtime. Updated the cloud's private token record to that same replacement-board token; the previous cloud token is rejected.
- Restarted only this application's guarded release, historical activation PID 28252, log/carstream-20261119T024906.647932803Z.log, then reopened the validated public route. Left both the real-source service and tunnel running. No production application/player source edit, quality reduction, latency investigation, Git commit or push.

### Testing

- PASS fail-closed/access boundary: pinned-certificate HTTPS returned 503 while gated; missing, foreign and former localhost Origins returned 403; invalid and previous cloud tokens were rejected. The unchanged replacement token returned RTSP ready with TURN/TCP relay policy. After opening, public /, /healthz and /player.js returned 200, while /.env returned 404.
- PASS tunnel persistence/configuration: enabled and active user unit, Linger=yes, private cloud listener only on 127.0.0.1:17777, healthy HTTP backend after deliberate tunnel restart. Initial activation specified explicit no-PTY/agent/X11 restrictions; before handoff the exact, stronger saved options including forced command and permitopen were restored, then a fresh tunnel reauthenticated and certificate-verified public health returned 200 alive. No reboot or network-blackhole fault injection was performed.
- PASS public media delivery but FAIL unchanged continuity criterion: the existing external native receiver used public WSS and selected relay/relay, negotiated DTLS/SRTP, and decoded 1241 real 2304x1296 frames over 60 seconds without reconnecting. First-frame wait after track negotiation was 2.63 seconds. Maximum decoded-frame gap 2.458 seconds exceeds the existing two-second limit, so the verifier exited 1. No limit was relaxed, frame saved or long-running/browser/latency pass claimed; the peer/WebSocket were closed afterward.
- PASS all 27 deployed configuration/signaling/Linux lifecycle tests. Final process PID/cwd/command match this release; original initializer, config.py and media.py hashes match their pre-migration values. The new MPP prefix remains loaded. Final process inspection found 22 open descriptors; this observation is not a lifecycle-leak test.
- PASS focused Ruff on the two new private diagnostics after fixing only two import-spacing issues. Standalone ruff was unavailable, so uvx supplied the tool without changing project dependencies. Eleven active notes pass tree/relative-link and format checks; git diff --check passes. IDE ReadLints returned totalFiles=0 and provides no additional coverage.
- TLS verification used the existing pinned certificate with Python's strict verifier and did not bypass verification. The old cloud curl rejected that non-CA self-signed leaf as an issuer; no certificate or security setting was weakened to satisfy it. Self-signed browser trust, expiry on 2027-02-16 and lack of automatic renewal remain operational limitations.

### Notes

- `README.md`: updates current public reachability, replacement-board access/token and unchanged-quality/continuity boundaries.
- `docs/deployment.md`: adds new-board cutover, current management path, exact backups, checks, public URL and private rollback instructions; marks the former localhost viewing path as pre-cutover.
- `docs/decisions/implemented/architecture/2026-11-18-public-access.md`: synchronizes current board/identity/token facts and failed continuity result without changing the established topology decision.
- `progress.md`: appends this migration's scope, verification, failures and rollback inventory; prior entries are unchanged.
- Ignored `.tmp/migrate-public-board.py` and `.tmp/verify-public-cutover.py`: contain secret-free one-off migration and boundary checks; private values are loaded at runtime and sent through SSH stdin rather than command arguments. Existing `.tmp/verify-public-media.py` is reused unchanged and saves no frames.
- Board `cam/.env`, `.public-migration-backup-20261119T024851Z/{.env,migration.json}`, `server.pid` and current startup log: hold active public configuration, private pre-migration rollback point and runtime state.
- Board `~/.ssh/carstream_tunnel_ed25519{,.pub}`, `~/.ssh/carstream_cloud_known_hosts`, `~/.config/systemd/user/carstream-tunnel.service` and its default.target.wants link: provide the new pinned tunnel identity and enabled service; linger is enabled for linaro.
- Cloud `/home/carstream-tunnel/.ssh/authorized_keys`, `/opt/carstream/private/public-access.env`, `/opt/carstream/config/backend-ready` and `/opt/carstream/private/migration-20261119T024851Z/`: select the new board/token, gate publication and preserve prior keys/environment/gate marker. Existing proxy, TURN and unrelated services are not redeployed.
- Board README/deployment/decision/progress copies are synchronized without deleting unrelated files or uploading private local diagnostics.

Rollback, not executed: first run `ssh company 'rm -f -- /opt/carstream/config/backend-ready'`. Then on the new board run `systemctl --user disable --now carstream-tunnel && cd ~/magnet_car_project/cam && ./stop.sh && cp -p .public-migration-backup-20261119T024851Z/.env .env && ./start.sh`, after checking for later edits. This returns to the private real camera/latest runtime with the same token. If intentionally returning to the old board, restore only the cloud authorized_keys/public-access.env from /opt/carstream/private/migration-20261119T024851Z after checking newer changes; keep the public gate closed until that board is reverified. Do not automatically restore the saved gate marker, delete user files, remove libraries or disable linger if later services depend on it.

## 2026-11-19 - Task: Diagnose board Firefox black video and repair false stall detection

### What was done

- Followed the report that even the board browser had no picture; obtained separate permission to operate the actual board Firefox and then to repair, test and deploy only its player progress detection. Distinguished rejected localhost Origin from public playback instead of treating native-client success as browser acceptance.
- Reproduced the player reporting `Video stopped advancing` despite visible camera video. Replaced its unconditional reliance on the live MediaStream playback-quality counter with actual presented-frame callbacks. Kept the stall threshold, backoff, pause/autoplay handling and real-freeze recovery. Older browsers fall back to a positive quality counter or playback time; that fallback alone cannot strictly prove incoming frames.
- Backed up and atomically replaced only the board's static player, refreshed its public Firefox page and connected through the ordinary password field. No Python service restart, environment/credential change, reduced resolution/bitrate, browser package installation, camera/network change or cloud deployment. App PID 28252 and tunnel remain running; no commit or push.
- Updated existing recovery guidance and decision facts rather than creating another decision for the same mechanism. Removed the task-created scoped screenshots from the board and Mac after inspection; unrelated tabs, files and the user's image attachment are not modified.

### Testing

- PASS regression reproduction: the two added zero-counter tests failed against the old player (8 pass, 2 fail). After the fix, all ten tests pass with `node --test tests/player.test.cjs`; JavaScript syntax checks pass for both edited JavaScript files. Tests exercise advancing presentation with zero quality count, real presentation freeze despite an advancing clock, cancellation and late-callback isolation, and legacy playback-time fallback, alongside existing recovery cases.
- PASS real Firefox evidence: post-deployment presentation count increases from 369 at 19.725351 seconds to 1458 at 77.543038 seconds while `getVideoPlaybackQuality().totalVideoFrames` stays zero. Metrics were read from the actual Firefox window title after a short console expression, then the original title restored and toolbox closed. Earlier clipboard-based probes could return stale text or incomplete input; they are not used as fresh repeated samples or decoder-stat evidence.
- PASS limited session observation: nine samples spanning 80 seconds keep the same RTSP connection (local port 46606) and unchanged log size 16460. This is not a long-term stability or decoded-frame-gap test. Independent external native testing earlier in this investigation delivered 1224 real 2304x1296 frames over 60 seconds, max gap 0.794 seconds, passing its unchanged two-second threshold; it did not prove Firefox rendering.
- REMAINING FAILURE: at 03:37:00-04 UTC the production log records `rtspsrc` resource errors 9 and 7 and subsequent automatic recovery. The final successful Firefox samples are from the recovered session. This player compatibility repair does not establish the camera/transport root cause, eliminate every reconnect or pass long-term continuous playback.
- PASS deployment integrity: local, board and strict certificate-verified public player SHA-256 is a0c659e0e6431e5d22ade8522f9cf38cbf508a6f149db70950d9aa621abcd082; pre-deployment hash is a529f7cc30083246aea911d6294f8f7ca42401e020c1703a5f30db9eff14a567. The user's initializer, config.py and media.py hashes still match the preserved values, process cwd/PID match the release, and the tunnel is active. Existing exact public Origin remains enforced; localhost WebSocket rejection is not bypassed.
- PASS focused Ruff on the three Python diagnostics, eleven existing note tree/link and format checks, and `git diff --check`. IDE ReadLints is unavailable in the current tool catalog, so no additional IDE lint result is claimed. Node tests use a simulated browser; actual Firefox evidence is reported separately above.

### Notes

- `carstream/static/player.js`: tracks session-scoped presented frames, cancels callbacks on teardown and handles zero legacy counters without disabling freeze recovery.
- `tests/player.test.cjs`: adds two focused regressions reproducing false Firefox stalls and verifying cleanup, true stalls and legacy fallback.
- `README.md`: updates the test count and explains the Firefox compatibility repair without claiming RTSP stability.
- `docs/deployment.md`: records public-versus-localhost access, browser evidence, independent RTSP errors, exact deployed hashes, backup and static-only rollback.
- `docs/decisions/implemented/feature/2026-11-17-player-recovery.md`: synchronizes the existing recovery mechanism, compatibility limits and evidence; no new topology or security decision.
- `progress.md`: appends this task's implementation, validation limits and rollback inventory; previous records remain unchanged.
- Ignored `.tmp/check-board-browser-session.py`, `.tmp/inspect-board-firefox.py`, `.tmp/operate-board-firefox.py` and `.tmp/read-diagnostic-image.swift`: contain bounded profile inspection, an unsuccessful accessibility probe, authorized Firefox operation/metrics and local OCR. Private tokens are loaded at runtime, never embedded in diagnostic source or console expressions. The two generated local screenshot files and their two board cache copies were deleted after use.
- Board `cam/carstream/static/player.js` and `cam/.firefox-player-backup-20261119T033100Z/player.js`: contain the tested deployed player and exact prior version. Documentation and regression-test copies are allowlisted for synchronization; no private diagnostics or unrelated files are uploaded.

Rollback, not executed: after checking for newer edits, run on the board `cd ~/magnet_car_project/cam && cp -p .firefox-player-backup-20261119T033100Z/player.js carstream/static/.player-rollback.js && mv carstream/static/.player-rollback.js carstream/static/player.js`, then refresh the browser. No service restart or environment change is needed. This restores the old Firefox false-stall risk, not private localhost access. Documentation/test changes can be manually reversed using the six-file inventory above, preserving unrelated work and all historical progress entries.

## 2026-11-19 - Task: Attempt domain HTTPS cutover; stop at public ICP filing block

### What was done

- Inspected the user's proxied `carstream.8259200.xyz` record and confirmed Cloudflare DNS. Explained that ordinary Cloudflare proxying does not support the existing 7777 port; the user selected standard HTTPS 443 and authorized preserving the separate existing 443 business while adjusting that entrypoint.
- Inspected the existing TCP passthrough listener and current isolated project proxy. Backed up their configurations and private environment under `/opt/carstream/private/domain-20261119/`. Prepared private ACME account/domain keys and CSR, and temporarily installed only a hostname-specific HTTP challenge route. Used isolated acme-tiny 5.0.3 without changing project dependencies or system packages.
- Two direct ACME exchanges failed with network timeouts. A temporary loopback-only SSH forward to the existing local proxy allowed the exchange to reach domain verification; Let's Encrypt then received HTTP 403. A separate public request returned an Alibaba Cloud HTML page titled `Non-compliance ICP Filing`. Stopped the cutover rather than changing ports, Host headers or transport to evade the observed filing block. The actual account/filing status remains unverified in the cloud console.
- Removed the task-created HTTP include and challenge files, validated/reloaded system Nginx and stopped the task-owned temporary forwarding process. Deleted undeployed local Nginx drafts and restored only this task's local template edits. No live 443 routing, domain certificate, renewal service, board environment, token, player, media setting, browser trust or application Origin change was activated. No application/proxy/TURN restart, commit or push.

### Verification and limitations

- PASS preparation/cleanup: local challenge response was 200. The existing cloud project proxy configuration, separate 443 configuration and private environment match their backups byte-for-byte after cleanup. The original 443 master/worker still own that port; temporary port 18790 is no longer listening. Project proxy and TURN containers retain their original uptime. Both the private backend and original public `/healthz` returned 200/alive; the public check used strict validation against the existing pinned certificate. Documentation-only `git diff --check` passes; no application tests were rerun because production source is unchanged.
- BLOCKED public validation: some Cloudflare requests and origin ACME log entries returned 200, but the certificate authority received 403 and independent public retrieval exposed the filing-block page. Local success is not public acceptance; no valid domain certificate was issued and no retry after that policy response was attempted.
- NOT VERIFIED: domain HTTPS application access, browser token submission, real media playback or resolution of the previously reported post-restart interruptions. The active endpoint remains `https://8.130.208.68:7777` with its original self-signed certificate and exact IP-based Origin.

### Artifacts and next step

- `docs/deployment.md`: records the unsuccessful domain cutover, evidence, cleanup, retained private artifacts and requirement to resolve filing/access status with Alibaba Cloud.
- `progress.md`: appends this attempt without rewriting previous entries. No new architecture decision was implemented, so existing decision notes remain unchanged.
- Ignored `.tmp/configure-domain.py` and `.tmp/acme-client/`: retain one-off provisioning/cleanup code and isolated ACME tooling; do not blindly rerun preparation. Private values are never embedded in tracked files.
- Cloud `/opt/carstream/private/domain-20261119/`: retains mode-restricted backups, ACME account/domain keys, CSR and client. No certificate from this attempt is installed. Temporary `/etc/nginx/conf.d/carstream-domain.conf` and task-created challenge files were removed.

Next step: confirm and resolve the domain's filing/access state through Alibaba Cloud, then revalidate public access before resuming certificate issuance and the separately authorized standard-443 cutover. Do not describe this attempt as a working domain deployment.

## 2026-11-19 - Task: Switch the dedicated public entrypoint to HTTP after explicit risk acceptance

### What was done

- Followed the user's decision to abandon domain/HTTPS setup. Explained that HTTP exposes the access token, TURN credentials, page and signaling to observation/tampering; obtained explicit acceptance before changing this authentication transport. First checked Cursor at the real public HTTP IP origin: receive-only WebRTC offer creation works despite a non-secure context, so a blanket claim that HTTP cannot play this receiver would be incorrect.
- Backed up exact board/cloud private settings and existing proxy configuration. Closed the backend-ready gate, validated the staged configuration, changed only the isolated 7777 listener to HTTP and its forwarded scheme to `$scheme`, and reloaded that proxy. Synchronized exact `http://8.130.208.68:7777` Origin in board/cloud private settings. Restarted only this application through guarded scripts: PID 43155, log `log/carstream-20261119T063230.126057786Z.log`. Validated access boundaries before reopening the gate.
- Preserved the original token, strong-token enforcement, authentication-before-media, exact-origin check, allowlisted routes, request limits, source/player code, 2304x1296 original quality profile, latest isolated MPP/plugin and existing TURN/TCP relay. The tunnel remained active. No change to unrelated 443, firewall/routing, camera, dependencies, browser trust/settings or boot policy; proxy/TURN containers were not restarted. The former certificate is retained unused for rollback.
- The user entered the existing token directly into Cursor and clicked Connect; no real token was posted to chat or browser-tool arguments. Measured actual presentation and receiver statistics without saving camera images. Removed temporary diagnostic callbacks, unlocked the browser and left playback running. Updated current access/security guidance, retained historical TLS rationale and linked the new explicit exception. No commit or push.

### Testing

- PASS configuration and boundaries: staged/live Nginx tests using the correct `/etc/carstream/nginx.conf`; gate returns 503 while closed; missing, foreign, old HTTPS and old localhost Origins return 403. Empty/invalid tokens return `Invalid access token`; unchanged valid token returns RTSP ready with relay policy. External `/`, `/healthz`, `/player.js` return 200/no-store; `/.env` returns 404. External player checksum matches the unchanged source.
- PASS actual Cursor HTTP rendering: non-secure HTTP page presents real 2304x1296 RTSP video with relay/relay candidates. Initial sample at playback time 28.865 seconds had 575 decoded/562 presented frames. A 90.0002-second observer starting 06:35:27 UTC recorded 1658 presentation callbacks and no session changes; player samples advanced from 1113 to 2751 presented frames. A later same-session sample at playback time 165.871 seconds had 3314 decoded/3152 presented frames. This is actual receiving/presentation evidence, not merely connected state.
- FAIL unchanged two-second presentation-continuity criterion: maximum observed presentation-callback interval was 5.6754 seconds. Browser inbound stats separately report three freezes totaling 0.888 seconds; callback timing, decoder freezes and network gaps are different measurements and do not establish a common root cause. No original stall/disconnection fix, long-term reliability or other-browser pass is claimed from this transport switch.
- PASS local regressions: `node --test tests/player.test.cjs` has ten passes; Python unittest discovery has nineteen passes and eight Linux-only lifecycle skips on macOS. No new low-value test was added for a two-directive deployment change. Final environment comparison finds only `CARSTREAM_PUBLIC_ORIGIN` changed; token equality, user initializer/config/media/player hashes, latest loaded runtime and active tunnel are unchanged. Cloud proxy matches the tracked template; unrelated 443 configuration matches its saved hash.
- PASS focused Ruff for the private switch script after removing its unused import, twelve-note tree/link/format/archive checks, and whitespace validation. IDE ReadLints reports zero diagnostics but totalFiles=0, so it adds no substantive lint coverage. Prepared and implemented note states were handled in the same task; the earlier TLS decision was not rewritten into its opposite.

### Notes

- `deploy/cloud/nginx.conf`: removes TLS from only the existing 7777 listener and forwards the actual HTTP scheme; retains gate, limits and route restrictions.
- `README.md`: updates current HTTP URL, unchanged token usage, security warning and measured playback boundary.
- `docs/deployment.md`: adds the authoritative HTTP cutover, explicit risk acceptance, exact evidence, private backups and executable HTTPS rollback.
- `docs/decisions/implemented/architecture/2026-11-19-public-http.md`: records the confirmed transport exception, real alternatives, security loss, browser evidence and audit of existing notes; temporary proposed copy was removed after implementation.
- `docs/decisions/implemented/architecture/2026-11-18-public-access.md`: links the new transport exception while preserving its original TLS rationale and still-valid tunnel/TURN constraints.
- `progress.md`: appends this task's work, checks, limitations and rollback inventory without editing earlier entries.
- Ignored `.tmp/switch-public-http.py` and `.tmp/http-cutover-stamp`: hold the one-off backup/activation/boundary/integrity diagnostic and task timestamp. The existing private helper is reused; no secrets are embedded in diagnostic source.
- Board `cam/.env`, `cam/.http-cutover-backup-20261119T063030Z/{.env,integrity.json}`, PID and startup log: select exact HTTP Origin, preserve pre-task settings/source hashes and record the restarted application. Cloud `/opt/carstream/config/nginx.conf`, private `public-access.env`, gate and `/opt/carstream/private/http-cutover-20261119T063030Z/`: hold HTTP proxy/Origin, publication state and prior private settings/configuration.

Rollback, not executed: after checking for subsequent private edits, close the cloud gate with `ssh company 'rm -f /opt/carstream/config/backend-ready'`; on the board run `cd ~/magnet_car_project/cam && ./stop.sh && cp -p .http-cutover-backup-20261119T063030Z/.env .env && ./start.sh`. Restore cloud `nginx.conf` and `public-access.env` from `/opt/carstream/private/http-cutover-20261119T063030Z/` to their original paths, then run `docker exec carstream-proxy nginx -t -c /etc/carstream/nginx.conf && docker exec carstream-proxy nginx -s reload -c /etc/carstream/nginx.conf`. Verify privately the restored exact HTTPS Origin/token boundaries, then restore the saved gate marker and check HTTPS with the original certificate pin. Full commands are in the new deployment section. Keep gate closed on any failure; this restores self-signed HTTPS, not the abandoned domain. Preserve all historical progress entries.

## 2026-11-19 - Task: Reproduce intermittent Cursor blackouts and repair false playback teardown

### What was done

- Continued investigation at the current HTTP public endpoint without restarting the application or reducing quality. Correlated session stop reasons, actual receiver decode/packet counts, presentation callbacks and small numeric brightness samples with sanitized board/proxy/tunnel diagnostics. No camera frames, pixel arrays, private credentials or raw native logs were retained or published.
- Reproduced a false-stall loop: video continued decoding but presentation callbacks stopped, so the player cleared its stream and retried with progressively longer delays. Added actual inbound video decoded-frame progress as a second signal. Retained the existing roughly fifteen-second true-stall recovery, pause/autoplay exclusions, capped retry and token behavior. Serialized asynchronous statistics checks and rechecked session identity/connection after completion; missing statistics preserve presentation-based detection. Growing bytes or playback time cannot conceal a decoder freeze when presentation callbacks are available.
- Backed up and atomically deployed only the static player at 07:00:38 UTC. Application PID 43155, media/config/user initializer, original 2304x1296 quality, private settings, cloud HTTP proxy, TURN, network and native libraries remain unchanged. No commit/push or browser security exception. Updated the existing player decision rather than creating a new decision for the same recovery mechanism; preserved prior uncommitted HTTP/domain-task changes.
- Activated the new monitor in the existing Cursor tab through direct DevTools function replacement and initialization of legacy session fields, retaining the token only in its existing password input. An attempted evaluation of the fetched source was blocked by CSP after stopping that test session; resumed with direct DevTools evaluation without changing CSP. This is an active-tab monitor check, not full-script clean-reload acceptance. Other open viewing pages must refresh and Connect to load the deployed player.
- Removed both bounded observers, numeric sample buffers, timers and the one-shot diagnostic close listener; unlocked Cursor and left playback running. Final 07:12:19 UTC snapshot is connected at 2304x1296 with 8164 monitor-decoded and 2774 presentation frames in the recovered session. No later close code was captured before cleanup.

### Testing

- PASS reproducible regression: three targeted Node cases were added; two failed against the prior player (eleven pass, two fail). After repair all thirteen pass with `node --test tests/player.test.cjs`. Coverage includes suppressed callbacks with continuing decode, a real decoder freeze despite receiving bytes/advancing playback time, statistics failure fallback, read deduplication and stale-result isolation. Existing retry, pause, autoplay, token, timeout and teardown checks remain passing.
- BEFORE real Cursor: observation from 06:53:12 UTC collected 301 samples over approximately 300 seconds, eight `Video stopped advancing` teardowns, nine sessions and 159 samples without an attached stream. One session decoded 30 to 328 frames and received 487014 to 3330998 bytes while its presentation counter remained zero and numeric brightness stayed around 121/255. This proves a player-induced blackout path, not that camera/network transport was failing during those false stalls.
- AFTER real Cursor: 300.7333 seconds from 07:01:57 UTC contains zero false-stall teardowns, two sessions and one sample without an attached stream. The first session decodes 509 to 4685 frames; the second 14 to 1770. No sampled decoded image exceeds 98% near-black pixels. Dimensions stay 2304x1296 and selected candidates are relay/relay. Decoder progress and sampled brightness are not proof of uninterrupted screen composition, and this is not a two-second frame-gap or long-term reliability pass.
- REMAINING FAILURE: one actual `Signaling connection closed` occurs at 209.3097 seconds while decode was still advancing in the preceding sample. Automatic recovery receives video again by 212.7316 seconds, approximately 3.42 seconds later. Its initiator/root cause was not captured by the initial observer. The absence of false-stall disconnects does not mean all blackouts are fixed; browser-reported short freezes also remain.
- PASS bounded infrastructure checks: board has no `Viewing session failed` entry, same process and protected source hashes, one camera connection and active tunnel. At 07:08 UTC tunnel PID 39463 still starts at 05:26 UTC; its NRestarts=2 is historical, with zero journal entries since 06:50. Proxy container has its original start time, zero restarts and no recent log output; gate remains open. These negative logs do not establish a network or heartbeat root cause. Server heartbeat/authentication/packet behavior was not changed.
- PASS static deployment integrity: local, board and external public player SHA-256 is `478470b1e549f736dc28a8284388c288934f99786ca35df752ca8ae163576bfe`; exact previous version is `a0c659e0e6431e5d22ade8522f9cf38cbf508a6f149db70950d9aa621abcd082`. Python unittest discovery passes nineteen tests and skips eight Linux-only lifecycle cases on macOS. JavaScript syntax checks, scoped diagnostic Ruff, twelve-note tree/link/format/archive checks and whitespace validation pass. IDE ReadLints returns zero diagnostics with totalFiles=0 and adds no substantive coverage. Initial pytest/acceptance-venv Ruff attempts found no such tools; verification used the existing unittest and root .venv Ruff instead, without installing dependencies.

### Notes

- `carstream/static/player.js`: cross-checks actual decoded video progress, prevents overlapping reads and isolates late results without changing signaling/authentication or media.
- `tests/player.test.cjs`: adds three focused regressions for the reproduced false teardown and asynchronous receiver-statistics boundary.
- `README.md`: updates the thirteen-test result and current recovery behavior, keeping all-blackout and continuity limitations explicit.
- `docs/deployment.md`: records before/after evidence, the separate real WebSocket close, deployment checksum/backup, active-tab verification limits and static-only rollback.
- `docs/decisions/implemented/feature/2026-11-17-player-recovery.md`: synchronizes the existing decision with actual decode cross-checks, rejected clock/byte/threshold alternatives and screen-composition limits.
- `progress.md`: appends this implementation, verification, remaining failure and rollback inventory; historical entries remain unchanged.
- Ignored `.tmp/check-blackout-runtime.py`, `.tmp/check-blackout-signaling.py` and `.tmp/deploy-blackout-player.py`: provide bounded sanitized diagnostics and a hash-guarded one-off static replacement, reusing existing SSH helpers without embedding secrets. Do not rerun deployment blindly after later edits.
- Board `cam/carstream/static/player.js` and `cam/.blackout-player-backup-20261119T070038Z/player.js`: contain the deployed new static player and exact prior version. No other board/cloud configuration or application files were written in this task.

Rollback, not executed: after checking for subsequent edits, run `ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && cp -p .blackout-player-backup-20261119T070038Z/player.js carstream/static/.player-rollback.js && mv carstream/static/.player-rollback.js carstream/static/player.js'`, then refresh viewing pages. This restores the known false-stall defect; it does not roll back HTTP or fix the separate signal close. For local source/test rollback, use `git restore --source=HEAD -- carstream/static/player.js tests/player.test.cjs` only after confirming these files have no later changes; manually reverse just this task's documentation paragraphs and preserve all prior HTTP/domain edits and append-only progress history.

## 2026-11-19 - Task: Extend blackout investigation and deploy explicitly approved close diagnostics

### What was done

- Continued real Cursor observation at the current HTTP endpoint without changing picture quality, camera, network, TURN, browser security or timeouts. Correlated receiver/presentation counts, close events and sanitized infrastructure state. Two bounded cloud TCP metadata captures collected no application payload or pcap; the board had no tcpdump/noninteractive sudo, so nothing was installed or escalated. Completed both captures; no capture remains running.
- Identified and reproduced an observability gap: aiohttp's missing-PONG timeout can end a session without the old warning log. This does not identify the cause of the earlier production signaling close. Obtained explicit user approval to add only close diagnostics and perform one guarded application restart, preserving authentication, heartbeat, media and recovery behavior.
- Added a per-created-session INFO exit summary before active cleanup: completed task names, original close code, socket/handler exception class and duration. No raw exception/close text, token, SDP, ICE, URL or client address is added to application logs. Reused the existing architecture note for these control-layer diagnostics rather than creating another decision.
- Backed up and atomically deployed only server.py, then performed exactly one guarded stop/start at 07:30:18 UTC: PID 43155 to 44139, log `log/carstream-20261119T073018.503817000Z.log`. Private environment, initializer, media/config and repaired player match the pre-deployment manifest. The existing watching page recovered without entering the token again; no secret crossed tool arguments or browser storage. No cloud configuration, dependency, commit or push change.
- Removed bounded browser observers/listeners/sample buffers and unlocked Cursor, leaving real playback running. Final 07:39:13 UTC sample is connected at 2304x1296, relay/relay, 8468 monitor-decoded and 4686 presentation frames in the recovered session. This task deploys evidence collection, not a newly proven root-cause repair.

### Testing

- PASS bounded pre-deployment real Cursor check: 600.0014 seconds, 601 samples, one session, zero close events/false-stall teardown/missing-stream samples. Decode grows 3633 to 15623 and presentation count 3514 to 13636; browser freeze metrics still grow by 32 freezes totaling 8.712 seconds. No-disconnect is not uninterrupted playback, an unchanged two-second frame-gap pass, or proof the historical real close is fixed.
- PASS limited transport observation: first 180-second loopback capture records no FIN/RST on active 17777; second 180-second metadata capture shows eight two-byte backend/six-byte client exchanges at roughly 21-second intervals and 40-50 ms return timing, consistent with healthy heartbeat traffic in that interval. Payloads were not decoded. Unrelated public HTTP FIN/RST packets are not treated as player disconnects. Tunnel PID 39463/start time 05:26 UTC and historical NRestarts=2 remain unchanged, with no recent journal entries. Proxy has its original start time, zero restarts and no recent error output.
- PASS diagnostic regressions: both added tests fail against the old server due to missing summaries. Final local unittest discovery runs 29 tests: 21 pass and 8 Linux-only lifecycle tests skip; all 13 player tests pass. All 9 signaling tests also pass isolated under board Python 3.10/aiohttp 3.14.5, without production camera or heartbeat changes. Early assertions incorrectly required a completed receive task despite aiohttp TestServer request cancellation, and assumed numeric IntEnum formatting on Python 3.10; corrected the tests/reader to accept the actual cancellation race and equivalent abnormal enum code. No second production restart was required.
- PASS intentional viewer recovery and production logging: at 07:32:05 UTC only this Cursor viewer is closed with code 1000; browser reports clean/1000 and server summary reports signaling-receive, code 1000, socket_error=none, failure=none, duration 106.7 seconds. The subsequent 360.0006-second observer contains only that intentional close, no spontaneous or false-stall close. Actual presentation/decode resumes by 21.5567 seconds, about 4.11 seconds after injection; recovered session reaches 6780 decoded/3035 presented frames. Two no-stream samples belong to controlled recovery. Thirteen browser freezes totaling 3.283 seconds remain in that recovered session.
- PASS deployment/boundaries: deployed server SHA-256 is `c51e6a5f864d0370f71214550853526264a05ac3a30be4228865a620e460e7fe`, matching local source; protected files/environment match backup. Final process/cwd, one camera connection, active tunnel and open cloud gate are verified; public health returns alive and foreign Origin still returns 403. Scoped Ruff, twelve-note tree/link/format/archive checks and whitespace checks pass. IDE ReadLints has zero diagnostics but totalFiles=0 and adds no substantive coverage.
- REMAINING BLOCKER: the earlier spontaneous real signaling close did not recur during these bounded observations with the new server diagnostics. Its initiator/cause and the remaining short freezes are not established. The missing-PONG regression proves logging behavior only, not that the production incident was a heartbeat failure. No speculative timeout, bitrate, retransmission or session-protocol modification was made; neither complete-blackout resolution nor long-term stability is claimed.

### Notes

- `carstream/server.py`: names existing session tasks and records sanitized close evidence before cleanup, without changing protocol, authentication or termination/retry decisions.
- `tests/test_server.py`: adds normal-close and missing-PONG diagnostic regressions, including token non-disclosure and Python-version-compatible abnormal-code validation.
- `README.md`: updates current test counts, extended observation boundary and the deployed close-diagnostic reference while retaining unresolved stability status.
- `docs/deployment.md`: records explicit approval, diagnostic schema/limits, exact deployment, before/after observations, intentional versus spontaneous close, private backup and executable rollback.
- `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md`: updates the existing control-layer boundary with sanitized exit diagnostics and rejects raw logging or unsupported timeout changes.
- `progress.md`: appends this task and its verification/remaining gap without altering prior records or unrelated uncommitted HTTP/player work.
- Ignored `.tmp/trace-signaling-close.py` and `.tmp/inspect-signaling-library.py`: perform bounded metadata-only capture/capability checks and actual installed heartbeat/TCP inspection.
- Ignored `.tmp/deploy-close-diagnostics.py` and `.tmp/verify-close-diagnostics.py`: implement a hash-guarded single-file deployment/one restart, isolated board test execution and allowlisted log/integrity summaries. They embed no secrets; do not blindly rerun deployment after subsequent edits.
- Board `cam/carstream/server.py`, `.close-diagnostics-backup-20261119T073017Z/{server.py,integrity.json}`, PID and new startup log: hold the deployed diagnostics, exact prior source/protected-file digests and controlled restart evidence. Regression tests are executed from in-memory source, not copied over unrelated board files.

Rollback, not executed: after confirming no subsequent source edits and accepting another brief interruption, run `ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && ./stop.sh && cp -p .close-diagnostics-backup-20261119T073017Z/server.py carstream/.server-rollback.py && mv carstream/.server-rollback.py carstream/server.py && ./start.sh'`. This removes diagnostics only, preserving the HTTP origin, current player and private settings. Local server/test source can be restored from HEAD only after checking for later edits; reverse just this task's documentation paragraphs manually, preserve all prior task changes and retain append-only progress history. Minimal next diagnostic action is to correlate the next spontaneous close's time/status with the retained server summary; no unattended observer remains running.

## 2026-11-19 - Task: Localize and simplify the public video interface

### What was done

- Changed the page title, access-token label, start/stop buttons, connection states, recovery countdown and error prompts to Simplified Chinese.
- Removed hardware/protocol descriptions, the ordinary camera-source label and the explanatory footer. Kept the access token, necessary viewing controls, connection status and explicit test-video warning.
- Published only the three static files to the existing HTTP entrypoint. The running application PID was 44476 before and after this deployment; no restart, token change, media/network change or recovery-timing change was performed. Existing source changes were preserved.
- Documented how to refresh and reconnect, the unchanged security/stability boundaries and the static-only rollback point.

### Testing

- `node --test tests/player.test.cjs`: 14 passed, including Chinese error prompts, test-source visibility and the existing recovery/backoff/stop behavior.
- `node --check carstream/static/player.js` and `node --check tests/player.test.cjs`: passed.
- `.venv/bin/python -m unittest discover -s tests -q`: 21 passed, 8 Linux-only checks skipped on macOS.
- `git diff --check`: passed. IDE ReadLints returned no diagnostics but reported zero checked files; this is not additional lint coverage.
- All three public static responses matched the corresponding local SHA-256 values. Public `/healthz` returned `{"status":"alive"}`. Protected board configuration, initializer, server and media sources were unchanged during deployment.
- Loaded the public Chinese page in a separate Cursor tab without reloading the existing viewer or copying its token. At 574 px and an emulated 375 px width, document width matched viewport width and the ordinary source label was hidden. The supplied screenshots confirm the Chinese initial interface; the empty video belongs to the displayed unconnected state, not a reproduced playback blackout. Emulation was cleared and the tab unlocked afterward.
- No fresh real-camera continuity acceptance was performed. Earlier unresolved intermittent freezes and signaling-close evidence remain unchanged by this UI-only task.

### Notes

- `carstream/static/index.html`: uses `zh-CN` and the minimal Chinese viewing form, with the test-source placeholder initially hidden.
- `carstream/static/player.js`: translates displayed states/errors without changing protocol strings, authentication decisions, video monitoring or recovery timing.
- `carstream/static/style.css`: removes the style rule for the deleted explanatory text.
- `tests/player.test.cjs`: updates affected status expectations and checks that only a test source shows the Chinese source warning.
- `README.md`: updates current button instructions and the JavaScript test count.
- `docs/deployment.md`: records this static deployment, refresh procedure, verification limits and executable rollback.
- `progress.md`: appends this task without rewriting prior records.
- Ignored `.tmp/deploy-chinese-interface.py`: performs hash-guarded static deployment, backups, PID/protected-file checks and public-response verification without exposing secrets; do not rerun blindly after later changes.
- Board `cam/carstream/static/{index.html,player.js,style.css}` and `.chinese-interface-backup-20261119T075853Z/`: contain the deployed interface and exact pre-task static copies, including the prior false-stall fix.

Rollback, not executed: first confirm no later static edits, then run `ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && for filename in index.html player.js style.css; do cp -p ".chinese-interface-backup-20261119T075853Z/$filename" "carstream/static/.ui-rollback-$filename" && mv "carstream/static/.ui-rollback-$filename" "carstream/static/$filename" || exit 1; done'`. No restart is needed; reload affected pages afterward. For local rollback, reverse only this task's Chinese interface/test/documentation edits, preserving earlier uncommitted player/server/HTTP changes; retain this append-only record. Do not restore the player wholesale from HEAD because that would discard earlier repairs.

## 2026-11-19 - Task: Remove the leftover UI verification query from the displayed address

- User repeatedly requested a plain IP-and-port URL. Earlier replies explained the query but did not remove it from old links. The player now removes only the retired `ui` marker on load with `history.replaceState`, preserving other query parameters, fragments and history state without navigation or automatic connection.
- Added a focused Node regression: it fails before the cleanup and passes afterward. All 15 player tests and both JavaScript syntax checks pass. Existing token submission, playback monitoring and recovery behavior remain unchanged.
- At 08:07:21 UTC, backed up and atomically replaced only the board's `carstream/static/player.js`. PID 44476 did not change. Private environment, user initializer, server diagnostics, media/config sources, HTML and CSS hashes remained unchanged during deployment. No restart or cloud configuration change was performed.
- Public `/player.js` matches local SHA-256 `ab2afdcb4eaa32acfb2ce794bd106042a96c6dd49e64276b9a8c114371a4a699`; plain root returns HTTP 200 and `/healthz` reports alive. Browser tools are unavailable in this turn, so no current tab was manipulated and no live address-bar verification is claimed. Already open pages need one reload to run the new script.
- Changed files: `carstream/static/player.js`, `tests/player.test.cjs`, `README.md` (current test count), `docs/deployment.md` (deployment/limits), the existing player-recovery decision (non-navigating cleanup rationale), and this append-only log. Ignored `.tmp/deploy-clean-page-url.py` holds the hash-guarded deployment/public checks without credentials.
- Rollback, not executed: after checking for subsequent player edits, run `ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && cp -p .clean-url-backup-20261119T080721Z/player.js carstream/static/.player-url-rollback.js && mv carstream/static/.player-url-rollback.js carstream/static/player.js'`. No restart is needed. This preserves the earlier Chinese interface and false-stall repair; do not restore an older player wholesale from HEAD. No new media-stability claim is made.

## 2026-11-19 - Task: Narrow intermittent playback failures using bounded sender, relay and receiver diagnostics

### What was done

- Correlated real browser video counters with retained sanitized server close summaries. Reproduced genuine complete-frame/decode stagnation while media bytes continue and signaling/WebRTC remain connected; the later observed disconnects are deliberate player stall recovery, not proof of a spontaneous signaling fault.
- Checked the camera/codec/payloader path, live encrypted RTP headers at the cloud relay, and an independent full-quality WebRTC receiver. Added four ignored, bounded local helpers; no production source, private configuration, camera settings, network settings, dependencies, quality, recovery thresholds or service state was changed.
- Observed both keyframe requests arriving upstream and real IDR output. Rejected an unsupported diagnosis that the encoder never emits keyframes. Source-only packet-offset/partition concerns are recorded as unproven, not patched.
- Removed the bounded browser sample observers. Stopped the assistant's redundant old English viewer to reduce test load, leaving the Chinese viewer watching. Browser tools disappeared before the old viewer could be resumed and the two tab locks released; final browser cleanup/unlock could not be verified. No token, image or raw signaling data was exported.
- Recorded evidence and its limitations in the existing deployment document. The precise trigger for missing/rejected complete pictures remains unresolved; this is not a root-cause repair or a continuity acceptance.

### Testing

- REPRODUCED browser stall at 08:22:27-08:22:44 UTC: received/decoded frames stay at 1500, decoded keyframes at 50, bytes rise from 14728663 to 18182524 and PLI requests from 7 to 81. Earlier browser closes are clean/1000 after about 16 seconds without progress, aligned with server receive-task exits without socket/handler exceptions. The jitter-buffer emitted counter is not interpreted as successful decoder input.
- PASS limited upstream framing check: an 80.07-second local-sink pipeline produces 1598 frames and RTP tail markers, with no observed sender sequence gaps, timestamp anomalies or bus failure. This bypasses WebRTC/TURN and does not validate payload integrity or full delivery.
- LIMITED cloud header observation: 75.03 seconds includes primary timestamp/marker progress for the exact browser SSRC during its stall, without later primary sequence discontinuities after startup. Encrypted payloads are not validated. A later 50.03-second per-flow capture overlaps only the beginning of another paired test, counts 307 skipped primary sequence numbers including startup discontinuities, and has zero reported kernel capture drops. It is not an all-window sender/client correlation or proof of a network loss percentage.
- LIMITED paired full-quality WebRTC test: at 80.06 seconds the sender has 1598 encoded frames, 54 IDR starts, 87 upstream keyframe requests and 5142 generated RTX packets; the independent receiver has 617 decoded frames, 6085 primary packets and 2739 RTX packets. Sender pre-negotiation packets and non-aligned snapshots prohibit treating aggregate differences as a measured network loss rate. A later 45-second bounded run reaches 754 decoded frames at 40.34 seconds without reproducing the long Chrome freeze. Both diagnostics exit zero and release their isolated sessions, but neither is a Chrome frame-assembly test.
- FAILED/INCONCLUSIVE attempts retained as such: initial independent clients encounter sanitized RTSP resource/read errors; a later wrapper attempt has a corrected `srtp_profiles` argument mismatch; another receiver decodes 875 frames before its media track ends and exits nonzero. None is counted as a continuity pass. Additional camera readers may confound comparisons, but their errors are not established as the browser-stall cause.
- PASS no-deployment/cleanup checks: final 08:45 UTC production PID remains 44476, protected media/config/initializer hashes and deployed player SHA-256 remain unchanged, and the tunnel is active. Cloud `tcpdump` checks confirm no capture process remains. At the resource snapshot there are two camera TCP connections, 46 threads and 215 descriptors; these are observations, not a proven leak or causal diagnosis. Cloud qdisc and UDP-buffer discard counters are zero; the cumulative TCP retransmission count does not localize this incident.
- PASS `node --test tests/player.test.cjs`: all 15 existing tests pass. Scoped Ruff on the four diagnostic helpers passes. No new product tests are added because there is no product repair to validate. IDE ReadLints is unavailable in the final tool set, so no IDE lint coverage is claimed.

### Notes

- `docs/deployment.md`: adds the genuine-frame-stall evidence, failed-test boundaries, unchanged production state, browser cleanup limitation and remaining packet-alignment gap.
- `progress.md`: appends this investigation without rewriting historical records.
- Ignored `.tmp/diagnose-rtp-framing.py`: checks bounded camera-to-payloader counters using a local sink and the running service's environment without printing secrets.
- Ignored `.tmp/diagnose-receiver-framing.py`: measures an independent public receiver and fails promptly on server errors; corrects the diagnostic DTLS wrapper argument only, without verification bypass.
- Ignored `.tmp/diagnose-relay-headers.py`: parses bounded encrypted RTP-header slices in memory, reporting per-flow numeric sequence/timestamp/marker aggregates without saving a packet capture.
- Ignored `.tmp/diagnose-paired-video.py`: observes one isolated sender and receiver together, including IDR starts, upstream keyframe requests and generated retransmissions, with bounded teardown and no production-file edits.

Rollback point: production remains unchanged at PID 44476 and the existing deployed player hash, so no service rollback/restart is required. To discard only the local diagnostic helpers after checking for subsequent edits, run `rm -f -- .tmp/diagnose-rtp-framing.py .tmp/diagnose-receiver-framing.py .tmp/diagnose-relay-headers.py .tmp/diagnose-paired-video.py`; remove only this task's new deployment-document section if desired and retain this append-only record. The old test viewer can be resumed with its existing start-watching control if needed; release any retained diagnostic tab locks through Cursor when browser tools return. The smallest decisive next check is a single isolated viewer with synchronized sender/relay/receiver sequence comparison and receiver discard reasons, not a speculative timeout, codec or bandwidth change.

## 2026-11-19 - Task: Preserve public viewing and add independent authenticated same-board media supply

### What was done

- Implemented the user-confirmed boundary: public playback retains its existing token, exact Origin and TURN relay policy; a separate native-backend listener on `127.0.0.1:8081` authenticates with the same token, requires no Origin header and rejects browser Origins. Its independent media configuration has no STUN/TURN and does not alter source, original quality, native media code or retransmission behavior.
- Enabled the new listener on the board after isolated tests. Backed up exact pre-task sources and private configuration, appended only `CARSTREAM_LOCAL_PORT='8081'`, and restarted CarStream once at 09:33:32 UTC. PID 44476 became 50404, with log `log/carstream-20261119T093332.819779546Z.log`. Cloud proxy, tunnel configuration, TURN, camera, network and dependencies were not changed; the tunnel remains active.
- Documented the WebSocket auth/offer/answer/ICE contract and the handoff boundary: the receiving backend must actually receive WebRTC media, then owns downstream distribution. No third-party webpage URL is required. Docker/container loopback isolation and independent media-session costs are explicitly stated.
- Preserved all prior worktree changes. No commit or push was requested or performed. This feature is not a fix for the earlier intermittent genuine frame stall.

### Testing

- Before implementation, the five new configuration/listener regressions fail on the missing local port support. After implementation the board staging suite passes all 36 tests, including 10 Linux lifecycle checks; local macOS passes 26 and skips those 10. Existing 15 Node player tests pass.
- Two isolated staging checks and the production endpoint check each decode 100 real 2304x1296 frames. Authenticated local ready settings contain no ICE servers and policy `all`; all exchanged candidates on both peers are host candidates. No images or raw signaling were retained. Installed GI bindings do not expose the selected-pair inspection used here, so exact interface selection is not claimed; real decode with only host candidates demonstrates no TURN media path.
- Production public 8080 rejects absent/foreign Origin; local 8081 rejects browser Origin. Wrong tokens are rejected on both. Focused tests also verify auth before media/ICE disclosure, empty token rejection, local answer/candidate processing, unchanged public relay settings, local session release and dual-listener startup/stop.
- The external relay-only native receiver runs 80.31 seconds after deployment, decodes 1566 frames at 2304x1296, stays connected, and records maximum decoded-frame gap 1.046 seconds. It exits zero and releases its session. This verifies current public delivery, not browser rendering or long-term stability.
- Source readback matches deployed config, server, start script and native smoke check. The board initializer, application entrypoint, media source, stop script and player assets match pre-task hashes; original private environment bytes are preserved. Both 8080 and 8081 listeners belong to PID 50404 and bind only `127.0.0.1`.
- Scoped Ruff, Bash syntax, `git diff --check` and all three decision-note validators pass. IDE ReadLints returns no diagnostics but reports zero covered files; no additional IDE lint coverage is claimed.

### Notes

- `carstream/config.py`: adds opt-in `LOCAL_PORT` parsing and distinct-port/range validation.
- `carstream/server.py`: creates the independent local-only app and host-ICE session profile while reusing auth/signaling/cleanup and preserving public Origin rules.
- `start.sh`: checks and waits for both enabled ports, and reports dual-listener readiness without changing PID ownership safeguards.
- `.env.example`: documents the disabled-by-default local port and backend handshake/ICE contract without credentials.
- `tests/test_config.py`: verifies default-off, environment parsing and invalid/conflicting local ports.
- `tests/test_server.py`: verifies local/public trust separation, auth-first behavior, local signaling, public relay preservation and local shutdown release.
- `tests/test_scripts.py`: checks local-port conflicts and unified two-port lifecycle behavior using temporary fixtures.
- `tests/smoke_local_feed.py`: supplies a bounded board-native authenticated receiver that decodes 100 frames, checks host-only ICE and saves no images.
- `README.md`: links the local supply contract, documents `LOCAL_PORT` and updates the verified Python/Linux test counts.
- `docs/local-feed.md`: provides the receiver handoff protocol, configuration, responsibility boundary, container caveat and executable validation command.
- `docs/deployment.md`: records production listeners, actual media checks, preservation guards, limitations and exact rollback.
- `docs/decisions/implemented/architecture/2026-11-19-local-feed.md`: records why an independent listener is required and the rejected global-Origin/relay alternatives.
- Existing `docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md` and `2026-11-18-public-access.md`: link the supplementary local supply decision without replacing the public one.
- `progress.md`: appends only this task's verified results and rollback point.
- Ignored `.tmp/adjust-local-feed.py` and `.tmp/local-feed-status.json`: stage and deploy the approved files with source/hash checks, record sanitized production readback, and never print private credentials. Do not rerun deployment blindly after subsequent changes.
- Board `cam/{carstream/config.py,carstream/server.py,start.sh,tests/smoke_local_feed.py,.env}` and `.local-feed-backup-20261119T093332Z/`: contain the deployed change and exact pre-task rollback copies. Private files remain private; no cloud or user initializer edit was made.

Rollback, not executed: after checking for later edits, run on the board `cd ~/magnet_car_project/cam && ./stop.sh && for filename in carstream/config.py carstream/server.py start.sh .env; do cp -p ".local-feed-backup-20261119T093332Z/$filename" "$filename" || exit 1; done && ./start.sh`. This restores the prior public strong-token configuration, not obsolete weak-token or HTTPS deployment values. To disable only the local capability, set `CARSTREAM_LOCAL_PORT='0'` and restart. Both actions interrupt active viewers. For local source rollback, reverse only this task's local-feed hunks/new documents/tests, preserving earlier uncommitted HTTP/player/diagnostic changes and this append-only record; do not restore entire files from HEAD.

## 2026-11-20 - Task: Persist the user-selected camera network without changing uplink connectivity

### What was done

- Diagnosed missing camera-subnet connectivity after reboot and inconsistent saved static versus generated DHCP configuration. Paused immediately when the user changed the camera connection concurrently; continued only after the user confirmed using `enP3p49s0 / 192.168.11.88`.
- At 02:34:13 UTC, unified the camera's Netplan source and saved/runtime NetworkManager profiles around `192.168.11.88/24`, autoconnect, no IPv4 gateway, never-default and native address-conflict detection. Removed only the camera's unnecessary high-metric default route; USB/Wi-Fi routes and other network profiles remain unchanged.
- Preserved CarStream PID 5220, application and initializer hashes, private environment, public/local authentication settings and player files. Did not restart the board, application, tunnel or whole network service, and did not run global `netplan apply`.
- Reported the separate public Origin mismatch and stopped further operational work when the user said the current result was sufficient. No public authentication change, autostart setup, dependency installation, commit or push was performed for this task.

### Testing

- PASS offline original/candidate Netplan generation: only the approved `enP3p49s0` profile differs; `enP2p33s0` output remains byte-identical. Saved Netplan SHA-256 is `a50b7fc72a7ce2d89e309457cec48549193a1219fcb9eacf0c5a56d8587244e8`; saved/runtime camera profile SHA-256 is `25012e84e14a6a790b36914f90ba8e3968eeaea5343efa6c87854aff7ad2261c`.
- PASS persisted repair evidence: all preservation guards pass, camera route is directly through `enP3p49s0` with source `192.168.11.88`, TCP 554 and 80 connect, the profile autoconnects with a 3000 ms conflict check, and the public tunnel remains active with zero reported restarts.
- PASS post-activation local feed: existing authentication/Origin isolation checks pass and the native receiver decodes 100 real 2304x1296 frames with host/host candidates and zero cloud ICE servers. No frames, private credentials or raw signaling are saved.
- LIMITED public check: root/health return HTTP 200, but the external `:7777` WebSocket media handshake returns 403. The live Origin is `http://8.130.208.68`, without `:7777`; this task does not change it. Public video is not marked passed, and the older intermittent frame stall is not claimed fixed.
- FAILED/INCONCLUSIVE checks: the first public diagnostic used an environment without `aioice`; rerunning in the existing acceptance environment reached the 403 above. A final combined regeneration/metadata probe exits nonzero without result output and supplies no additional evidence. Earlier guarded attempts have backups but no final success record. No reboot or browser playback acceptance was performed.
- PASS scoped Ruff on the operational helper. Documentation whitespace and decision-note validation are checked during task closeout; their outcomes are recorded below after execution.

### Notes

- `docs/deployment.md`: records the accepted interface/address, preservation evidence, public-video limitation and executable targeted rollback.
- `docs/decisions/implemented/architecture/2026-11-17-camera-network.md`: synchronizes the existing static-camera-network decision with the current board and authoritative Netplan source.
- `progress.md`: appends this task without changing historical records.
- Ignored `.tmp/adopt-camera-network.py`: applies the approved camera-only configuration with backups, preservation guards and rollback, accepting the password via stdin without storing it; do not rerun blindly after later changes.
- Ignored `.tmp/camera-network-result.json`: retains sanitized final success, checks, deployed hashes and backup location.
- Board `/etc/netplan/config.yaml`: consolidates duplicate network mappings and persists only the selected camera's static settings while preserving the other interface's DHCP configuration.
- Board `/etc/NetworkManager/system-connections/netplan-enP3p49s0.nmconnection` and `/run/NetworkManager/system-connections/netplan-enP3p49s0.nmconnection`: contain the matching approved static camera profile.
- Board `cam/.camera-network-backup-20261120T023413Z/`: retains exact pre-task files, existence metadata and success evidence; earlier `022521Z`/`023100Z` backups are not the accepted deployment.

Rollback point: board private backup `.camera-network-backup-20261120T023413Z/`; execute only the targeted restore block in `docs/deployment.md` after checking for later edits. It restores original file existence and the user's earlier static profile/DHCP-source inconsistency, then activates only the camera connection. It may briefly interrupt video but does not restart CarStream or alter uplink profiles. For local rollback, reverse only this task's two documentation edits and remove its ignored helper/evidence if desired, retaining this append-only task record.

### Testing - closeout

- PASS `git diff --check` and all three decision-note validators: 13 active notes, zero archived notes. IDE ReadLints returns no diagnostics but reports zero checked files, so it adds no lint coverage.
- No further board commands or operational changes were executed after the user requested closure; only the existing task's documentation and append-only record were completed.
