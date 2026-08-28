# Provider-Independent Residential Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent OpenClash startup failures when subscription updates rename `Provider_*` identifiers.

**Architecture:** The residential chain's Singapore front group will discover all proxy providers dynamically and retain the existing Singapore-node filter. A regression test will reject hard-coded provider identifiers in the overwrite module, while the README will document the update-safe behavior.

**Tech Stack:** OpenClash overwrite modules, Mihomo proxy groups, Python `unittest`, GitHub Actions.

**Spec:** `README.md#新加坡住宅链式代理`

## Global Constraints

- Keep residential credentials as placeholders in the repository.
- Preserve the residential SOCKS5 node, AI routing, DNS, IPv6, and UDP behavior.
- Do not edit generated `metafenliu.ini` manually.
- Production is the `main` branch served by `https://raw.githubusercontent.com/Bloomberg-zhong/openclash-rules/main/`.

---

### Task 1: Make the Singapore front group independent of provider IDs

**Files:**
- Modify: `tests/test_chain_config.py`
- Modify: `openclash/sg-residential-chain.conf`
- Modify: `README.md`

**Interfaces:**
- Consumes: Any `proxy-providers` keys emitted by the current subscription.
- Produces: A `链式前置-新加坡` select group using `include-all-providers: true` and the existing Singapore filter.

- [x] **Step 1: Write the failing regression test**

Update `test_overwrite_module_adds_udp_chain_without_real_credentials` to require `include-all-providers: true`, require the Singapore filter, and fail when the module contains any `Provider_[A-Z0-9]+` identifier.

- [x] **Step 2: Run the focused test to verify it fails**

Run: `python -m unittest tests.test_chain_config.ChainConfigTests.test_overwrite_module_adds_udp_chain_without_real_credentials -v`

Expected: FAIL because the existing module contains fixed provider identifiers and lacks `include-all-providers: true`.

- [x] **Step 3: Implement the minimal template change**

Replace the `use:` provider list under `链式前置-新加坡` with:

```yaml
    include-all-providers: true
    filter: '(?i)(🇸🇬|新加坡|\bSG\b|singapore)'
```

- [x] **Step 4: Update the operator documentation**

Document that the front group automatically includes all providers, continues to filter Singapore nodes, and does not need edits when provider IDs change.

- [x] **Step 5: Run the full test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass with no failures.

- [ ] **Step 6: Commit and deploy**

Commit the template, regression test, README, and this plan with message `fix: make residential chain provider independent`, push `main` to `origin`, and verify the GitHub Actions workflow result.
