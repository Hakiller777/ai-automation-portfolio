# AcmeCRM — Automation Workflows

## What automations do

Automation workflows let you trigger actions automatically when something
happens in AcmeCRM, without writing code. Each workflow has a trigger, an
optional condition, and one or more actions.

## Common triggers

- A new contact or deal is created
- A deal moves to a specific stage
- A field is updated (e.g. deal value changes)
- A deal has been inactive for N days
- A scheduled time (e.g. every Monday at 9am)

## Common actions

- Assign the record to a specific user or round-robin across a team
- Send an internal Slack or email notification
- Update a field (e.g. set priority to "High" for deals over $20,000)
- Create a task with a due date
- Send an automated email to the contact (using a template)

## Building a workflow

1. Go to Automations → New Workflow.
2. Choose a trigger and, optionally, a condition (e.g. "only if deal value
   > $10,000").
3. Add one or more actions.
4. Turn on "Test mode" to see which existing records would have triggered
   the workflow, without actually running the actions.
5. Activate the workflow.

## Limits

Growth plans support up to 20 active workflows; Enterprise plans have
unlimited workflows plus multi-step branching logic (if/else actions).

## Debugging a workflow that isn't firing

Check the Automations → Activity Log, which lists every time a workflow
was evaluated, whether it matched the condition, and any action errors.
The most common cause of a "silent" workflow is a condition that's stricter
than intended — test it against a record you expect to match.
