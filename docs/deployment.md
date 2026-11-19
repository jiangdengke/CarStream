# Deployment and acceptance boundaries

## Independent local feed (2026-11-19)

The user approved preserving public playback while adding an independent native
backend feed on the same board. The production endpoint is now
`ws://127.0.0.1:8081/ws`, with the existing access token and no `Origin` header.
Any supplied Origin, including the public one, is rejected on this listener.
Public 8080 retains its exact public Origin and relay-only TURN configuration.
The local session clears STUN/TURN and uses host ICE; source, resolution, codec,
quality, native media implementation and retransmission settings are unchanged.
The third-party backend must terminate WebRTC and owns subsequent distribution.
Protocol and integration instructions are in [local-feed.md](local-feed.md).

Deployment at 09:33:32 UTC replaced only `carstream/config.py`,
`carstream/server.py` and `start.sh`, added `tests/smoke_local_feed.py`, and
appended `CARSTREAM_LOCAL_PORT='8081'` to the private board environment. Original
environment bytes are preserved as a prefix; token, camera and public ICE values
were not changed. One application restart changed PID 44476 to 50404. Both
listeners are owned by that process and bound to `127.0.0.1`; the current log is
`log/carstream-20261119T093332.819779546Z.log`. The tunnel remains active. No cloud
proxy, TURN, SSH forwarding, firewall, route, camera or dependency change was made.
The board user initializer, application entrypoint, media source, stop script and
all player assets retain their pre-task hashes. Source readback matches local
deployment inputs. Private originals are backed up under
`.local-feed-backup-20261119T093332Z/` (0700), including the private environment.

Verification:

- The new configuration/listener regressions fail before implementation.
  Afterward all 36 configuration, signaling and Linux lifecycle tests pass in
  an isolated board staging directory. Local macOS execution passes 26 tests and
  skips the 10 Linux lifecycle checks. Existing 15 player tests pass.
- Staging and production each decode 100 real 2304x1296 frames through the new
  authenticated WebSocket endpoint. The ready message has no ICE servers and
  policy `all`; both endpoints exchange only host candidates. This establishes
  direct host-media delivery without TURN, not the exact selected interface or
  long-term continuity. Native selected-pair introspection was unavailable in
  the installed GI bindings; no memory-level workaround or dependency install
  was attempted.
- Deployed public 8080 rejects missing/foreign Origin; local 8081 rejects browser
  Origin. Both reject a wrong token. Unit coverage also checks empty token,
  no session/config disclosure before auth, local answer/ICE handling, public
  relay config isolation, local shutdown release and dual-port startup/stop.
- The existing external relay-only receiver remains connected for 80.31 seconds,
  decodes 1566 real 2304x1296 frames, and observes a longest decoded-frame gap of
  1.046 seconds, then exits zero and closes its session. This is a short native
  public-path regression, not a fresh browser or long-term stability acceptance;
  the older intermittent genuine frame stall is not claimed fixed.
- Scoped Ruff, Bash syntax, diff whitespace and the three decision-note
  validators pass. IDE ReadLints returns no diagnostics but reports zero checked
  files, so it is not additional lint coverage.

Rollback (not executed): inspect for later edits first; on the board run:

```bash
cd ~/magnet_car_project/cam
./stop.sh &&
for filename in carstream/config.py carstream/server.py start.sh .env; do
  cp -p ".local-feed-backup-20261119T093332Z/$filename" "$filename" || exit 1
done &&
./start.sh
```

The previous configuration has the same public strong token and HTTP Origin,
so this rollback does not restore an obsolete weak/public configuration. The
unused local smoke file can remain for reference; removal is optional after
checking for later edits. To disable just the local capability without rolling
back code, set `CARSTREAM_LOCAL_PORT='0'` in the private environment and restart
through the same scripts. Either operation interrupts all current viewers.

## Genuine frame-reception stalls: investigation, not a fix (2026-11-19)

The later HTTP playback failures are not the earlier false presentation-counter
stall. In the observed sessions, incoming bytes/packets continue while both
`framesReceived` and `framesDecoded` stop, with ICE/WebRTC and signaling still
connected. The player then deliberately recovers after about 16 seconds without
video progress. Browser clean/1000 closes align with the server receive-task exit
summaries. This explains those observed disconnects; it does not settle the
separate historical spontaneous signaling close.

At 08:22:27-08:22:44 UTC, one browser stream remains at 1500 received/decoded
frames and 50 decoded keyframes while received bytes increase from 14728663 to
18182524 and PLI requests increase from 7 to 81. The jitter-buffer emitted count
advances slightly, but that is not proof that complete decodable pictures reach
the decoder. These counters localize the visible failure to complete-frame
delivery/recovery; they do not identify why frames are lost or rejected.

The bounded diagnostics narrow, but do not close, that gap:

- An 80.07-second isolated camera/codec/payloader test produces 1598 frames and
  RTP frame-tail markers, with no observed sender sequence gaps or abnormal RTP
  timestamp changes. Its output terminates at a local sink, so it is not a
  WebRTC/TURN acceptance test or byte-level bitstream validation.
- A 75.03-second cloud capture sees the stalled browser's primary SSRC continue
  sending timestamp changes and frame-tail markers. Its only primary-stream
  timestamp discontinuity is near session startup, before the observed stall.
  This is encrypted-media header evidence only: it cannot establish payload
  correctness, final client delivery, or successful keyframe reconstruction.
- One paired full-resolution WebRTC diagnostic observes 1598 encoded frames,
  54 actual IDR NAL starts, 87 upstream keyframe requests and 5142 generated RTX
  packets at 80.06 seconds. The independent receiver has decoded 617 frames,
  received 6085 primary packets and 2739 RTX packets. The sender probe includes
  pre-negotiation packets and the snapshots are not packet-by-packet aligned;
  do not calculate a network loss rate from those totals. This demonstrates
  impaired end-to-end delivery/recovery, not a proven encoder or relay defect.
- A shorter paired run reaches 754 decoded frames by 40.34 seconds and does not
  reproduce the long browser freeze. A concurrent 50.03-second per-flow cloud
  capture overlaps only the first part of that run. It records 307 skipped
  primary sequence numbers, including startup discontinuities; it is not an
  all-window correlation or proof of the source of later freezes. Neither
  paired run uses Chrome's frame-assembly implementation.
- Earlier independent-client attempts fail on sanitized RTSP resource/read
  errors, and one helper attempt has a DTLS-wrapper argument error. Another
  independent run decodes 875 frames before the media track ends and exits with
  failure. None is a continuity pass. Concurrent camera reads are a diagnostic
  confounder, not a proven cause of the browser's media-arrival stall.

The implementation handles force-keyframe requests, and the paired test sees
both upstream requests and actual IDRs. It is therefore unsupported to conclude
that the encoder never emits keyframes or that requests never reach the sender.
The inspected codec source has conditional packet-offset/partition assumptions,
but no runtime evidence ties them to this incident. No speculative codec patch,
timeout increase, bitrate reduction or network change was deployed.

Only ignored local diagnostic helpers and this documentation/log are changed.
No camera images or packet capture files are saved; the cloud helpers parse
bounded encrypted packet slices in memory and report numeric RTP header counts.
Production PID 44476, protected media/config/initializer hashes and player hash
are unchanged at the final 08:45 UTC check, and the tunnel is active. Cloud
capture processes have ended. Existing 15 player regressions and scoped helper
Ruff checks pass; they do not validate long-term live continuity. IDE ReadLints
is unavailable in the final tool set.

