# app/sheets

This folder contains the Google Sheets data layer.

The goal is to keep low-level spreadsheet access in one place. Services should call this layer instead of calling gspread directly.

## File

| File | Purpose |
|---|---|
| `client.py` | Connects to Google Sheets, validates schema, reads/writes data, retries requests, and attempts rollback |

Google Sheets is practical and transparent, but it is not a transactional database. Because of that, this project uses best-effort rollback for multi-step write operations.
