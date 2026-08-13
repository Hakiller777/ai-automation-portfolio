# AcmeCRM — Troubleshooting

**I can't log in.**
First confirm you're using the correct workspace URL (yourcompany.acmecrm.example).
If you forgot your password, use "Forgot password" on the login page — reset
emails arrive within 2 minutes. If your account was deactivated by an admin,
you'll see an "Account inactive" message; contact your workspace admin.

**Email sync stopped working.**
This is usually caused by an expired OAuth token. Go to Settings → Email Sync
and click "Reconnect." If you use two-factor authentication on your email
provider, you may need to generate a new app password. See the Email Sync
guide for provider-specific steps.

**Deals aren't showing up on the pipeline board.**
Check the active filter at the top of the board — a saved filter may be
hiding deals that don't match its criteria. Also confirm the deal is
assigned to the pipeline you're viewing; deals belong to exactly one
pipeline at a time.

**Import failed with "invalid format" error.**
Your CSV must use UTF-8 encoding and include a header row. Column names
must match the field names in AcmeCRM exactly, or you can map columns
manually in step 2 of the import wizard. Files larger than 25MB must be
split into multiple imports.

**The mobile app won't sync new changes.**
Pull down on any list screen to force a manual sync. If that doesn't work,
log out and back in. Persistent sync issues are almost always a connectivity
problem — check that the app has background data permission enabled.

**I'm getting a 429 "rate limited" error from the API.**
The API allows 100 requests per minute per API key. Add exponential backoff
to your integration, or contact support to request a higher limit on
Enterprise plans.
