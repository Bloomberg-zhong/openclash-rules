#!/usr/bin/env python3
from pathlib import Path
from urllib.request import urlopen


UPSTREAM_URL = "https://raw.githubusercontent.com/usbog232/clashmetadingyue/main/metafenliu.ini"

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_DIR = ROOT / "upstream"
CUSTOM_DIR = ROOT / "custom"
OUTPUT_FILE = ROOT / "metafenliu.ini"
UPSTREAM_FILE = UPSTREAM_DIR / "metafenliu.ini"

LOWER_MARKER = ";------------请在下方区域内添加应用---------------"
GROUP_PREFIX = "custom_proxy_group="


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def download_upstream() -> str:
    with urlopen(UPSTREAM_URL, timeout=30) as response:
        return response.read().decode("utf-8")


def insert_after_nth_marker(text: str, marker: str, nth: int, block: str) -> str:
    if not block:
        return text

    start = -1
    cursor = 0
    for _ in range(nth):
        start = text.find(marker, cursor)
        if start == -1:
            raise RuntimeError(f"找不到第 {nth} 个插入标记：{marker}")
        cursor = start + len(marker)

    insert_at = start + len(marker)
    injected = (
        "\n"
        "; >>> personal rules start\n"
        f"{block}\n"
        "; <<< personal rules end\n"
    )
    return text[:insert_at] + injected + text[insert_at:]


def group_name(line: str) -> str:
    return line[len(GROUP_PREFIX):].split("`", 1)[0].strip()


def drop_overridden_groups(upstream: str, custom_groups: str) -> str:
    """custom/groups.ini 里与上游同名的策略组替换上游定义，避免重名。"""
    names = {
        group_name(line)
        for line in custom_groups.splitlines()
        if line.startswith(GROUP_PREFIX)
    }
    kept = [
        line
        for line in upstream.splitlines(keepends=True)
        if not (line.startswith(GROUP_PREFIX) and group_name(line) in names)
    ]
    return "".join(kept)


def main() -> None:
    UPSTREAM_DIR.mkdir(parents=True, exist_ok=True)

    upstream = download_upstream()
    UPSTREAM_FILE.write_text(upstream, encoding="utf-8")

    custom_rules = read_text(CUSTOM_DIR / "rules.ini")
    custom_groups = read_text(CUSTOM_DIR / "groups.ini")

    result = drop_overridden_groups(upstream, custom_groups)
    result = insert_after_nth_marker(result, LOWER_MARKER, 1, custom_rules)
    result = insert_after_nth_marker(result, LOWER_MARKER, 2, custom_groups)

    OUTPUT_FILE.write_text(result, encoding="utf-8")
    print(f"Generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
