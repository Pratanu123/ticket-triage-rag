# API: Common Status Codes

| HTTP | Code | Meaning |
|------|------|---------|
| 200 | `ok` | Success |
| 201 | `created` | Resource created |
| 400 | `invalid_request` | Malformed JSON or missing fields |
| 401 | `unauthorized` | Auth failed |
| 403 | `forbidden` | Authenticated but not allowed |
| 404 | `not_found` | Unknown resource ID |
| 409 | `conflict` | Idempotency key reused with a different body |
| 422 | `validation_error` | Field-level validation failed (`errors[]`) |
| 429 | `rate_limited` | Slow down; see rate-limit docs |
| 500 | `internal_error` | Retry with exponential backoff |
| 503 | `unavailable` | Temporary outage; check status.cloudnova.example |

## Idempotency
POST create endpoints accept header `Idempotency-Key` (UUID). Keys are stored
for **24 hours**. Replays with the same key and body return the original result.
