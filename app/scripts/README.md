# app/scripts

## Purpose

This folder owns canonical application-aware CLI implementations. `ai_command_tester.py` exercises local parsing/routing contracts and only performs live AI work behind explicit opt-in configuration.

The top-level `scripts/ai_command_tester.py` is a compatibility wrapper. New tester behavior belongs here; generic setup, documentation, PDF, and debug entry points belong in top-level `scripts/`.

Tests and default runs must remain offline and must not use production credentials.
