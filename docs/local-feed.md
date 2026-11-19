# 板子本机供流接口

## 给接收方的连接信息

- 协议：WebRTC，使用本项目的 WebSocket JSON 信令，不是 WHEP。
- 本机信令地址：`ws://127.0.0.1:8081/ws`。
- 认证：沿用现有 `CARSTREAM_ACCESS_TOKEN`，通过私下渠道提供，不写入 URL、日志或前端代码。
- WebSocket 握手：**不发送 `Origin` 请求头**。这个入口只供原生后端客户端使用，带有任何 `Origin`（包括空值或 `null`）都会返回 403。
- 视频：H.264，沿用当前摄像头源和画质。当前板端配置为 H.265 转码、2304×1296、20 fps、原画质档位。
- 接收端和发送端不配置 STUN/TURN，接收端使用 `iceServers: []`、`iceTransportPolicy: "all"`，通过 host 候选直接协商。

本地址用于**运行在板子主机网络中的后端服务**，不是让终端用户浏览器直接打开的播放 URL。
普通 Docker 容器里的 `127.0.0.1` 指容器本身；隔离容器不能直接使用这个地址。当前接口不自动调整容器网络，也不监听局域网地址。

## 信令流程

1. 接收后端建立上述 WebSocket。连接后 10 秒内发送认证消息：

   ```json
   {"type":"auth","token":"<私下提供的访问令牌>"}
   ```

2. 认证成功后服务端发送 `ready`；认证失败发送 `error` 并关闭，不创建媒体管线：

   ```json
   {"type":"ready","source":"rtsp","iceServers":[],"iceTransportPolicy":"all"}
   ```

3. 服务端发送 offer，接收方设置远端描述、创建 answer、设置本地描述，然后回传 answer：

   ```json
   {"type":"offer","sdp":"<服务端 SDP>"}
   ```

   ```json
   {"type":"answer","sdp":"<接收方 SDP>"}
   ```

4. 双方持续交换 ICE 候选。远端描述设置完成之前收到的候选应先缓存，之后按序加入：

   ```json
   {"type":"ice","candidate":"candidate:...","sdpMLineIndex":0}
   ```

5. 接收方通过自己的 WebRTC 接收回调取得视频轨道/RTP。媒体通过协商出的 DTLS/SRTP 连接传输，**不是从 WebSocket 消息里读取视频字节**。保持 WebSocket 存活并响应 ping；关闭 WebSocket 会释放该媒体会话。协商须在 30 秒内完成。

服务端错误统一使用 `{"type":"error","message":"..."}`。接收方负责断开重连和重新协商；重连后是新的媒体会话。
完整接收示例见 [原生本机收流检查](../tests/smoke_local_feed.py)，它只解码验证、不保存图像，不是下游分发服务器。

## 我方与对方的责任

- 我方负责通过此入口认证并交付视频，维护摄像头接入和本次 WebRTC 发送会话。
- 对方后端必须真正终止 WebRTC、接收媒体，之后负责转推、网页播放协议、下游鉴权、带宽和重连等。
- 只代理 WebSocket 信令、不接收媒体，不等于完成后端收流和后续分发。
- 无需向我方提供对方网页地址。公网原页面仍走原来的 8080 信令入口和云端 TURN，既有精确 Origin 校验不变。

每个本机接收连接同样创建独立摄像头/转码会话，与公网观看并存会增加板端和摄像头负载。本次不增加共享转码、多级媒体服务器或容量承诺。

## 运维配置与验证

在板端 `.env` 中设置 `CARSTREAM_LOCAL_PORT='8081'` 后，通过原有启停脚本重启。默认值 `0` 表示关闭本机供流，端口必须与 `CARSTREAM_PORT` 不同。
本机监听地址固定为 `127.0.0.1`，不随公网 `HOST` 改成全网监听。启停脚本检查并等待两个监听端口，停止时统一清理公网和本机媒体会话。

不要把 8081 加入云端代理、反向 SSH 转发或其他公开反代。公网隧道请求到板子时也可能呈现回环来源，因此本项目不根据请求来源地址或 `X-Forwarded-For` 放宽 8080 的 Origin 校验；隔离依赖独立监听端口。
没有 Origin 不代表请求可信，token 校验始终保留。双方不配置 TURN 才是当前本机直连契约；接收方不应自行加入云端 TURN。

板子上从可信 `.env` 加载环境变量后，执行：

```bash
cd ~/magnet_car_project/cam
set -a
. ./.env
set +a
curl --fail --max-time 5 http://127.0.0.1:8081/healthz
.venv/bin/python -B -m tests.smoke_local_feed
```

原生检查最多等待 45 秒，要求解码至少 100 帧，校验双方交换的 ICE 候选均为 host，并且认证后的 ICE 服务器为空。它不保存媒体、令牌或 SDP，也不证明长期连续播放已经达标。
生产部署证据和可执行回滚见[部署记录](deployment.md#independent-local-feed-2026-11-19)；设计取舍见[本机供流决定](decisions/implemented/architecture/2026-11-19-local-feed.md)。
