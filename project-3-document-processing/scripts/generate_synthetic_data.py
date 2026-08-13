"""Generate synthetic sample data for the document processing demo.

Produces 10 fictional documents in data/incoming/, split across the two
simulated input channels the pipeline supports:
  - 4 real PDF files (rendered with reportlab, parsed with pypdf at runtime)
  - 6 simulated inbound emails (JSON with a `body` field)

All companies, amounts, and contacts are 100% invented for this portfolio
demo — no real third-party data is used.

Run once from the project root:
    python -m scripts.generate_synthetic_data
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path("data/incoming")


def _write_pdf(filename: str, lines: list[str]) -> None:
    path = OUTPUT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=letter)
    _, height = letter
    y = height - 72
    c.setFont("Helvetica", 11)
    for line in lines:
        c.drawString(72, y, line)
        y -= 16
    c.save()
    print(f"Wrote {path}")


def _write_email(filename: str, from_addr: str, subject: str, body: str) -> None:
    path = OUTPUT_DIR / filename
    path.write_text(
        json.dumps(
            {
                "channel": "email",
                "from": from_addr,
                "to": "ap@ourcompany.example",
                "subject": subject,
                "received_at": "2026-06-15T09:00:00",
                "body": body,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {path}")


# --- 4 real PDF documents -------------------------------------------------

PDF_INVOICE_1 = [
    "INVOICE",
    "",
    "Invoice Number: INV-2026-1001",
    "Invoice Date: 2026-06-02",
    "Due Date: 2026-06-16",
    "Vendor: Skyline Cloud Services Inc",
    "Vendor Address: 900 Harbor Blvd, Seattle, WA 98101",
    "Bill To: Acme Retail Group",
    "Customer Email: billing@acmeretail.com",
    "",
    "Line Items:",
    "3 x Cloud Compute - Standard Instance $900.00",
    "1 x Managed Backup Service $150.00",
    "2 x Priority Support Hours $300.00",
    "",
    "Subtotal: $1350.00",
    "Tax (8.5%): $114.75",
    "Total Due: $1464.75",
]

PDF_RECEIPT_1 = [
    "RECEIPT",
    "",
    "Receipt Number: RCT-55210",
    "Transaction Date: 2026-06-05",
    "Vendor: Riverside Print & Copy",
    "Vendor Address: 44 River Rd, Austin, TX 78701",
    "",
    "1 x Business Card Printing (500ct) $65.00",
    "3 x Poster Printing A1 $135.00",
    "",
    "Subtotal: $200.00",
    "Tax: $16.50",
    "Total: $216.50",
]

PDF_PURCHASE_ORDER_1 = [
    "PURCHASE ORDER",
    "",
    "PO Number: PO-7734",
    "Invoice Date: 2026-06-08",
    "Vendor: BrightWorks Office Furniture",
    "Vendor Address: 220 Industrial Way, Denver, CO 80202",
    "",
    "8 x Ergonomic Task Chair $1600.00",
    "4 x Adjustable Standing Desk $1800.00",
    "",
    "Subtotal: $3400.00",
    "Tax: $0.00",
    "Total: $3400.00",
]

PDF_INVOICE_2 = [
    "INVOICE",
    "",
    "Invoice Number: INV-2026-1042",
    "Invoice Date: 2026-06-11",
    "Due Date: 2026-06-25",
    "Vendor: Vertex Marketing Group",
    "Vendor Address: 77 Madison Ave, New York, NY 10016",
    "Bill To: Acme Retail Group",
    "Customer Email: billing@acmeretail.com",
    "",
    "Line Items:",
    "1 x Q3 Campaign Strategy $2200.00",
    "4 x Social Media Content Package $1200.00",
    "",
    "Subtotal: $3400.00",
    "Tax (8.5%): $289.00",
    "Total Due: $3689.00",
]


# --- 6 simulated inbound emails --------------------------------------------

EMAIL_INVOICE_1 = """INVOICE

Invoice Number: INV-2026-2005
Invoice Date: 2026-06-12
Due Date: 2026-06-26
Vendor: NimbusData Analytics
Vendor Address: 1200 Innovation Dr, San Jose, CA 95110
Bill To: Acme Retail Group
Customer Email: billing@acmeretail.com

Line Items:
1 x Data Pipeline Setup $1800.00
2 x Monthly Analytics Subscription $600.00

Subtotal: $2400.00
Tax (8.5%): $204.00
Total Due: $2604.00
"""

EMAIL_RECEIPT_1 = """RECEIPT

Receipt Number: RCT-91004
Transaction Date: 2026-06-13
Vendor: GreenLeaf Office Catering
Vendor Address: 58 Pine St, Chicago, IL 60601

1 x Team Lunch Catering (20 people) $340.00
1 x Delivery Fee $25.00

Subtotal: $365.00
Tax: $29.20
Total: $394.20
"""

EMAIL_PURCHASE_ORDER_1 = """PURCHASE ORDER

PO Number: PO-8842
Invoice Date: 2026-06-14
Vendor: Anchor Point Logistics
Vendor Address: 305 Dockside Ave, Newark, NJ 07102

12 x Pallet Shipping - Regional $4800.00
1 x Freight Insurance $150.00

Subtotal: $4950.00
Tax: $0.00
Total: $4950.00
"""

EMAIL_INCOMPLETE_INVOICE = """INVOICE

Invoice Number: INV-2026-2099
Invoice Date: 2026-06-16

Line Items:
1 x Miscellaneous Consulting Services $500.00
"""

EMAIL_UNRELATED = """Hi team,

Just a heads up that the office will be closed next Monday for the holiday.
See you all Tuesday!

Best,
Facilities
"""

EMAIL_INVOICE_2 = """INVOICE

Invoice Number: INV-2026-2110
Invoice Date: 2026-06-18
Due Date: 2026-07-02
Vendor: Solstice Renewable Energy Co
Vendor Address: 40 Solar Way, Phoenix, AZ 85001
Bill To: Acme Retail Group
Customer Email: billing@acmeretail.com

Line Items:
1 x Solar Panel Maintenance Visit $450.00
1 x Inverter Inspection $150.00

Subtotal: $600.00
Tax (8.5%): $51.00
Total Due: $651.00
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _write_pdf("invoice_1001.pdf", PDF_INVOICE_1)
    _write_pdf("receipt_5210.pdf", PDF_RECEIPT_1)
    _write_pdf("purchase_order_7734.pdf", PDF_PURCHASE_ORDER_1)
    _write_pdf("invoice_1042.pdf", PDF_INVOICE_2)

    _write_email("email_invoice_2005.json", "billing@nimbusdata.example", "Invoice INV-2026-2005", EMAIL_INVOICE_1)
    _write_email("email_receipt_91004.json", "receipts@greenleafcatering.example", "Receipt RCT-91004", EMAIL_RECEIPT_1)
    _write_email("email_po_8842.json", "orders@anchorpointlogistics.example", "PO-8842 Confirmation", EMAIL_PURCHASE_ORDER_1)
    _write_email("email_invoice_incomplete.json", "billing@unknownvendor.example", "Invoice INV-2026-2099", EMAIL_INCOMPLETE_INVOICE)
    _write_email("email_unrelated.json", "facilities@ourcompany.example", "Office closure notice", EMAIL_UNRELATED)
    _write_email("email_invoice_2110.json", "billing@solsticerenewable.example", "Invoice INV-2026-2110", EMAIL_INVOICE_2)


if __name__ == "__main__":
    main()
