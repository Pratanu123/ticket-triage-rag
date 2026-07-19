# API: Rate Limits

Base URL: `https://api.cloudnova.example/v1`

## Limits by plan
| Plan | Requests / day | Burst / minute |
|------|----------------|----------------|
| Pro | 5,000 | 60 |
| Business | 50,000 | 300 |
| Starter | API not included | — |

## Rate-limit response
When exceeded, the API returns **HTTP 429** with:
- `Retry-After` (seconds)
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset` (Unix timestamp)

## Best practices
- Cache GETs for project and member lists
- Use webhooks instead of polling
- Back off with jitter on 429s
- Rotate to a Business plan if you consistently hit Pro limits
