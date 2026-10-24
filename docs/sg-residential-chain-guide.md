# 新加坡住宅链式代理使用说明

这份说明配套仓库中的脱敏覆写模板：

```text
openclash/sg-residential-chain.conf
```

模板只保存链式代理结构，住宅代理的服务器地址、端口、账号和密码用 `${RESIDENTIAL_*}` 环境变量引用。真实值只填写在路由器 OpenClash 覆写模块的「环境变量」里。

## 一、这套配置解决什么问题

配置把需要稳定住宅出口的 Claude、OpenAI 流量按下面的路径转发（`singapore.yaml` 里的新加坡网站优先走同一路径）：

```text
客户端 → OpenClash → 新加坡机场节点 → 新加坡住宅 SOCKS5 → AI 服务
```

Gemini 等其他海外 AI、普通网页、下载和大多数 UDP 流量仍按原有规则分流，不经过住宅双跳。这样可以保持 AI 出口稳定，同时避免住宅链拖慢普通下载。

## 二、各部分的作用

### `[General]`

- 使用 Meta/Mihomo 核心并保持规则模式。
- 用 `fake-ip-mix` 接管 TCP、UDP 和 DNS。
- 禁用 IPv6，防止住宅代理只有 IPv4 时出现 IPv6 旁路。
- 禁用 QUIC，使 AI 的 HTTPS 连接使用更稳定的 TCP。
- 更新并启用模块后自动重启 OpenClash。

### `dns` 与 `sniffer`

- 默认 `nameserver` 只用经 `♻️ 自动选择` 代理的 Cloudflare / Google DoH，国内 DNS 看不到国外域名，DNS 泄露检测不会出现国内运营商或阿里、腾讯的 DNS。
- Claude 与 OpenAI 域名分别通过 `🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 查询，DNS 出口与连接出口一致。
- `geosite:cn,private` 用国内 DoH，国内网站解析结果不受影响。
- `proxy-server-nameserver` 只解析机场节点自身的域名，`direct-nameserver` 只解析直连流量的域名，都用国内 DoH，避免启动时 DNS 与代理互相等待。
- 所有 DoH 都写成 IP 形式，不依赖明文 DNS 引导。
- `+.ts.net` 加入 `fake-ip-filter`，Tailscale MagicDNS 名称不分配假 IP。
- sniffer 从 TLS/HTTP 握手识别真实域名：客户端绕过路由器 DNS 时，Claude/OpenAI 仍能命中住宅链规则。

### `+rules`

规则按下面的顺序插到全部规则最前面：

1. **Tailscale 放行（所有设备）**：`100.64.0.0/10`、源或目标端口 41641 的 UDP、发往 `tailscale.com` / `tailscale.io` 的 UDP 直连。41641 是 Tailscale 默认端口，WireGuard 隧道和 STUN 打洞都从它发出。控制面和 DERP 中转（TCP）照常按后面的规则走普通节点，不进住宅链。
2. **WebRTC 防泄露**：受保护设备 `192.168.198.218`、`192.168.198.216`、`192.168.198.15` 除 DNS(53)、NTP(123) 和上面的 Tailscale 外，UDP 一律拒绝。WebRTC 拿不到 UDP 就收集不到公网地址，视频会议会自动改走 TCP。其他设备不拦 STUN，保证 Tailscale 打洞正常。
3. **拒绝 DoT(853)**：客户端回落到路由器 DNS。
4. **Claude / OpenAI 只走住宅链**：`claude`、`openai` 规则集和对应 GEOSITE。

前三类规则只会 REJECT，或只放行 Tailscale 流量，不可能把 Claude/OpenAI 送到普通节点或直连。受保护设备应在路由器 DHCP 中设置静态租约；地址改变时需要同步修改这里的 `SRC-IP-CIDR`。Mac 上的 Tailscale App 如果不用 41641 端口，受保护 Mac 的 P2P 会退回 DERP 中转，仍能连通。

### `proxies+`

- 创建两条住宅链 `住宅链-经新加坡`、`住宅链-经亚洲备用`。它们连的是同一个住宅 SOCKS5，出口 IP 相同。
- `dialer-proxy` 决定住宅 SOCKS5 连接先经过哪组机场节点：分别是 `前置-新加坡` 和 `前置-亚洲备用`（香港 / 日本 / 台湾）。
- 服务器、端口、账号、密码都引用 `${RESIDENTIAL_*}` 环境变量，两条链共用同一组值。

### `proxy-groups+`

- 创建机场前置组 `前置-新加坡` 和 `前置-亚洲备用`，类型都是 `fallback`。
- 当前节点健康检查失败，或真实连接连续失败 2 次（`max-failed-times: 2`），就自动切到下一个节点，不需要手动选。
- `include-all-providers: true` 自动读取最终配置中的全部订阅 provider。
- `filter` 按节点名称筛选新加坡，或香港 / 日本 / 台湾节点。
- 配置不再依赖固定的 `Provider_xxxxxx` 名称，因此机场更新 provider ID 后不会因为旧 ID 而启动失败。

### `proxy-groups*`

- 模板生成的 `🤖 Claude 住宅链` 和 `🤖 OpenAI 住宅链` 是 fallback 组，健康检查分别请求 `https://api.anthropic.com` 和 `https://api.openai.com`。检查的是整条住宅链，不只是前置节点。
- 覆写后，这两个组的成员只剩两条住宅链：第一条不通就切第二条；两条都不通时仍停在住宅链上，不会落到普通节点。
- 模板里这两个 AI 组的兜底成员只有 `REJECT`。覆写模块没生效时，Claude/OpenAI 直接连不上，不会走普通节点或直连。
- `新加坡住宅优先` 先走 `🤖 Claude 住宅链`，住宅链整体不通时回落到普通 `🇸🇬 SG`。

