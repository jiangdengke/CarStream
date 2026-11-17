# CarStream

面向 **RK3588 + Ubuntu** 的网络摄像头直播项目，将 RTSP 视频转换为浏览器可播放的 WebRTC 视频。

应用使用 Python：aiohttp 负责网页、配置和 WebSocket 信令，GStreamer 负责取流、硬件编解码、RTP 和 WebRTC 传输。不依赖 Rust，也不需要厂商 SDK。

## 功能与当前状态

- **单摄像头、多人观看**：不设置固定观看人数上限，实际容量受摄像头连接数、板端资源和上行带宽限制。
- **测试画面**：默认提供明确标识的 640×360 实时合成彩条，不代表真实摄像头画面。
- **H.264 摄像头**：直接转发压缩视频，不重复解码、编码。
- **H.265 摄像头**：使用 Rockchip MPP 硬件解码，再编码为 H.264 Baseline 供浏览器播放。
- **访问控制**：访问令牌鉴权、同源校验，可配置 STUN/TURN。
- **播放器恢复**：点一次 Connect 后，断线或画面停滞时自动重试；Disconnect 停止重试。该修复已在本地完成，**尚未部署到板子**。

当前不包含摄像头自动发现、主机网络自动配置、录像、开机服务安装或公网部署。

### 验证进度

| 项目 | 状态 |
| --- | --- |
| Python 配置与信令测试 | 16 项通过，板端此前也已通过 |
| 播放器恢复逻辑 | 本地 8 项 JavaScript 测试通过，尚未板端实测 |
| 原生 WebRTC 测试源回环 | 已收到至少 10 个解码帧，验证 RTP 包不超过 1200 字节 |
| 浏览器测试彩条 | 已验证播放、刷新重连和两个页面同时观看 |
| 真实摄像头取流 | 已确认 H.265 Main、2304×1296、20 帧/秒，浏览器出现过真实画面 |
| 真实摄像头持续播放 | **未通过**：出现停帧和媒体会话错误，根因待定位 |
| 公网 HTTPS / TURN | **尚未部署、未验收** |

板端服务已切换为真实摄像头源，但后续 SSH 连接超时，网页转发也中断。因此，出现过画面不等于直播稳定性已通过；自动恢复逻辑也不能替代停帧根因修复。

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
| `TURN_URL` | 可选，格式为 `turn[s]://username:password@host:port`，凭据中的保留字符需要百分号编码 |
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

本地播放器支持以下行为，板端部署与真实摄像头验证仍待完成：

- WebSocket 中断、WebRTC 失败、媒体错误或首次连接超时后，自动创建新会话。
- 重试间隔依次为 1、2、4、8、16、30 秒，之后保持最长 30 秒；画面持续推进 10 秒才重置间隔。
- 每两秒检查视频进度，连接正常但约 15 秒没有新画面时重建会话。
- 主动 Disconnect、离开页面或访问令牌错误时停止重试；用户暂停和浏览器阻止自动播放不触发重连循环。

自动恢复不能保证故障期间无中断，也不能代替网络、摄像头或编解码问题的根因修复。完整边界见[播放器恢复说明](docs/deployment.md#player-recovery-local-change-not-yet-deployed)。

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
```

Python 单测使用媒体会话替身；JavaScript 测试使用模拟 DOM、连接和时钟，不需要额外 npm 依赖。这些测试不证明真实摄像头的解码、吞吐或长期稳定性。

媒体回环测试需要完整 GStreamer、ICE 和 H.264 解码器，要求至少 10 个解码帧，且实际发出的 RTP 包不超过 1200 字节。它不连接真实摄像头，也不等同于浏览器兼容性验收。`/healthz` 仅报告 HTTP 服务存活，不报告视频健康。

开发检查，在可访问系统 GI 的环境中执行 `uv sync --dev` 后运行：

```bash
uv run ruff check carstream tests
node --check carstream/static/player.js
bash -n scripts/install-ubuntu-deps.sh scripts/sync-board.sh
```

## 同步到板子

```bash
CARSTREAM_SSH_TARGET='cat@BOARD_IP' bash scripts/sync-board.sh
```

两端需要 SSH 和 rsync。脚本当前面向 `cat` 用户，发布目录固定在 `/home/cat/`；SSH 正常提示输入密码，不在代码中保存密码。

每次上传创建新的私有目录 `/home/cat/carstream-<UTC 时间戳>`，不会覆盖现有发布、上传 `.env` 或 `.venv`、安装依赖、修改网络或启动服务。上传超时或非零退出表示同步不完整，不要启动该目录中的服务。

## 公网访问与安全

- 公网访问需要单独配置 HTTPS 反向代理和可达的板端后端，并按精确来源设置 `PUBLIC_ORIGIN`。
- HTTP 代理或 SSH 隧道不会自动转发 WebRTC 媒体；需要独立验证直连或部署 TURN，并检查云安全组和主机防火墙。
- 使用 `ICE_POLICY='relay'` 和外网浏览器验收 TURN，确认实际收到解码视频且选中的候选对来自中继。
- 不要直接公开摄像头 RTSP 端口，也不要在公网暴露私有调试 HTTP 服务。
- 当前使用共享访问令牌，不是完整的用户账号、权限管理或生产级防滥用系统。
- 不要公开 `.env`、完整带凭据的 RTSP/TURN 地址或可能包含凭据的原生调试日志。

项目尚未完成阿里云 HTTPS/TURN 部署。详细步骤与回滚边界见[公网部署说明](docs/deployment.md#public-access-through-alibaba-cloud)。

设计依据：[Python 与 GStreamer 的职责边界](docs/decisions/implemented/architecture/2026-11-17-python-gstreamer.md)。
