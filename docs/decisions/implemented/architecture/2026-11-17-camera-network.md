# Agent Note: 摄像头网口使用持久静态地址

Status: implemented

## Problem

摄像头地址为 192.168.11.83，DHCP 配置没有为摄像头专用网口提供同网段地址，导致取流失败。
保存的静态 NetworkManager 配置与 Netplan 的 DHCP 来源不一致，重启生成的配置不能保留预期地址。
用户确认摄像头使用 enP3p49s0 和 192.168.11.88，并要求沿用该设置。

## Decision

使用板上现有 NetworkManager 1.36.6 管理摄像头网口，不增加第二套网络管理工具。
复用绑定 enP3p49s0 的 netplan-enP3p49s0，UUID 为 a61d4cd9-2c83-3d5b-b0fb-5628b27d3ac7。
连接保存静态地址 192.168.11.88/24，开启自动连接，不配置 IPv4 网关和 DNS，设置 ipv4.never-default=yes。
启用 NetworkManager 自带的 IPv4 地址冲突检测，ipv4.dad-timeout 为 3000 毫秒；激活失败时恢复检查到的原设置。
Netplan 来源与保存及运行时的摄像头 profile 保持一致，避免下次生成时退回 DHCP。
只激活摄像头连接，USB 网卡和 Wi-Fi 的上网配置及默认路由保持不变，不重启板子、整个网络服务或 CarStream。

这是经用户批准的板端部署配置，不是应用自动配置网络的能力。
[Python 与 GStreamer 的媒体边界](2026-11-17-python-gstreamer.md)继续成立；应用和同步脚本不修改主机网络。
持久来源为 /etc/netplan/config.yaml 和 /etc/NetworkManager/system-connections/netplan-enP3p49s0.nmconnection。
对应生成配置位于 /run/NetworkManager/system-connections/netplan-enP3p49s0.nmconnection。

## Alternatives considered

- 临时地址和摄像头专用主机路由便于测试后撤销，但重启不会保留，不符合本次永久配置要求。
- 保留现有 DHCP 配置可以避免手工分配地址，但当前连接没有获得地址且摄像头不可达，因此改用摄像头网段的静态地址。
- 只保存 NetworkManager 静态 profile 改动最少，但 Netplan 来源仍会生成 DHCP 配置，因此同步修正摄像头的 Netplan 来源。

## Consequences

摄像头地址与用户选择一致，并写入持久来源；代价是 192.168.11.88 必须保持不被其他设备占用，摄像头换网段时需要同步修改来源与 profile。
离线 Netplan 生成验证通过，只有目标摄像头 profile 的输出变化，另一网口的生成配置不变。
连接激活通过原生地址冲突检测，路由选择为 dev enP3p49s0 src 192.168.11.88，摄像头 TCP 554 和 80 均连接成功。
本机入口实测解码 100 帧 2304x1296 视频，仅交换 host ICE，无云端 ICE 服务器。
摄像头口原有的高 metric 默认路由被移除；USB 和 Wi-Fi 上网默认路由、其他网口地址及 profile、私有环境和应用文件哈希保持不变，CarStream PID 5220 未变。
公网 HTTP 正常，但使用 :7777 Origin 的外部视频检查返回 403，当前服务 Origin 缺少端口；本次没有修改或修复公网鉴权配置。
未执行重启验收或长期播放验收；最后一次组合元数据检查非零退出，不作为新增验证依据。
可执行撤销命令与私有备份路径见[部署说明](../../../deployment.md#current-camera-network-after-reboot-2026-11-20)，撤销不涉及上网网口或应用重启。

## Existing decision audit

检查现有两篇活跃记录：媒体边界与本决定部分重叠，双向链接明确部署配置与应用能力的区别；多观看者决定只涉及会话准入，与网口配置无关。
没有被本决定取代的旧决定，无需删除或归档。
