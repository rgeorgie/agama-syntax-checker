#!/usr/bin/env python3
"""
Agama JSON Profile Syntax Checker
Based on:
  https://agama-project.github.io/docs/user/reference/profile
  https://documentation.suse.com/sles/16.0/html/SLES-x86-64-agama-automated-installation/
  SUSE KB 000022590

Usage: ./check-agama-profile.py <profile.json>
"""

import sys
import json
import re

RESET  = "\033[0m"
RED    = "\033[31m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"

errors   = []
warnings = []

def err(msg):  errors.append(f"{RED}  ✗ ERROR:{RESET} {msg}")
def warn(msg): warnings.append(f"{YELLOW}  ⚠ WARN:{RESET}  {msg}")
def ok(msg):   print(f"{GREEN}  ✓{RESET} {msg}")
def info(msg): print(f"{CYAN}  ℹ{RESET} {msg}")


# ──────────────────────────────────────────────────────────────────────────────
# 1. Load & parse
# ──────────────────────────────────────────────────────────────────────────────
def load_json(path):
    try:
        with open(path) as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"{RED}File not found:{RESET} {path}")
        sys.exit(1)

    if re.search(r',\s*[}\]]', raw):
        err("Trailing comma(s) found before '}' or ']'. JSON does not allow trailing commas.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        err(f"JSON parse error — {e}")
        _print_summary()
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Top-level keys
# ──────────────────────────────────────────────────────────────────────────────
VALID_TOP = {
    "product", "root", "localization", "questions",
    "software", "scripts", "storage", "legacyAutoyastStorage",
    "network", "users", "user", "hostname", "bootloader", "security",
    "files", "access", "ntp"
}

def check_top_level(p):
    for key in p:
        if key not in VALID_TOP:
            err(f"Unknown top-level key '{key}'. Valid keys: {sorted(VALID_TOP)}")
    if "product" not in p:
        err("Missing required section 'product'.")


# ──────────────────────────────────────────────────────────────────────────────
# 3. product
# ──────────────────────────────────────────────────────────────────────────────
VALID_PRODUCT_KEYS = {"id", "mode", "registrationCode", "registrationEmail", "registrationUrl", "addons"}

def check_product(p):
    if "product" not in p:
        return
    prod = p["product"]
    if not isinstance(prod, dict):
        err("'product' must be an object."); return
    if "id" not in prod:
        err("'product.id' is required (e.g. \"SLES\", \"SLED\", \"Tumbleweed\").")
    else:
        ok(f"product.id = \"{prod['id']}\"")
    for key in prod:
        if key not in VALID_PRODUCT_KEYS:
            err(f"Unknown key in 'product': '{key}'. Valid: {sorted(VALID_PRODUCT_KEYS)}")
    if "registrationCode" not in prod:
        warn("No 'product.registrationCode' — registration prompt may appear. "
             "Set to \"\" to skip registration silently.")
    else:
        label = "empty — registration skipped" if prod["registrationCode"] == "" else "value provided"
        ok(f"product.registrationCode ({label}).")


# ──────────────────────────────────────────────────────────────────────────────
# 4. root
# ──────────────────────────────────────────────────────────────────────────────
def check_root(p):
    if "root" not in p:
        warn("No 'root' section — root password/key will not be set."); return
    r = p["root"]
    if not isinstance(r, dict):
        err("'root' must be an object."); return
    if "password" not in r and "sshPublicKey" not in r:
        err("'root' must have at least 'password' or 'sshPublicKey'.")
    if "password" in r:
        ok("root.password is set.")
    if "sshPublicKey" in r:
        ok("root.sshPublicKey is set.")
    if "hashedPassword" in r:
        if not isinstance(r["hashedPassword"], bool):
            err("'root.hashedPassword' must be a boolean (true/false).")
        elif r["hashedPassword"]:
            info("root.hashedPassword = true — password value is a pre-hashed string.")


# ──────────────────────────────────────────────────────────────────────────────
# 5. users
# ──────────────────────────────────────────────────────────────────────────────
def check_users(p):
    if "user" in p and "users" in p:
        err("Both 'user' and 'users' defined — Agama standard schema uses 'user' (single object).")
    elif "user" in p:
        u = p["user"]
        if not isinstance(u, dict):
            err("'user' must be an object."); return
        if "userName" not in u:
            err("'user' missing required field 'userName'.")
        else:
            ok(f"user.userName = \"{u['userName']}\"")
        if "password" not in u and "hashedPassword" not in u and "sshPublicKey" not in u:
            warn("'user' has no password or sshPublicKey set.")
    elif "users" in p:
        warn("'users' (array) was specified, but Agama's schema expects 'user' (single object). Change 'users: [...]' to 'user: { ... }'.")


# ──────────────────────────────────────────────────────────────────────────────
# 6. localization
# ──────────────────────────────────────────────────────────────────────────────
def check_localization(p):
    if "localization" not in p:
        warn("No 'localization' section — installer defaults will be used."); return
    loc = p["localization"]
    for field in ("language", "keyboard", "timezone"):
        if field not in loc:
            warn(f"'localization.{field}' not set.")
        else:
            val = loc[field]
            if field == "timezone" and re.match(r'^[A-Z]{3,4}$', str(val)) and val not in {"UTC", "GMT"}:
                warn(f"'localization.timezone' is \"{val}\" (abbreviation). Prefer standard IANA timezone name (e.g. \"Europe/Sofia\", \"America/New_York\", \"UTC\").")
            else:
                ok(f"localization.{field} = \"{val}\"")


# ──────────────────────────────────────────────────────────────────────────────
# 7. questions
# ──────────────────────────────────────────────────────────────────────────────
VALID_POLICIES = {"auto", "interactive"}

def check_questions(p):
    if "questions" not in p:
        warn("No 'questions' section — installer may prompt interactively, "
             "breaking unattended install. Add: \"questions\": {\"policy\": \"auto\"}")
        return
    q = p["questions"]
    policy = q.get("policy")
    if policy not in VALID_POLICIES:
        err(f"'questions.policy' must be one of {VALID_POLICIES}, got: \"{policy}\"")
    else:
        ok(f"questions.policy = \"{policy}\"")


# ──────────────────────────────────────────────────────────────────────────────
# 8. software
# ──────────────────────────────────────────────────────────────────────────────
def check_software(p):
    # Cross-check: In SLES 16, if registrationCode is empty (skipping SCC), extraRepositories or local media must provide packages
    prod = p.get("product", {})
    is_sles = isinstance(prod, dict) and prod.get("id", "").upper().startswith("SLES")
    is_skipping_reg = isinstance(prod, dict) and prod.get("registrationCode") == ""

    if "software" not in p:
        if is_sles and is_skipping_reg:
            warn("SLES 16 with skipped registration requires 'software.extraRepositories' to download base packages, or the installer will show 'must be registered'.")
        else:
            warn("No 'software' section.")
        return

    sw = p["software"]
    if not isinstance(sw, dict):
        err("'software' must be an object."); return

    has_repos = "extraRepositories" in sw and isinstance(sw["extraRepositories"], list) and len(sw["extraRepositories"]) > 0

    if is_sles and is_skipping_reg and not has_repos:
        warn("SLES 16 installer media does not include package pools. When skipping SCC registration (\"registrationCode\": \"\"), you must specify 'software.extraRepositories' pointing to your install mirror/Uyuni/SUMA server, otherwise the installer will halt saying 'SUSE Linux Enterprise Server 16.0 must be registered'.")

    if "packages" in sw:
        if not isinstance(sw["packages"], list):
            err("'software.packages' must be an array.")
        else:
            pkgs = sw["packages"]
            ok(f"software.packages: {len(pkgs)} package(s).")
            if is_sles and not any("patterns-base" in pkg or "pattern:" in pkg for pkg in pkgs) and "patterns" not in sw:
                info("Tip: Include 'patterns-base-minimal_base' in 'software.packages' for a clean base SLES 16 install.")

    if "patterns" in sw:
        if not isinstance(sw["patterns"], list):
            err("'software.patterns' must be an array.")
        else:
            ok(f"software.patterns: {len(sw['patterns'])} pattern(s).")

    if "extraRepositories" in sw:
        repos = sw["extraRepositories"]
        if not isinstance(repos, list):
            err("'software.extraRepositories' must be an array.")
        else:
            for i, repo in enumerate(repos):
                pfx = f"software.extraRepositories[{i}]"
                if "url" not in repo:
                    err(f"{pfx} missing required field 'url'.")
                if "alias" not in repo:
                    err(f"{pfx} missing required field 'alias'.")
                if "url" in repo and "alias" in repo:
                    ok(f"{pfx} alias=\"{repo['alias']}\" url OK.")
                if "allowUnsigned" in repo and not isinstance(repo["allowUnsigned"], bool):
                    err(f"{pfx}.allowUnsigned must be boolean (true/false).")


# ──────────────────────────────────────────────────────────────────────────────
# 9. scripts
# ──────────────────────────────────────────────────────────────────────────────
WRONG_SCRIPT_KEYS  = {"string", "body", "source", "inline", "text", "script", "data"}
VALID_SCRIPT_PHASES = {"pre", "post", "init", "chroot"}
# Keywords that suggest a script is trying to register/bootstrap a Salt minion
_BOOTSTRAP_PATTERNS = re.compile(
    r'bootstrap\.sh|venv-salt-minion|salt-minion|susemanager|uyuni|mgrctl|activation.key',
    re.IGNORECASE
)

def check_scripts(p):
    if "scripts" not in p:
        return
    scripts = p["scripts"]
    if not isinstance(scripts, dict):
        err("'scripts' must be an object."); return

    for phase in scripts:
        if phase not in VALID_SCRIPT_PHASES:
            err(f"Unknown script phase '{phase}'. Valid: {sorted(VALID_SCRIPT_PHASES)}")
            continue
        items = scripts[phase]
        if not isinstance(items, list):
            err(f"'scripts.{phase}' must be an array."); continue

        for i, s in enumerate(items):
            name = s.get("name", "(unnamed)")
            pfx  = f"scripts.{phase}[{i}] name=\"{name}\""
            # Warn when a bootstrap/registration script is placed in 'post'.
            # The 'post' phase runs inside the installer chroot — systemd is not
            # running there, so services started by the bootstrap script (e.g.
            # venv-salt-minion) will be left disabled after first boot.
            # Use 'init' instead: it runs as a systemd unit on the first real boot.
            if phase == "post":
                content_val = s.get("content", "") or ""
                url_val     = s.get("url", "") or ""
                if _BOOTSTRAP_PATTERNS.search(content_val) or \
                   _BOOTSTRAP_PATTERNS.search(url_val) or \
                   _BOOTSTRAP_PATTERNS.search(name):
                    warn(
                        f"{pfx} — bootstrap/registration script is in the 'post' phase. "
                        f"'post' runs inside the installer chroot where systemd is not active; "
                        f"services (e.g. venv-salt-minion) will be left disabled after first boot. "
                        f"Move this script to the 'init' phase so it runs on first boot."
                    )
            for bad in WRONG_SCRIPT_KEYS:
                if bad in s:
                    err(f"{pfx} — uses '{bad}' for script content. "
                        f"The correct property is 'content'. Rename \"{bad}\" → \"content\".")
            has_content = "content" in s
            has_url     = "url" in s
            if not has_content and not has_url:
                err(f"{pfx} — no script source. Use 'content' (inline) or 'url' (remote file).")
            elif has_content and has_url:
                err(f"{pfx} — both 'content' and 'url' present. Use only one.")
            elif has_content:
                if not s["content"].strip().startswith("#!"):
                    warn(f"{pfx} — 'content' does not start with a shebang (e.g. #!/bin/bash).")
                ok(f"{pfx} — inline 'content' ✓")
            elif has_url:
                ok(f"{pfx} — url=\"{s['url']}\" ✓")


# ──────────────────────────────────────────────────────────────────────────────
# 10. storage
# ──────────────────────────────────────────────────────────────────────────────
def check_storage(p):
    has_storage = "storage" in p
    has_legacy  = "legacyAutoyastStorage" in p
    if has_storage and has_legacy:
        err("Both 'storage' and 'legacyAutoyastStorage' present — use only one.")
    elif has_storage:
        ok("storage section present (native Agama format).")
    elif has_legacy:
        ok("legacyAutoyastStorage section present (AutoYaST compatibility format).")
    else:
        warn("No storage section — disk layout will not be configured automatically.")


# ──────────────────────────────────────────────────────────────────────────────
# 11. network
# ──────────────────────────────────────────────────────────────────────────────
def check_network(p):
    if "network" not in p:
        return
    if not isinstance(p["network"], dict):
        err("'network' must be an object."); return
    ok("network section present.")


# ──────────────────────────────────────────────────────────────────────────────
# 12. other top sections: hostname, bootloader, security, files, access, ntp
# ──────────────────────────────────────────────────────────────────────────────
def check_other_sections(p):
    if "hostname" in p:
        if not isinstance(p["hostname"], dict):
            err("'hostname' must be an object.")
        else:
            ok("hostname section present.")
    if "bootloader" in p:
        if not isinstance(p["bootloader"], dict):
            err("'bootloader' must be an object.")
        else:
            ok("bootloader section present.")
    if "security" in p:
        if not isinstance(p["security"], dict):
            err("'security' must be an object.")
        else:
            ok("security section present.")
    if "files" in p:
        if not isinstance(p["files"], list):
            err("'files' must be an array.")
        else:
            ok(f"files section: {len(p['files'])} file(s).")
    if "access" in p:
        if not isinstance(p["access"], dict):
            err("'access' must be an object.")
        else:
            ok("access section present.")
    if "ntp" in p:
        if not isinstance(p["ntp"], dict):
            err("'ntp' must be an object.")
        else:
            ok("ntp section present.")


# ──────────────────────────────────────────────────────────────────────────────
# Summary & main
# ──────────────────────────────────────────────────────────────────────────────
def _print_summary():
    print()
    for w in warnings: print(w)
    if warnings: print()
    for e in errors:   print(e)
    if errors: print()
    if errors:
        print(f"{BOLD}{RED}RESULT: INVALID — {len(errors)} error(s), {len(warnings)} warning(s).{RESET}")
    elif warnings:
        print(f"{BOLD}{YELLOW}RESULT: Valid with {len(warnings)} warning(s).{RESET}")
    else:
        print(f"{BOLD}{GREEN}RESULT: Profile is valid ✓{RESET}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <profile.json>")
        sys.exit(1)
    path = sys.argv[1]
    print(f"\n{BOLD}Agama Profile Checker{RESET} — {path}\n")
    profile = load_json(path)
    check_top_level(profile)
    check_product(profile)
    check_root(profile)
    check_users(profile)
    check_localization(profile)
    check_questions(profile)
    check_software(profile)
    check_scripts(profile)
    check_storage(profile)
    check_network(profile)
    check_other_sections(profile)
    _print_summary()
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