The browser sample observers were removed. The assistant's old English test
viewer was stopped to reduce load; the Chinese viewer was left watching.
Browser tools became unavailable before the old viewer could be resumed and
both tab locks released. No final browser-state/unlock acceptance is claimed.
The next decisive check is one isolated viewer with synchronized RTP sequence
comparison at sender, relay and receiver, including receiver discard reasons.
Until that evidence exists, the precise trigger remains unresolved. There is no
production rollback to execute for this investigation.

## Chinese minimal interface (2026-11-19)

The page title, buttons, connection states, automatic-retry countdown and playback
errors now use Simplified Chinese. The interface keeps only the access token,
start/stop watching buttons, status and native video controls. Hardware/protocol
descriptions, the normal camera-source label and the footer are removed. A test
source still displays an explicit Chinese warning that it is not the real camera.
Native video-control labels follow the browser's own language settings.

The public entrypoint is simply `http://8.130.208.68:7777/`; the earlier `ui`
query was only a verification marker, never a version requirement. A follow-up
static-only player update at 08:07:21 UTC removes this marker with
`history.replaceState` when the page loads. Other query parameters, fragments
and history state remain unchanged. This does not navigate, connect or restart
the service. Already open tabs need one reload to execute the updated script.
PID 44476 and protected files were unchanged; the public player response matches
local SHA-256 `ab2afdcb4eaa32acfb2ce794bd106042a96c6dd49e64276b9a8c114371a4a699`.
All 15 Node tests pass, including a cleanup regression that failed before the
fix. Browser tools are unavailable for this follow-up, so no live address-bar
check was performed. Backup: `cam/.clean-url-backup-20261119T080721Z/player.js`.
To undo only this follow-up after checking for later edits, atomically restore
that backup over `carstream/static/player.js`; no restart is needed.

Only `carstream/static/{index.html,player.js,style.css}` were deployed at
07:58:53 UTC. PID 44476 was unchanged across this deployment; the service was not
restarted. Private configuration, the user initializer, server diagnostics and
media/config sources were unchanged. Authentication decisions, signaling payloads,
retry timings and video-progress monitoring are unchanged. English server error
strings remain on the wire; the page displays a Chinese invalid-token or general
connection message instead of raw error details.

All three public static responses match the local file SHA-256 values, and public
`/healthz` reports alive. The public page was loaded in a separate Cursor tab
without reloading the existing viewer or copying its token. The initial Chinese
interface was visually checked at 574 px and an emulated 375 px width; neither
has horizontal overflow. Test-source visibility, Chinese errors and existing
recovery behavior pass 14 JavaScript tests. Python tests pass 21 checks with
8 Linux-only skips. This interface check is not a new real-camera continuity
acceptance or a repair of the remaining intermittent freezes.

Refresh the public page to load the new interface, re-enter the existing token
and select "开始观看". Tokens are still not persisted. Refreshing interrupts only
that viewer. Backup: `cam/.chinese-interface-backup-20261119T075853Z/`.
To roll back only these static files, first check for later edits, then run:

```bash
ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && for filename in index.html player.js style.css; do cp -p ".chinese-interface-backup-20261119T075853Z/$filename" "carstream/static/.ui-rollback-$filename" && mv "carstream/static/.ui-rollback-$filename" "carstream/static/$filename" || exit 1; done'
```

No restart is needed for rollback; reload affected viewers afterward. The backup
preserves the earlier false-stall fix, unlike restoring an older HEAD player.

## Session close diagnostics (2026-11-19)

The user authorized a diagnostic-only server change and one guarded application
restart to investigate the remaining real signaling close. No heartbeat,
authentication, signaling schema, retry behavior, media quality, network or
cloud configuration was changed. This deployment improves evidence collection;
it is not another root-cause repair or a claim that every blackout is fixed.

After media creation, every server session exit now writes one INFO summary
before active cleanup can replace its original state. Fields are completed task
names, original WebSocket close code, socket exception class, handler failure
class and elapsed seconds. Raw exception text, close-reason text, token, SDP/ICE
and client addresses are not included. The normal server log remains private.
On Python 3.10, an enum-valued abnormal code prints as
`WSCloseCode.ABNORMAL_CLOSURE`; newer Python prints `1006`. These are equivalent,
not missing diagnostics. `completed=none, failure=CancelledError` can occur
when a request is cancelled before a child task result is collected.

Before this change, a real Cursor observation starting 07:18:22 UTC lasted
600.0014 seconds in one session, with no close event, false-stall teardown or
missing stream sample. Decoded frames grew from 3633 to 15623 and presentation
callbacks from 3514 to 13636. Browser freeze metrics nevertheless increased
by 32 freezes totaling 8.712 seconds. This is not uninterrupted playback or a
two-second frame-gap pass. Earlier real signaling closes remain unexplained.

Two bounded, read-only cloud packet-metadata captures did not record a close
on the active loopback 17777 signaling connection. The second showed eight
two-byte backend writes followed by six-byte client writes at roughly
21-second intervals, with about 40-50 ms return timing. That is consistent
with healthy heartbeat traffic during this interval; payloads were not decoded
or saved, and it does not prove what happened during the prior close. Public
7777 FIN/RST packets from other TCP connections must not be attributed to the
player without matching the connection. No capture process remains running.
The board lacks tcpdump/noninteractive sudo; nothing was installed or escalated.

Only `carstream/server.py` was backed up and atomically replaced. The guarded
restart changed PID 43155 to 44139 at 07:30:18 UTC; the current log is
`log/carstream-20261119T073018.503817000Z.log`. Always reread `server.pid`.
Backup: `cam/.close-diagnostics-backup-20261119T073017Z/server.py`, alongside
an integrity manifest. The deployed server SHA-256 is
`c51e6a5f864d0370f71214550853526264a05ac3a30be4228865a620e460e7fe`.
Private environment, user initializer, media/config and previously repaired
player hashes match the pre-deployment manifest. The HTTP entrypoint and tunnel
remain unchanged. Existing browser watching intent recovered automatically.

At 07:32:05 UTC, a controlled close of only the Cursor viewer's WebSocket
produced client code 1000/clean and server `completed=signaling-receive`,
`close_code=1000`, `socket_error=none`, `failure=none`. This is an intentional
recovery test, not another spontaneous failure. The test token remained in the
existing password input; no secret was passed through tool arguments.

The post-deployment observer runs 360.0006 seconds from 07:31:48 UTC. Its
only close is the intentional test above; no spontaneous close or false-stall
teardown occurs. The recovered session shows 18 decoded frames and actual
presentation by 21.5567 seconds, at most about 4.11 seconds after the intentional
close, then 6780 decoded/3035 presented frames by the final sample. The two
samples without a stream belong to that controlled recovery. Thirteen
browser-reported freezes total 3.283 seconds in the recovered session, so even
this no-unexpected-disconnect interval is not a smoothness pass. Observers and
diagnostic listeners are removed afterward; playback is left running. The
remaining historical real close did not reproduce with new diagnostics during
this bounded check and its cause is still unknown.

Two diagnostic regressions fail against the old server because it emits no
close summary. After the change, all 21 local Python tests pass with 8 Linux-only
lifecycle skips, and all 13 player tests pass. Nine isolated signaling tests
also pass under the board's actual Python 3.10/aiohttp 3.14.5, without touching
the production media or heartbeat interval. The simulated missing-PONG test
confirms timeout/abnormal-close diagnostics, not the cause of a past real close.
aiohttp's test server cancels disconnected request handlers unlike this
production runner; tests assert close/error evidence without requiring an
identical task-completion race. Ruff and decision-note checks pass.

Rollback, after checking for subsequent edits and accepting another brief
application interruption:

```bash
ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && ./stop.sh && cp -p .close-diagnostics-backup-20261119T073017Z/server.py carstream/.server-rollback.py && mv carstream/.server-rollback.py carstream/server.py && ./start.sh'
```

