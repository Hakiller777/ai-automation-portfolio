# AcmeCRM — Data Import & Export

## Importing contacts or deals

1. Go to Settings → Data → Import and choose Contacts or Deals.
2. Upload a CSV file (UTF-8 encoded, with a header row).
3. Map each CSV column to an AcmeCRM field in the mapping screen — AcmeCRM
   auto-matches columns with similar names.
4. Choose how to handle duplicates: skip, update existing record, or create
   a new record. Duplicates are detected by email (contacts) or by deal name
   + contact (deals).
5. Review the preview of the first 10 rows, then confirm to start the
   import.

Imports run in the background; you'll get a notification and an email when
the import finishes, including a summary of rows imported, skipped, and
failed. Failed rows can be downloaded as a CSV with an error reason per row.

## Import limits

A single file can contain up to 50,000 rows and must be under 25MB. Larger
datasets should be split into multiple files, imported one at a time.

## Exporting data

Go to Settings → Data → Export, choose the object type and any filters, and
export to CSV. Exports include all standard and custom fields. Enterprise
plans support scheduled recurring exports delivered to an S3 bucket you
configure.

## Migrating from another CRM

AcmeCRM provides guided import templates for Salesforce, HubSpot, and
Pipedrive exports, which pre-map common fields automatically. For custom or
legacy systems, use the generic CSV import and the manual field mapping
screen.
