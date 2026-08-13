# AcmeCRM — Admin Roles & Permissions

## Built-in roles

**Admin** — Full access: billing, integrations, user management, data
export, and all records regardless of owner. Every workspace must have at
least one Admin.

**Manager** — Can see and edit all deals and contacts across the team, view
team-wide reports, and manage automations. Cannot access billing or delete
the workspace.

**Rep** — Can see and edit only the contacts and deals they own by default.
Admins can grant a Rep visibility into a specific pipeline or team if
needed.

## Custom roles (Enterprise only)

Enterprise workspaces can define custom roles with granular permissions per
object (Contacts, Deals, Reports, Automations) — for example a "Read-only
Analyst" role that can view reports but not edit any records.

## Changing a user's role

Go to Settings → Team Members, click a user, and select a new role from the
dropdown. Role changes take effect immediately, including for that user's
currently open browser sessions.

## Record-level ownership

Every contact and deal has a single owner, shown at the top of the record.
Only the owner, their manager (if manager visibility is enabled), and
Admins can edit an owned record by default. Ownership can be reassigned
from the record page or in bulk from a list view.

## Removing a user

Removing a user from Settings → Team Members reassigns their open deals and
contacts to the workspace Admin unless you choose a different reassignment
target during removal. Historical activity records remain attributed to the
removed user for reporting accuracy.
