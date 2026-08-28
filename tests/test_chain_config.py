import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build import LOWER_MARKER, insert_after_nth_marker  # noqa: E402


CHAIN_POLICY = "住宅链式出口"
CHAIN_PROXY = "链式代理-新加坡住宅"
WEBRTC_PROTECTED_CLIENTS = ["192.168.198.218/32", "192.168.198.216/32"]


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
    def test_generated_template_routes_singapore_and_ai_before_upstream_rules(self) -> None:
        upstream = "\n".join(
            [
                "[custom]",
                LOWER_MARKER,
                "ruleset=访问新加坡,https://upstream.invalid/singapore.yaml",
                "ruleset=🤖 ChatGPT,[]GEOSITE,openai",
                "ruleset=🧠 AI,[]GEOSITE,category-ai-!cn",
                LOWER_MARKER,
                "custom_proxy_group=访问新加坡`select`[]🇸🇬 SG",
            ]
        )
        custom_rules = (ROOT / "custom" / "rules.ini").read_text(encoding="utf-8").strip()
        custom_groups = (ROOT / "custom" / "groups.ini").read_text(encoding="utf-8").strip()

        generated = insert_after_nth_marker(upstream, LOWER_MARKER, 1, custom_rules)
        generated = insert_after_nth_marker(generated, LOWER_MARKER, 2, custom_groups)

        expected_rules = [
            f"ruleset={CHAIN_POLICY},clash-domain:https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/rules/singapore.yaml,86400",
            f"ruleset={CHAIN_POLICY},clash-classic:https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/rules/claude.yaml,86400",
            f"ruleset={CHAIN_POLICY},[]GEOSITE,openai",
            f"ruleset={CHAIN_POLICY},[]GEOSITE,category-ai-!cn",
        ]
        for rule in expected_rules:
            self.assertIn(rule, generated)

        self.assertIn(
            f"custom_proxy_group={CHAIN_POLICY}`select`[]🇸🇬 SG",
            generated,
        )

        self.assertLess(
            generated.index(f"ruleset={CHAIN_POLICY},[]GEOSITE,openai"),
            generated.index("ruleset=🤖 ChatGPT,[]GEOSITE,openai"),
        )
        self.assertLess(
            generated.index(f"ruleset={CHAIN_POLICY},[]GEOSITE,category-ai-!cn"),
            generated.index("ruleset=🧠 AI,[]GEOSITE,category-ai-!cn"),
        )

        self.assertLess(
            generated.index("/rules/claude.yaml,86400"),
            generated.index(f"ruleset={CHAIN_POLICY},[]GEOSITE,category-ai-!cn"),
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
        module_path = ROOT / "openclash" / "sg-residential-chain.conf"
        self.assertTrue(module_path.exists(), "OpenClash overwrite module is missing")
        module = module_path.read_text(encoding="utf-8")

        for required in [
            "[YAML]",
            "proxies+:",
            f"name: '{CHAIN_PROXY}'",
            "type: socks5",
            "udp: true",
            "dialer-proxy: '链式前置-新加坡'",
            "proxy-groups+:",
            "proxy-groups*:",
            f"name: '{CHAIN_POLICY}'",
            f"- '{CHAIN_PROXY}'",
            "include-all-providers: true",
            "filter: '(?i)(🇸🇬|新加坡|\\bSG\\b|singapore)'",
            "__RESIDENTIAL_SERVER__",
            "__RESIDENTIAL_PORT__",
            "__RESIDENTIAL_USERNAME__",
            "__RESIDENTIAL_PASSWORD__",
        ]:
            self.assertIn(required, module)

        front_group_block = module.split("proxy-groups+:", 1)[1].split(
            "proxy-groups*:", 1
        )[0]
        self.assertNotRegex(front_group_block, r"Provider_[A-Z0-9]+")
        self.assertNotIn("\n    use:", front_group_block)

        proxy_block = module.split("proxies+:", 1)[1].split("proxy-groups+:", 1)[0]
        expected_credentials = {
            "server": "'__RESIDENTIAL_SERVER__'",
            "port": "'__RESIDENTIAL_PORT__'",
            "username": "'__RESIDENTIAL_USERNAME__'",
            "password": "'__RESIDENTIAL_PASSWORD__'",
        }
        actual_credentials = {}
        for raw_line in proxy_block.splitlines():
            line = raw_line.strip()
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key in expected_credentials:
                actual_credentials[key] = value.strip()

        self.assertEqual(actual_credentials, expected_credentials)

    def test_overwrite_module_scopes_ai_dns_and_blocks_common_webrtc_ports(self) -> None:
        module = (ROOT / "openclash" / "sg-residential-chain.conf").read_text(
            encoding="utf-8"
        )
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
            "'rule-set:claude':",
            "'geosite:openai':",
            "https://1.1.1.1/dns-query#住宅链式出口",
            "https://dns.google/dns-query#住宅链式出口",
            "proxy-server-nameserver!:",
            "+rules:",
        ]:
            self.assertIn(required, module)

        default_nameserver_block = module.split("  nameserver!:", 1)[1].split(
            "  nameserver-policy!:", 1
        )[0]
        self.assertIn("https://dns.alidns.com/dns-query", default_nameserver_block)
        self.assertIn("https://doh.pub/dns-query", default_nameserver_block)
        self.assertNotIn(CHAIN_POLICY, default_nameserver_block)

        ai_dns_policy_block = module.split("  nameserver-policy!:", 1)[1].split(
            "  proxy-server-nameserver!:", 1
        )[0]
        self.assertIn("'rule-set:claude':", ai_dns_policy_block)
        self.assertIn("'geosite:openai':", ai_dns_policy_block)
        self.assertIn(
            f"https://1.1.1.1/dns-query#{CHAIN_POLICY}", ai_dns_policy_block
        )
        self.assertIn(
            f"https://dns.google/dns-query#{CHAIN_POLICY}", ai_dns_policy_block
        )

        for client in WEBRTC_PROTECTED_CLIENTS:
            self.assertIn(
                f"AND,((SRC-IP-CIDR,{client}),(NETWORK,udp),(DST-PORT,3478-3481)),REJECT",
                module,
            )
            self.assertIn(
                f"AND,((SRC-IP-CIDR,{client}),(NETWORK,udp),(DST-PORT,19302-19309)),REJECT",
                module,
            )
            self.assertNotIn(
                f"AND,((SRC-IP-CIDR,{client}),(NETWORK,udp)),{CHAIN_POLICY}",
                module,
            )

        self.assertNotIn(f"- NETWORK,udp,{CHAIN_POLICY}", module)


if __name__ == "__main__":
    unittest.main()
