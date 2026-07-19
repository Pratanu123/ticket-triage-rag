# SSO and Multi-Factor Authentication (MFA)

## Enable MFA (all plans)
1. Open **Settings → Security → Multi-factor authentication**
2. Scan the QR code with an authenticator app
3. Enter the 6-digit code to confirm

Backup codes are shown once — store them securely.

## SSO (Scale plan only)
Scale workspaces can enable SAML 2.0 SSO:
1. Go to **Settings → Security → SSO**
2. Enter your IdP metadata URL or upload the XML metadata file
3. Map the `email` attribute to CloudLedger users
4. Optionally enforce **SSO-only login** for the workspace

Supported IdPs include Okta, Azure AD / Entra ID, and Google Workspace SAML.

## Common SSO errors
- `SAML assertion expired`: check clock sync between IdP and CloudLedger.
- `Email not found`: the user must already be invited to the workspace.
- `Audience mismatch`: verify the Entity ID shown in CloudLedger SSO settings.
