import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build import (  # noqa: E402
    LOWER_MARKER,
    drop_overridden_groups,
    insert_after_nth_marker,
)


AI_POLICY = "🧠 AI"
CHATGPT_POLICY = "🤖 ChatGPT"
SINGAPORE_POLICY = "新加坡住宅优先"
CHAIN_PROXY = "链式代理-新加坡住宅"
FRONT_GROUP = "🇸🇬 SG"
WEBRTC_PROTECTED_CLIENTS = [
    "192.168.198.218/32",
    "192.168.198.216/32",
    "192.168.198.15/32",
]
TAILSCALE_RULES = [
    "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
    "AND,((NETWORK,UDP),(SRC-PORT,41641)),DIRECT",
    "AND,((NETWORK,UDP),(DST-PORT,41641)),DIRECT",
    "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,tailscale.com)),DIRECT",
    "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,tailscale.io)),DIRECT",
]
AI_RULES = [
    f"RULE-SET,claude,{AI_POLICY}",
    f"GEOSITE,anthropic,{AI_POLICY}",
    f"RULE-SET,openai,{AI_POLICY}",
    f"GEOSITE,openai,{AI_POLICY}",
]
DOMESTIC_DOH = ["https://223.5.5.5/dns-query", "https://1.12.12.12/dns-query"]
RESIDENTIAL_ENV = [
    "RESIDENTIAL_SERVER",
    "RESIDENTIAL_PORT",
    "RESIDENTIAL_USERNAME",
    "RESIDENTIAL_PASSWORD",
]


def read_module() -> str:
    return (ROOT / "openclash" / "sg-residential-chain.conf").read_text(encoding="utf-8")


def read_prepended_rules(module: str) -> list[str]:
    rules_block = module.split("\n+rules:", 1)[1].split("\n\n", 1)[0]
    return [
        line.strip()[2:].strip("'")
        for line in rules_block.splitlines()
        if line.strip().startswith("- ")
    ]


def webrtc_rule(client: str) -> str:
    return (
        f"AND,((SRC-IP-CIDR,{client}),(NETWORK,UDP),"
        "(NOT,((OR,((DST-PORT,53),(DST-PORT,123)))))),REJECT"
    )


def read_general_settings(module: str) -> dict[str, str]:
    general = module.split("[General]", 1)[1].split("[YAML]", 1)[0]
    settings = {}
    for raw_line in general.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        settings[key.strip()] = value.strip()
    return settings


