# OpenClash 自用分流模板

这个仓库基于上游模板自动生成最终的 `metafenliu.ini`：

```text
https://raw.githubusercontent.com/usbog232/clashmetadingyue/main/metafenliu.ini
```

日常分流入口主要是：

```text
custom/rules.ini
custom/groups.ini
rules/*.yaml
openclash/*.conf
```

不要手动改生成后的 `metafenliu.ini`，否则下次同步时会被覆盖。

## 新加坡住宅链式代理

链式代理分成两层维护：

- GitHub 仓库中的 `custom/rules.ini`、`custom/groups.ini` 和 `rules/claude.yaml` 负责把 Claude 指向 `🤖 Claude 住宅链`、OpenAI 指向 `🤖 OpenAI 住宅链`、新加坡域名指向 `新加坡住宅优先`；其他海外 AI 交给上游 `🧠 AI` 组走普通节点。
- OpenClash 路由器上的覆写模块负责加入住宅 SOCKS5 节点、`dialer-proxy`、DNS 与 WebRTC 防泄露、Tailscale 放行；真实凭据只填在模块的「环境变量」里。

这样重新同步上游或重新转换整份配置时，分流规则仍会保留，同时住宅代理账号密码不会进入 GitHub。

覆写模板位于：

```text
openclash/sg-residential-chain.conf
```

完整的配置说明、部署步骤、验证方法和故障回退见：

```text
docs/sg-residential-chain-guide.md
```

### 住宅 IP、端口和账号密码放在哪里

仓库里的 `openclash/sg-residential-chain.conf` 只引用四个环境变量，不写真实值：

```text
${RESIDENTIAL_SERVER}
${RESIDENTIAL_PORT}
${RESIDENTIAL_USERNAME}
${RESIDENTIAL_PASSWORD}
```

真实值填在 OpenClash 覆写模块的「环境变量」里，格式是：

```text
RESIDENTIAL_SERVER=1.2.3.4;RESIDENTIAL_PORT=6666;RESIDENTIAL_USERNAME=xxx;RESIDENTIAL_PASSWORD=xxx
```

模块开头的 `#!ENV` 会在添加时自动生成这四个键。模块可以直接用 GitHub 链接订阅，刷新模块只会更新模板正文，不会覆盖环境变量。密码里不能含英文分号 `;`，它是环境变量的分隔符。

使用步骤：

1. 确认 OpenClash 版本不低于 `v0.47.081`，并使用 Meta/Mihomo 核心。
2. 「运行状态」页顶部点「覆写模块」→「+ 添加新模块」→「订阅链接」，填入：
   `https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/openclash/sg-residential-chain.conf`
3. 「匹配配置文件」只选要启用链式代理的那份配置的完整路径，例如 `/etc/openclash/config/西部数据-加强链式代理.yaml`。
4. 在「环境变量」里填写住宅代理的四项真实值，保存并打开模块开关。
5. 切换到对应配置并重启 OpenClash。模块只在重启时生效。
6. 不需要手动选前置节点：`前置-新加坡`、`前置-亚洲备用` 都是 fallback 组，会自动跳过失效节点。

如果重启后面板里住宅节点的地址仍显示为 `${RESIDENTIAL_SERVER}` 原文，说明 OpenClash 版本不支持环境变量展开，需要先升级。

前置组会自动包含当前订阅的全部 proxy provider，再通过名称筛选节点。机场更新后即使 `Provider_*` ID 发生变化，也不需要修改覆写模块；前置组是 fallback，节点改名或失效后会自动选下一个可用节点。

Claude/OpenAI 的故障切换分三层：

1. `🤖 Claude 住宅链` / `🤖 OpenAI 住宅链` 每 180 秒经整条住宅链请求 `api.anthropic.com` / `api.openai.com`。
2. 当前住宅链不通时，自动从 `住宅链-经新加坡` 切到 `住宅链-经亚洲备用`。两条链出口是同一个住宅 IP，只是前置线路不同。
3. 每条链的前置组本身是 fallback，节点健康检查失败或真实连接连续失败 2 次就换下一个节点。

两条住宅链都不通时，AI 组仍停在住宅链上，不会落到普通机场节点。

未启用覆写模块时，两个 AI 组只剩 `REJECT`：Claude/OpenAI 会直接连不上，绝不会改走普通节点或直连。`新加坡住宅优先` 此时回落到普通 `🇸🇬 SG`。

覆写模块用 `+rules` 把自己的规则插到全部规则最前面，并自带 `claude`、`openai` 两个规则集。排在 Claude/OpenAI 规则前面的只有 Tailscale 放行和 REJECT 规则，第三方直连 / 代理列表以后怎么更新都抢不走这些流量。

### DNS、IPv6、WebRTC 与 Tailscale

覆写模板当前固定执行以下策略：

