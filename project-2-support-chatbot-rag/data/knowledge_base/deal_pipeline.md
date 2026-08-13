# AcmeCRM — Deal Pipeline Management

## What a pipeline is

A pipeline is an ordered set of stages a deal moves through, from first
contact to close (won or lost). You can create multiple pipelines for
different sales motions — for example "New Business" and "Renewals" often
have very different stages.

## Creating and editing a pipeline

Go to Settings → Pipelines → New Pipeline, name it, and add stages in
order. Existing pipelines can be edited the same way; reordering stages
does not move deals, but deleting a stage requires moving its deals to
another stage first.

## Working the Kanban board

The Deals view shows a Kanban board with one column per stage. Drag a deal
card to a new column to change its stage — this is logged as an activity
and can trigger automation workflows tied to that stage change.

## Deal probability and forecasting

Each stage has a default win probability (e.g. Proposal = 50%, Negotiation
= 75%) used to calculate weighted forecast in the Forecast report.
Probabilities can be overridden per-deal if a rep has more specific insight.

## Marking a deal won or lost

Move a deal to the Won or Lost stage (every pipeline has both as terminal
stages). Marking a deal Lost requires selecting a "lost reason" from a
configurable list (e.g. "Price," "Timing," "Chose competitor"), which feeds
the Win Rate report's loss analysis.

## Multiple pipelines and reporting

Reports can be scoped to a single pipeline or rolled up across all
pipelines. If your team uses multiple pipelines, make sure stage names are
distinct enough (or use pipeline filters) to avoid confusing cross-pipeline
reports.