class ChainConfigTests(unittest.TestCase):
    def test_generated_template_keeps_upstream_ai_groups(self) -> None:
        upstream = (ROOT / "upstream" / "metafenliu.ini").read_text(encoding="utf-8")
        custom_rules = (ROOT / "custom" / "rules.ini").read_text(encoding="utf-8").strip()
        custom_groups = (ROOT / "custom" / "groups.ini").read_text(encoding="utf-8").strip()

        # Claude / OpenAI 只用上游自带的 🧠 AI、🤖 ChatGPT，模板里不再自建 AI 组。
        for name in [AI_POLICY, CHATGPT_POLICY]:
            self.assertIn(f"custom_proxy_group={name}`select`", upstream)
            self.assertNotIn(f"custom_proxy_group={name}`", custom_groups)
        self.assertIn(f"ruleset={CHATGPT_POLICY},[]GEOSITE,openai", upstream)
        self.assertIn(f"ruleset={AI_POLICY},[]GEOSITE,category-ai-!cn", upstream)
        for removed in ["🤖 Claude 住宅链", "🤖 OpenAI 住宅链"]:
            self.assertNotIn(removed, custom_rules + custom_groups)

        generated = drop_overridden_groups(upstream, custom_groups)
        generated = insert_after_nth_marker(generated, LOWER_MARKER, 1, custom_rules)
        generated = insert_after_nth_marker(generated, LOWER_MARKER, 2, custom_groups)

        self.assertIn(
            f"ruleset={SINGAPORE_POLICY},clash-domain:https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/rules/singapore.yaml,86400",
            generated,
        )
        self.assertIn(
            f"custom_proxy_group={SINGAPORE_POLICY}`fallback`[]{AI_POLICY}`[]🇸🇬 SG`",
            generated,
        )
        for name in [AI_POLICY, CHATGPT_POLICY]:
            self.assertEqual(generated.count(f"custom_proxy_group={name}`"), 1)

    def test_custom_cloudflare_group_replaces_upstream_and_prefers_singapore(self) -> None:
        upstream = (ROOT / "upstream" / "metafenliu.ini").read_text(encoding="utf-8")
        custom_rules = (ROOT / "custom" / "rules.ini").read_text(encoding="utf-8").strip()
        custom_groups = (ROOT / "custom" / "groups.ini").read_text(encoding="utf-8").strip()

        generated = drop_overridden_groups(upstream, custom_groups)
        generated = insert_after_nth_marker(generated, LOWER_MARKER, 1, custom_rules)
        generated = insert_after_nth_marker(generated, LOWER_MARKER, 2, custom_groups)

        cloudflare = [
            line
            for line in generated.splitlines()
            if line.startswith("custom_proxy_group=☁️ cloudflare`")
        ]
        self.assertEqual(len(cloudflare), 1, "☁️ cloudflare must be defined once")
        self.assertTrue(cloudflare[0].startswith("custom_proxy_group=☁️ cloudflare`select`[]🇸🇬 SG`"))

        # 其他上游组不受影响。
        self.assertIn("custom_proxy_group=🔎 Google`select`[]🇭🇰 HK`", generated)

    def test_openai_rules_list_core_domains(self) -> None:
        rules = (ROOT / "rules" / "openai.yaml").read_text(encoding="utf-8")
        for domain in [
            "openai.com",
            "chatgpt.com",
            "chat.com",
            "sora.com",
            "oaistatic.com",
            "oaiusercontent.com",
        ]:
            self.assertIn(f"DOMAIN-SUFFIX,{domain}", rules)
        self.assertIn("DOMAIN-KEYWORD,openai", rules)

    def test_overwrite_module_rules_cannot_divert_ai_traffic(self) -> None:
        module = read_module()
        rules = read_prepended_rules(module)

        ai_start = rules.index(AI_RULES[0])
        self.assertEqual(rules[ai_start : ai_start + 4], AI_RULES)

        # AI 规则前面只允许出现 REJECT，或只匹配 Tailscale 的放行规则，
        # 这些都不可能把 Claude / OpenAI 送到普通节点或直连。
        for rule in rules[:ai_start]:
            self.assertTrue(
                rule.endswith(",REJECT") or rule in TAILSCALE_RULES,
                f"rule ahead of AI rules may divert AI traffic: {rule}",
            )

        # 规则集由模块自己定义，不依赖订阅转换生成的名称。
        providers_block = module.split("\nrule-providers:", 1)[1].split("\n\n", 1)[0]
        for name in ["claude", "openai"]:
            self.assertIn(f"\n  {name}:", providers_block)
            self.assertIn(
                f"url: 'https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/rules/{name}.yaml'",
                providers_block,
            )

    def test_claude_rules_cover_the_site_domain_list_and_ip_fallbacks(self) -> None:
        rule_path = ROOT / "rules" / "claude.yaml"
        self.assertTrue(rule_path.exists(), "Claude domain rule provider is missing")
        rules = rule_path.read_text(encoding="utf-8")

        expected_suffixes = [
            "anthropic.com",
            "clau.de",
            "claude.ai",
            "claude.com",
            "claudemcpclient.com",
            "claudemcpcontent.com",
            "claudeusercontent.com",
            "servd-anthropic-website.b-cdn.net",
            "anthropic.auth0.com",
            "anthropic-com.ghost.io",
            "anthropic.com.cdn.cloudflare.net",
            "sentry.io",
            "statsigapi.net",
            "browser-intake-us5-datadoghq.com",
            "intercom.io",
            "intercomcdn.com",
            "cdn.usefathom.com",
        ]
        for domain in expected_suffixes:
            self.assertIn(f"DOMAIN-SUFFIX,{domain}", rules)

        for keyword in ["datadog", "sentry", "sift"]:
            self.assertIn(f"DOMAIN-KEYWORD,{keyword}", rules)
        self.assertNotIn("GEOSITE,category-ntp", rules)

        self.assertNotIn("stun.l.google.com", rules)
        self.assertNotIn("stun.cloudflare.com", rules)
        self.assertIn("IP-CIDR,160.79.104.0/21,no-resolve", rules)
        self.assertIn("IP-CIDR6,2607:6bc0::/32,no-resolve", rules)
        self.assertIn("IP-ASN,399358,no-resolve", rules)

    def test_overwrite_module_adds_udp_chain_without_real_credentials(self) -> None:
        module = read_module()

        for required in [
            "[YAML]",
            "proxies+:",
            "type: socks5",
            "udp: true",
            "proxy-groups*:",
            "name: '/^(🧠 AI|🤖 ChatGPT)$/'",
            "#!ENV = " + ";".join(RESIDENTIAL_ENV),
        ]:
            self.assertIn(required, module)

        # 真实凭据只填在路由器的模块环境变量里，仓库只保留变量引用。
        self.assertNotIn("__RESIDENTIAL_", module)

        # 前置直接用模板里的 🇸🇬 SG，模块不再自建前置组。
        self.assertNotIn("proxy-groups+:", module)
        upstream = (ROOT / "upstream" / "metafenliu.ini").read_text(encoding="utf-8")
        self.assertIn(f"custom_proxy_group={FRONT_GROUP}`url-test`", upstream)

        proxy_block = module.split("proxies+:", 1)[1].split("proxy-groups*:", 1)[0]
        chain_entries = proxy_block.split("  - name: ")[1:]
        self.assertEqual(
            [entry.splitlines()[0].strip("'") for entry in chain_entries], [CHAIN_PROXY]
        )
        entry = chain_entries[0]
        self.assertIn(f"dialer-proxy: '{FRONT_GROUP}'", entry)
        expected_credentials = {
            "server": "'${RESIDENTIAL_SERVER}'",
            "port": "${RESIDENTIAL_PORT}",
            "username": "'${RESIDENTIAL_USERNAME}'",
            "password": "'${RESIDENTIAL_PASSWORD}'",
        }
        actual_credentials = {}
        for raw_line in entry.splitlines():
            line = raw_line.strip()
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key in expected_credentials:
                actual_credentials[key] = value.strip()
        self.assertEqual(actual_credentials, expected_credentials)

        # AI 组覆写后只能包含住宅链，不能出现普通节点或 DIRECT。
        ai_set_block = module.split("proxy-groups*:", 1)[1]
        members = [
            line.strip()[2:].strip("'")
            for line in ai_set_block.split("    proxies:", 1)[1].splitlines()[1:]
            if line.startswith("      - ")
        ]
        self.assertEqual(members, [CHAIN_PROXY])

    def test_overwrite_module_prevents_dns_leaks(self) -> None:
        module = read_module()
        general = read_general_settings(module)

        expected_general = {
            "ENABLE_REDIRECT_DNS": "1",
            "ENABLE_CUSTOM_DNS": "0",
            "ENABLE_RESPECT_RULES": "0",
            "APPEND_DEFAULT_DNS": "0",
            "APPEND_WAN_DNS": "0",
            "IPV6_ENABLE": "0",
            "IPV6_DNS": "0",
            "ENABLE_UDP_PROXY": "1",
            "DISABLE_UDP_QUIC": "1",
        }
        for key, value in expected_general.items():
            self.assertEqual(general.get(key), value, f"unexpected {key}")

        for required in [
            "dns:",
            "enable: true",
            "ipv6: false",
            "enhanced-mode: fake-ip",
            "respect-rules: false",
            "default-nameserver!:",
            "nameserver!:",
            "nameserver-policy!:",
            "proxy-server-nameserver!:",
            "direct-nameserver!:",
            "- '+.ts.net'",
            "sniffer!:",
            "override-destination: true",
        ]:
            self.assertIn(required, module)

        # 默认 nameserver 只能是经代理的境外 DoH，国内 DNS 不能看到国外域名。
        nameserver_block = module.split("  nameserver!:", 1)[1].split(
            "  nameserver-policy!:", 1
        )[0]
        self.assertIn("https://1.1.1.1/dns-query#♻️ 自动选择", nameserver_block)
        self.assertIn("https://8.8.8.8/dns-query#♻️ 自动选择", nameserver_block)
        for domestic in DOMESTIC_DOH + ["alidns", "doh.pub", "223.5.5.5", "119.29.29.29"]:
            self.assertNotIn(domestic, nameserver_block)

        # ♻️ 自动选择 必须由上游模板提供，否则 DNS 无法建立连接。
        upstream = (ROOT / "upstream" / "metafenliu.ini").read_text(encoding="utf-8")
        self.assertIn("custom_proxy_group=♻️ 自动选择`", upstream)

        policy_block = module.split("  nameserver-policy!:", 1)[1].split(
            "  proxy-server-nameserver!:", 1
        )[0]
        for selector in ["'rule-set:claude,openai':", "'geosite:anthropic,openai':"]:
            entry = policy_block.split(selector, 1)[1].split("    '", 1)[0]
            self.assertIn(f"https://1.1.1.1/dns-query#{AI_POLICY}", entry)
            self.assertIn(f"https://8.8.8.8/dns-query#{AI_POLICY}", entry)

        cn_entry = policy_block.split("'geosite:cn,private':", 1)[1]
        for doh in DOMESTIC_DOH:
            self.assertIn(doh, cn_entry)

    def test_overwrite_module_blocks_webrtc_udp_but_allows_tailscale(self) -> None:
        module = read_module()
        rules = read_prepended_rules(module)

        for client in WEBRTC_PROTECTED_CLIENTS:
            self.assertIn(webrtc_rule(client), rules)
        self.assertIn("DST-PORT,853,REJECT", rules)

        # Tailscale 放行必须排在所有 WebRTC 拒绝规则前面。
        first_reject = min(rules.index(webrtc_rule(c)) for c in WEBRTC_PROTECTED_CLIENTS)
        for rule in TAILSCALE_RULES:
            self.assertIn(rule, rules)
            self.assertLess(rules.index(rule), first_reject)

        # 不再使用只拦固定端口的旧规则，也不把 UDP 整体送进住宅链。
        self.assertNotRegex(module, r"DST-PORT,(3478-3481|19302-19309)\)\),REJECT")
        self.assertNotRegex(module, r"(?i)NETWORK,udp\)?,.*住宅链")


if __name__ == "__main__":
    unittest.main()
