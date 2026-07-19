# Security and Privacy

## Data residency
CloudLedger stores primary data in `us-east-1`. Enterprise (custom) contracts can
request EU residency — contact sales@cloudledger.example.

## Encryption
- In transit: TLS 1.2+
- At rest: AES-256 for databases and object storage

## Roles
- **Owner** — full control including billing and deletion
- **Admin** — manage members, approvals, integrations
- **Member** — create expenses/invoices per permissions
- **Auditor** — read-only access to reports (Scale)

## GDPR / data export
Any member can export their own data. Workspace owners can export all workspace
data from **Settings → Data export**. Deletion requests: privacy@cloudledger.example.

## Incident response
Security issues: security@cloudledger.example. We acknowledge reports within
2 business days.
