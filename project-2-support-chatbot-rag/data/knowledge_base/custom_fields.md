# AcmeCRM — Custom Fields

## Why use custom fields

Default fields (name, email, deal value, stage, etc.) don't capture
everything specific to your business. Custom fields let you track anything
extra — for example "Contract Length," "Referral Source," or "Renewal
Date" — on Contacts, Deals, or Companies.

## Supported field types

Text, number, date, dropdown (single select), multi-select, checkbox
(yes/no), and currency. Dropdown and multi-select fields let you define a
fixed list of allowed values, which keeps reporting consistent.

## Creating a custom field

1. Go to Settings → Custom Fields and choose the object (Contacts, Deals,
   or Companies).
2. Click "New Field," choose a name and type, and, for dropdowns, define
   the option list.
3. Optionally mark the field as required — required fields must be filled
   in before a record can be saved.
4. Choose which roles can view and edit the field (Admins can always see
   all fields).

## Custom fields in reports and automations

Custom fields can be used as a report grouping or filter, and as a
condition or update target in automation workflows — for example,
"if Contract Length = 12 months, create a renewal task 30 days before
Renewal Date."

## Limits

Growth plans support up to 50 custom fields per object; Enterprise plans
have no limit. Deleting a custom field permanently removes its data from
all records — export the data first if you might need it later.

## Reordering fields

Field order on the record detail page can be changed by dragging fields in
Settings → Custom Fields → Layout, which affects how the page looks for
every user, not just yourself.