This removes close diagnostics only. It preserves the HTTP entrypoint, current
player repair and private environment. Do not change timeouts or quality based
on a healthy observation alone. Correlate the next spontaneous close with its
server summary before selecting a further fix.

## Cursor false-stall blackout repair (2026-11-19)

The current player adds inbound video `framesDecoded` as a second progress
signal. A suppressed `requestVideoFrameCallback` alone must not tear down
a session that is still decoding. Actual presentation or decoded-frame progress
keeps the existing session alive; neither bytes received nor playback time can
substitute for decoded frames in this cross-check. A true freeze still recovers
after the existing roughly 15-second threshold. Statistics reads do not overlap,
recheck session identity after completion and fall back to presentation monitoring
if unavailable. Pause, autoplay, authentication and retry limits remain unchanged.
This prevents false reconnects; continued decoding does not prove that the screen
compositor is displaying frames or detect every possible black image.

Before repair, the real HTTP Cursor session was observed from 06:53:12 UTC
for approximately 300 seconds. It recorded eight `Video stopped advancing`
teardowns and nine sessions, with 159 of 301 one-second samples having no
attached stream. One session's decoded frames grew from 30 to 328 and received
bytes from 487014 to 3330998 while its presentation counter stayed at zero.
Sampled video brightness remained around 121 on a 0-255 scale, not black.
The player nevertheless cleared `video.srcObject`, then increased retry delays
to 30 seconds. This establishes one cause of the reported blackouts rather than
attributing them to the cloud, camera or HTTP. The corresponding board log had
no `Viewing session failed` entry, and the tunnel remained active.

Only the board's `carstream/static/player.js` was backed up and atomically
replaced at 07:00:38 UTC. PID 43155 was not restarted; camera quality, media
code, private environment, cloud proxy, TURN and browser security were unchanged.
The backup is `cam/.blackout-player-backup-20261119T070038Z/player.js`.
The deployed player's SHA-256 is
`478470b1e549f736dc28a8284388c288934f99786ca35df752ca8ae163576bfe`;
the previous version is
`a0c659e0e6431e5d22ade8522f9cf38cbf508a6f149db70950d9aa621abcd082`.
Already open pages need a refresh and Connect to load this static change.

The existing Cursor tab retained the token only in its password input. The
new monitor was activated through direct DevTools function replacement with
legacy-session field initialization, not by copying the token into tool
arguments or browser storage. An earlier attempt to evaluate downloaded source
was blocked by the existing CSP; that policy was not relaxed. This active-tab
check is not a clean-reload acceptance test of the entire script.

The subsequent 300.7333-second observation starting 07:01:57 UTC records no
`Video stopped advancing` teardown, but does record one genuine `Signaling
connection closed` at 209.3097 seconds. Frames were still decoding immediately
before that close. Automatic recovery received video again by 212.7316 seconds,
about 3.42 seconds later. The two sessions' sampled decoded counts grow from
509 to 4685 and from 14 to 1770 respectively. Only one of 301 samples has no
attached stream, versus 159 before repair; none of the sampled decoded images
has more than 98% near-black pixels. These are sampled conditions, not proof
that every visible blackout or short freeze is eliminated. The stream remains
2304x1296 over relay/relay. No camera images or pixel buffers were retained.

At 07:08 UTC the tunnel has the same PID 39463 and start time 05:26 UTC,
with no journal entries since 06:50 UTC. Its two historical restarts are not
new restarts during this check. The proxy has zero container restarts, unchanged
start time and no recent error output; the board has no session-failure entry.
These checks do not identify the initiator/cause of the remaining WebSocket
close. Network, heartbeat or rendering root causes are not established, and
neither server heartbeat nor signaling/authentication behavior was modified.

The three new focused Node cases cover suppressed callbacks with advancing
decode, real decoder stalls despite growing bytes/clock, unavailable statistics,
read deduplication and stale-result isolation. Two fail against the prior player;
all thirteen pass after repair. The existing Python unittest suite passes nineteen
tests, with eight Linux-only lifecycle tests skipped on macOS. No dependencies
were added. Syntax checks and focused diagnostic Ruff checks pass.

Rollback only this player, after checking for subsequent edits:

```bash
ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && cp -p .blackout-player-backup-20261119T070038Z/player.js carstream/static/.player-rollback.js && mv carstream/static/.player-rollback.js carstream/static/player.js'
```

Refresh the viewing page afterward. No service restart or environment rollback
is needed. This restores the known false-stall defect. The recovery decision is
maintained in [the existing player note](decisions/implemented/feature/2026-11-17-player-recovery.md).

## Public HTTP cutover (2026-11-19)

**Current viewing URL: http://8.130.208.68:7777. Use HTTP, not HTTPS.**
This section supersedes the older HTTPS viewing instructions below. The user
abandoned domain setup and explicitly accepted the plaintext risks before this
cutover. Page content, the access token, TURN credentials and signaling can be
observed or modified in transit. DTLS/SRTP still protects the media transport,
but untrusted signaling does not defend against an active intermediary.
This is not a security-equivalent replacement for HTTPS.

Only the isolated project's Nginx listener on 7777 changed from TLS to HTTP;
its forwarded scheme now follows `$scheme`. Board and cloud private settings
use the exact `CARSTREAM_PUBLIC_ORIGIN=http://8.130.208.68:7777`. The strong
token, weak-token false, authentication-before-media, route allowlist, rate
limits and publication gate remain. Previous HTTPS and localhost Origins are
rejected, not added to an allowlist. No domain listener or browser security
exception was installed. The original certificate/key remain unused for rollback.

The public gate was closed while changing configuration. Nginx configuration
validation passed before reload; only the board application was restarted via
its guarded scripts. Activation PID was 43155, log
`log/carstream-20261119T063230.126057786Z.log`; reread `server.pid` before any
later process operation. The SSH tunnel stayed active, and proxy/TURN containers
were not restarted. The separate cloud 443 passthrough configuration matches its
backup. No firewall, route, camera setting, source/player code, device access,
library or quality change was made. The user's initializer is unchanged.

Before publication, missing, foreign, old HTTPS and localhost Origins returned
403; empty and invalid tokens returned `Invalid access token`; the unchanged
token returned RTSP ready with relay policy. External HTTP `/`, `/healthz` and
`/player.js` return 200 with `Cache-Control: no-store`; `/.env` returns 404.
At the HTTP cutover, the deployed player hash was
`a0c659e0e6431e5d22ade8522f9cf38cbf508a6f149db70950d9aa621abcd082`.
The later static-player repair above supersedes that version.
Local regressions: ten Node player tests and nineteen Python tests pass;
eight Linux-only lifecycle tests are skipped on macOS.

The user entered the existing token directly in Cursor and clicked Connect;
no secret was passed through chat or browser-tool arguments. The real Cursor
page at the HTTP IP origin reports `isSecureContext=false`, presents
2304x1296 RTSP video and selects relay/relay. An initial sample had 562
presented frames at 28.865 seconds. A focused 90.0002-second observation from
06:35:27 UTC presented 1658 additional frames, with no session change; player
presentation count advanced from 1113 at the first one-second sample to 2751
at the final sample. The maximum presentation-callback interval was 5.6754
seconds, exceeding the unchanged two-second continuity criterion. This is a
presentation timing observation, not a network-frame-gap measurement or proof
of its cause. A later sample at playback time 165.871 seconds showed 3314
decoded frames, three browser-reported freezes totaling 0.888 seconds and the
same session. Those differing metrics must not be conflated. HTTP access and
actual rendering pass; smoothness, historical restart disconnections and other
browsers are not fixed or fully accepted. Diagnostic callbacks were removed,
the browser unlocked and playback left running. No camera image was saved.

