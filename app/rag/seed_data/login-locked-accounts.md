# Login: Locked Accounts

## Why an account locks
CloudNova locks an account after **10 failed password attempts** within
**15 minutes**. SSO-only users are not locked by password failures; failures are
handled by the identity provider.

## Unlock timing
Locks expire automatically after **30 minutes**. Password reset is still
available during a lockout and immediately unlocks the account when completed.

## Admin unlock
Workspace admins can unlock a member early:
1. **Settings → Team**
2. Open the member
3. Click **Unlock account**

Owners who lock themselves should use password reset or contact
support@cloudnova.example with the workspace slug.
