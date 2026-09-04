# benchmarks

## Purpose

`phase3_synthetic.py` provides deterministic offline operation-count profiles for 100, 1,000, and 10,000 synthetic finance rows. Timing is local and informational; call/row/rewrite counts are the regression contract.

`phase5_scale.py` exercises the retained Google Sheets scale boundary and
produces the evidence used by the Phase 5 persistence decision.

The benchmark must use fictional generated data, fake profiles, and no Telegram, Sheets, Gemini, HTTP, or credentials. Production load testing does not belong here.
