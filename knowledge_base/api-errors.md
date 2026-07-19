# Common API Errors

| HTTP | Code | Meaning | What to do |
|------|------|---------|------------|
| 400 | `invalid_request` | Missing/invalid JSON fields | Check the request schema |
| 401 | `unauthorized` | Missing or invalid API key | Verify the Bearer token |
| 403 | `forbidden` | Key lacks permission or plan too low | Upgrade plan or use a key with the right scopes |
| 404 | `not_found` | Resource ID does not exist | Confirm the ID and workspace |
| 409 | `conflict` | Duplicate idempotency key with different body | Reuse the same body or a new key |
| 422 | `validation_error` | Field failed validation | Inspect `errors[]` in the response |
| 429 | `rate_limited` | Daily or burst limit exceeded | Back off using `Retry-After` |
| 500 | `internal_error` | Unexpected server error | Retry with exponential backoff; contact support if persistent |

## Idempotency
POST endpoints that create resources accept `Idempotency-Key` (UUID recommended).
Keys are remembered for 24 hours.

## Sandbox vs live
Never send `clk_test_` keys to production endpoints or the reverse. Mismatched
environments return `401 unauthorized`.
