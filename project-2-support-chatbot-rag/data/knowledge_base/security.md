# AcmeCRM — Security & Compliance

## Data protection

All data in transit is encrypted with TLS 1.2+, and all data at rest is
encrypted using AES-256. Backups run every 6 hours and are retained for 30
days.

## Access control

Every workspace supports role-based access control (Admin, Manager, Rep) —
see the Admin Roles & Permissions guide for details. Enterprise plans add
Single Sign-On (SSO) via SAML 2.0 and support enforcing SSO-only login for
the whole workspace.

## Two-factor authentication

All users can enable 2FA (TOTP authenticator apps) from Settings → Security.
Admins can require 2FA for every user in the workspace on Growth and
Enterprise plans.

## Audit logs

Enterprise plans include a full audit log of every login, permission
change, export, and record deletion, retained for 12 months and exportable
for compliance review.

## Compliance

AcmeCRM is SOC 2 Type II certified and GDPR compliant. Data processing
agreements (DPAs) are available for Enterprise customers on request. EU
customers can choose EU-region data residency at signup.

## Data deletion requests

Account owners can request full account data deletion from Settings →
Privacy → Delete Account. Deletion is permanent after a 30-day recovery
window and completes within 30 days of the window closing, in line with
GDPR Article 17 (Right to Erasure).

## Reporting a security issue

Email security@acmecrm.example. We acknowledge reports within 24 hours and
follow a coordinated disclosure process for verified vulnerabilities.