Private backups:

- Board: `cam/.http-cutover-backup-20261119T063030Z/{.env,integrity.json}`.
- Cloud: `/opt/carstream/private/http-cutover-20261119T063030Z/`, containing
  prior `nginx.conf`, `public-access.env`, `backend-ready` and the separate
  443 configuration's SHA-256.

To restore the exact prior HTTPS configuration, first check for subsequent
private edits. Close the gate, restore the board environment and restart only
this application, then restore/test/reload this project's cloud configuration.
Keep the gate closed if any command or boundary check fails:

```bash
ssh company 'rm -f /opt/carstream/config/backend-ready'
ssh linaro@192.168.50.84 'cd ~/magnet_car_project/cam && ./stop.sh && cp -p .http-cutover-backup-20261119T063030Z/.env .env && ./start.sh'
ssh company 'cp -p /opt/carstream/private/http-cutover-20261119T063030Z/public-access.env /opt/carstream/private/public-access.env && cp -p /opt/carstream/private/http-cutover-20261119T063030Z/nginx.conf /opt/carstream/config/nginx.conf && docker exec carstream-proxy nginx -t -c /etc/carstream/nginx.conf && docker exec carstream-proxy nginx -s reload -c /etc/carstream/nginx.conf'
```

Before reopening, verify privately that the restored backend requires the exact
HTTPS Origin and accepts only the intended token. Then restore the backed-up
gate marker and check HTTPS health using the original pinned certificate:

```bash
ssh company 'cp -p /opt/carstream/private/http-cutover-20261119T063030Z/backend-ready /opt/carstream/config/backend-ready'
```

This rollback restores the original self-signed browser-trust problem; it does
not deploy the abandoned domain. No rollback was executed. The scoped transport
decision is recorded in [the HTTP note](decisions/implemented/architecture/2026-11-19-public-http.md).

## New board installation (2026-11-19)

The new target is `linaro@192.168.50.84`, a Rockchip RK3588 ZYSJ 2288A V10
board running Ubuntu 22.04.5, Python 3.10.12 and GStreamer 1.20.3. The final
project root requested by the user is:

```text
/home/linaro/magnet_car_project/cam
```

Project artifacts are directly inside `cam`, not in a nested `CarStream`
directory. Its pre-existing `__init__.py` is untouched, with SHA-256
`4d0e4b367c19703a7fad65e42e86e3571f88cd41f1ccbc4dbe23b91f8ba560a5`.
The initial `/home/linaro/CarStream` copy remains inactive as a fallback.
The virtualenv was rebuilt at the final path instead of moving absolute
interpreter/script paths from that first copy.

After package-plan review, installation added 49 packages without upgrades
or removals, using `--no-upgrade --no-remove --no-install-recommends`.
Explicit additions were `python3-venv`, `python3-gst-1.0`,
`gir1.2-gst-plugins-bad-1.0`, `gstreamer1.0-plugins-bad`,
`gstreamer1.0-nice` and `gstreamer1.0-plugins-ugly`; the latter supplies the
software encoder for synthetic checks. Locked Python dependencies are in the
new system-site-packages `.venv`; `pip check` passes. No vendor media stack,
route, network interface, firewall, cloud service or boot service was changed.

The private `.env` is mode 0600 with a newly generated strong token. Initially
it used the test source; it now uses the original real H.265 camera credentials
recovered from the user's existing script. `HOST=127.0.0.1`, `PORT=8080` and
`VIDEO_PROFILE=original` are unchanged. Initially no public Origin or STUN/TURN
configuration was copied. The separately authorized public cutover below adds
the existing cloud Origin and TURN, not the old board's 720p / 350 kbps profile.

At initial installation all 27 configuration/signaling/Linux lifecycle tests pass.
Synthetic native WebRTC decodes at least ten frames with RTP packets at most
1200 bytes. Exact-sequence RTX recovery passes, and all three cleanup checks
pass, with eight descriptors after each of ten closes. These checks use local
ICE, not real TURN allocation. A temporary start, HTTP 200 health check,
repeat-start refusal to duplicate and graceful stop all pass; the service is
stopped afterward. Its test log is
`log/carstream-20261119T015316.686333810Z.log`.

The initial image lacked the GStreamer MPP plugin, not the underlying vendor
libraries: follow-up inspection found MPP 1.3.9, RGA 2.1.0 pkg-config metadata
and headers. The hardware plugin is now installed and tested as described below.
The initial H.265 SSRC regression failed before that installation; its subsequent
pass does not erase that historical failure. The service is now running with
the latest isolated plugin/MPP pair and real camera; the native client decodes
2304x1296 frames, but its initial private one-minute continuity check ended early.
The later public cutover below verifies public video delivery; browser,
low-latency and continuous-playback acceptance remain incomplete.

On the board, start or stop from the final root:

```bash
cd /home/linaro/magnet_car_project/cam
./start.sh
# Stop this deployment when needed:
./stop.sh
```

Before the public cutover, private viewing used an SSH forward of loopback 8080
and the new token from this deployment's `.env`. The Mac loopback-only forward
on 18080 remains available, but its page Origin is now rejected; use the public
URL instead, as described below.
The old `scripts/sync-board.sh`
still uses `/home/cat` internally and must not be used for this new target merely
by overriding its SSH username. The old-board records below remain historical.

Rollback/disable point: the initial `/home/linaro/CarStream` copy is preserved.
To disable the final deployment, use its identity-checking `./stop.sh`; it is
currently running. Preserve the user's `cam/__init__.py`, private
configuration and logs. Package removal is a separate reviewed action, not an
automatic rollback. Initial installation did not perform a cloud cutover;
the later authorized migration is recorded below.

### Replacement-board hardware plugins and camera blocker

This subsection records the initial compatible-plugin installation. The latest
pair and recovered camera settings below supersede its version/blocker state.

The camera at `192.168.11.83` accepts TCP connections on 554 and 80. The existing
route uses `enP2p33s0`, source `192.168.11.84`; no network address, default route,
firewall or interface was changed. The application's private `.env` still has
an empty RTSP URL and empty camera credentials. The previous board's SSH timed
out, so its private camera settings could not be retrieved. No URL or password
was guessed, no camera setting was changed, and no real camera playback is claimed.

The plugin comes from `JeffyCN/mirrors`, branch `gstreamer-rockchip`, pinned to
`0fc75d3710fede7ca2dfb4687362fb6979100d9e` (2024-07-17). Current branch revision
`bff0659a51c13585b3c9c9a68aa8c435beeb3fe1` failed to build because the installed
MPP headers do not have `MppSysCfg`. Selecting the matching older plugin avoids
replacing MPP, RGA or the kernel. Source and build files are preserved in
`/home/linaro/.cache/carstream-rockchip-0fc75d3`; the incompatible source/build
is inactive in the corresponding `carstream-rockchip-bff0659` directory.

Development dependencies added 43 packages and upgraded only
`libgstreamer1.0-0` and `gir1.2-gstreamer-1.0` from `1.20.3-0ubuntu1.1` to
`1.20.3-0ubuntu1.2`, with no removals. GLib development packages were explicitly
pinned to the installed `2.72.4-0ubuntu2.10`; GLib runtime, vendor media libraries
and kernel were not replaced. APT reported an unrelated libffi doc-base format
warning; installation exited successfully and `dpkg --audit` reports nothing.

The native build and installation commands, from the pinned source root, are:

