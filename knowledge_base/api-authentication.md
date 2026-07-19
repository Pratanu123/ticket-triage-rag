# API Authentication

CloudLedger exposes a REST API at `https://api.cloudledger.example/v1`.

## Create an API key
1. Open **Settings → Developers → API keys** (Growth and Scale only)
2. Click **Create key**, name it, and copy the secret once

Keys begin with `clk_live_` for production and `clk_test_` for sandbox.

## Authenticate requests
Send the key in the `Authorization` header:

```
Authorization: Bearer clk_live_xxx
```

## Rate limits
- Growth: 1,000 requests / day
- Scale: 20,000 requests / day

Rate-limit responses return HTTP 429 with headers:
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## Key rotation
Create a new key, update your integration, then revoke the old key. Revocation
is immediate.
