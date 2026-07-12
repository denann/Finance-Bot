# app/sheets

This folder contains the Google Sheets data access layer.

The bot uses Google Sheets as a transparent operational data store. This layer handles worksheet access, schema checks, default setup, retry, and best-effort rollback.

## Main file

- `client.py`: Google Sheets client, schema bootstrap, read/write helpers, and atomic write wrapper.

## Important note

Google Sheets is practical for a personal finance bot, but it is not a full transactional database. The rollback logic is best-effort and designed to reduce inconsistent writes.

## Ownership Contract

`client.py` is the only gspread boundary and canonical schema registry. Services request reads/writes; handlers must not write directly. Blind mutation retry, global finance caches, schema semantics, and Telegram rendering do not belong here. Fake-adapter, retry, snapshot, sort, and reconciliation tests live under `tests/service`.
