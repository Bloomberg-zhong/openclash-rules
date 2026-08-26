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

- GitHub 仓库中的 `custom/rules.ini`、`custom/groups.ini` 和 `rules/claude.yaml` 负责把新加坡域名、Claude、OpenAI、海外 AI 指向 `住宅链式出口`。
- OpenClash 路由器本地的覆写模块负责加入住宅 SOCKS5 节点、`dialer-proxy`、代理 DNS、指定客户端 UDP 规则和真实凭据。

这样重新同步上游或重新转换整份配置时，分流规则仍会保留，同时住宅代理账号密码不会进入 GitHub。

覆写模板位于：

```text
openclash/sg-residential-chain.conf
```

### 住宅 IP、端口和账号密码放在哪里

真实住宅代理信息只保存在路由器的 OpenClash 本地覆写模块中。Git 仓库里的
`openclash/sg-residential-chain.conf` 永远保留以下四个占位符，不能填入真实值：

```text
__RESIDENTIAL_SERVER__
__RESIDENTIAL_PORT__
__RESIDENTIAL_USERNAME__
__RESIDENTIAL_PASSWORD__
```

住宅 IP、端口或密码发生变化时，直接编辑路由器中已经启用的覆写模块，然后更新配置并重启 OpenClash。同步 Git、重新生成 `metafenliu.ini` 或在 OpenClash 中手动更新订阅配置，不会改写这个本地覆写模块。

只有再次把仓库中的模板导入并替换现有覆写模块时，四项真实值才会被占位符覆盖。因此日常更新只更新订阅配置，不要重新覆盖本地模块；如确实需要重建模块，先导出现有模块或记录四项值，再重新填写。

使用步骤：

1. 确认 OpenClash 版本不低于 `v0.47.081`，并使用 Meta/Mihomo 核心。
2. 在 OpenClash 的“运行状态 → 覆写模块”中新增模块，复制该模板内容。
3. 只在路由器本地替换 `__RESIDENTIAL_SERVER__`、`__RESIDENTIAL_PORT__`、`__RESIDENTIAL_USERNAME__`、`__RESIDENTIAL_PASSWORD__`。
4. 端口必须替换为数字，例如 `10000`，不要保留占位符。
5. 为当前配置启用该覆写模块，然后更新配置并重启 OpenClash。
6. 在面板的 `链式前置-新加坡` 中选择一个稳定的新加坡机场节点。

不要把填入真实凭据后的覆写模块提交到这个仓库。未启用覆写模块时，`住宅链式出口` 会暂时回退到普通 `🇸🇬 SG`，避免整份配置无法启动。

### DNS、IPv6 与 WebRTC UDP

覆写模板当前固定执行以下策略：

- 普通域名使用 Cloudflare 和 Google DoH，并明确通过 `住宅链式出口` 建立连接。
- 机场节点自身的域名使用独立的 `proxy-server-nameserver` 引导解析，避免 DNS 与代理互相等待而无法启动。
- 不追加 WAN DNS，也不追加 OpenClash 默认业务 DNS。
- 关闭 IPv6 和 AAAA 解析，避免住宅出口只有 IPv4 时从 IPv6 旁路。
- 禁用 QUIC，让 Claude/HTTPS 优先使用更稳定、也更容易保持出口一致的 TCP。
- 仅 `192.168.198.218/32` 和 `192.168.198.216/32` 的全部 UDP 进入住宅链；不会影响其他局域网设备。

应当在路由器 DHCP 中为这两台设备设置静态租约。如果设备地址改变，需要同时修改覆写模块中的两条 `SRC-IP-CIDR`。浏览器的“安全 DNS/私密 DNS”应关闭，让 DNS 请求统一交给 OpenClash。

Claude 精确域名、CDN、认证、监控、第三方组件与 NTP 域名规则维护在：

```text
rules/claude.yaml
```

其中不加入检测网站使用的两个 STUN 域名；WebRTC 由上述两台客户端的 UDP 规则统一覆盖。规则末尾同时保留 Anthropic IPv4、IPv6 网段和 ASN 兜底，其中 IPv6 当前会被覆写模块的全局 IPv6 开关阻断，不会形成旁路。

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

`住宅链式出口`：

```text
massive.com
富途 / moomoo 常用域名
盈透 / IBKR 常用域名
OpenAI
其他海外 AI 域名
Claude / Anthropic 精确域名、监控与 NTP 域名
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