```bash
meson setup build \
  --prefix=/home/linaro/.local/opt/carstream-rockchip-0fc75d3 --libdir=lib \
  -Drockchipmpp=enabled -Drga=enabled -Drkximage=disabled \
  -Dkmssrc=disabled -Dvpxalphadec=disabled
meson compile -C build -j 4
meson install -C build
```

The mode-0600 application `.env` adds only these native environment variables:

```bash
GST_PLUGIN_PATH='/home/linaro/.local/opt/carstream-rockchip-0fc75d3/lib/gstreamer-1.0'
GST_REGISTRY='/home/linaro/.cache/carstream-rockchip-0fc75d3/registry.bin'
```

The separate registry avoids retaining the initial scan's decoder-only results
from before device access was granted. `./start.sh` exports both variables.
The original `.env` is preserved in `.hardware-config-backup-20261119T020844Z/`.

Devices were root-only. `/etc/udev/rules.d/99-carstream-media-access.rules`
now grants only `linaro` read/write ACL entries on `mpp_service`, `rga` and
`dma_heap` devices. It does not make devices world-writable, change user groups,
or run the application as root. Existing device ACLs are preserved in
`.camera-hardware-backup-20261119T020758Z/device-access-before.acl`.
The rules were reloaded and ACLs applied to eight existing device nodes.
`udevadm test` confirms the heap rule matches; reboot persistence is not tested.

Verification with the configured plugin:

- `--check` reports the required MPP decoder/encoder, and factory properties
  include the application's bitrate, GOP, profile and scale controls.
- A finite 60-frame NV12 source at 640x360 / 20 fps passes MPP H.265 encoding,
  MPP decoding, Baseline H.264 encoding, parsing and actual H.264 decoding to EOS.
- All 27 Linux unit/lifecycle tests pass. Native WebRTC decodes at least ten
  synthetic frames, RTP maximum is 1200 bytes, and exact original sequence
  26081 is recovered via RTX followed by ten further decoded frames.
- The H.265 SSRC pad regression passes. Three cleanup tests pass; each of ten
  hardware-enabled closes settles at 17 descriptors, with no TURN configured.
- A temporary test-source start launches historical PID 22366, health returns
  HTTP 200, repeat start recognizes it, and stop removes it. Log:
  `log/carstream-20261119T021428.142988314Z.log`. Final state has no PID file
  and no 8080 listener. The user's `__init__.py` hash remains unchanged.

Real startup requires the confirmed RTSP URL, camera username/password and actual
codec in private `.env`, then `./start.sh` and actual decoded-frame verification.
It is intentionally not left serving a test pattern as if camera setup passed.
The listener remains loopback-only, and no public migration has been performed.

Rollback after checking for later edits: stop this deployment, restore `.env`
from `.hardware-config-backup-20261119T020844Z/.env`, then restore device access
and remove only this installation's dedicated rule:

```bash
cd /home/linaro/magnet_car_project/cam
./stop.sh
cp -p .hardware-config-backup-20261119T020844Z/.env .env
sudo setfacl --restore=.camera-hardware-backup-20261119T020758Z/device-access-before.acl
sudo rm /etc/udev/rules.d/99-carstream-media-access.rules
sudo udevadm control --reload-rules
```

This disables application plugin loading without deleting builds or changing
system packages. Package downgrade/removal is a separate reviewed action;
there was no automatic rollback or broad `autoremove`.

### Latest isolated media runtime and real camera startup

The user requested the new plugin rather than the compatibility-pinned 2024
revision, and confirmed the same camera and previously supplied credentials.
The original script was found at
`~/Desktop/voice_project/voice_project/video_stream/inter_video.py` on the Mac.
Its literal URL is parsed without importing or running the OpenCV script;
credentials are transmitted privately over SSH stdin and stored separately
from the camera URL in mode-0600 `.env`. Do not ask for them again merely because
the previous board is unavailable. No credentials are copied into source or docs.
A single preceding unauthenticated check of the already verified URL returned
401; the recovered credentials subsequently delivered actual camera frames.

Current upstream revisions were resolved and pinned on 2026-11-19:

- `rockchip-linux/mpp`, develop:
  `9b56348cc61393c84662e6d6dd78feae67773a36` (2026-11-03), pkg-config 1.3.10.
- `JeffyCN/mirrors`, gstreamer-rockchip:
  `bff0659a51c13585b3c9c9a68aa8c435beeb3fe1` (2026-10-22).
  Its embedded plugin version still says 1.14.4; identify it by commit, not
  that unchanged label.

Both are installed under
`/home/linaro/.local/opt/carstream-media-latest-20261119`. The original system
MPP 1.3.9 and RGA libraries, kernel and previous compatible plugin are retained.
No additional APT transaction, system-library replacement, `ldconfig`, network
change or application-source edit was needed. MPP is built with CMake Release,
`BUILD_TEST=OFF`, `CMAKE_INSTALL_LIBDIR=lib` and the independent prefix. Its source
and build remain in `/home/linaro/.cache/carstream-mpp-9b56348/`.
The latest plugin uses the same existing RGA library; GPU, X11/KMS and alpha
components are disabled, since they are not used by the media pipeline.

From the latest plugin source root, its matching build is:

```bash
PKG_CONFIG_PATH=/home/linaro/.local/opt/carstream-media-latest-20261119/lib/pkgconfig \
  meson setup build-latest \
  --prefix=/home/linaro/.local/opt/carstream-media-latest-20261119 --libdir=lib \
  -Dc_link_args=-Wl,-rpath,/home/linaro/.local/opt/carstream-media-latest-20261119/lib \
  -Drockchipmpp=enabled -Drga=enabled -Dgpu=disabled \
  -Drkximage=disabled -Dkmssrc=disabled -Dvpxalphadec=disabled
meson compile -C build-latest -j 4
meson install -C build-latest
```

The active private native environment is:

```bash
GST_PLUGIN_PATH=/home/linaro/.local/opt/carstream-media-latest-20261119/lib/gstreamer-1.0
LD_LIBRARY_PATH=/home/linaro/.local/opt/carstream-media-latest-20261119/lib
GST_REGISTRY=/home/linaro/.cache/carstream-rockchip-bff0659/registry-latest.bin
```

The process's `/proc/PID/maps` confirms both MPP and plugin are loaded from this
prefix, not the old vendor library. MPP's diagnostic version string says unknown
because the transferred source omits VCS metadata; the pinned commit, build
location and loaded-library paths provide the provenance instead.

The former test configuration and compatible plugin settings are preserved in
`cam/.latest-runtime-backup-20261119T022813Z/.env`. The active configuration uses
real RTSP/H.265, original resolution/1500 kbps transcode target, unchanged strong
web token, loopback listener and existing device ACL rule. Start launched PID
25947 at 02:28:41 UTC; verify its live identity rather than trusting this number.
Log: `log/carstream-20261119T022841.824589954Z.log`. The service is left running.

Passed on the new pair: 60-frame finite hardware H.265-to-H.264 decode, all
27 Linux unit/lifecycle tests, native synthetic WebRTC, RTP <=1200 bytes,
exact-sequence RTX recovery (13650), H.265 SSRC regression and all three cleanup
tests with 17 descriptors after each of ten closes. These are not real-camera
continuity acceptance.

The running HTTP/authenticated WebSocket service was then tested through a
native WebRTC receiver on the Mac, without saving camera images. It authenticated
as `source=rtsp`, decoded 2304x1296 actual frames, and the last progress sample
recorded 546 frames at 44.13 seconds. The intended 60-second check failed:
observed frame gap reached 4.244 seconds, then `MediaStreamError` ended the
receiver after 52.49 seconds overall. Regression checks overlapped its beginning;
this is not proof they caused the interruption. The two-second threshold was
not relaxed. The diagnostic receiver exited and closed its peer/WebSocket;
the application remains running. This proves camera authentication and initial
real WebRTC delivery, not smoothness, browser playback, public access or measured
glass-to-glass latency. Latency/root-cause work remains paused as requested.

