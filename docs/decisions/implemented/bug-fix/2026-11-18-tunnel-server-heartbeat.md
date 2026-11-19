# Agent Note: 专用隧道启用双向失活检测

Status: implemented

## Problem

公网复测时板端应用健康、云端 HTTPS 与代理容器正常，但云端回环 17777 的 HTTP 请求不返回。板端日志显示旧 SSH 客户端超时退出，自动重试持续报 remote port forwarding failed。
云端该端口仍被旧专用账号 sshd 进程占用；客户端失活检测不能主动清理服务端半开连接。服务端有效配置 ClientAliveInterval=0，使 systemd 重启客户端也无法重建同一监听。

## Decision

云端 SSH 仅对 carstream-tunnel 专用账号设置 ClientAliveInterval=15、ClientAliveCountMax=3。已有板端 ServerAliveInterval=15、ServerAliveCountMax=3 与五秒自动重试保持不变；两端分别检测失活，不修改 TCP 系统参数、防火墙、路由、转发范围或其他用户鉴权。

此旧主机没有自动包含 sshd_config.d 的配置，部署使用 deploy/cloud/sshd-carstream-tunnel.conf 中的 Match User 块追加到主配置，并用 Match all 结束作用域。应用前保存权限为 0600 的完整备份，使用 sshd -t 验证候选；sshd -T 比较 root、其他用户的全部有效配置均不变，专用账号只允许两个心跳字段变化。
验证后只 reload SSH，不重启主服务。首次清理仅终止已确认占用 17777、属于专用账号且父进程身份一致的失效 sshd 子进程；绝不使用 pkill sshd 或结束其他用户会话。

本决定部分取代[初次公网部署](../architecture/2026-11-18-public-access.md)中“不修改 SSH 服务端配置”的边界，其他公网拓扑与权限约束保留；此次变更已获用户单独确认。

## Testing

旧监听由专用账号进程 13988 持有，其父进程为 13949；云端到 17777 的请求超时，板端连续重试占位失败。应用经过语法及有效配置对比的专用心跳后，只关闭这个旧进程。板端自动重连，新监听由另一专用账号进程持有，17777 返回 alive，公网验证证书的 HTTPS 健康请求也返回 alive。
root 的新 SSH 会话正常，两个既有容器持续运行。有效专用配置为 15/3，其他用户配置未变化；备份、哈希和操作时间见[部署记录](../../../deployment.md#tunnel-server-heartbeat)。未做丢弃网络流量的故障注入，也不声称恢复时延已实测达到固定上限。

## Alternatives considered

- 仅结束旧连接能立即恢复，但下一次客户端单边超时仍可能留下同样占位，因此同时补服务端检测。
- 全局设置 ClientAliveInterval 更简单，但会影响现有 SSH 用户；专用 Match 块限制此次变更范围。
- 修改系统 TCP keepalive 可以清理半开连接，但影响所有 TCP 连接且默认回收可能很慢；不需要为一个独立隧道修改全局网络参数。

## Consequences

收益是失活服务端连接可主动退出，客户端自动重连不再无限等待旧端口。代价是专用账号在持续无响应时会被服务端断开，后续由原有 systemd 重建；故障期间网页和信令仍可能短暂中断，不保证视频无停顿。
该修复不改变 TURN 媒体路径。公网入口恢复后真实视频仍有首帧超时，不能将全部媒体卡顿归因于这个隧道；[原生 NACK/RTX 修复](2026-11-18-native-video-retransmission.md)与其验证缺口独立记录。

## Existing decision audit

检索八篇活跃记录：初次公网部署与本次局部边界变更部分重叠，以互链保留其余拓扑、安全与旧主机风险。启停流程、播放器恢复部分关联但决定未变。其余媒体、摄像头网络和多人观看不被取代；没有可删除或归档的被完全吸收记录。
