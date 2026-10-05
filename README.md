# agama-syntax-checker

Tools for working with [Agama](https://agama-project.github.io) JSON autoinstall profiles used with SLES 16, Uyuni, and SUSE Multi-Linux Manager 5.x.

🌐 **Live:** [rgeorgie.github.io/agama-syntax-checker](https://rgeorgie.github.io/agama-syntax-checker/)

## References

- [Agama Profile Reference](https://agama-project.github.io/docs/user/reference/profile)
- [SLES 16 Automated Installation](https://documentation.suse.com/sles/16.0/html/SLES-x86-64-agama-automated-installation/)
- [SUSE KB 000022590 — Autoinstalling SLES 16 with Agama Using Uyuni/SMLM](https://support.scc.suse.com/s/kb/Autoinstalling-SLES-16-with-Agama-Using-Uyuni-SUSE-Multi-Linux-Manager)

---

## Profile Builder — `agama-profile-builder.html`

A self-contained web UI for generating Agama JSON profiles. No server or dependencies required — open it directly in any browser.

```bash
open agama-profile-builder.html        # macOS
xdg-open agama-profile-builder.html   # Linux
```

Or serve it statically from your SUMA/Uyuni server so your team can access it by URL:

```bash
cp agama-profile-builder.html /srv/www/htdocs/pub/
# → http://<suma-server>/pub/agama-profile-builder.html
```

### Covered sections

| Section | Fields |
|---|---|
| **Product** | Product ID, mode (standard/immutable), registration code/email/URL, add-ons/extensions |
| **Root** | Password, hashedPassword, SSH public key(s) |
| **First User** | Standard Agama `"user": { ... }` object, userName, fullName, password, hashedPassword, SSH public key(s) |
| **Localization** | language, keyboard, timezone (with IANA name checks) |
| **Hostname** | static, transient |
| **Network** | Connections — IPv4/IPv6 method, manual IP/gateway/DNS, Wi-Fi (SSID, security, password), Bridge (ports), autoconnect, persistent |
| **Software** | Packages, patterns (replace/add/remove modes), extra repositories (url, alias, name, priority, allowUnsigned, gpgFingerprints), SLES 16 offline install cross-check |
| **Bootloader** | stopOnBootMenu, timeout, extraKernelParams, updateNvram |
| **Storage** | legacyAutoyastStorage (AutoYaST) with preset layouts, or native Agama storage JSON (drives/VGs/RAIDs/encryption) |
| **Security** | Trusted SSL certificates (fingerprint + algorithm) |
| **Scripts** | pre / post / init phases, inline content or URL, chroot option, bootstrap-in-post warning |
| **Files** | Deploy files to installed system — content or URL, destination, permissions, user, group |
| **Questions** | policy (auto/interactive), automatic answers for unsigned packages / unknown GPG keys |
| **Access** | ssh, webConsole |
| **NTP** | Sources — pool/server/peer, address, iburst, offline |
| **Kernel / PXE Generator** | Generates exact kernel boot parameters for Uyuni/SUMA and Cobbler CLI to prevent `inst.auto=1` and `rd.live.image=~` bugs |

The right panel shows a live syntax-highlighted JSON preview with a validation bar. Use **Copy** or **⬇ Download** to save the profile.

---

## Profile Validator — `check-agama-profile.py`

A command-line validator that checks an existing Agama JSON profile for errors and warnings.

### Requirements

- Python 3.6+
- No external dependencies

### Usage

```bash
chmod +x check-agama-profile.py
./check-agama-profile.py <profile.json>
```

Exit code `0` = valid, exit code `1` = errors found.

### What it checks

| Section | Checks |
|---|---|
| JSON syntax | Parse errors, trailing commas |
| `product` | Required `id` field, unknown keys, missing `registrationCode` warning |
| `root` | Requires `password` or `sshPublicKey`, validates `hashedPassword` type |
| `users` | Requires `userName` per entry |
| `localization` | Warns on missing `language`, `keyboard`, `timezone` |
| `questions` | `policy` must be `auto` or `interactive` |
| `software` | Validates `extraRepositories` (requires `url` + `alias`), `packages`, `patterns` |
| `scripts` | Detects wrong property names (`body`, `string`, `source` → should be `content`), validates phases, warns when bootstrap/registration scripts are in `post` instead of `init` |
| `storage` | Warns if missing, errors if both `storage` and `legacyAutoyastStorage` present |
| `network` | Type validation |
| Top-level | Unknown keys flagged |

### Common errors caught

| Error | Cause | Fix |
|---|---|---|
| Trailing comma | `{"id": "SLES",}` | Remove the comma |
| Unknown top-level key `registration` | Not a valid Agama key | Remove it; use `product.registrationCode: ""` instead |
| Wrong script property `body` / `string` | Agama uses `content` | Rename to `content` |
| Missing `questions.policy` | Installer will prompt interactively | Add `"questions": {"policy": "auto"}` |
| Both `storage` and `legacyAutoyastStorage` | Conflict | Use only one |
| Bootstrap script in `post` phase | systemd not active in `post` — services left disabled after boot | Move script to `init` phase |

### Examples

```bash
# Test against the included examples
./check-agama-profile.py examples/valid-profile.json
./check-agama-profile.py examples/invalid-profile.json
```