### `rule-providers`

- 模块自带 `claude`、`openai` 两个规则集，不依赖订阅转换生成的名称。

## 三、首次部署

1. 确认 OpenClash 版本不低于 `v0.47.081`，核心选择 Meta/Mihomo。
2. 在「配置订阅」里为链式代理准备一份配置，订阅转换模板使用本仓库的 `metafenliu.ini`，例如配置文件名 `西部数据-加强链式代理`。
3. 「运行状态」页顶部点「覆写模块」→「+ 添加新模块」→「订阅链接」，填入：

   ```text
   https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/openclash/sg-residential-chain.conf
   ```

4. 「匹配配置文件」只选这份配置的完整路径，例如 `/etc/openclash/config/西部数据-加强链式代理.yaml`。不要选 `all`，以免影响其他配置。
5. 在「环境变量」里填写四项真实值（`#!ENV` 会自动生成键名）：

   ```text
   RESIDENTIAL_SERVER=1.2.3.4;RESIDENTIAL_PORT=6666;RESIDENTIAL_USERNAME=xxx;RESIDENTIAL_PASSWORD=xxx
   ```

   端口只填数字；密码里不能含英文分号 `;`。
6. 保存并打开模块开关。停用旧版的本地链式代理模块，避免节点和策略组重名。
7. 切换到这份配置并重启 OpenClash。不需要手动选节点，前置组会自动选可用节点。

## 四、日常更新

### 机场订阅更新

正常更新订阅并重启即可。前置组会自动读取新的 provider，不需要手动填写 `Provider_*` 名称。节点改名或消失后，fallback 前置组会自动选下一个可用节点。

### 住宅代理信息更新

只修改覆写模块的「环境变量」，然后重启 OpenClash。不需要改模块正文，也不要把真实值写进 Git 仓库。

### Git 模板更新

仓库模板更新后，在覆写模块列表里点该模块的「刷新」，再重启 OpenClash。刷新只更新模板正文，环境变量里的真实值保持不变。

## 五、启动后验证

按顺序检查：

1. OpenClash 状态为“运行中”，日志中没有 `Parse config error`。
2. 面板存在 `前置-新加坡`、`前置-亚洲备用`、`🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 和 `新加坡住宅优先`。
3. 两个前置组都有节点，并显示延迟。
4. `🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 的成员只有 `住宅链-经新加坡` 和 `住宅链-经亚洲备用`，没有 `REJECT`。如果看到 `REJECT`，说明覆写模块没有生效，此时 Claude/OpenAI 会连不上，这是有意的。
5. Claude 连接命中 `🤖 Claude 住宅链`，OpenAI 连接命中 `🤖 OpenAI 住宅链`；Gemini 等其他 AI、国内网站和普通下载都不命中住宅链。
6. 住宅出口检测显示预期的 IPv4。
7. 在受保护设备上打开 WebRTC 检测页（如 browserleaks.com/webrtc），不出现任何公网 IP。
8. DNS 泄露检测页（如 browserleaks.com/dns）不出现国内运营商或阿里、腾讯的 DNS。
9. `tailscale status` 中，非受保护设备可以出现 `direct`；受保护 Mac 显示 `relay` 属于正常。

更新前后测速应分开观察两类流量：普通下载用于判断机场普通节点速度，AI 请求用于判断住宅链稳定性。住宅双跳本身延迟通常高于普通单跳，不应把它设置成所有流量的全局出口。

## 六、常见故障

### `Provider_xxxxxx not found`

说明正在使用旧版覆写模块，其中写死了 provider 名称。使用当前模板的 `include-all-providers: true` 与新加坡 `filter`，不要恢复固定 `use: Provider_xxxxxx`。

### 配置解析失败或住宅节点不可用

检查模块「环境变量」里四个键是否都已填写，端口是否为纯数字，密码是否含分号。如果面板里住宅节点地址显示为 `${RESIDENTIAL_SERVER}` 原文，说明 OpenClash 版本不支持环境变量展开，需要升级。

### 前置组没有节点

机场可能改变了新加坡节点的命名方式。先确认订阅确实包含新加坡节点；如名称没有“新加坡”“SG”“Singapore”或新加坡旗帜，需要按实际命名调整 `filter`。

### AI 可用但普通下载仍慢

在 OpenClash 连接面板确认下载连接实际命中的策略组。如果未命中住宅链，问题通常是当前普通机场节点速度或线路质量，需要在相应地区组中切换节点测速，而不是继续修改住宅链。

### 修改后无法恢复

先停用这一个覆写模块并重启 OpenClash，确认基础订阅配置可以启动；随后恢复上一次可用的本地模块。不要删除仓库规则，也不要修改生成后的 `metafenliu.ini`。

## 七、安全要求

- Git 中只允许保存 `${RESIDENTIAL_*}` 变量引用，真实值只在路由器的模块环境变量里。
- 不在 Issue、截图、日志或聊天中公开真实服务器、端口、账号和密码。
- 如果凭据曾经公开，应在住宅代理服务商处轮换密码或整套凭据。
- 提交前运行仓库测试并检查 Git 差异，确认没有真实凭据进入跟踪文件。
