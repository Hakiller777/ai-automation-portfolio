# AcmeCRM — Integrations

AcmeCRM connects to the tools your sales team already uses. Integrations are
managed from Settings → Integrations.

**Email providers** — Gmail and Microsoft 365 connect via OAuth in one
click, enabling two-way email sync and activity logging.

**Calendar** — Google Calendar and Outlook Calendar sync meeting invites and
show availability directly on contact and deal pages.

**Slack** — Get real-time notifications in Slack when a deal changes stage,
a new lead is assigned to you, or a task is due. Configure which channels
receive which events under Integrations → Slack.

**Zapier & n8n** — AcmeCRM publishes a REST API and webhook events
(deal.created, deal.stage_changed, contact.created) that work with Zapier,
n8n, or any custom automation tool. See the API Reference for authentication
details.

**Accounting software** — QuickBooks and Xero integrations sync won deals
into invoices automatically, avoiding duplicate manual entry.

**Data warehouses (Enterprise only)** — Nightly sync to Snowflake or
BigQuery via a managed connector, useful for teams that centralize reporting
outside AcmeCRM.

## Setting up a new integration

1. Go to Settings → Integrations and select the tool you want to connect.
2. Authorize AcmeCRM's access via OAuth (or paste an API key for
   non-OAuth tools).
3. Choose which objects and events to sync.
4. Test the connection using the "Send test event" button before relying on
   it in production workflows.

Disconnecting an integration stops future syncs but does not delete data
that was already synced into AcmeCRM.
