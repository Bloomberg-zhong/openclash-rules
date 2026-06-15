# OpenClash 自用分流模板

这个仓库基于上游模板自动生成最终的 `metafenliu.ini`：

```text
https://raw.githubusercontent.com/usbog232/clashmetadingyue/main/metafenliu.ini
```

日常使用时，你只需要改：

```text
custom/rules.ini
custom/groups.ini
```

不要手动改生成后的 `metafenliu.ini`，否则下次同步时会被覆盖。

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

`访问新加坡`：

```text
massive.com
富途 / moomoo 常用域名
盈透 / IBKR 常用域名
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
