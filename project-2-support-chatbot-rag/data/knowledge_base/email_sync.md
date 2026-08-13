# AcmeCRM — Email Sync

## Supported providers

Gmail / Google Workspace and Microsoft 365 / Outlook are supported via
OAuth. Other IMAP/SMTP providers can be connected manually under
Settings → Email Sync → Other Provider.

## What gets synced

Emails sent to or received from addresses that match an existing contact
are automatically logged to that contact's timeline. You can also log an
email to a contact manually if the address doesn't match exactly (e.g. a
personal vs. work email).

## Setting up email sync

1. Go to Settings → Email Sync → Connect Account.
2. Sign in and authorize AcmeCRM's requested permissions (read/send access
   to your mailbox).
3. Choose a sync direction: two-way (log AcmeCRM-sent emails and inbox
   emails) or one-way (log only emails sent from AcmeCRM).
4. Optionally exclude specific folders (e.g. Promotions, Spam) from sync.

## Sending emails from AcmeCRM

Compose an email directly from a contact or deal page. Sent emails appear
in your connected mailbox's Sent folder and are automatically logged to the
record's timeline, including open and click tracking if enabled.

## Reconnecting after sync failure

OAuth tokens can expire or be revoked (e.g. after a company-wide password
reset). If sync stops, go to Settings → Email Sync and click Reconnect. If
you use two-factor authentication with an app-specific password, you may
need to generate a new one from your email provider.

## Privacy

Only emails to/from addresses that exist as AcmeCRM contacts are synced —
your entire mailbox is never imported. Team members can only see synced
emails for records they have permission to view.