- **DNS 防泄露**：默认 `nameserver` 只用经 `♻️ 自动选择` 代理的 Cloudflare / Google DoH，国内 DNS 看不到国外域名；Claude、OpenAI 域名分别经 `🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 查询；只有 `geosite:cn,private`、机场节点域名（`proxy-server-nameserver`）和直连流量（`direct-nameserver`）使用国内 DoH。所有 DoH 都写成 IP，不依赖明文 DNS 引导。
- 不追加 WAN DNS，也不追加 OpenClash 默认业务 DNS；拒绝 DoT(853)，客户端只能用路由器 DNS。
- 开启 sniffer：客户端绕过路由器 DNS 时，仍能从 TLS/HTTP 握手识别出 Claude/OpenAI 域名并命中住宅链。
- 关闭 IPv6 和 AAAA 解析，避免住宅出口只有 IPv4 时从 IPv6 旁路。
- 禁用 QUIC，让 Claude/HTTPS 使用更稳定、也更容易保持出口一致的 TCP。
- **WebRTC 防泄露**：受保护设备 `192.168.198.218`、`192.168.198.216`、`192.168.198.15` 除 DNS(53)、NTP(123) 和 Tailscale 外的 UDP 一律拒绝，任何端口的 STUN/TURN 都拿不到公网地址。其他设备不拦 STUN。
- **Tailscale 放行（所有设备）**：`100.64.0.0/10`、源或目标端口 41641 的 UDP、发往 `tailscale.com` / `tailscale.io` 的 UDP 直连，排在 WebRTC 拒绝规则之前；控制面和 DERP 中转（TCP）照常按规则走普通节点，都不进住宅链。`+.ts.net` 不分配 fake-ip。Mac 上的 Tailscale App 如果不用 41641 端口，受保护 Mac 的 P2P 会退回 DERP 中转，仍能连通。

应当在路由器 DHCP 中为受保护设备设置静态租约。如果设备地址改变，需要同时修改覆写模块 `+rules` 中对应的 `SRC-IP-CIDR`。浏览器的“安全 DNS/私密 DNS”应关闭，让 DNS 请求统一交给 OpenClash。Chrome 还可以在 Mac 上执行 `defaults write com.google.Chrome WebRtcIPHandling -string disable_non_proxied_udp`，作为 WebRTC 的第二层防护。

Claude 精确域名、CDN、认证、监控与第三方组件规则维护在：

```text
rules/claude.yaml
```

其中不加入检测网站使用的两个 STUN 域名；WebRTC 由上述受保护设备的 UDP 拒绝规则与 QUIC 禁用共同防护。NTP 保持正常分流，不再使用住宅出口。规则末尾同时保留 Anthropic IPv4、IPv6 网段和 ASN 兜底，其中 IPv6 当前会被覆写模块的全局 IPv6 开关阻断，不会形成旁路。

## 使用方法

1. 在 GitHub 新建一个空仓库，例如 `openclash-rules`。
2. 把本目录里的文件上传到你的仓库。
3. 进入 GitHub 仓库的 `Actions` 页面，启用 workflow。
4. 手动运行一次 `Sync OpenClash Template`。
5. OpenClash 里使用你自己的 raw 地址：

```text
https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/metafenliu.ini
```

## 新增一个应用

例如你要新增 `Discord`：

在 `custom/rules.ini` 里添加：

```ini
ruleset= Discord,[]GEOSITE,discord
```

在 `custom/groups.ini` 里添加：

```ini
custom_proxy_group= Discord`select`[]🇭🇰 HK`[]🇹🇼 TW`[]🇯🇵 JP`[]🇸🇬 SG`[]🇺🇸 US`[]🧊 冷门节点`[]🌐 Default
```

提交到 GitHub 后，手动运行一次 Actions，或者等它每天自动同步。

## 新增自己的域名列表

如果 GEOSITE 里没有你要的网站，可以自己加一个规则文件，例如：

```text
rules/mysite.yaml
```

内容示例：

```yaml
payload:
  - DOMAIN-SUFFIX,example.com
  - DOMAIN-SUFFIX,example.net
```

然后在 `custom/rules.ini` 添加：

```ini
ruleset= MySite,clash-domain:https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/rules/mysite.yaml,86400
```

在 `custom/groups.ini` 添加：

```ini
custom_proxy_group= MySite`select`[]🇭🇰 HK`[]🇹🇼 TW`[]🇯🇵 JP`[]🇸🇬 SG`[]🇺🇸 US`[]🧊 冷门节点`[]DIRECT`[]🌐 Default
```

## 当前已内置的自定义规则

`🤖 Claude 住宅链`（只走住宅链）：

```text
rules/claude.yaml：Claude / Anthropic 精确域名、监控组件与官方网段
GEOSITE,anthropic
```

`🤖 OpenAI 住宅链`（只走住宅链）：

```text
rules/openai.yaml：OpenAI / ChatGPT / Sora 核心域名、静态资源与 CDN
GEOSITE,openai
```

`新加坡住宅优先`（优先住宅链，不通时回落普通新加坡节点）：

```text
rules/singapore.yaml：massive.com、盈透 / IBKR 常用域名
```

`DIRECT`：

```text
taifanbo.com
taifanbo.top
```

## 推荐原则

- 原模板负责整体结构和默认策略。
- 你自己的规则只放在 `custom/`。
- 规则名和策略组名保持一致。
- 更具体的规则放前面，兜底规则放后面。
- 如果不确定某个网站该走代理还是直连，先给它建独立策略组，后续在 OpenClash 面板里手动选。
