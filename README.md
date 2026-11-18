# CarStream

面向 **RK3588 + Ubuntu** 的网络摄像头直播项目，将 RTSP 视频转换为浏览器可播放的 WebRTC 视频。

应用使用 Python：aiohttp 负责网页、配置和 WebSocket 信令，GStreamer 负责取流、硬件编解码、RTP 和 WebRTC 传输。不依赖 Rust，也不需要厂商 SDK。

## 功能与当前状态

- **单摄像头、多人观看**：不设置固定观看人数上限，实际容量受摄像头连接数、板端资源和上行带宽限制。
- **测试画面**：默认提供明确标识的 640×360 实时合成彩条，不代表真实摄像头画面。
- **H.264 摄像头**：直接转发压缩视频，不重复解码、编码。
- **H.265 摄像头**：使用 Rockchip MPP 硬件解码，再编码为 H.264 Baseline 供浏览器播放。
- **访问控制**：访问令牌鉴权、同源校验，可配置 STUN/TURN。
- **播放器恢复**：点一次 Connect 后，断线或画面停滞时自动重试；Disconnect 停止重试。该修复已部署到板子，浏览器已验证信令中断后自动恢复真实摄像头画面。

当前不包含摄像头自动发现、主机网络自动配置或录像。阿里云公网入口已独立部署；应用仍手动启停，只有 SSH 反向隧道配置了自动重连和开机启动。

### 验证进度

| 项目 | 状态 |
| --- | --- |
| Python 配置与信令测试 | 本地 18 项通过，另有 8 项 Linux 启停测试已在板端隔离执行通过 |
| 播放器恢复逻辑 | 本地 8 项 JavaScript 测试通过；板端已部署，浏览器信令中断后自动恢复出画 |
| 原生 WebRTC 测试源回环 | 已收到至少 10 个解码帧，验证 RTP 包不超过 1200 字节 |
| 浏览器测试彩条 | 已验证播放、刷新重连和两个页面同时观看 |
| 真实摄像头取流 | 已确认 H.265 Main、2304×1296、20 帧/秒，浏览器出现过真实画面 |
| 真实摄像头持续播放 | **未通过**：两项已复现缺陷已修复部署，板端隔离取流推进 180 秒，但公网 300 秒目标测试仍因停帧失败 |
| 公网 HTTPS / TURN | 已部署；早期 60 秒试验解码 992 帧；最新延长试验最后周期样本为第 163 秒、2352 帧，随后 20 秒无新帧超时，未通过 |

板端服务使用真实摄像头源，SSH 和本机网页转发已恢复。播放器静态文件已更新，无需重启服务；浏览器仅点一次 Connect，信令中断后自动恢复播放。但后续观察再次出现停帧，页面自动重试仍未恢复持续播放，媒体或传输问题尚未解决。

2026-11-18 已配置独立公网入口 **https://8.130.208.68:7777** 和 TURN/TCP，并重启应用启用强令牌。随后修复并部署了会话关闭后原生回调未释放、摄像头后续 SSRC 输出未连接两项问题；回归通过，但公网延长测试仍停帧。同期应用记录 RTSP 读取错误，隧道没有重启；尚不能确认剩余停流根因，也不能仅凭接收端丢包统计归咎某段网络。访问方式见下方“公网访问与安全”。

