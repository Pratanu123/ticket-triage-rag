# Webhooks

Webhooks notify your server when events occur in CloudLedger.

## Supported events
- `invoice.paid`
- `invoice.failed`
- `expense.submitted`
- `expense.approved`
- `expense.rejected`
- `member.invited`

## Configure an endpoint
1. Go to **Settings → Developers → Webhooks**
2. Add an HTTPS URL
3. Select events
4. Copy the signing secret (`whsec_...`)

## Signature verification
Each delivery includes headers:
- `X-CloudLedger-Signature` (HMAC SHA-256 hex digest)
- `X-CloudLedger-Timestamp` (Unix seconds)

Compute HMAC over `{timestamp}.{raw_body}` using the signing secret and compare
to the signature header. Reject requests older than 5 minutes.

## Retries
Failed deliveries (non-2xx) are retried up to 8 times over 24 hours with
exponential backoff.