Before the public cutover, viewing on this Mac used `http://127.0.0.1:18080`.
After cutover, use **https://8.130.208.68:7777** instead: the localhost page's
Origin is now intentionally rejected. The private forwarding
master uses `.tmp/linaro-latest-ssh.sock`, with `ControlPersist=1800`; it is not a
boot service, and it can expire after idle disconnect. Closing that forward does
not stop the board application. Retrieve the web token in the user's terminal
without posting its output:

```bash
ssh linaro@192.168.50.84 \
  'cd ~/magnet_car_project/cam && . ./.env && printf "%s\n" "$CARSTREAM_ACCESS_TOKEN"'
```

Use the token in the page's Access token field, then Connect. It is not the SSH
or camera password. If the Mac forward has expired and port 18080 is free,
recreate it in a terminal with:

```bash
ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 linaro@192.168.50.84
```

Stop only the task-created forward, after checking it still serves this board:

```bash
ssh -S /Users/jiangdk/code/company/CarStream/.tmp/linaro-latest-ssh.sock \
  -O cancel -L 127.0.0.1:18080:127.0.0.1:8080 linaro@192.168.50.84
```

Rollback, only after checking for later private edits: `./stop.sh`, then restore
`.env` from `.latest-runtime-backup-20261119T022813Z/.env`. That point deliberately
restores the previous **test** source and older compatible plugin; it is not a
working-camera rollback. To stop real video without restoring anything, use
only `./stop.sh`. Do not delete user files, remove ACLs or downgrade system
packages to switch this application-local codec runtime. No rollback, camera
setting change or cloud migration was performed. The version-alignment decision
is recorded in [the isolated latest-runtime note](decisions/implemented/process/2026-11-19-isolated-latest-media-runtime.md).

### Replacement-board public cutover (2026-11-19)

The user authorized migrating the replacement board to the existing Alibaba
Cloud entrypoint through `ssh company`. The current URL is
**https://8.130.208.68:7777**. Enter the same strong web token already supplied
for the replacement board, not the former board's cloud token or camera password.
The cloud's private `public-access.env` now holds that replacement-board token.
The existing certificate and its fingerprint in the TLS section below are unchanged;
verify the fingerprint before trusting this self-signed certificate.

The existing proxy and TURN containers were reused without restarting them or
changing their configurations, images, firewall rules, host routing, or SSH server.
Cloud `127.0.0.1:17777` now forwards to the new board's `127.0.0.1:8080`.
The board application remains in `/home/linaro/magnet_car_project/cam` and was
restarted through its guarded scripts: historical activation PID 28252, log
`log/carstream-20261119T024906.647932803Z.log`. Always reread `server.pid`.
Its latest isolated plugin/MPP runtime, real camera credentials, original
2304x1296 resolution profile and 1500 kbps transcode target are preserved.

Only these application settings changed: exact public HTTPS Origin, weak-token
opt-in explicitly false, existing TURN credentials with `transport=tcp`, forced
relay policy, and empty STUN. No production Python or player source changed.
Private `.env` and cloud credential files remain mode 0600.

A fresh Ed25519 identity was generated on the new board; its private key never
left that board. The cloud authorized-key entry replaces only the verified old
board key, preserving its exact `command="/bin/false",restrict,port-forwarding,
permitopen="127.0.0.1:1"` options. The old board key is no longer authorized,
preventing it from reclaiming the same backend port if it comes online.
The cloud host key is pinned from the authenticated `ssh company` session.
The unchanged tracked `deploy/board/carstream-tunnel.service` is installed as
`linaro`'s user service; it is enabled, active, and `Linger=yes`. A deliberate
tunnel restart recovered the private backend. The tunnel starts automatically;
the application still requires `./start.sh` after a board reboot. Reboot and
network-blackhole recovery have not been tested.

The public gate was closed during migration. Before reopening it, missing,
foreign and old localhost Origins returned 403; invalid and old cloud tokens
were rejected; the unchanged replacement token authenticated as RTSP with
TURN/TCP relay. Certificate-verified public requests then returned 200 for
the page, player and health, while `/.env` returned 404. All 27 deployed unit
and Linux lifecycle regressions pass. The user's pre-existing `__init__.py`,
`carstream/config.py` and `carstream/media.py` hashes are unchanged.

The external native acceptance client authenticated over public WSS and selected
relay/relay. It decoded **1241 real 2304x1296 frames over 60 seconds**, without
reconnecting. The first-frame wait after track negotiation was 2.63 seconds.
However, the longest decoded-frame gap was **2.458 seconds**, so the unchanged
two-second continuity check **failed** (exit 1). Public video delivery is verified,
not smoothness, browser behavior, long-term reliability or glass-to-glass latency.
No test threshold or video-quality setting was changed; no camera images were saved.
The diagnostic peer and WebSocket closed afterward; the service remains running.

Backups, both private, are:

- Board: `.public-migration-backup-20261119T024851Z/`, containing `.env` and migration metadata.
- Cloud: `/opt/carstream/private/migration-20261119T024851Z/`, containing prior
  `authorized_keys`, `public-access.env` and the original `backend-ready` marker.

To return this board to private viewing, first close the public gate, then run
the following after checking for newer edits:

```bash
ssh company 'rm -f -- /opt/carstream/config/backend-ready'
ssh linaro@192.168.50.84 '
  systemctl --user disable --now carstream-tunnel &&
  cd ~/magnet_car_project/cam && ./stop.sh &&
  cp -p .public-migration-backup-20261119T024851Z/.env .env && ./start.sh
'
```

This restores the private real-camera/latest-runtime configuration, not a test
source. Restore cloud keys and its prior private environment from the cloud
backup only if intentionally returning to the old board; keep the gate closed
until that board is independently verified. Do not reopen the gate just because
its backed-up marker exists. Only disable linger or remove this task's key/unit
after checking whether later services depend on them. No rollback was executed.

### Firefox presented-frame progress repair (2026-11-19)

The user reported black video even in the replacement board's local browser,
then authorized direct Firefox inspection and the narrowly scoped player fix.
The board's `http://127.0.0.1:8080` page still loads, but its WebSocket handshake
returns **403 Origin not allowed** under the public configuration. This is an
access-origin mismatch, not proof of camera failure. Keep the exact public Origin;
on the board too, use **https://8.130.208.68:7777** with its existing web token.

The external native receiver separately passed 60 seconds with 1224 decoded
2304x1296 frames and maximum frame gap 0.794 seconds. This does not substitute
for checking Firefox. The actual board Firefox displayed camera video but the
old player's `getVideoPlaybackQuality().totalVideoFrames` remained zero, so its
15-second watchdog repeatedly reported `Video stopped advancing` and reconnected.
OpenH264 2.6.0 is installed for this aarch64 profile; its shared dependencies
resolve. Missing browser codec packages were not assumed or installed.

The player now counts actual presentation callbacks with `requestVideoFrameCallback`
where available. Session teardown cancels that callback and late callbacks cannot
reschedule themselves. Without that API, a positive quality counter is used,
otherwise playback time is the compatibility fallback. The existing 15-second
stall threshold, two-second polling, backoff, autoplay/pause handling and security
checks remain. A continuously advancing clock cannot bypass a real freeze when
presentation callbacks are available.

Two focused regressions fail before the fix and pass after it; all ten Node
player tests pass. They cover zero quality counters with progressing presented
frames, actual frozen presentation despite advancing time, callback cleanup,
late callbacks and the older-browser fallback. JavaScript syntax checks pass.

