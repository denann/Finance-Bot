# AGENTS.md - Finance Bot Development Guide

## Project Context

This repository is a Python Telegram bot for personal finance tracking. It records expenses, income, transfers, debts, receivables, split bills, account balances, categories, reports, charts, and AI finance insights.

The main data layer is Google Sheets. Correctness, confirmation flow, and data safety are more important than speed.

Use Indonesian for user-facing explanations unless the user explicitly asks for another language.

## Priority Rules

1. Follow the user's latest explicit request first.
2. If the latest request conflicts with this file, follow the user but clearly mention the conflict and what was prioritized.
3. Do not guess business logic. Inspect relevant files before claiming, reviewing, or changing behavior.
4. Do not invent files, functions, callbacks, schemas, commands, routes, test results, categories, accounts, people, balances, debts, receivables, transactions, or history.
5. Preserve existing working flows unless the user explicitly asks to change them.
6. Keep changes focused, reviewable, and limited to the requested behavior.

## Anti-Hallucination Rules

When answering, reviewing, or modifying code:

1. Do not mention a file, function, class, variable, callback, command, or schema unless it exists in the repo or you are explicitly proposing to create it.
2. Do not summarize code behavior from memory. Re-read the relevant file before making claims.
3. Do not claim compatibility with an existing flow unless the affected files/flow were checked.
4. Do not claim a bug is fixed or a check passed unless the relevant fix/check was actually performed.
5. If repository behavior contradicts the user's description, state the discrepancy clearly.
6. Separate verified facts, assumptions, recommendations, and unverified risks.
7. If required information is missing, ask for clarification or state the assumption explicitly.
8. If data is insufficient for an AI finance insight, say the data is insufficient.

## Finance Safety Rules

1. Always keep preview-before-write/save.
2. Never write to Google Sheets before explicit user confirmation.
3. Do not silently change Google Sheets schema, callback format, command behavior, or transaction flow.
4. Transaction parsing must not bypass account selection unless the account is already explicit and valid.
5. Keep debt, receivable, split bill, transfer, set balance, normal expense, and normal income flows clearly separated.
6. Ambiguous inputs must ask for clarification instead of forcing classification.
7. Do not modify historical transaction data unless the user explicitly requests edit, update, delete, void, or settlement.
8. If a requested change may alter schema or a sensitive flow, ask the user for confirmation first.

## Regression-Sensitive Flows

Be extra careful with changes affecting:

- `/start`
- `/help`
- Transaction parsing
- Multi-input parsing
- Account selection
- Confirmation preview
- Save, edit, delete, cancel callbacks
- Category add/edit/matching flows
- Debt payment, receivable payment, debt settlement, and debt void/edit
- Split bill
- Transfer
- Set balance
- Monthly summaries, reports, charts, audit, coach, and AI insight
- Google Sheets write logic
- README and user-facing documentation

## User-Facing Flow Rules

1. Every new or changed interactive output must include a clear Batal button when cancellation is possible.
2. Prefer button-based cancellation over asking the user to type `/cancel`.
3. Keep preview text consistent with the saved data. Labels, subjects, descriptions, amounts, categories, accounts, and dates must match the actual transaction or pending action.
4. Do not write final data before the user confirms the final preview.
5. Bulk flows must not reject an entire batch only because one item needs clarification. Queue clarification per item when possible, then show a final preview before saving.
6. If a category input matches an existing category by name, alias, or similarity, ask whether to use the existing category or add a new one.
7. When adding or editing categories, keep type, symbol, name, and aliases consistent with the documented flow.

## Transaction Parsing Rules

Prioritize explicit intent over loose keyword matching.

- `beli kopi 10k dari Cash` is a normal expense if no debt, split, transfer, or set-balance signal exists.
- `bayar hutang Budi 100rb dari BCA` must route to debt payment or ask for clarification, not normal expense.
- `makan bareng Budi 80k` may need clarification because it can mean split bill, treat, or normal expense.
- Transfer-like inputs must not become expenses.
- Set-balance inputs must not become income or expense.

## AI Finance Insight Rules

For `/ask`, `/audit`, `/coach`, summaries, or insight features:

1. Base answers only on available transaction data.
2. Mention the analyzed period.
3. Separate facts from interpretation.
4. Prefer numeric summaries over vague claims.
5. Do not infer causes, habits, psychology, or future predictions without data.
6. If data is incomplete or categories are unclear, say so.

## Documentation Rules

When user-facing behavior changes, update affected documentation if it exists:

- `/start`
- `/help`
- Root README
- Parent or subfolder README files
- Feature docs
- Example commands
- Prompt or phase instruction files

Do not document behavior that is not implemented.

## Coding Style

1. Keep code readable and maintainable.
2. Prefer explicit names over clever abstractions.
3. Preserve existing project style unless there is a strong reason to change it.
4. Add comments for all syntax, but keep them short, concise, and clear.
5. Add detailed docstrings for important parser, routing, state, callback, helper, and sheet-writing functions.
6. Docstrings should explain the function purpose, expected input types/shape, output/return shape, side effects, and relevant flow constraints.
7. Do not over-refactor unrelated code.
8. Avoid mixing large refactors with bug fixes unless explicitly requested.

## Verification Rules

Before saying a coding task is complete:

1. Run the most relevant available check.
2. If a test/check cannot be run, clearly say it was not run and why.
3. Do not claim a fix passed unless the command was actually run.
4. Report command and result.

Common checks:

```bash
python -m compileall .
python -m pytest
pytest
```

If no automated tests exist, provide a minimal manual regression checklist for the affected flow.

## Final Response For Coding Tasks

Use this structure:

### What I changed

- ...

### Files touched

- `path/to/file.py`: ...

### Verification

- Tests run: `...`
- Result: pass/fail/not run

### Risks / assumptions

- ...

### Recommended next check

- ...

## Final Response For Review Or Audit Tasks

Use this structure:

### Verified findings

- ...

### Potential issues

- ...

### Outdated or inconsistent docs

- ...

### Suggested changes

- ...

## Communication Style

- Be direct, practical, specific, and evidence-based.
- Separate verified facts, assumptions, and recommendations.
- For professional writing, connect problem, solution, process, tools, output, and impact.
- For technical explanations, use concrete examples and end-to-end flow when useful.
- Keep answers concise enough for the audience; do not add filler.

## Writing Style

The user's preferred writing style is direct, practical, detailed when useful, analytical, structured, iterative, business-aware, and grounded in real implementation.

For README files, documentation, portfolio descriptions, LinkedIn-style drafts, project summaries, and professional explanations:

- Do not only list tools.
- Explain the practical problem, how the system works, what process/tools are used, what output is produced, and why the output is useful.
- Keep the tone natural, clear, direct, human, specific, and not overly polished.
- Avoid generic claims that are not supported by the implementation.

For casual or technical explanations:

- Start simple, then add technical detail only when needed.
- Use concrete examples and end-to-end workflows.
- Be honest about uncertainty.
- Keep the explanation practical and easy to act on.
