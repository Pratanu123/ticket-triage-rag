# Login: Two-Factor Authentication (2FA)

## Enable 2FA
1. Open **Settings → Security → Two-factor authentication**
2. Scan the QR code with an authenticator app (Authy, Google Authenticator, 1Password)
3. Enter the 6-digit code to confirm
4. Save the one-time **backup codes** — they are shown only once

## Reset or recover 2FA
If you lost your authenticator device:
1. Use a backup code on the login screen (**Use a backup code**)
2. After signing in, go to **Settings → Security → Two-factor authentication**
3. Click **Disable 2FA**, then set it up again on your new device

If you have **no backup codes** and cannot sign in, a workspace admin can clear
your 2FA from **Settings → Team → member menu → Reset 2FA**. Solo owners should
email security@cloudnova.example from the account email with government ID for
manual recovery (1–2 business days).

## Common 2FA errors
- **Invalid code**: check the phone clock (time drift breaks TOTP)
- **Too many attempts**: wait 10 minutes before trying again
