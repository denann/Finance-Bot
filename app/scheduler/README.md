# app/scheduler

This folder contains scheduled jobs.

Scheduled jobs are used for recurring transactions, reminders, summaries, and exports. The scheduler helps the bot run useful background tasks without requiring the user to send a message every time.

## Main file

- `jobs.py`: defines scheduler setup and job execution logic.

## Deployment contract

Scheduled jobs are supported only in a single application instance (`APP_INSTANCE_COUNT=1`). Startup rejects a multi-instance configuration while `SCHEDULER_ENABLED=true` because duplicate execution cannot be prevented without distributed locking.

Set `SCHEDULER_ENABLED=false` only when an approved separate process owns scheduled work. The `/ready` endpoint reports scheduler readiness when scheduling is enabled.