Only `carstream/static/player.js` was atomically replaced on the board, with
the prior file in `.firefox-player-backup-20261119T033100Z/player.js`. The local,
board and certificate-verified public player SHA-256 is
`a0c659e0e6431e5d22ade8522f9cf38cbf508a6f149db70950d9aa621abcd082`.
The previous player hash is
`a529f7cc30083246aea911d6294f8f7ca42401e020c1703a5f30db9eff14a567`.
Application PID 28252 is unchanged; no restart, private environment, camera
quality, cloud proxy/TURN or network configuration changed. Firefox was refreshed
and connected through its ordinary password field; no token was typed into the
developer console or diagnostic source.

Actual Firefox presentation telemetry after deployment shows 369 presented
frames at playback time 19.725 seconds, then 1458 at 77.543 seconds, while its
quality frame counter remains zero. The real camera image is visible. This
verifies the compatibility mechanism, not full camera stability: the same round
also recorded `rtspsrc` resource errors 9 and 7 at 03:37:00-04 UTC, followed by
automatic recovery. Do not attribute every reconnect or prior native-client
failure to the browser counter, or claim the camera/network root cause is fixed.

Rollback only this static change, after checking for newer edits:

```bash
cd ~/magnet_car_project/cam
cp -p .firefox-player-backup-20261119T033100Z/player.js carstream/static/.player-rollback.js
mv carstream/static/.player-rollback.js carstream/static/player.js
```

Refresh the browser afterward; no service restart is needed. This restores the
old false-stall risk on Firefox, not private localhost access. The recovery
decision is maintained in the [existing player note](decisions/implemented/feature/2026-11-17-player-recovery.md).

### Domain cutover blocked by ICP filing response (2026-11-19)

The user supplied `8259200.xyz` with a proxied DNS record for
`carstream.8259200.xyz`, and explicitly selected standard HTTPS without a port.
DNS resolves that subdomain to Cloudflare. Its ordinary HTTPS proxy does not
support the existing 7777 port. Cloud port 443 is already owned by a separate
Nginx TCP passthrough service; no change to that listener was activated.

A temporary, hostname-scoped HTTP ACME challenge route was installed after
backing up the existing cloud configuration. Local validation returned 200,
and some public requests also reached the origin successfully. However, public
validation was inconsistent: Let's Encrypt received HTTP 403, and an independent
public request returned an HTML page titled **Non-compliance ICP Filing** with
an Alibaba Cloud filing-block URL. Origin access logs also contain successful
challenge requests, so local route success alone does not prove public
validation works. The observed public filing response is the deployment blocker;
the domain's actual filing/account status has not been checked in the console.

Two preceding certificate-authority connections timed out. A temporary
loopback-only SSH proxy allowed the ACME exchange to reach domain validation,
but did not resolve the public 403. Certificate issuance failed; no domain
certificate, renewal job, HTTPS router or application Origin change was
activated. No browser certificate verification was disabled. Resolve the
domain's filing/access status through Alibaba Cloud before retrying the cutover.

The temporary HTTP include and task-created challenge files were removed, the
system Nginx configuration passed validation and was reloaded, and the temporary
SSH forwarding process was stopped. Port 18790 is no longer listening. The
existing cloud proxy configuration, separate 443 configuration and private
environment match their backups byte-for-byte; the original proxy/TURN
containers were not restarted. The board application, token, quality settings,
exact IP-based Origin and tunnel remain unchanged. The active entrypoint is
still **https://8.130.208.68:7777**, with its original self-signed certificate.
Domain token submission and actual browser playback have not been tested.

Private preparation artifacts remain in
`/opt/carstream/private/domain-20261119/`: configuration backups, an ACME
account key, a domain key, CSR and the isolated acme-tiny 5.0.3 client. They are
not installed service credentials or a successful certificate deployment; do
not publish them or blindly rerun the one-off preparation. Undeployed local
Nginx drafts were removed. Only this blocked-state documentation is retained
as a tracked change.

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
| Board application | Replacement board `/home/linaro/magnet_car_project/cam`, historical activation PID 28252; always reread `server.pid` |
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

On the replacement board as `linaro`:

