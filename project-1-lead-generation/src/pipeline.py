"""End-to-end lead generation pipeline runner.

Orchestrates the full flow:
  CSV input → enrich → score → outreach → enriched CSV + JSON report

Called by n8n webhook or executed directly:
  python -m src.pipeline --input data/sample_leads.csv
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from .config import Settings, setup_logging
from .enrichment import enrich_batch
from .models import CompanySize, Lead, LeadStatus, PipelineResult
from .outreach import generate_outreach_batch
from .scoring import score_batch


def load_leads(csv_path: Path) -> list[Lead]:
    """Load leads from a CSV file into validated Lead models.

    Both read options are deliberate:

    `index_col=False` — when a row carries more fields than the header
    declares (a stray trailing comma is enough), pandas silently promotes the
    first column to the index, shifting every field one position left. Reading
    is then quietly wrong rather than loudly broken: `id` yields the company
    name, `company_size` yields the revenue band, and every row fails
    validation for reasons that point at the data instead of the parse.

    `keep_default_na=False` — by default pandas turns empty cells into NaN,
    and NaN is truthy, so the `value or None` idiom below passes a float into
    fields typed as `Optional[str]` and the row fails validation. Every lead
    with a blank website or LinkedIn URL would be dropped from the batch.
    Keeping empties as empty strings makes `or None` behave as intended.
    """
    df = pd.read_csv(csv_path, index_col=False, keep_default_na=False)
    leads: list[Lead] = []

    for _, row in df.iterrows():
        try:
            lead = Lead(
                id=str(row["id"]),
                company_name=str(row["company_name"]),
                industry=str(row["industry"]),
                company_size=CompanySize(str(row["company_size"])),
                annual_revenue=row.get("annual_revenue") or None,
                website=row.get("website") or None,
                location_city=str(row["location_city"]),
                location_country=str(row["location_country"]),
                contact_name=str(row["contact_name"]),
                contact_title=str(row["contact_title"]),
                contact_email=str(row["contact_email"]),
                contact_linkedin=row.get("contact_linkedin") or None,
                lead_source=str(row["lead_source"]),
                product_interest=str(row["product_interest"]),
                pain_points=str(row["pain_points"]),
            )
            leads.append(lead)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to parse row {row.get('id', '?')}: {exc}")

    logger.info(f"Loaded {len(leads)} valid leads from {csv_path}")
    return leads


def save_leads(leads: list[Lead], output_path: Path) -> None:
    """Persist processed leads to CSV."""
    records = [lead.model_dump() for lead in leads]
    # Serialize datetime and enum fields for CSV compatibility
    for r in records:
        r["status"] = r["status"].value if hasattr(r["status"], "value") else r["status"]
        r["company_size"] = r["company_size"].value if hasattr(r["company_size"], "value") else r["company_size"]
        r["created_at"] = str(r.get("created_at", ""))
        r["processed_at"] = str(r.get("processed_at", ""))
    pd.DataFrame(records).to_csv(output_path, index=False)
    logger.info(f"Saved {len(leads)} leads to {output_path}")


def run_pipeline(input_csv: Path, settings: Settings) -> PipelineResult:
    """Execute the full pipeline and return a summary report."""
    setup_logging(settings.log_level)
    logger.info(f"Pipeline started — input: {input_csv}")

    leads = load_leads(input_csv)
    total = len(leads)

    # Stage 1: Enrich
    leads = enrich_batch(leads)

    # Stage 2: Score (process in batches)
    all_scores = []
    for i in range(0, len(leads), settings.batch_size):
        batch = leads[i : i + settings.batch_size]
        leads[i : i + settings.batch_size], batch_scores = score_batch(batch)
        all_scores.extend(batch_scores)

    # Stage 3: Generate outreach
    leads, outreach_results = generate_outreach_batch(leads, all_scores)

    # Stage 4: Persist output
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / f"leads_processed_{timestamp}.csv"
    save_leads(leads, output_csv)

    # Build summary
    result = PipelineResult(
        total_leads=total,
        enriched=sum(1 for l in leads if l.status != LeadStatus.PENDING),
        scored=sum(1 for l in leads if l.status in (LeadStatus.SCORED, LeadStatus.OUTREACHED)),
        outreached=sum(1 for l in leads if l.status == LeadStatus.OUTREACHED),
        disqualified=sum(1 for l in leads if l.status == LeadStatus.DISQUALIFIED),
        hot_leads=sum(1 for s in all_scores if s.qualification_tier == "hot"),
        warm_leads=sum(1 for s in all_scores if s.qualification_tier == "warm"),
        cold_leads=sum(1 for s in all_scores if s.qualification_tier == "cold"),
        output_file=str(output_csv),
    )

    report_path = output_dir / f"report_{timestamp}.json"
    report_path.write_text(json.dumps(result.model_dump(), indent=2, default=str))

    logger.info(
        f"Pipeline complete — {result.outreached} outreached, "
        f"{result.hot_leads} hot, {result.warm_leads} warm, "
        f"{result.disqualified} disqualified"
    )
    return result


if __name__ == "__main__":
    import argparse

    from .config import settings

    parser = argparse.ArgumentParser(description="Lead generation pipeline")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample_leads.csv"),
        help="Path to input CSV file",
    )
    args = parser.parse_args()
    run_pipeline(args.input, settings)