具体证据见 [progress.md](progress.md)，部署现状见[摄像头源试运行记录](docs/deployment.md#current-camera-source-trial)。

## 运行环境

- Python 3.10 或更新版本。
- Ubuntu 系统的 GI、GStreamer、WebRTC 和 ICE 组件。
- RK3588 上保留厂商提供的 `mppvideodec`、`mpph264enc` 等插件。
- JavaScript 测试需要 Node.js 18 或更新版本；板端正常运行不需要 Node.js。

已检查的板端环境为 Ubuntu 22.04.5、Python 3.10.12、GStreamer 1.20.3。其他系统需要独立验证插件兼容性。

## 快速开始

以下命令在 **Ubuntu 板子的项目目录**中执行。安装依赖是独立操作，同步脚本不会自动执行安装。

```bash
bash scripts/install-ubuntu-deps.sh
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m carstream --check
```

安装前请检查脚本的 apt 安装列表，尤其是使用厂商系统镜像时。不要替换板子现有的 Rockchip MPP 组件。

`--system-site-packages` 用于访问系统提供的 GI 绑定；不要尝试仅通过 pip 安装 PyGObject 来替代系统依赖。

### 1. 创建私有配置

```bash
cp .env.example .env
chmod 600 .env
```

生成随机访问令牌：

```bash
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

将结果填入 `.env` 的 `CARSTREAM_ACCESS_TOKEN`。首次测试保留 `CARSTREAM_SOURCE='test'`，先确认浏览器链路，再接入摄像头。

**不要提交 `.env`，也不要把摄像头密码写入 README、测试或公开日志。**

### 2. 加载配置并启动

```bash
set -a
. ./.env
set +a
.venv/bin/python -m carstream
```

服务**不会自动读取 `.env`**，必须先加载环境变量。`.env` 是可信的 shell 配置文件，不是用于接收外部上传的文件格式。

### 3. 打开浏览器

在板子本机打开 `http://127.0.0.1:8080`，输入访问令牌后点击 Connect。不需要授予浏览器麦克风或摄像头权限。

从另一台可以 SSH 访问板子的电脑观看时，在该电脑上建立转发，将 `BOARD_IP` 替换为实际板子地址：

```bash
ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 cat@BOARD_IP
```

然后在这台电脑的浏览器打开 `http://127.0.0.1:18080`。`127.0.0.1` 始终指当前设备，不是板子的局域网地址。

**SSH 转发只承载网页和信令，不承载 WebRTC 媒体。** 视频仍需要可达的 ICE 直连路径或 TURN 中继。

以上本机访问方式适用于未设置 `PUBLIC_ORIGIN` 的私有配置。当前已部署服务固定校验公网 HTTPS Origin，请从 `https://8.130.208.68:7777` 观看；本机或旧 SSH 页面可能打开，但 Connect 会因来源不符被拒绝，不要为此关闭同源校验。

## 启动、停止与重启

以下服务命令在 **Ubuntu 板子上使用 Bash 执行**，依赖系统的 `ss` 和 `flock`。当前发布目录为 `/home/cat/carstream-20261117T060914Z`；后续换发布目录时，相应替换路径。已部署的 `.env` 和 `.venv` 直接复用，不要重新覆盖配置。

先从电脑登录板子，将 `BOARD_IP` 替换为板子地址：

```bash
ssh cat@BOARD_IP
cd /home/cat/carstream-20261117T060914Z
```

### 启动服务

```bash
./start.sh
```

直接执行即可后台启动，不需要额外加 `&` 或 `nohup`。脚本自动定位项目目录、加载 `.env` 并校验应用配置，退出 SSH 后仍继续运行。重复调用时，如果记录的进程属于当前发布，会提示已经运行；端口被占用或 PID 属于其他进程时拒绝启动。

脚本使用 `.env` 中的端口，默认 8080；最多等待约 10 秒确认新进程已监听端口，启动失败返回非零状态。超时但进程仍在时保留 PID，按提示检查日志、先停止再重试，不会谎报成功。

`server.pid` 保存进程号，`server.lock` 防止启动和停止操作重叠。脚本不安装依赖、不改网络，也不配置开机自启。

### 日志目录

每次实际启动单独创建一个日志文件，标准输出和错误输出统一写入项目根目录的 `log/`，启动时会打印完整日志路径，例如：

```text
log/carstream-20261117T100000.123456789Z.log
```

文件名使用 UTC 启动时间，精确到纳秒；一次运行只写这个文件，重启生成新文件，重复调用已运行的服务不会产生新日志。不做跨天切分或自动清理，历史日志不会被覆盖，需自行关注磁盘占用。旧版本的 `server.log` 不会被删除或迁移。

`log/` 权限为 0700，日志和 PID 文件权限为 0600。日志、PID 和锁文件不提交到 Git，也不会由同步脚本上传。

### 检查状态与日志

```bash
service_pid="$(<server.pid)"
ps -p "$service_pid" -o pid=,args=
readlink -f "/proc/$service_pid/cwd"
curl --fail --max-time 5 http://127.0.0.1:8080/healthz
latest_log="$(ls -1t log/*.log | head -n 1)"
tail -n 50 "$latest_log"
```

修改过端口时同步替换上述访问地址。`server.pid` 存在不代表进程仍在运行；`/healthz` 成功仅说明 HTTP 服务存活，不代表视频播放正常。日志可能包含运行信息，不要直接公开。

### 停止服务

```bash
./stop.sh
```

脚本不依赖 `.env`，先核对 `server.pid`、进程命令和工作目录，只向当前发布的 CarStream 发送 SIGTERM。最多等待约 30 秒；退出后删除 PID 文件，超时则保留 PID 并报错，不发送强制结束信号。过期 PID 会清理，无 PID 时不会扫描或结束其他进程。

如果原来在终端前台手动启动，回到那个终端按 `Ctrl+C`；这类进程没有脚本管理的 PID 文件。若 PID 身份不符，先用 `ss -ltnp 'sport = :8080'` 和进程命令确认实际服务，不要使用 `pkill python`。

**停止服务会中断所有观看者。** 浏览器里的 Disconnect 只停止当前页面观看，不会关闭板端服务。

### 重启与停止网页转发

重启服务，修改 `.env` 后也执行同一条命令：

```bash
./stop.sh && ./start.sh
```

- **前台调试**：仍可按上方“加载配置并启动”手动运行，在原终端按 `Ctrl+C` 停止，不要与后台服务同时运行。
- **停止网页转发**：如果 SSH 转发在电脑终端前台运行，在那个终端按 `Ctrl+C`。这不会停止板端服务；观看时需要重新建立转发。
- 当前未为 Python 应用配置 systemd 单元或开机自启，不要使用 `systemctl start/stop carstream`；本文命令用于手动管理进程。

根目录的两个启停脚本已部署到当前板端发布，`log/` 已创建；原 `server.log` 保留。公网部署另有 `carstream-tunnel` 用户级服务，只管理隧道，不负责启动 Python 应用。详细边界见[启停脚本说明](docs/deployment.md#startstop-scripts)。

## 配置项

所有配置项均以 `CARSTREAM_` 为前缀。下表省略此前缀，完整示例见 [.env.example](.env.example)。

| 配置项 | 说明 |
| --- | --- |
| `HOST` / `PORT` | 默认 `127.0.0.1` / `8080`，仅监听板子回环地址 |
| `ACCESS_TOKEN` | 必填，默认至少 24 个字符，建议使用随机令牌 |
| `ALLOW_WEAK_TOKEN` | 默认 `false`；短令牌仅允许显式开启、绑定 `127.0.0.1` 或 `::1` 且不设置 `PUBLIC_ORIGIN` 的私有调试 |
| `SOURCE` | `test` 或 `rtsp`，默认 `test` |
| `RTSP_URL` | 摄像头完整取流地址，`rtsp` 模式必填 |
| `CAMERA_USERNAME` / `CAMERA_PASSWORD` | 摄像头账号密码，与板子的 SSH 凭据、网页访问令牌不同 |
| `CAMERA_CODEC` | `h264` 或 `h265`，默认 `h264`，不自动探测 |
| `ENCODER` | `auto`、`mpph264enc` 或 `x264enc`；自动选择优先 MPP，H.264 透传不使用编码器 |
| `PUBLIC_ORIGIN` | 浏览器访问的精确来源，如 `https://video.example.com`，不带路径或末尾斜杠 |
| `STUN_URL` | 可选，格式为 `stun://host:port` |
| `TURN_URL` | 可选，格式为 `turn[s]://username:password@host:port`，支持 `?transport=tcp` 或 `?transport=udp`，`turns` 只允许 TCP；凭据中的保留字符需要百分号编码 |
| `ICE_POLICY` | `all` 或 `relay`；`relay` 必须配置 TURN |

短令牌开关不是生产安全方案。公开部署前关闭该开关并更换强令牌；仅绑定回环地址，也不能防止反向代理或 SSH 转发把服务暴露出去。

## 接入真实摄像头

1. 先确认板子能够到达摄像头网段，且 RTSP 服务可连接。应用不会修改主机 IP、路由或网关。
2. 使用摄像头提供的完整 RTSP 地址验证取流和编码，不要根据开放端口或设备名称猜测路径。
3. 在私有 `.env` 中设置 `CARSTREAM_SOURCE='rtsp'`、`CARSTREAM_RTSP_URL`、实际 `CARSTREAM_CAMERA_CODEC`，按需填写摄像头账号密码。
4. 重新加载环境变量并重启服务，再验证浏览器解码帧数持续增长，而不只是页面显示 connected。

当前忽略音频，摄像头侧使用 RTSP over TCP。H.264 透传会保留摄像头原始 profile 和 level；若浏览器不兼容，需要调整摄像头输出，单纯重新打包无法修复。

每位观看者使用独立媒体管线，RTSP 模式下也会独立连接摄像头。测试源和 H.265 转码还会使用独立编码会话，**没有固定观看人数上限不等于硬件容量无限**。

部署与故障记录见 [docs/deployment.md](docs/deployment.md)。

## 自动恢复

已部署的播放器支持以下行为；浏览器已实测信令中断后恢复出画、停帧触发重试和主动停止，其他故障分支由逻辑测试覆盖。停帧后的持续播放仍未通过：

- WebSocket 中断、WebRTC 失败、媒体错误或首次连接超时后，自动创建新会话。
- 重试间隔依次为 1、2、4、8、16、30 秒，之后保持最长 30 秒；画面持续推进 10 秒才重置间隔。
- 每两秒检查视频进度，连接正常但约 15 秒没有新画面时重建会话。
- 主动 Disconnect、离开页面或访问令牌错误时停止重试；用户暂停和浏览器阻止自动播放不触发重连循环。

自动恢复不能保证故障期间无中断，也不能代替网络、摄像头或编解码问题的根因修复。完整边界见[播放器恢复说明](docs/deployment.md#player-recovery-deployed)。

## 测试与检查

配置、信令和播放器逻辑测试：

```bash
.venv/bin/python -m unittest discover -s tests -v
node --test tests/player.test.cjs
```

原生运行环境检查与可选媒体回环测试：

```bash
.venv/bin/python -m carstream --check
.venv/bin/python -m tests.smoke_media
.venv/bin/python -m tests.smoke_rtsp
.venv/bin/python -m tests.smoke_cleanup
```

Python 单测使用媒体会话替身；JavaScript 测试使用模拟 DOM、连接和时钟，不需要额外 npm 依赖。这些测试不证明真实摄像头的解码、吞吐或长期稳定性。

另有 8 项启停脚本集成测试，在具备 `ss` 和 `flock` 的 Linux 上使用临时目录、临时端口和模拟 HTTP 服务执行，验证直接执行、后台运行和按启动时间保留日志，不连接真实摄像头；macOS 自动跳过这些检查。

媒体回环测试需要完整 GStreamer、ICE 和 H.264 解码器，要求至少 10 个解码帧，且实际发出的 RTP 包不超过 1200 字节。它不连接真实摄像头，也不等同于浏览器兼容性验收。`/healthz` 仅报告 HTTP 服务存活，不报告视频健康。
RTSP pad 回归仅模拟同一摄像头的 SSRC 0/1 动态输出，不连接真实摄像头。清理回归使用测试视频；若环境中加载了 TURN 配置，会等待实际 relay 候选后关闭十次，核对 Python/原生对象终结和文件描述符是否回到基线。
已复现的原生回调泄漏与后续视频输出未连接已修复并部署；持续播放验收和回滚见[RTSP 稳定性排查](docs/deployment.md#rtsp-stability-repair)。局部缺陷修复不等于长期稳定性保证。

开发检查，在可访问系统 GI 的环境中执行 `uv sync --dev` 后运行：

```bash
uv run ruff check carstream tests
node --check carstream/static/player.js
bash -n scripts/install-ubuntu-deps.sh scripts/sync-board.sh start.sh stop.sh
```

## 同步到板子

```bash
CARSTREAM_SSH_TARGET='cat@BOARD_IP' bash scripts/sync-board.sh
```

两端需要 SSH 和 rsync。脚本当前面向 `cat` 用户，发布目录固定在 `/home/cat/`；SSH 正常提示输入密码，不在代码中保存密码。

每次上传创建新的私有目录 `/home/cat/carstream-<UTC 时间戳>`，不会覆盖现有发布、上传 `.env` 或 `.venv`、安装依赖、修改网络或启动服务。上传超时或非零退出表示同步不完整，不要启动该目录中的服务。

## 公网访问与安全

当前入口为 **https://8.130.208.68:7777**，必须使用 `https`。首次打开会提示自签证书；核对证书指纹后再信任，正式对外使用应换成域名和受信任证书。当前证书到期时间为 **2027-02-16 02:10:20 UTC**，不会自动续期。

在自己电脑终端获取访问令牌，不要把结果贴到公开聊天或日志：

```bash
ssh company 'set -a; . /opt/carstream/private/public-access.env; printf "%s\n" "$CARSTREAM_ACCESS_TOKEN"'
```

将结果填入页面的 Access token，点击 Connect。旧令牌 `jiangdk` 已失效。云端强令牌与 TURN 密码分别随机生成，摄像头凭据不变；源码和文档不包含这些密钥。

网页和信令经云端 `7777` → 回环 `17777` → 板端 `8080`；媒体使用独立 TURN `3478/TCP`。访问者不需要加入 Tailscale。公网 UDP 探测超时，当前配置强制两端中继并显式使用 TCP；不是“所有流量都只走 7777”。

- 公网访问需要单独配置 HTTPS 反向代理和可达的板端后端，并按精确来源设置 `PUBLIC_ORIGIN`。
- HTTP 代理或 SSH 隧道不会自动转发 WebRTC 媒体；需要独立验证直连或部署 TURN，并检查云安全组和主机防火墙。
- 使用 `ICE_POLICY='relay'` 和外网浏览器验收 TURN，确认实际收到解码视频且选中的候选对来自中继。
- 不要直接公开摄像头 RTSP 端口，也不要在公网暴露私有调试 HTTP 服务。
- 当前使用共享访问令牌，不是完整的用户账号、权限管理或生产级防滥用系统。
- 不要公开 `.env`、完整带凭据的 RTSP/TURN 地址或可能包含凭据的原生调试日志。

部署维护、证书指纹、日志、停止公网入口和回滚方式见[公网部署说明](docs/deployment.md#public-access-through-alibaba-cloud)。公网基础设施已配置，不代表多浏览器兼容性、断线恢复、容量或长期稳定性已验收；云主机 Ubuntu 18.04 和旧 Docker 仍有独立维护风险。

设计依据：[Python 与 GStreamer 的职责边界](docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md)。