```bash
systemctl --user status carstream-tunnel
journalctl --user -u carstream-tunnel -n 100 -f
cd /home/linaro/magnet_car_project/cam
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
adjustment was deployed. Browser and long-term stability are not accepted.

### Correlated isolated viewer: playback gap after RTP packaging

After checkpoint commits were pushed to `origin/master` at `65301be`, a bounded
isolated viewer reused the production Python package and private settings on
board loopback port 18081. Only that diagnostic viewer had native per-stage
buffer counters and five-second UTC progress samples. Signaling used a temporary
SSH local forward with the configured public Origin and strong token; media
still selected relay/relay through the existing public TURN/TCP service. This
deliberately bypassed the public HTTPS/WSS proxy and did not replace or restart
the production service.

The 300-second observation window completed with 5765 decoded frames, but
recorded a 6.61-second interval between decoded frames after startup. Completion
only means it avoided the client's 20-second no-frame timeout; it is not smooth
playback acceptance. The initial frame wait was 4.87 seconds and is separate.

At 03:57:09 and 03:57:14 UTC, the same session's encoder output increased from
4795 to 4895 frames and RTP payloader output from 38969 to 39739 packets; active
source stages had about 0.02 seconds of inactivity at each sample. Meanwhile,
receiver progress showed a 3.37-second then 1.70-second age since its latest
decoded frame, and its reported loss counter rose from 617 to 1553. Decoding
recovered without reconnecting. The final source totals were 6020 encoded
frames and 48978 packaged RTP packets; the receiver reported 47378 packets
received and 1596 lost. No native source bus warning/error was observed.

For this particular gap, camera ingestion and MPP encoding continued; the
remaining investigation is after RTP packaging, including native WebRTC send,
TURN/network transport and receive/decode recovery. These counters do not
distinguish those causes, and they do not explain the earlier RTSP read errors
or establish that the public proxy was responsible. The next minimum evidence
is same-session sender transport statistics alongside receiver progress.

Both diagnostic processes exited normally. The board loopback listener and
temporary Mac forward were removed; active camera connections returned from two
to one. Production PID 137473 and the media hash below stayed unchanged, the
managed tunnel remained active with zero restarts, and verified public TLS
health returned alive. No media parameters, production files or credentials
were changed. The diagnostic findings were recorded after the pushed checkpoint.

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

<a id="native-video-retransmission"></a>

### Native NACK/RTX packet recovery

The installed GStreamer 1.20.3 transceiver default was `do-nack=false`.
The actual sender offer advertised H.264 and `nack pli`, but no generic NACK
or RTX. The application now enables native NACK/RTX before creating the offer.
The original synthetic test still checks decoded frames and the 1200-byte RTP
budget; the focused recovery regression can be run separately:

```bash
.venv/bin/python -B -m tests.smoke_retransmission
```

This test deliberately drops one known sequence after the sender RTX cache,
requires that exact original sequence to be retransmitted as RTX, then waits
for ten further decoded frames. It failed against the old offer and passes
with the repair. It is not a real-camera or browser acceptance test.

The native RTX history is capped at 1000 packets per viewer, about 1.2 MB of
maximum-size original RTP data plus native overhead. It is not an unbounded
queue or an added playback delay. A tracked `deep-element-added` handler
configures `rtprtxsend`; the regression checks the actual property. During
close, `webrtcbin` is stopped before the pipeline's hardware encoder so cached
buffers are released in time. The first RTX-only build failed the unchanged
strict cleanup test because DMA-buffer descriptors remained; after the
shutdown correction the final build passed ten real-relay allocation/close
cycles with 17 descriptors each, including Python/native finalization checks.

The first isolated real-camera 300-second trial with RTX and the native
100-packet default decoded 5796 frames, but its maximum steady-playback gap was
2.70 seconds. It therefore **failed** the new two-second continuity limit.
At the last sender sample, 3346 retransmission requests produced 3205 RTX
packets. Source and sender counters continued to advance; these observations
support a longer bounded history, not a claim that every remaining gap has
the same cause. The next trial checks the 1000-packet version without changing
camera parameters, authentication, bitrate, GOP, MTU, routes or TURN settings.

The complete repair rationale and limits are in the
[native recovery decision](decisions/implemented/bug-fix/2026-11-18-native-video-retransmission.md).

<a id="tunnel-server-heartbeat"></a>

### Dedicated tunnel server heartbeat

At 04:29:56 UTC the board's old SSH tunnel timed out. Subsequent automatic
restarts failed because the cloud's old `carstream-tunnel` sshd process still
owned loopback 17777. Board HTTP remained alive and the proxy/TURN containers
were running, but cloud requests to that reverse listener timed out.

After separate approval, only the dedicated account received the settings in
`deploy/cloud/sshd-carstream-tunnel.conf`: `ClientAliveInterval 15` and
`ClientAliveCountMax 3`, scoped with `Match User` and terminated by `Match all`.
This older host does not automatically include an `sshd_config.d` directory.
The candidate and installed configuration passed `sshd -t`; root and an
unrelated user's complete `sshd -T` output stayed identical, and the dedicated
account changed only those two fields. SSH was reloaded, not restarted.

Private backup: `/opt/carstream/private/sshd_config-before-heartbeat-20261118T043841Z`.
Original SSH configuration SHA-256:
`939a89a19b7147d7ab07b4e3e8aaa208cfe0b0aaa9ac367c88788852d7e31333`.
Installed SHA-256:
`658fb4ea3339779c5ecf5792586efab734e0d63a7df6eda208494c7fd87bdc96`.
The confirmed old listener child PID 13988, parent 13949, was identity-checked
and sent SIGTERM; no other SSH session or master was stopped. The board
automatically reconnected, cloud loopback and certificate-verified public
health returned alive, and new root SSH access worked. Historical tunnel
NRestarts was 86 after this recovery, not zero. No packet-blackhole fault
injection was performed, so a fixed recovery-time bound is not claimed.

To revert, compare the current SSH configuration with the installed hash,
preserve any newer edits, prepare the private backup as a candidate, validate
it with `sshd -t -f`, then replace and reload SSH. Do not blindly overwrite
later SSH changes or restart the daemon. Reverting removes server-side dead
peer detection and can reintroduce the abandoned-listener failure.
See the [heartbeat decision](decisions/implemented/bug-fix/2026-11-18-tunnel-server-heartbeat.md).

<a id="low-bandwidth-video-profile"></a>

### Explicit low-bandwidth hardware profile

Independent aioice packet tests used 1200-byte payloads at 160 packets/second,
without camera or GStreamer. On the Mac-to-TURN-to-Mac path, both eight-packet
bursts and uniformly spaced packets delivered all 1600 test packets. On the
board-to-TURN-to-Mac path, the first window received only 745 of 1600; the
following window was still affected by the earlier queue, and teardown did
not settle within its original bound. These are timely-delivery samples,
not a count of packets proved permanently lost or independent pacing trials.

At that time the board's TURN TCP socket had about 63 KB queued, reported
delivery rate 547016 bps and roughly 210 KB retransmitted. Original video
targets 1.5 Mbps before transport/RTX overhead. This establishes insufficient
timely throughput on that observed board path, not its precise dropping hop.
The source probe was stopped; its dependencies were installed only in
`/tmp/carstream-stability-20261118/transport-venv`, never the application venv.

After explicit approval to prefer stability over resolution, the application
adds `CARSTREAM_VIDEO_PROFILE=low-bandwidth`: H.265 MPP decode scales to
1280x720, and H.264 MPP uses a 350 kbps CBR target with 300-400 kbps bounds.
`original` is still the default. This is a selectable fixed profile, not
automatic bandwidth adaptation. H.264 camera passthrough rejects this profile
rather than silently ignoring it; the synthetic source remains 640x360.
The camera itself, credentials, routes, GOP, MTU and TURN policy do not change.
The isolated real-camera acceptance passed: 300 seconds after the first frame,
6031 decoded frames, actual 1280x720, maximum steady frame gap 1.556 seconds,
startup wait 1.13 seconds, relay/relay, no reconnect. Original packet arrivals
were 13163 and RTX arrivals 92. This bypassed public HTTPS/WSS signaling and
does not by itself prove the full production path or browser playback.

After that gate, production activated this profile at 05:21:04 UTC, historical
PID 148815, log `log/carstream-20261118T052104.459906832Z.log`. Media SHA-256:
`16f1eadeec0d466672f73f3fdcb352aaeb9175f0eeb08e32736af7515ada8b5f`.
Configuration SHA-256:
`42887e03107a48910856f69da108623f5808e24911f25c3fed0c9ca334ccf7ba`.
Private `.env` gained only `CARSTREAM_VIDEO_PROFILE='low-bandwidth'`; the
existing strong token, exact Origin, camera and TURN secrets stayed intact.
The full public-path trial is evaluated separately from the isolated result.

The production HTTPS/WSS plus TURN/TCP trial ended at 05:26:18 UTC with
4846 decoded 1280x720 frames over 300 seconds after the first frame, startup
wait 1.41 seconds and relay/relay media. It did not reconnect or hit the
20-second no-frame timeout, but the maximum steady frame gap was 2.183 seconds.
The unchanged two-second acceptance assertion correctly failed (exit 1).
Original packet arrivals were 13522 and RTX arrivals 153. This is an improved
finite observation, not a smoothness pass or browser acceptance. Two camera
TCP connections were observed during that trial; their combined bandwidth is
a capacity consideration, not proof that the other connection caused the gap.

A subsequent diagnostic-only 200 kbps experiment decoded 439 frames, then
stopped receiving media while its SSH transport also failed. The client timed
out and the SSH process exited 255 at 05:30:23 UTC. Public health returned 502;
the cloud's reverse listener was absent, unlike the earlier stale-listener
failure. At 05:36:27 UTC the listener was still absent and a fresh board SSH
connection timed out. Cloud SSH remained reachable. This does not identify
whether board power, its network, or another board-side failure is responsible.
No further bitrate reduction or network/service restart was deployed.

The experimental bitrate override and its test were removed locally; local
media/config hashes again match the recorded production build above. The board
diagnostic fixture may still contain the experiment, but is not production.
Its SSH process and local receiver have exited; the observer has a 400-second
lifetime setting, but final remote process/listener cleanup cannot be confirmed
while board access is unavailable. On reconnection, first inspect application
identity, tunnel state and this task's diagnostic processes; do not kill other
viewers. Recover connectivity before another full public acceptance trial.

Rollback backup `.profile-backup-20261118T051818Z` contains `media.py`,
`config.py` and private `.env` immediately before profile activation, with RTX
already enabled. To restore only the old quality using current code, set
`CARSTREAM_VIDEO_PROFILE='original'` in private `.env`, then use an
identity-checked `./stop.sh && ./start.sh`; this can reintroduce congestion.
For a complete profile-code rollback, stop first, compare current code/private
settings against the installed version and preserve newer edits, restore both
Python files and this task's private environment backup, then start. Never
use unrelated older weak-token backups. Neither rollback was executed.

See the [profile decision](decisions/implemented/bug-fix/2026-11-18-low-bandwidth-video-profile.md).

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
