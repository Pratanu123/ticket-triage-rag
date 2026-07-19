# Billing: Failed Charges

CloudNova is a project-management SaaS. This page covers what happens when a
subscription payment fails.

## Why a charge fails
Common causes:
- Expired or cancelled card
- Insufficient funds
- Bank declining an international / recurring charge
- Billing address or ZIP mismatch with the card issuer

## What CloudNova does after a failure
1. Immediate email: **Action required — payment failed**
2. Automatic retry after **3 days**, then again after **7 days**
3. If all retries fail, the workspace enters **read-only mode**
4. Data is retained for **60 days** while the account is past due

## Fix it
1. Open **Settings → Billing → Payment method**
2. Add a valid card (Visa, Mastercard, Amex)
3. Click **Retry payment now**

Successful retry restores full write access within a few minutes. Contact
billing@cloudnova.example if the charge succeeds at your bank but CloudNova
still shows past due.
