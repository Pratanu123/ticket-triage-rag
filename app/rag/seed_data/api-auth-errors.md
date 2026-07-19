# API: Authentication Errors

## Create an API key
Pro and Business only: **Settings → Developers → API keys → Create key**.
Keys look like `cnv_live_...` (production) or `cnv_test_...` (sandbox).

## Authenticate
```
Authorization: Bearer cnv_live_xxx
```

## Common auth errors
| HTTP | Code | Cause | Fix |
|------|------|-------|-----|
| 401 | `unauthorized` | Missing/invalid key | Check Bearer token and environment |
| 401 | `key_revoked` | Key was revoked | Create a new key |
| 403 | `forbidden` | Key lacks scope or plan too low | Upgrade plan or create a key with needed scopes |
| 403 | `ip_not_allowed` | IP allowlist enabled | Add your egress IP under Developers → Allowlist |

Never send `cnv_test_` keys to production hosts (or the reverse). Mismatched
environments always return `401 unauthorized`.
