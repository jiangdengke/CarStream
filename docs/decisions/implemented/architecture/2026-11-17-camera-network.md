# Agent Note: 摄像头网口使用持久静态地址

Status: implemented

## Problem

摄像头地址为 192.168.11.83，板子 eth0 虽已检测到物理链路，但现有 DHCP 连接没有获得 IPv4 地址。
访问摄像头时流量经 eth1 的上网网关发送，TCP 554 和 80 均超时。用户明确要求直接完成永久配置。

## Decision

使用板上现有 NetworkManager 1.36.6 管理摄像头网口，不增加第二套网络管理工具。
复用绑定 eth0 的 Wired connection 1，UUID 为 eeb55747-033d-3ed0-87b3-d5641bc753a7。
连接保存静态地址 192.168.11.82/24，开启自动连接，不配置 IPv4 网关和 DNS，设置 ipv4.never-default=yes。
启用 NetworkManager 自带的 IPv4 地址冲突检测，ipv4.dad-timeout 为 3000 毫秒；激活失败时恢复检查到的原设置。
eth1 的上网配置、默认路由、Tailscale 和运行中的 CarStream 服务保持不变，不重启板子或整个网络服务。

这是经用户批准的板端部署配置，不是应用自动配置网络的能力。
[Python 与 GStreamer 的媒体边界](2026-11-17-python-gstreamer.md)继续成立；应用和同步脚本不修改主机网络。
持久配置文件是 /etc/NetworkManager/system-connections/Wired connection 1.nmconnection。

## Alternatives considered

- 临时地址和摄像头专用主机路由便于测试后撤销，但重启不会保留，不符合本次永久配置要求。
- 保留现有 DHCP 配置可以避免手工分配地址，但当前连接没有获得地址且摄像头不可达，因此改用摄像头网段的静态地址。

## Consequences

摄像头网络不再依赖每次手动添加地址，默认上网流量仍经 eth1。代价是 192.168.11.82 必须保持不被其他设备占用，摄像头换网段时也需要同步修改此连接。
连接激活通过原生地址冲突检测，路由选择为 dev eth0 src 192.168.11.82，摄像头 TCP 554 和 80 均连接成功。
NetworkManager 报告 Unsaved=false，配置文件位于 /etc 且自动连接开启，证明不是仅运行时配置；未执行重启验收。
新建 SSH 连接成功，默认路由与修改前一致，板端和 Mac 转发后的 /healthz 均返回 HTTP 200。
本次不验证摄像头账号、编码或实际视频，不修改私有 .env，不将合成测试画面切换为摄像头。
原设置是 DHCP、空地址/网关/DNS、ipv4.never-default=no、ipv4.dad-timeout=-1、自动连接开启，且 eth0 未连接。
可执行撤销命令见[部署说明](../../../deployment.md#camera-setup)，撤销不涉及 eth1 或服务重启。

## Existing decision audit

检查现有两篇活跃记录：媒体边界与本决定部分重叠，双向链接明确部署配置与应用能力的区别；多观看者决定只涉及会话准入，与网口配置无关。
没有被本决定取代的旧决定，无需删除或归档。
