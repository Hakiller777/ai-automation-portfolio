# AcmeCRM — Notifications

## Notification channels

AcmeCRM can notify you via in-app banner, email digest, mobile push, and
Slack (if connected). Configure each channel independently under Profile →
Notification Settings.

## Default notification events

- A deal you own changes stage
- A new lead is assigned to you
- You're mentioned in a note (@yourname)
- A task assigned to you is due today or overdue
- A deal you own has had no activity in 14 days ("stale deal" alert)

## Email digests

Instead of an email per event, you can switch to a daily or weekly digest
that summarizes all notifications from that period. This is configured
under Profile → Notification Settings → Email Frequency.

## Team-wide notifications (Managers and Admins)

Managers can subscribe to notifications for their whole team's deals, not
just their own, useful for monitoring pipeline health without checking the
dashboard constantly. Admins can also configure workspace-wide alerts, such
as notifying a #sales-alerts Slack channel whenever any deal over $50,000
is won.

## Muting notifications

Individual contacts or deals can be muted from their detail page (bell icon)
if you want to stop receiving updates on a specific record without changing
your global settings. Muted records can be unmuted at any time from the
same icon.

## Troubleshooting missing notifications

Check that the relevant channel is enabled in Notification Settings, and
for email, check your spam folder and confirm notifications@acmecrm.example
is allow-listed by your email provider.
