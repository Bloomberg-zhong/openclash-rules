# 新加坡住宅链式代理使用说明

这份说明配套仓库中的脱敏覆写模板：

```text
openclash/sg-residential-chain.conf
```

模板只保存链式代理结构，不保存住宅代理的服务器地址、端口、账号或密码。真实值只能填写在路由器的 OpenClash 本地覆写模块中。

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

### `dns`

- 普通域名使用阿里云和腾讯 DoH，避免所有 DNS 查询都走住宅双跳。
- Claude 与 OpenAI 域名使用 Cloudflare 和 Google DoH，并分别通过 `🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 连接。
- `proxy-server-nameserver` 只解析机场和住宅代理自身的域名，避免启动时产生 DNS 与代理互相依赖的循环。

### `+rules`

- 仅拒绝两台受保护客户端的常见 WebRTC/STUN UDP 端口。
- 不再把这两台设备的全部 UDP 强制送入住宅链，因此下载、游戏和其他 UDP 应用不会无条件承受双跳延迟。
- 当前受保护地址是 `192.168.198.218` 和 `192.168.198.216`。应在路由器 DHCP 中给它们设置静态租约；地址改变时需要同步修改这里的 `SRC-IP-CIDR`。

### `proxies+`

- 创建两条住宅链 `住宅链-经新加坡`、`住宅链-经亚洲备用`。它们连的是同一个住宅 SOCKS5，出口 IP 相同。
- `dialer-proxy` 决定住宅 SOCKS5 连接先经过哪组机场节点：分别是 `前置-新加坡` 和 `前置-亚洲备用`（香港 / 日本 / 台湾）。
- 四个 `__RESIDENTIAL_*__` 值在两条链里各出现一次，共 8 处，必须在 OpenClash 本地全部替换。

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

### `rule-providers` 与 `+rules`

- 模块自带 `claude`、`openai` 两个规则集，不依赖订阅转换生成的名称。
- `+rules` 把 Claude/OpenAI 规则插到全部规则最前面，先于 `GEOSITE,cn`、Aethersailor 直连 / 代理列表等任何规则匹配。

## 三、首次部署

1. 确认 OpenClash 版本不低于 `v0.47.081`，核心选择 Meta/Mihomo。
2. 打开仓库中的 `openclash/sg-residential-chain.conf`，复制全部内容。
3. 在 OpenClash 的“运行状态 → 覆写模块”中新建模块并粘贴。
4. 只在路由器本地替换以下四个占位符（每个出现两次，用全部替换）：

   ```text
   __RESIDENTIAL_SERVER__
   __RESIDENTIAL_PORT__
   __RESIDENTIAL_USERNAME__
   __RESIDENTIAL_PASSWORD__
   ```

5. 把端口占位符替换为纯数字；不要给端口加引号，也不要留下任何占位符。
6. 保存模块，为当前配置启用它，然后更新配置并重启 OpenClash。
7. 不需要手动选节点，前置组会自动选可用节点。

如果需要在电脑上临时保留已填写版本，请命名为：

```text
openclash/sg-residential-chain.local.conf
```

仓库已经忽略 `openclash/*.local.conf`。但更安全的做法仍然是只把真实凭据保存在路由器中。

## 四、日常更新

### 机场订阅更新

正常更新订阅并重启即可。前置组会自动读取新的 provider，不需要手动填写 `Provider_*` 名称。节点改名或消失后，fallback 前置组会自动选下一个可用节点。

### 住宅代理信息更新

只编辑路由器中已经启用的覆写模块，替换服务器、端口、账号或密码，然后更新配置并重启。不要把填好真实值的模块复制回 Git 仓库。

### Git 模板更新

仓库模板更新时，先比较变更，再把非敏感配置同步到路由器。不要直接用带占位符的新模板覆盖正在使用的本地模块，否则真实凭据会被占位符替换，OpenClash 将无法正常连接住宅代理。

## 五、启动后验证

按顺序检查：

1. OpenClash 状态为“运行中”，日志中没有 `Parse config error`。
2. 面板存在 `前置-新加坡`、`前置-亚洲备用`、`🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 和 `新加坡住宅优先`。
3. 两个前置组都有节点，并显示延迟。
4. `🤖 Claude 住宅链`、`🤖 OpenAI 住宅链` 的成员只有 `住宅链-经新加坡` 和 `住宅链-经亚洲备用`，没有 `REJECT`。如果看到 `REJECT`，说明覆写模块没有生效，此时 Claude/OpenAI 会连不上，这是有意的。
5. Claude 连接命中 `🤖 Claude 住宅链`，OpenAI 连接命中 `🤖 OpenAI 住宅链`；Gemini 等其他 AI、国内网站和普通下载都不命中住宅链。
6. 住宅出口检测显示预期的 IPv4；浏览器 WebRTC 检测不暴露本地公网出口。

更新前后测速应分开观察两类流量：普通下载用于判断机场普通节点速度，AI 请求用于判断住宅链稳定性。住宅双跳本身延迟通常高于普通单跳，不应把它设置成所有流量的全局出口。

## 六、常见故障

### `Provider_xxxxxx not found`

说明正在使用旧版覆写模块，其中写死了 provider 名称。使用当前模板的 `include-all-providers: true` 与新加坡 `filter`，不要恢复固定 `use: Provider_xxxxxx`。

### 配置解析失败或住宅节点不可用

检查四个占位符的 8 处是否已全部替换，端口是否为有效数字，YAML 缩进是否在复制时被破坏。不要复制网页渲染产生的反斜杠转义或 Markdown 链接格式。

### 前置组没有节点

机场可能改变了新加坡节点的命名方式。先确认订阅确实包含新加坡节点；如名称没有“新加坡”“SG”“Singapore”或新加坡旗帜，需要按实际命名调整 `filter`。

### AI 可用但普通下载仍慢

在 OpenClash 连接面板确认下载连接实际命中的策略组。如果未命中住宅链，问题通常是当前普通机场节点速度或线路质量，需要在相应地区组中切换节点测速，而不是继续修改住宅链。

### 修改后无法恢复

先停用这一个覆写模块并重启 OpenClash，确认基础订阅配置可以启动；随后恢复上一次可用的本地模块。不要删除仓库规则，也不要修改生成后的 `metafenliu.ini`。

## 七、安全要求

- Git 中只允许保存 `__RESIDENTIAL_*__` 占位符。
- 不在 Issue、截图、日志或聊天中公开真实服务器、端口、账号和密码。
- 如果凭据曾经公开，应在住宅代理服务商处轮换密码或整套凭据。
- 提交前运行仓库测试并检查 Git 差异，确认没有真实凭据进入跟踪文件。
