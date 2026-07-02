# app/scheduler

This folder contains scheduled jobs.

The scheduler is used for workflows that should run automatically, such as recurring transactions, reminders, exports, or summaries.

## File

| File | Purpose |
|---|---|
| `jobs.py` | Defines scheduled jobs and scheduler setup |

Scheduler logic should stay separate from Telegram handlers so the same finance logic can run manually or automatically.
