# agama-syntax-checker

A command-line validator for [Agama](https://agama-project.github.io) JSON autoinstall profiles used with SLES 16, Uyuni, and SUSE Multi-Linux Manager 5.x.

## References

- [Agama Profile Reference](https://agama-project.github.io/docs/user/reference/profile)
- [SLES 16 Automated Installation](https://documentation.suse.com/sles/16.0/html/SLES-x86-64-agama-automated-installation/)
- [SUSE KB 000022590 — Autoinstalling SLES 16 with Agama Using Uyuni/SMLM](https://support.scc.suse.com/s/kb/Autoinstalling-SLES-16-with-Agama-Using-Uyuni-SUSE-Multi-Linux-Manager)

## Requirements

- Python 3.6+
- No external dependencies

## Usage

```bash
chmod +x check-agama-profile.py
./check-agama-profile.py <profile.json>
```

Exit code `0` = valid, exit code `1` = errors found.

## What it checks

| Section | Checks |
|---|---|
| JSON syntax | Parse errors, trailing commas |
| `product` | Required `id` field, unknown keys, missing `registrationCode` warning |
| `root` | Requires `password` or `sshPublicKey`, validates `hashedPassword` type |
| `users` | Requires `userName` per entry |
| `localization` | Warns on missing `language`, `keyboard`, `timezone` |
| `questions` | `policy` must be `auto` or `interactive` |
| `software` | Validates `extraRepositories` (requires `url` + `alias`), `packages`, `patterns` |
| `scripts` | Detects wrong property names (`body`, `string`, `source` → should be `content`), validates phases |
| `storage` | Warns if missing, errors if both `storage` and `legacyAutoyastStorage` present |
| `network` | Type validation |
| Top-level | Unknown keys flagged |

## Common errors caught

| Error | Cause | Fix |
|---|---|---|
| Trailing comma | `{"id": "SLES",}` | Remove the comma |
| Unknown top-level key `registration` | Not a valid Agama key | Remove it; use `product.registrationCode: ""` instead |
| Wrong script property `body` / `string` | Agama uses `content` | Rename to `content` |
| Missing `questions.policy` | Installer will prompt interactively | Add `"questions": {"policy": "auto"}` |
| Both `storage` and `legacyAutoyastStorage` | Conflict | Use only one |

## Examples

```bash
# Test against the included examples
./check-agama-profile.py examples/valid-profile.json
./check-agama-profile.py examples/invalid-profile.json
```
