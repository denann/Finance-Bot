# 09. Function Reference

This file is a quick reference for top-level functions and classes. It is useful when you want to locate where a flow is implemented.

## `app/api/webhook.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `set_telegram_app(app: Application)` | Set a value for telegram app. |
| `async def` | `webhook(request: Request, x_telegram_bot_api_secret_token: str=Header(None))` | Helper for webhook in the webhook API layer. |

## `app/app/bot/application.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `atomic_bot_handler(callback)` | Wrap a Telegram handler inside a best-effort Google Sheets transaction context. |
| `def` | `register_handlers(telegram_app: Application)` | Register all Telegram commands, message handlers, callback handlers, and error handlers. |
| `async def` | `scheduled_data_export(context)` | Helper for scheduled data export in the application. |
| `def` | `register_job_queue_jobs(telegram_app: Application)` | Helper for register job queue jobs in the application. |
| `def` | `build_telegram_app()` | Create one configured Telegram Application instance with handlers and scheduled jobs. |

## `app/app/bot/handler_parts/callback_handler.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `is_skip_account_choice(account: str)` | Check whether a condition is true for skip account choice. |
| `def` | `mark_transaction_as_historical(parsed: dict)` | Mark a record as transaction as historical. |
| `def` | `mark_debt_as_historical(debt_parsed: dict)` | Mark a record as debt as historical. |
| `def` | `_split_debt_id_text(value)` | Helper for split debt id text in the application. |
| `def` | `_merge_debt_ids(*values)` | Helper for merge debt ids in the application. |
| `def` | `create_fronted_split_receivable_debts(debt_parsed: dict)` | Create a new data object for fronted split receivable debts. |
| `def` | `attach_fronted_split_debt_relations(debt_parsed: dict, debt_result: dict, split_result: dict)` | Helper for attach fronted split debt relations in the application. |
| `def` | `append_fronted_split_result_lines(lines: list[str], split_result: dict, *, indent: str='')` | Append data to fronted split result lines. |
| `def` | `build_edit_txn_preview_text_for_callback(preview: dict, split_parsed: dict \| None=None)` | Handle callback-related behavior in the application. |
| `def` | `parse_debt_ids_from_txn_record_for_edit(txn: dict)` | Parse input into structured data for debt ids from txn record for edit. |
| `def` | `overpayment_decision_keyboard()` | Helper for overpayment decision keyboard in the application. |
| `def` | `build_overpayment_decision_text(parsed: dict, outcome: dict)` | Build the data structure or message text for overpayment decision text. |
| `def` | `resolve_payment_target_type(parsed: dict, debts: list[dict])` | Resolve a user input or reference for payment target type. |
| `def` | `clear_parse_clarification_state(context: ContextTypes.DEFAULT_TYPE)` | Helper for clear parse clarification state in the application. |
| `def` | `infer_clarified_payment_target_type(raw: str)` | Helper for infer clarified payment target type in the application. |
| `def` | `build_clarified_debt_payment(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified debt payment. |
| `def` | `build_expense_candidate_raw(raw: str)` | Build the data structure or message text for expense candidate raw. |
| `def` | `build_clarified_expense(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified expense. |
| `def` | `build_clarified_fronting(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified fronting. |
| `async def` | `callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle inline button callbacks for save, edit, cancel, account choice, split bill, debt, and asset flows. |

## `app/app/bot/handler_parts/command_handlers.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `async def` | `start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for start. |
| `def` | `_format_account_name_list(accounts: list[dict])` | Format data into a readable display for account name list. |
| `def` | `_format_accounts_table_for_message(accounts: list[dict])` | Format data into a readable display for accounts table for message. |
| `def` | `_resolve_account_name_from_sheet(input_name: str, accounts: list[dict])` | Resolve a user input or reference for account name from sheet. |
| `def` | `_parse_set_balance_args(raw_arg: str)` | Parse input into structured data for set balance args. |
| `async def` | `quickstart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Send a first-use checklist that guides users through account setup, balance setup, and basic test inputs. |
| `async def` | `set_saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle /set_saldo and prepare a confirmation preview before updating an account balance. |
| `async def` | `help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for help. |
| `def` | `add_session_chat_history(context: ContextTypes.DEFAULT_TYPE, role: str, text: str, limit: int=10)` | Helper for add session chat history in the application. |
| `def` | `get_session_chat_history(context: ContextTypes.DEFAULT_TYPE, limit: int=8)` | Get data needed for session chat history. |
| `def` | `attach_session_history(context: ContextTypes.DEFAULT_TYPE, context_data: dict)` | Helper for attach session history in the application. |
| `async def` | `send_finance_insight_reply(update: Update, mode: str, context_data: dict, question: str='', prefix: str='🤖 Insight Gemini', context: ContextTypes.DEFAULT_TYPE \| None=None, remember_history: bool=False)` | Send a Telegram message for finance insight reply. |
| `async def` | `examples_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for examples. |
| `async def` | `insight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for insight. |
| `async def` | `audit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for audit. |
| `async def` | `ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for ask. |
| `async def` | `coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for coach. |
| `async def` | `handle_natural_finance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle natural finance question in the application. |
| `def` | `format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool=False)` | Format data into a readable display for report delta. |
| `def` | `append_report_comparison_lines(lines: list[str], report: dict, label: str)` | Append data to report comparison lines. |
| `def` | `get_report_expense_display(report: dict)` | Get data needed for report expense display. |
| `def` | `append_report_metric_lines(lines: list[str], report: dict)` | Append data to report metric lines. |
| `def` | `append_account_report_lines(lines: list[str], report: dict)` | Append data to account report lines. |
| `def` | `append_recent_account_transaction_lines(lines: list[str], report: dict, limit: int=8)` | Append data to recent account transaction lines. |
| `def` | `append_report_category_breakdown_lines(lines: list[str], report: dict, comparison_label: str)` | Append data to report category breakdown lines. |
| `def` | `build_top_expense_debt_lines(txn: dict, amount: float)` | Build the data structure or message text for top expense debt lines. |
| `def` | `is_category_detail_report(report: dict)` | Check whether a condition is true for category detail report. |
| `def` | `get_category_list_title(category: str)` | Get data needed for category list title. |
| `def` | `append_category_detail_summary(lines: list[str], report: dict, comparison_label: str)` | Append data to category detail summary. |
| `def` | `append_category_transaction_lines(lines: list[str], report: dict, *, include_date: bool)` | Append data to category transaction lines. |
| `async def` | `saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for saldo. |
| `async def` | `rekening_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for rekening. |
| `async def` | `harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for harian. |
| `async def` | `mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for mingguan. |
| `async def` | `bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for bulanan. |
| `async def` | `cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for cari. |
| `def` | `format_budget_net_gross(net_amount: float, gross_amount: float)` | Format data into a readable display for budget net gross. |
| `async def` | `budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for budget. |
| `async def` | `budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for budget history. |
| `def` | `build_pending_expense_lines(items: list[dict], title: str, total: float \| None=None)` | Build the data structure or message text for pending expense lines. |
| `async def` | `pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending. |
| `async def` | `pending_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending add. |
| `async def` | `pending_paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending paid. |
| `async def` | `pending_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending cancel. |
| `def` | `parse_amount_text(value: str)` | Parse input into structured data for amount text. |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Extract the required part of input for split bill total amount. |
| `async def` | `set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for set budget. |
| `def` | `short_debt_id(debt_id: str)` | Helper for short debt id in the application. |
| `def` | `parse_debt_void_args(args: list[str])` | Parse input into structured data for debt void args. |
| `def` | `build_debt_void_preview_text(preview: dict)` | Build the data structure or message text for debt void preview text. |
| `async def` | `debt_void_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt void. |
| `def` | `normalize_debt_edit_type(value: str)` | Normalize and clean input for debt edit type. |
| `def` | `parse_debt_edit_args(args: list[str])` | Parse input into structured data for debt edit args. |
| `def` | `build_debt_edit_result_text(result: dict)` | Build the data structure or message text for debt edit result text. |
| `async def` | `debt_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt edit. |
| `def` | `format_debt_created_date_for_display(debt: dict)` | Format data into a readable display for debt created date for display. |
| `def` | `debt_detail_sort_key_for_display(debt: dict)` | Helper for debt detail sort key for display in the application. |
| `def` | `parse_debt_number_selection(selection: str)` | Parse input into structured data for debt number selection. |
| `def` | `parse_debt_settle_command_args(args: list[str])` | Parse input into structured data for debt settle command args. |
| `def` | `parse_natural_debt_settle_text(text: str)` | Parse input into structured data for natural debt settle text. |
| `def` | `resolve_selected_debts_from_last_detail(context: ContextTypes.DEFAULT_TYPE, person_name: str, numbers: list[str])` | Resolve a user input or reference for selected debts from last detail. |
| `def` | `build_selected_debt_total_text(payload: dict)` | Build the data structure or message text for selected debt total text. |
| `def` | `build_selected_debt_settle_preview_text(payload: dict)` | Build the data structure or message text for selected debt settle preview text. |
| `def` | `build_selected_settle_catatan(payload: dict, result: dict)` | Build the data structure or message text for selected settle catatan. |
| `def` | `prepare_selected_debt_settle_payload(context: ContextTypes.DEFAULT_TYPE, parsed: dict)` | Helper for prepare selected debt settle payload in the application. |
| `def` | `selected_debt_settle_overpay_keyboard()` | Helper for selected debt settle overpay keyboard in the application. |
| `async def` | `debt_settle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt settle. |
| `async def` | `handle_natural_debt_settle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str)` | Helper for handle natural debt settle in the application. |
| `def` | `build_selected_debt_settle_transaction(payload: dict, result: dict)` | Build the data structure or message text for selected debt settle transaction. |
| `def` | `_collect_known_debt_person_names()` | Helper for collect known debt person names in the application. |
| `def` | `_strip_trailing_known_names_for_summary(text: str, known_names: list[str])` | Helper for strip trailing known names for summary in the application. |
| `def` | `_clean_debt_description_for_share(desc: str, person: str, known_names: list[str] \| None=None)` | Clean input values for debt description for share. |
| `def` | `_format_shareable_date_heading(date_value)` | Format data into a readable display for shareable date heading. |
| `def` | `_group_debts_for_shareable_summary(debts: list[dict], person: str, known_names: list[str])` | Helper for group debts for shareable summary in the application. |
| `def` | `build_shareable_debt_summary_text(person_query: str)` | Build the data structure or message text for shareable debt summary text. |
| `async def` | `ringkasan_hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for ringkasan hutang. |
| `async def` | `hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for hutang. |

## `app/app/bot/handler_parts/command_router.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `build_gemini_low_confidence_text(router_result: dict)` | Build the data structure or message text for gemini low confidence text. |
| `def` | `build_gemini_fallback_text()` | Build the data structure or message text for gemini fallback text. |
| `def` | `router_args_to_last_filter(args: dict)` | Helper for router args to last filter in the application. |
| `def` | `extract_edit_updates_from_router(args: dict)` | Extract the required part of input for edit updates from router. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `md_safe(value)` | Helper for md safe in the application. |
| `def` | `clean_command_token(command_text: str)` | Clean input values for command token. |
| `def` | `command_description(command_name: str)` | Helper for command description in the application. |
| `def` | `is_destructive_command(command_name: str)` | Check whether a condition is true for destructive command. |
| `def` | `similarity_score(a: str, b: str)` | Helper for similarity score in the application. |
| `def` | `get_similarity_candidates(clean_command: str)` | Get data needed for similarity candidates. |
| `def` | `resolve_command_local(command_text: str)` | Resolve a user input or reference for command local. |
| `def` | `build_command_suggestion_text(resolved: dict, original_text: str)` | Build the data structure or message text for command suggestion text. |
| `def` | `maybe_text_is_command_typo(text: str)` | Try to detect text is command typo. |
| `async def` | `unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for unknown command. |
| `def` | `short_txn_id(txn_id: str)` | Helper for short txn id in the application. |
| `def` | `expand_txn_refs(refs: list[str])` | Helper for expand txn refs in the application. |
| `def` | `resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str])` | Resolve a user input or reference for txn refs from last. |
| `def` | `build_last_transactions_text(transactions: list[dict], title: str)` | Build the data structure or message text for last transactions text. |
| `def` | `build_delete_preview_text(preview: dict)` | Build the data structure or message text for delete preview text. |
| `def` | `is_authorized(update: Update)` | Check whether a condition is true for authorized. |
| `async def` | `reject_unauthorized(update: Update)` | Helper for reject unauthorized in the application. |

## `app/app/bot/handler_parts/common_imports.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `short_debt_id(debt_id: str)` | Helper for short debt id in the application. |
| `def` | `md_safe(value)` | Helper for md safe in the application. |
| `def` | `md_code_text(value)` | Helper for md code text in the application. |
| `def` | `short_txn_id(txn_id: str)` | Helper for short txn id in the application. |
| `def` | `format_indonesian_date_group_label(date_value)` | Format data into a readable display for indonesian date group label. |
| `def` | `_safe_float_for_display(value, default: float=0.0)` | Helper for safe float for display in the application. |
| `def` | `get_transaction_receivable_parts(txn: dict)` | Get data needed for transaction receivable parts. |
| `def` | `get_transaction_payable_parts(txn: dict)` | Get data needed for transaction payable parts. |
| `def` | `get_net_expense_after_receivable(txn: dict)` | Get data needed for net expense after receivable. |
| `def` | `build_debt_parts_text(parts: list[dict])` | Build the data structure or message text for debt parts text. |
| `def` | `has_expense_transactions(transactions: list[dict] \| None)` | Check whether data has expense transactions. |
| `def` | `has_net_gross_difference(transactions: list[dict] \| None)` | Check whether data has net gross difference. |
| `def` | `append_net_gross_note(lines: list[str], transactions: list[dict] \| None=None, *, force: bool=False)` | Append data to net gross note. |
| `def` | `format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool=False)` | Format data into a readable display for expense net gross. |
| `def` | `get_transaction_account_text(txn: dict)` | Get data needed for transaction account text. |
| `def` | `build_transaction_display_lines(txn: dict, *, index: int \| None=None, include_date: bool=True, include_id: bool=False, contribution_pct: float \| None=None, note: str \| None=None)` | Build the data structure or message text for transaction display lines. |
| `def` | `build_transactions_full_text_shared(transactions: list[dict], title: str, account_filter: str \| None=None, *, current_balance: float \| None=None)` | Build the data structure or message text for transactions full text shared. |
| `def` | `is_authorized(update: Update)` | Check whether a condition is true for authorized. |
| `async def` | `reject_unauthorized(update: Update)` | Helper for reject unauthorized in the application. |
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | Helper for split long message in the application. |
| `async def` | `reply_long_markdown(update: Update, text: str)` | Send a Telegram reply for long markdown. |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram reply for message safely. |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram reply for update safely. |
| `async def` | `edit_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Edit a status message and split long follow-up text when needed. |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Helper for safe edit message in the application. |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | Handle callback-related behavior in the application. |
| `def` | `build_progress_bar(pct: float, length: int=10)` | Build the data structure or message text for progress bar. |
| `def` | `_parse_human_amount_atom(value: str \| None)` | Parse input into structured data for human amount atom. |
| `def` | `_safe_eval_amount_expression(expr: str)` | Helper for safe eval amount expression in the application. |
| `def` | `parse_human_amount(value: str \| None)` | Parse input into structured data for human amount. |
| `def` | `parse_amount_text(value: str)` | Parse input into structured data for amount text. |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Extract the required part of input for split bill total amount. |

## `app/bot/application.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `atomic_bot_handler(callback)` | Wrap a Telegram handler inside a best-effort Google Sheets transaction context. |
| `def` | `register_handlers(telegram_app: Application)` | Register all Telegram commands, message handlers, callback handlers, and error handlers. |
| `async def` | `scheduled_data_export(context)` | Helper for scheduled data export in the Telegram bot flow. |
| `def` | `register_job_queue_jobs(telegram_app: Application)` | Helper for register job queue jobs in the Telegram bot flow. |
| `def` | `build_telegram_app()` | Create one configured Telegram Application instance with handlers and scheduled jobs. |

## `app/bot/handler_parts/callback_handler.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `is_skip_account_choice(account: str)` | Check whether a condition is true for skip account choice. |
| `def` | `mark_transaction_as_historical(parsed: dict)` | Mark a record as transaction as historical. |
| `def` | `mark_debt_as_historical(debt_parsed: dict)` | Mark a record as debt as historical. |
| `def` | `_split_debt_id_text(value)` | Helper for split debt id text in the Telegram bot flow. |
| `def` | `_merge_debt_ids(*values)` | Helper for merge debt ids in the Telegram bot flow. |
| `def` | `create_fronted_split_receivable_debts(debt_parsed: dict)` | Create a new data object for fronted split receivable debts. |
| `def` | `attach_fronted_split_debt_relations(debt_parsed: dict, debt_result: dict, split_result: dict)` | Helper for attach fronted split debt relations in the Telegram bot flow. |
| `def` | `append_fronted_split_result_lines(lines: list[str], split_result: dict, *, indent: str='')` | Append data to fronted split result lines. |
| `def` | `build_edit_txn_preview_text_for_callback(preview: dict, split_parsed: dict \| None=None)` | Handle callback-related behavior in the Telegram bot flow. |
| `def` | `parse_debt_ids_from_txn_record_for_edit(txn: dict)` | Parse input into structured data for debt ids from txn record for edit. |
| `def` | `overpayment_decision_keyboard()` | Helper for overpayment decision keyboard in the Telegram bot flow. |
| `def` | `build_overpayment_decision_text(parsed: dict, outcome: dict)` | Build the data structure or message text for overpayment decision text. |
| `def` | `resolve_payment_target_type(parsed: dict, debts: list[dict])` | Resolve a user input or reference for payment target type. |
| `def` | `clear_parse_clarification_state(context: ContextTypes.DEFAULT_TYPE)` | Helper for clear parse clarification state in the Telegram bot flow. |
| `def` | `infer_clarified_payment_target_type(raw: str)` | Helper for infer clarified payment target type in the Telegram bot flow. |
| `def` | `build_clarified_debt_payment(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified debt payment. |
| `def` | `build_expense_candidate_raw(raw: str)` | Build the data structure or message text for expense candidate raw. |
| `def` | `build_clarified_expense(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified expense. |
| `def` | `build_clarified_fronting(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified fronting. |
| `async def` | `callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle inline button callbacks for save, edit, cancel, account choice, split bill, debt, and asset flows. |

## `app/bot/handler_parts/command_handlers.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `async def` | `start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for start. |
| `def` | `_format_account_name_list(accounts: list[dict])` | Format data into a readable display for account name list. |
| `def` | `_format_accounts_table_for_message(accounts: list[dict])` | Format data into a readable display for accounts table for message. |
| `def` | `_resolve_account_name_from_sheet(input_name: str, accounts: list[dict])` | Resolve a user input or reference for account name from sheet. |
| `def` | `_parse_set_balance_args(raw_arg: str)` | Parse input into structured data for set balance args. |
| `async def` | `quickstart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Send a first-use checklist that guides users through account setup, balance setup, and basic test inputs. |
| `async def` | `set_saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle /set_saldo and prepare a confirmation preview before updating an account balance. |
| `async def` | `help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for help. |
| `def` | `add_session_chat_history(context: ContextTypes.DEFAULT_TYPE, role: str, text: str, limit: int=10)` | Helper for add session chat history in the Telegram bot flow. |
| `def` | `get_session_chat_history(context: ContextTypes.DEFAULT_TYPE, limit: int=8)` | Get data needed for session chat history. |
| `def` | `attach_session_history(context: ContextTypes.DEFAULT_TYPE, context_data: dict)` | Helper for attach session history in the Telegram bot flow. |
| `async def` | `send_finance_insight_reply(update: Update, mode: str, context_data: dict, question: str='', prefix: str='🤖 Insight Gemini', context: ContextTypes.DEFAULT_TYPE \| None=None, remember_history: bool=False)` | Send a Telegram message for finance insight reply. |
| `async def` | `examples_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for examples. |
| `async def` | `insight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for insight. |
| `async def` | `audit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for audit. |
| `async def` | `ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for ask. |
| `async def` | `coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for coach. |
| `async def` | `handle_natural_finance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle natural finance question in the Telegram bot flow. |
| `def` | `format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool=False)` | Format data into a readable display for report delta. |
| `def` | `append_report_comparison_lines(lines: list[str], report: dict, label: str)` | Append data to report comparison lines. |
| `def` | `get_report_expense_display(report: dict)` | Get data needed for report expense display. |
| `def` | `append_report_metric_lines(lines: list[str], report: dict)` | Append data to report metric lines. |
| `def` | `append_account_report_lines(lines: list[str], report: dict)` | Append data to account report lines. |
| `def` | `append_recent_account_transaction_lines(lines: list[str], report: dict, limit: int=8)` | Append data to recent account transaction lines. |
| `def` | `append_report_category_breakdown_lines(lines: list[str], report: dict, comparison_label: str)` | Append data to report category breakdown lines. |
| `def` | `build_top_expense_debt_lines(txn: dict, amount: float)` | Build the data structure or message text for top expense debt lines. |
| `def` | `is_category_detail_report(report: dict)` | Check whether a condition is true for category detail report. |
| `def` | `get_category_list_title(category: str)` | Get data needed for category list title. |
| `def` | `append_category_detail_summary(lines: list[str], report: dict, comparison_label: str)` | Append data to category detail summary. |
| `def` | `append_category_transaction_lines(lines: list[str], report: dict, *, include_date: bool)` | Append data to category transaction lines. |
| `async def` | `saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for saldo. |
| `async def` | `rekening_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for rekening. |
| `async def` | `harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for harian. |
| `async def` | `mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for mingguan. |
| `async def` | `bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for bulanan. |
| `async def` | `cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for cari. |
| `def` | `format_budget_net_gross(net_amount: float, gross_amount: float)` | Format data into a readable display for budget net gross. |
| `async def` | `budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for budget. |
| `async def` | `budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for budget history. |
| `def` | `build_pending_expense_lines(items: list[dict], title: str, total: float \| None=None)` | Build the data structure or message text for pending expense lines. |
| `async def` | `pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending. |
| `async def` | `pending_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending add. |
| `async def` | `pending_paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending paid. |
| `async def` | `pending_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending cancel. |
| `def` | `parse_amount_text(value: str)` | Parse input into structured data for amount text. |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Extract the required part of input for split bill total amount. |
| `async def` | `set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for set budget. |
| `def` | `short_debt_id(debt_id: str)` | Helper for short debt id in the Telegram bot flow. |
| `def` | `parse_debt_void_args(args: list[str])` | Parse input into structured data for debt void args. |
| `def` | `build_debt_void_preview_text(preview: dict)` | Build the data structure or message text for debt void preview text. |
| `async def` | `debt_void_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt void. |
| `def` | `normalize_debt_edit_type(value: str)` | Normalize and clean input for debt edit type. |
| `def` | `parse_debt_edit_args(args: list[str])` | Parse input into structured data for debt edit args. |
| `def` | `build_debt_edit_result_text(result: dict)` | Build the data structure or message text for debt edit result text. |
| `async def` | `debt_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt edit. |
| `def` | `format_debt_created_date_for_display(debt: dict)` | Format data into a readable display for debt created date for display. |
| `def` | `debt_detail_sort_key_for_display(debt: dict)` | Helper for debt detail sort key for display in the Telegram bot flow. |
| `def` | `parse_debt_number_selection(selection: str)` | Parse input into structured data for debt number selection. |
| `def` | `parse_debt_settle_command_args(args: list[str])` | Parse input into structured data for debt settle command args. |
| `def` | `parse_natural_debt_settle_text(text: str)` | Parse input into structured data for natural debt settle text. |
| `def` | `resolve_selected_debts_from_last_detail(context: ContextTypes.DEFAULT_TYPE, person_name: str, numbers: list[str])` | Resolve a user input or reference for selected debts from last detail. |
| `def` | `build_selected_debt_total_text(payload: dict)` | Build the data structure or message text for selected debt total text. |
| `def` | `build_selected_debt_settle_preview_text(payload: dict)` | Build the data structure or message text for selected debt settle preview text. |
| `def` | `build_selected_settle_catatan(payload: dict, result: dict)` | Build the data structure or message text for selected settle catatan. |
| `def` | `prepare_selected_debt_settle_payload(context: ContextTypes.DEFAULT_TYPE, parsed: dict)` | Helper for prepare selected debt settle payload in the Telegram bot flow. |
| `def` | `selected_debt_settle_overpay_keyboard()` | Helper for selected debt settle overpay keyboard in the Telegram bot flow. |
| `async def` | `debt_settle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt settle. |
| `async def` | `handle_natural_debt_settle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str)` | Helper for handle natural debt settle in the Telegram bot flow. |
| `def` | `build_selected_debt_settle_transaction(payload: dict, result: dict)` | Build the data structure or message text for selected debt settle transaction. |
| `def` | `_collect_known_debt_person_names()` | Helper for collect known debt person names in the Telegram bot flow. |
| `def` | `_strip_trailing_known_names_for_summary(text: str, known_names: list[str])` | Helper for strip trailing known names for summary in the Telegram bot flow. |
| `def` | `_clean_debt_description_for_share(desc: str, person: str, known_names: list[str] \| None=None)` | Clean input values for debt description for share. |
| `def` | `_format_shareable_date_heading(date_value)` | Format data into a readable display for shareable date heading. |
| `def` | `_group_debts_for_shareable_summary(debts: list[dict], person: str, known_names: list[str])` | Helper for group debts for shareable summary in the Telegram bot flow. |
| `def` | `build_shareable_debt_summary_text(person_query: str)` | Build the data structure or message text for shareable debt summary text. |
| `async def` | `ringkasan_hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for ringkasan hutang. |
| `async def` | `hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for hutang. |

## `app/bot/handler_parts/command_router.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `build_gemini_low_confidence_text(router_result: dict)` | Build the data structure or message text for gemini low confidence text. |
| `def` | `build_gemini_fallback_text()` | Build the data structure or message text for gemini fallback text. |
| `def` | `router_args_to_last_filter(args: dict)` | Helper for router args to last filter in the Telegram bot flow. |
| `def` | `extract_edit_updates_from_router(args: dict)` | Extract the required part of input for edit updates from router. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `md_safe(value)` | Helper for md safe in the Telegram bot flow. |
| `def` | `clean_command_token(command_text: str)` | Clean input values for command token. |
| `def` | `command_description(command_name: str)` | Helper for command description in the Telegram bot flow. |
| `def` | `is_destructive_command(command_name: str)` | Check whether a condition is true for destructive command. |
| `def` | `similarity_score(a: str, b: str)` | Helper for similarity score in the Telegram bot flow. |
| `def` | `get_similarity_candidates(clean_command: str)` | Get data needed for similarity candidates. |
| `def` | `resolve_command_local(command_text: str)` | Resolve a user input or reference for command local. |
| `def` | `build_command_suggestion_text(resolved: dict, original_text: str)` | Build the data structure or message text for command suggestion text. |
| `def` | `maybe_text_is_command_typo(text: str)` | Try to detect text is command typo. |
| `async def` | `unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for unknown command. |
| `def` | `short_txn_id(txn_id: str)` | Helper for short txn id in the Telegram bot flow. |
| `def` | `expand_txn_refs(refs: list[str])` | Helper for expand txn refs in the Telegram bot flow. |
| `def` | `resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str])` | Resolve a user input or reference for txn refs from last. |
| `def` | `build_last_transactions_text(transactions: list[dict], title: str)` | Build the data structure or message text for last transactions text. |
| `def` | `build_delete_preview_text(preview: dict)` | Build the data structure or message text for delete preview text. |
| `def` | `is_authorized(update: Update)` | Check whether a condition is true for authorized. |
| `async def` | `reject_unauthorized(update: Update)` | Helper for reject unauthorized in the Telegram bot flow. |

## `app/bot/handler_parts/common_imports.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `short_debt_id(debt_id: str)` | Helper for short debt id in the Telegram bot flow. |
| `def` | `md_safe(value)` | Helper for md safe in the Telegram bot flow. |
| `def` | `md_code_text(value)` | Helper for md code text in the Telegram bot flow. |
| `def` | `short_txn_id(txn_id: str)` | Helper for short txn id in the Telegram bot flow. |
| `def` | `format_indonesian_date_group_label(date_value)` | Format data into a readable display for indonesian date group label. |
| `def` | `_safe_float_for_display(value, default: float=0.0)` | Helper for safe float for display in the Telegram bot flow. |
| `def` | `get_transaction_receivable_parts(txn: dict)` | Get data needed for transaction receivable parts. |
| `def` | `get_transaction_payable_parts(txn: dict)` | Get data needed for transaction payable parts. |
| `def` | `get_net_expense_after_receivable(txn: dict)` | Get data needed for net expense after receivable. |
| `def` | `build_debt_parts_text(parts: list[dict])` | Build the data structure or message text for debt parts text. |
| `def` | `has_expense_transactions(transactions: list[dict] \| None)` | Check whether data has expense transactions. |
| `def` | `has_net_gross_difference(transactions: list[dict] \| None)` | Check whether data has net gross difference. |
| `def` | `append_net_gross_note(lines: list[str], transactions: list[dict] \| None=None, *, force: bool=False)` | Append data to net gross note. |
| `def` | `format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool=False)` | Format data into a readable display for expense net gross. |
| `def` | `get_transaction_account_text(txn: dict)` | Get data needed for transaction account text. |
| `def` | `build_transaction_display_lines(txn: dict, *, index: int \| None=None, include_date: bool=True, include_id: bool=False, contribution_pct: float \| None=None, note: str \| None=None)` | Build the data structure or message text for transaction display lines. |
| `def` | `build_transactions_full_text_shared(transactions: list[dict], title: str, account_filter: str \| None=None, *, current_balance: float \| None=None)` | Build the data structure or message text for transactions full text shared. |
| `def` | `is_authorized(update: Update)` | Check whether a condition is true for authorized. |
| `async def` | `reject_unauthorized(update: Update)` | Helper for reject unauthorized in the Telegram bot flow. |
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | Helper for split long message in the Telegram bot flow. |
| `async def` | `reply_long_markdown(update: Update, text: str)` | Send a Telegram reply for long markdown. |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram reply for message safely. |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram reply for update safely. |
| `async def` | `edit_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Edit a status message and split long follow-up text when needed. |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Helper for safe edit message in the Telegram bot flow. |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | Handle callback-related behavior in the Telegram bot flow. |
| `def` | `build_progress_bar(pct: float, length: int=10)` | Build the data structure or message text for progress bar. |
| `def` | `_parse_human_amount_atom(value: str \| None)` | Parse input into structured data for human amount atom. |
| `def` | `_safe_eval_amount_expression(expr: str)` | Helper for safe eval amount expression in the Telegram bot flow. |
| `def` | `parse_human_amount(value: str \| None)` | Parse input into structured data for human amount. |
| `def` | `parse_amount_text(value: str)` | Parse input into structured data for amount text. |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Extract the required part of input for split bill total amount. |

## `app/bot/handler_parts/core.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | Helper for split long message in the Telegram bot flow. |
| `async def` | `reply_long_markdown(update: Update, text: str)` | Send a Telegram reply for long markdown. |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram reply for message safely. |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram reply for update safely. |
| `async def` | `edit_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Edit a status message and split long follow-up text when needed. |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Helper for safe edit message in the Telegram bot flow. |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | Handle callback-related behavior in the Telegram bot flow. |
| `async def` | `error_handler(update: object, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for error. |

## `app/bot/handler_parts/health_recurring_export.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `health_status_icon(ok: bool)` | Helper for health status icon in the Telegram bot flow. |
| `def` | `health_warn_icon(ok: bool)` | Helper for health warn icon in the Telegram bot flow. |
| `def` | `safe_health_check(label: str, check_func)` | Helper for safe health check in the Telegram bot flow. |
| `def` | `check_google_sheets_connection()` | Helper for check google sheets connection in the Telegram bot flow. |
| `def` | `check_sheet_readable(sheet_name: str)` | Helper for check sheet readable in the Telegram bot flow. |
| `def` | `check_wispybite()` | Helper for check wispybite in the Telegram bot flow. |
| `def` | `check_wispybite_port()` | Helper for check wispybite port in the Telegram bot flow. |
| `def` | `check_gemini_config()` | Helper for check gemini config in the Telegram bot flow. |
| `def` | `check_environment_config()` | Helper for check environment config in the Telegram bot flow. |
| `def` | `build_health_report_text(results: list[dict])` | Build the data structure or message text for health report text. |
| `async def` | `health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for health. |
| `def` | `parse_recurring_add_args(args: list[str])` | Parse input into structured data for recurring add args. |
| `def` | `parse_recurring_edit_args(args: list[str])` | Parse input into structured data for recurring edit args. |
| `def` | `build_recurring_edit_result_text(result: dict)` | Build the data structure or message text for recurring edit result text. |
| `async def` | `recurring_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for recurring edit. |
| `def` | `short_rule_id(rule_id: str)` | Helper for short rule id in the Telegram bot flow. |
| `def` | `build_recurring_rules_text(rules: list[dict])` | Build the data structure or message text for recurring rules text. |
| `def` | `build_recurring_run_text(result: dict)` | Build the data structure or message text for recurring run text. |
| `async def` | `recurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for recurring. |
| `async def` | `recurring_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for recurring add. |
| `async def` | `recurring_run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for recurring run. |
| `async def` | `recurring_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for recurring off. |
| `def` | `write_transactions_to_csv(records: list[dict], file_path: str)` | Helper for write transactions to csv in the Telegram bot flow. |
| `def` | `build_export_caption(export_result: dict)` | Build the data structure or message text for export caption. |
| `async def` | `export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for export. |
| `async def` | `scheduled_export_transactions(bot, chat_id: int, period=None)` | Helper for scheduled export transactions in the Telegram bot flow. |

## `app/bot/handler_parts/message_handlers.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `async def` | `send_parse_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str, parsed: dict \| None, assessment: dict)` | Send a Telegram message for parse clarification. |
| `def` | `try_gemini_draft_for_parse_safety(raw: str, fallback_parsed: dict, assessment: dict)` | Helper for try gemini draft for parse safety in the Telegram bot flow. |
| `async def` | `debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt message. |
| `async def` | `handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle gemini intent in the Telegram bot flow. |
| `def` | `normalize_text_command(text: str)` | Normalize and clean input for text command. |
| `async def` | `handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle local natural intent in the Telegram bot flow. |
| `async def` | `handle_pending_receipt_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Handle text replies for partial receipt item selection and extra-charge divisor. |
| `async def` | `_continue_receipt_batch_after_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict], receipt_context: dict)` | Continue a receipt-derived batch after item selection is complete. |
| `async def` | `image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle image input, including itemized receipt review before saving. |
| `async def` | `message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Route natural text input into pending edits, asset flow, debt flow, parser flow, parse safety, or AI fallback. |
| `def` | `build_transactions_full_text(transactions: list[dict], title: str, account_filter: str \| None=None)` | Build the data structure or message text for transactions full text. |
| `def` | `build_transaction_filter_title(base_title: str, category_filter: str \| None=None, account_filter: str \| None=None)` | Build the data structure or message text for transaction filter title. |
| `def` | `_build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str)` | Build the data structure or message text for transaksi prefixed period arg. |
| `def` | `parse_transaksi_period(args: list[str])` | Parse input into structured data for transaksi period. |
| `async def` | `transaksi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for transaksi. |
| `async def` | `last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for last. |
| `async def` | `delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for delete txn. |
| `def` | `parse_edit_updates(args: list[str])` | Parse input into structured data for edit updates. |
| `def` | `edit_args_contain_split_bill(args: list[str])` | Helper for edit args contain split bill in the Telegram bot flow. |
| `def` | `_normalize_edit_arg_token(token: str)` | Normalize and clean input for edit arg token. |
| `def` | `parse_edit_debt_payment_conversion_args(args: list[str])` | Parse input into structured data for edit debt payment conversion args. |
| `def` | `build_debt_payment_conversion_updates(conversion: dict, old_txn: dict \| None=None)` | Build the data structure or message text for debt payment conversion updates. |
| `def` | `validate_edit_debt_payment_conversion(conversion: dict, amount: float)` | Validate data before it is used by edit debt payment conversion. |
| `def` | `build_edit_debt_payment_preview_text(preview: dict, conversion: dict, debt_check: dict)` | Build the data structure or message text for edit debt payment preview text. |
| `def` | `build_edit_split_preview_text(preview: dict, split_parsed: dict \| None=None)` | Build the data structure or message text for edit split preview text. |
| `def` | `build_edit_preview_text(preview: dict)` | Build the data structure or message text for edit preview text. |
| `def` | `extract_bulk_edit_txn_lines(raw_text: str)` | Extract the required part of input for bulk edit txn lines. |
| `def` | `_format_bulk_edit_value(value)` | Format data into a readable display for bulk edit value. |
| `def` | `build_bulk_edit_preview_text(entries: list[dict])` | Build the data structure or message text for bulk edit preview text. |
| `def` | `build_bulk_edit_error_text(errors: list[str])` | Build the data structure or message text for bulk edit error text. |
| `def` | `parse_bulk_edit_txn_entries(lines: list[str], context: ContextTypes.DEFAULT_TYPE)` | Parse input into structured data for bulk edit txn entries. |
| `async def` | `bulk_edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str])` | Handle the Telegram request for bulk edit txn. |
| `async def` | `edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for edit txn. |

## `app/bot/handler_parts/networth_assets.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `parse_asset_quantity_input(value: str)` | Parse input into structured data for asset quantity input. |
| `def` | `_parse_human_amount_atom(value: str \| None)` | Parse input into structured data for human amount atom. |
| `def` | `_safe_eval_amount_expression(expr: str)` | Helper for safe eval amount expression in the Telegram bot flow. |
| `def` | `parse_human_amount(value: str \| None)` | Parse input into structured data for human amount. |
| `def` | `parse_asset_extra_fields(extra_parts: list[str])` | Parse input into structured data for asset extra fields. |
| `def` | `format_asset_gain_lines(asset: dict, indent: str='   ')` | Format data into a readable display for asset gain lines. |
| `def` | `guess_asset_category_and_name(name: str, category: str \| None=None)` | Helper for guess asset category and name in the Telegram bot flow. |
| `def` | `build_asset_unit_price_prompt(data: dict)` | Build the data structure or message text for asset unit price prompt. |
| `def` | `parse_pipe_add_args(args: list[str], item_type: str)` | Parse input into structured data for pipe add args. |
| `def` | `parse_natural_asset_add(text: str)` | Parse input into structured data for natural asset add. |
| `def` | `parse_pipe_update_args(args: list[str], command_name: str)` | Parse input into structured data for pipe update args. |
| `def` | `short_networth_id(record_id: str)` | Helper for short networth id in the Telegram bot flow. |
| `def` | `build_networth_text(summary: dict)` | Build the data structure or message text for networth text. |
| `def` | `build_assets_text(assets: list[dict])` | Build the data structure or message text for assets text. |
| `def` | `build_liabilities_text(liabilities: list[dict])` | Build the data structure or message text for liabilities text. |
| `def` | `build_update_result_text(result: dict, label: str)` | Build the data structure or message text for update result text. |
| `def` | `build_snapshots_text(snapshots: list[dict])` | Build the data structure or message text for snapshots text. |
| `async def` | `networth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for networth. |
| `async def` | `assets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for assets. |
| `async def` | `liabilities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for liabilities. |
| `def` | `build_asset_added_text(asset: dict)` | Build the data structure or message text for asset added text. |
| `def` | `asset_edit_or_continue_keyboard()` | Helper for asset edit or continue keyboard in the Telegram bot flow. |
| `def` | `build_asset_confirm_preview(data: dict)` | Build the data structure or message text for asset confirm preview. |
| `def` | `_asset_flow_is_skip(text: str)` | Helper for asset flow is skip in the Telegram bot flow. |
| `def` | `_asset_flow_is_cancel(text: str)` | Helper for asset flow is cancel in the Telegram bot flow. |
| `def` | `_asset_flow_prompt(step: str, data: dict \| None=None)` | Helper for asset flow prompt in the Telegram bot flow. |
| `def` | `start_asset_add_flow(context: ContextTypes.DEFAULT_TYPE)` | Helper for start asset add flow in the Telegram bot flow. |
| `def` | `_build_asset_data_from_flow(data: dict)` | Build the data structure or message text for asset data from flow. |
| `async def` | `handle_pending_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle pending asset add flow in the Telegram bot flow. |
| `async def` | `asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for asset add. |
| `async def` | `liability_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for liability add. |
| `async def` | `asset_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for asset update. |
| `async def` | `liability_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for liability update. |
| `async def` | `asset_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for asset off. |
| `async def` | `liability_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for liability off. |
| `async def` | `networth_snapshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for networth snapshot. |
| `async def` | `networth_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for networth history. |

## `app/bot/handler_parts/transaction_flow.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `parse_input(text: str)` | Parse input into structured data for input. |
| `def` | `build_progress_bar(pct: float, length: int=10)` | Build the data structure or message text for progress bar. |
| `def` | `split_user_inputs(text: str)` | Helper for split user inputs in the Telegram bot flow. |
| `def` | `needs_account(parsed: dict)` | Helper for needs account in the Telegram bot flow. |
| `def` | `is_debt_item(parsed: dict)` | Check whether a condition is true for debt item. |
| `def` | `is_transaction_item(parsed: dict)` | Check whether a condition is true for transaction item. |
| `def` | `build_mixed_preview(mixed_items: list[dict])` | Build the data structure or message text for mixed preview. |
| `def` | `parse_income_missing_amount(line: str)` | Parse input into structured data for income missing amount. |
| `def` | `build_missing_amount_prompt(raw: str, parsed: dict, current: int \| None=None, total: int \| None=None)` | Build the data structure or message text for missing amount prompt. |
| `def` | `finalize_missing_amount_item(item: dict, amount: float)` | Helper for finalize missing amount item in the Telegram bot flow. |
| `async def` | `continue_after_missing_amount_mixed(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict])` | Helper for continue after missing amount mixed in the Telegram bot flow. |
| `async def` | `handle_pending_missing_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle pending missing amount in the Telegram bot flow. |
| `def` | `parse_mixed_item(line: str)` | Parse input into structured data for mixed item. |
| `def` | `mixed_needs_account(mixed_items: list[dict])` | Helper for mixed needs account in the Telegram bot flow. |
| `def` | `edit_or_continue_keyboard(scope: str)` | Helper for edit or continue keyboard in the Telegram bot flow. |
| `def` | `_confirm_target_for_edit_scope(scope: str)` | Helper for confirm target for edit scope in the Telegram bot flow. |
| `def` | `save_edit_cancel_keyboard(scope: str)` | Save data after validation and confirmation for edit cancel keyboard. |
| `def` | `preview_action_keyboard(scope: str, ready_to_save: bool)` | Helper for preview action keyboard in the Telegram bot flow. |
| `def` | `preview_action_question(ready_to_save: bool)` | Helper for preview action question in the Telegram bot flow. |
| `def` | `single_ready_to_save(parsed: dict)` | Helper for single ready to save in the Telegram bot flow. |
| `def` | `mixed_ready_to_save(mixed_items: list[dict])` | Helper for mixed ready to save in the Telegram bot flow. |
| `def` | `debt_ready_to_save(debt_parsed: dict)` | Helper for debt ready to save in the Telegram bot flow. |
| `def` | `build_parse_safety_notice(assessment: dict, mode: str='warning')` | Build the data structure or message text for parse safety notice. |
| `def` | `build_preview_with_parse_safety(parsed: dict, assessment: dict, mode: str='warning')` | Build the data structure or message text for preview with parse safety. |
| `def` | `build_pending_expense_confirm_preview(item: dict, include_question: bool=True)` | Build the data structure or message text for pending expense confirm preview. |
| `def` | `parse_clarification_keyboard()` | Parse input into structured data for clarification keyboard. |
| `def` | `build_parse_clarification_prompt(raw: str, assessment: dict \| None=None)` | Build the data structure or message text for parse clarification prompt. |
| `def` | `parse_participant_count(value: str)` | Parse input into structured data for participant count. |
| `def` | `build_account_delta_summary_from_transaction_items(items: list[dict])` | Build the data structure or message text for account delta summary from transaction items. |
| `def` | `build_mixed_detail_preview(mixed_items: list[dict], receipt_context: dict \| None=None)` | Build the detailed multi-input preview before the account step. |
| `def` | `build_mixed_final_summary(mixed_items: list[dict], receipt_context: dict \| None=None, account_label: str \| None=None)` | Build the compact final summary for mixed and receipt batches. |
| `def` | `build_mixed_category_summary(mixed_items: list[dict])` | Build compact category totals for the final mixed preview. |
| `def` | `build_mixed_short_summary(mixed_items: list[dict])` | Build the data structure or message text for mixed short summary. |
| `def` | `build_single_short_summary(parsed: dict)` | Build the data structure or message text for single short summary. |
| `def` | `build_updated_item_summary(item: dict, index: int \| None=None)` | Build the data structure or message text for updated item summary. |
| `def` | `_preview_edit_fields_for_scope(scope: str)` | Helper for preview edit fields for scope in the Telegram bot flow. |
| `def` | `build_preview_edit_keyboard(scope: str='single')` | Build the data structure or message text for preview edit keyboard. |
| `def` | `build_preview_field_help(scope: str, field: str)` | Build the data structure or message text for preview field help. |
| `def` | `build_preview_field_value_prompt(scope: str, field: str)` | Ask for a raw replacement value after the user taps one edit field. |
| `def` | `parse_preview_direct_field_update(field: str, value: str)` | Parse a raw replacement value for one selected edit field. |
| `def` | `build_preview_edit_help(scope: str='single')` | Build the data structure or message text for preview edit help. |
| `def` | `build_mixed_edit_choose_prompt(mixed_items: list[dict])` | Build the data structure or message text for mixed edit choose prompt. |
| `def` | `_split_preview_edit_segments(raw: str)` | Helper for split preview edit segments in the Telegram bot flow. |
| `def` | `_strip_preview_edit_value(value: str)` | Helper for strip preview edit value in the Telegram bot flow. |
| `def` | `_parse_preview_edit_pair(segment: str)` | Parse input into structured data for preview edit pair. |
| `def` | `parse_preview_edit_updates(text: str)` | Parse input into structured data for preview edit updates. |
| `def` | `apply_preview_edit_updates_to_parsed(parsed: dict, updates: dict)` | Apply changes for preview edit updates to parsed. |
| `async def` | `proceed_after_preview_edit(query, context: ContextTypes.DEFAULT_TYPE, scope: str)` | Helper for proceed after preview edit in the Telegram bot flow. |
| `async def` | `handle_pending_preview_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle pending preview edit in the Telegram bot flow. |
| `def` | `format_split_bill_preview_line(parsed: dict)` | Format data into a readable display for split bill preview line. |
| `def` | `build_preview(parsed: dict)` | Build the data structure or message text for preview. |
| `def` | `build_batch_preview(parsed_items: list[dict])` | Build the data structure or message text for batch preview. |
| `def` | `is_receipt_image_result(result: dict, items: list[dict])` | Decide whether image output should enter the receipt review flow. |
| `def` | `build_receipt_review_text(receipt: dict, items: list[dict])` | Build the OCR detail review for itemized receipts. |
| `def` | `build_receipt_part_selection_prompt(receipt: dict, items: list[dict])` | Build instructions for selecting only part of a receipt. |
| `def` | `parse_receipt_part_selection(user_text: str, items: list[dict])` | Parse selected receipt rows such as `4 beli 1` or `5 beli 1 dibagi 2`. |
| `def` | `build_receipt_selected_breakdown(receipt: dict, selection_result: dict)` | Show selected receipt item calculations before splitting extra charges. |
| `def` | `parse_receipt_divisor(user_text: str)` | Parse how many people split receipt service, PPN, or other extra charges. |
| `def` | `build_receipt_all_mixed_items(receipt: dict, items: list[dict])` | Convert all receipt rows into mixed batch transaction items. |
| `def` | `build_receipt_partial_mixed_items(receipt: dict, selection_result: dict, divisor: int)` | Convert selected receipt rows into mixed batch transaction items. |
| `def` | `build_receipt_account_prompt(mixed_items: list[dict], receipt_context: dict)` | Build the account prompt after receipt rows are converted into a batch. |
| `def` | `build_receipt_final_preview(mixed_items: list[dict], receipt_context: dict, account_label: str \| None=None)` | Build the final receipt batch preview before saving. |
| `def` | `strip_split_bill_phrase(text: str)` | Helper for strip split bill phrase in the Telegram bot flow. |
| `def` | `strip_trailing_split_person_names(text: str, person_names: list[str])` | Helper for strip trailing split person names in the Telegram bot flow. |
| `def` | `strip_split_bill_account_tail(name_text: str)` | Helper for strip split bill account tail in the Telegram bot flow. |
| `def` | `limit_split_bill_friends_to_participants(person_names: list[str], person_shares: dict, participants: int, base_share_amount: float)` | Helper for limit split bill friends to participants in the Telegram bot flow. |
| `def` | `split_split_bill_person_names(name_text: str)` | Helper for split split bill person names in the Telegram bot flow. |
| `def` | `strip_split_bill_name_tail(name_text: str)` | Helper for strip split bill name tail in the Telegram bot flow. |
| `def` | `is_split_bill_allocation_token(value: str)` | Check whether a condition is true for split bill allocation token. |
| `def` | `parse_split_bill_share_value(value: str, base_share: float)` | Parse input into structured data for split bill share value. |
| `def` | `parse_split_bill_people_and_shares(name_text: str, total_amount: float, participants: int)` | Parse input into structured data for split bill people and shares. |
| `def` | `format_split_bill_person_shares(split_bill: dict)` | Format data into a readable display for split bill person shares. |
| `def` | `clean_split_person_name(name: str)` | Clean input values for split person name. |
| `def` | `build_split_bill_item_description_from_raw(raw: str, fallback: str='')` | Build the data structure or message text for split bill item description from raw. |
| `def` | `detect_split_bill(parsed: dict, raw: str)` | Helper for detect split bill in the Telegram bot flow. |
| `def` | `attach_split_bill_if_any(parsed: dict, raw: str)` | Helper for attach split bill if any in the Telegram bot flow. |
| `def` | `split_bill_needs_decision(parsed: dict)` | Helper for split bill needs decision in the Telegram bot flow. |
| `def` | `mixed_split_bill_needs_decision(mixed_items: list[dict])` | Helper for mixed split bill needs decision in the Telegram bot flow. |
| `def` | `split_bill_keyboard(scope: str='single', item_index: int \| None=None)` | Helper for split bill keyboard in the Telegram bot flow. |
| `def` | `mixed_split_bill_keyboard(mixed_items: list[dict])` | Helper for mixed split bill keyboard in the Telegram bot flow. |
| `def` | `build_split_bill_prompt_from_parsed(parsed: dict)` | Build the data structure or message text for split bill prompt from parsed. |
| `def` | `build_mixed_split_bill_prompt(mixed_items: list[dict])` | Build the data structure or message text for mixed split bill prompt. |
| `def` | `get_mixed_split_bill_indexes(mixed_items: list[dict])` | Get data needed for mixed split bill indexes. |
| `def` | `get_next_mixed_split_bill_index(mixed_items: list[dict])` | Get data needed for next mixed split bill index. |
| `def` | `build_mixed_split_bill_queue_prompt(mixed_items: list[dict])` | Build the data structure or message text for mixed split bill queue prompt. |
| `def` | `apply_split_bill_decision_to_current_mixed(mixed_items: list[dict], status: str)` | Apply changes for split bill decision to current mixed. |
| `def` | `apply_split_bill_decision_to_mixed_index(mixed_items: list[dict], item_index: int, status: str)` | Apply changes for split bill decision to mixed index. |
| `def` | `apply_split_bill_decision_to_parsed(parsed: dict, status: str)` | Apply changes for split bill decision to parsed. |
| `def` | `apply_split_bill_decision_to_mixed(mixed_items: list[dict], status: str)` | Apply changes for split bill decision to mixed. |
| `def` | `create_split_bill_debt(parsed: dict, raw: str='', source_transaction_id: str='')` | Create a new data object for split bill debt. |
| `def` | `format_split_debt_result_lines(debt_result: dict)` | Format data into a readable display for split debt result lines. |
| `def` | `summarize_saved_transaction_items(items: list[dict])` | Summarize data for saved transaction items. |
| `def` | `append_saved_summary_lines(lines: list[str], items: list[dict], title: str='Ringkasan tersimpan')` | Append data to saved summary lines. |
| `def` | `_clean_fronting_item_text(text: str, person: str='')` | Clean input values for fronting item text. |
| `def` | `_fronting_expense_description(debt_parsed: dict)` | Helper for fronting expense description in the Telegram bot flow. |
| `def` | `_fronting_expense_category(debt_parsed: dict)` | Helper for fronting expense category in the Telegram bot flow. |
| `def` | `is_ditalangin_expense_without_balance(debt_parsed: dict)` | Check whether a condition is true for ditalangin expense without balance. |
| `def` | `normalize_slash_split_syntax(raw: str)` | Normalize and clean input for slash split syntax. |
| `def` | `enrich_ditalangin_split_bill_if_any(debt_parsed: dict, raw: str \| None=None)` | Helper for enrich ditalangin split bill if any in the Telegram bot flow. |
| `def` | `_debt_payment_catatan(debt_parsed: dict, raw: str)` | Helper for debt payment catatan in the Telegram bot flow. |
| `def` | `build_debt_cashflow_transaction(debt_parsed: dict, account: str, debt_type_for_payment: str \| None=None)` | Build the data structure or message text for debt cashflow transaction. |
| `def` | `debt_uses_cashflow(debt_parsed: dict)` | Helper for debt uses cashflow in the Telegram bot flow. |
| `def` | `build_debt_only_confirm_preview(debt_parsed: dict)` | Build the data structure or message text for debt only confirm preview. |
| `def` | `build_debt_initial_preview(debt_parsed: dict)` | Build the data structure or message text for debt initial preview. |
| `def` | `build_debt_short_summary(debt_parsed: dict)` | Build the data structure or message text for debt short summary. |
| `def` | `build_debt_account_prompt(debt_parsed: dict)` | Build the data structure or message text for debt account prompt. |
| `def` | `build_debt_confirm_preview(debt_parsed: dict, account: str, debt_type_for_payment: str \| None=None)` | Build the data structure or message text for debt confirm preview. |
| `def` | `build_debt_batch_confirm_preview(debt_items: list[dict], account: str)` | Build the data structure or message text for debt batch confirm preview. |
| `def` | `build_debt_batch_account_prompt(debt_items: list[dict])` | Build the data structure or message text for debt batch account prompt. |

## `app/bot/keyboards.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `account_keyboard(prefix: str='acc', include_skip: bool=True)` | Helper for account keyboard in the Telegram bot flow. |
| `def` | `confirm_keyboard(txn_id: str)` | Helper for confirm keyboard in the Telegram bot flow. |
| `def` | `cancel_keyboard()` | Helper for cancel keyboard in the Telegram bot flow. |
| `def` | `receipt_ownership_keyboard()` | Build the initial all-items, partial-items, or cancel keyboard for receipt images. |

## `app/config.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_parse_int_env(name: str, default: int \| None=None)` | Parse input into structured data for int env. |

## `app/nlp/gemini_finance_insight.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_json_dumps(data: dict)` | Helper for json dumps in the NLP and parser layer. |
| `def` | `build_finance_insight_prompt(mode: str, context: dict, question: str='')` | Build the data structure or message text for finance insight prompt. |
| `def` | `generate_finance_insight(mode: str, context: dict, question: str='')` | Helper for generate finance insight in the NLP and parser layer. |

## `app/nlp/gemini_image_parser.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `clean_gemini_json(raw_text: str)` | Clean input values for gemini json. |
| `def` | `build_image_prompt(caption: str='')` | Build the data structure or message text for image prompt. |
| `def` | `safe_number(value, default: float=0.0)` | Convert Gemini numeric fields into floats safely. |
| `def` | `normalize_receipt(data: dict, items: list[dict])` | Normalize receipt-level metadata such as merchant, total, service, PPN, and discount. |
| `def` | `normalize_item(item: dict)` | Normalize item rows from an image, including quantity and unit price when available. |
| `def` | `parse_transactions_from_image(image_bytes: bytes, mime_type: str='image/jpeg', caption: str='')` | Parse image input into transactions plus optional receipt metadata. |

## `app/nlp/gemini_intent_router.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `should_try_gemini_intent_router(text: str)` | Decide whether the flow should try gemini intent router. |
| `def` | `extract_json_object(text: str)` | Extract the required part of input for json object. |
| `def` | `normalize_router_result(data: dict)` | Normalize and clean input for router result. |
| `def` | `route_intent_with_gemini(user_text: str)` | Helper for route intent with gemini in the NLP and parser layer. |

## `app/nlp/gemini_langchain_client.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_require_api_key()` | Helper for require api key in the NLP and parser layer. |
| `def` | `get_gemini_llm(model_name: str, temperature: float=0.0)` | Get data needed for gemini llm. |
| `def` | `_extract_text(response: Any)` | Extract the required part of input for text. |
| `def` | `generate_text_with_gemini(prompt: str, *, model_name: str \| None=None, temperature: float=0.0)` | Helper for generate text with gemini in the NLP and parser layer. |
| `def` | `_make_data_url(image_bytes: bytes, mime_type: str)` | Helper for make data url in the NLP and parser layer. |
| `def` | `generate_text_from_image_with_gemini(prompt: str, image_bytes: bytes, *, mime_type: str='image/jpeg', model_name: str \| None=None, temperature: float=0.0)` | Helper for generate text from image with gemini in the NLP and parser layer. |

## `app/nlp/gemini_parser.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `build_prompt(user_input: str)` | Build the data structure or message text for prompt. |
| `def` | `clean_gemini_json(raw_text: str)` | Clean input values for gemini json. |
| `def` | `parse_with_gemini(user_input: str)` | Parse input into structured data for with gemini. |
| `def` | `parse_with_pending_fallback(user_input: str)` | Parse input into structured data for with pending fallback. |

## `app/nlp/normalizer.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `normalize_amount(text: str)` | Normalize and clean input for amount. |
| `def` | `normalize_text(text: str)` | Normalize and clean input for text. |
| `def` | `parse_amount_value(number_str: str, unit: str='')` | Parse input into structured data for amount value. |
| `def` | `extract_amount_from_text(text: str)` | Extract the required part of input for amount from text. |
| `def` | `apply_split_operation(text: str, base_amount: int)` | Apply changes for split operation. |

## `app/nlp/parse_safety.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_has_amount(clean: str)` | Check whether data has amount. |
| `def` | `_has_debt_keyword(clean: str)` | Check whether data has debt keyword. |
| `def` | `_has_account(clean: str)` | Check whether data has account. |
| `def` | `_first_token(value: str)` | Helper for first token in the NLP and parser layer. |
| `def` | `_looks_like_person(value: str)` | Helper for looks like person in the NLP and parser layer. |
| `def` | `_append_unique(items: list[str], value: str)` | Append data to unique. |
| `def` | `_add_reason(reasons: list[str], reason: str)` | Helper for add reason in the NLP and parser layer. |
| `def` | `extract_person_candidate(text: str)` | Extract the required part of input for person candidate. |
| `def` | `detect_pre_parse_clarification_flags(text: str)` | Helper for detect pre parse clarification flags in the NLP and parser layer. |
| `def` | `detect_post_parse_flags(text: str, parsed: dict[str, Any] \| None)` | Helper for detect post parse flags in the NLP and parser layer. |
| `def` | `assess_parse_safety(text: str, parsed: dict \| None)` | Helper for assess parse safety in the NLP and parser layer. |

## `app/nlp/regex_parser.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `display_account_name(account: str)` | Helper for display account name in the NLP and parser layer. |
| `def` | `parse_debt_input(text: str)` | Parse input into structured data for debt input. |
| `def` | `detect_type(text: str)` | Helper for detect type in the NLP and parser layer. |
| `def` | `detect_category(text: str, transaction_type: str)` | Helper for detect category in the NLP and parser layer. |
| `def` | `detect_account(text: str)` | Helper for detect account in the NLP and parser layer. |
| `def` | `detect_transfer_accounts(text: str)` | Helper for detect transfer accounts in the NLP and parser layer. |
| `def` | `parse_explicit_date(date_text: str)` | Parse input into structured data for explicit date. |
| `def` | `parse_day_only_date(day_text: str)` | Parse input into structured data for day only date. |
| `def` | `strip_date_phrases(text: str)` | Helper for strip date phrases in the NLP and parser layer. |
| `def` | `parse_relative_number(value: str)` | Parse input into structured data for relative number. |
| `def` | `detect_relative_date(text: str)` | Helper for detect relative date in the NLP and parser layer. |
| `def` | `detect_date(text: str)` | Helper for detect date in the NLP and parser layer. |
| `def` | `extract_description(text: str, amount=None)` | Extract the required part of input for description. |
| `def` | `detect_subject(text: str, transaction_type: str, category: str, description: str)` | Helper for detect subject in the NLP and parser layer. |
| `def` | `extract_note(text: str)` | Extract the required part of input for note. |
| `def` | `detect_spending_type(text: str, category: str, transaction_type: str)` | Helper for detect spending type in the NLP and parser layer. |
| `def` | `parse_with_regex(text: str)` | Parse input into structured data for with regex. |

## `app/scheduler/jobs.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `async def` | `job_recurring_run()` | Helper for job recurring run in the scheduler layer. |
| `async def` | `send_message(text: str, parse_mode: str \| None='Markdown', reply_markup=None)` | Send a Telegram message for message. |
| `async def` | `job_daily_summary()` | Helper for job daily summary in the scheduler layer. |
| `async def` | `job_weekly_summary()` | Helper for job weekly summary in the scheduler layer. |
| `async def` | `job_monthly_summary()` | Helper for job monthly summary in the scheduler layer. |
| `async def` | `job_debt_reminder()` | Helper for job debt reminder in the scheduler layer. |
| `def` | `create_scheduler()` | Create a new data object for scheduler. |

## `app/scripts/ai_command_tester.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_ensure_test_env()` | Ensure that setup is ready for test env. |
| `class` | `_Dummy` | Class used by Dummy in the developer utility script. |
| `class` | `_DummyBadRequest` | Class used by DummyBadRequest in the developer utility script. |
| `def` | `_module_exists(module_name: str)` | Helper for module exists in the developer utility script. |
| `def` | `_install_optional_import_stubs()` | Helper for install optional import stubs in the developer utility script. |
| `class` | `AssertionResult` | Result model for one assertion inside a command test case. |
| `class` | `CommandRun` | Result model for one simulated command or user input run. |
| `def` | `classify_known_route(text: str)` | Helper for classify known route in the developer utility script. |
| `class` | `CommandTester` | Command test runner that loads cases, simulates bot behavior, and produces regression reports. |
| `def` | `get_path(data: Any, path: str)` | Get data needed for path. |
| `def` | `compare_value(actual: Any, expected: Any)` | Helper for compare value in the developer utility script. |
| `def` | `evaluate_expectations(run: CommandRun, expect: dict[str, Any] \| None)` | Helper for evaluate expectations in the developer utility script. |
| `def` | `_has_split_keyword(text: str)` | Check whether data has split keyword. |
| `def` | `_split_has_friend_name(text: str)` | Helper for split has friend name in the developer utility script. |
| `def` | `evaluate_heuristics(run: CommandRun)` | Helper for evaluate heuristics in the developer utility script. |
| `def` | `case_status(assertions: list[AssertionResult])` | Helper for case status in the developer utility script. |
| `def` | `deterministic_diagnosis(run: CommandRun, assertions: list[AssertionResult])` | Helper for deterministic diagnosis in the developer utility script. |
| `def` | `ai_diagnosis(run: CommandRun, assertions: list[AssertionResult])` | Helper for ai diagnosis in the developer utility script. |
| `def` | `command_run_to_dict(run: CommandRun)` | Helper for command run to dict in the developer utility script. |
| `def` | `resolve_input_path(path_text: str)` | Resolve a user input or reference for input path. |
| `def` | `load_cases(path: Path)` | Load data for cases. |
| `def` | `load_text_cases(path: Path, *, decision: str \| None=None)` | Load data for text cases. |
| `def` | `default_sample_cases()` | Helper for default sample cases in the developer utility script. |
| `def` | `write_sample(path: Path)` | Helper for write sample in the developer utility script. |
| `class` | `CaseResult` | Summary model for one test case execution. |
| `def` | `run_one_case(tester: CommandTester, case: dict[str, Any], index: int, *, use_ai: bool)` | Run the process for one case. |
| `def` | `print_case_report(result: CaseResult, *, show_json: bool, use_ai: bool)` | Helper for print case report in the developer utility script. |
| `def` | `make_markdown_report(results: list[CaseResult])` | Helper for make markdown report in the developer utility script. |
| `def` | `run_cases(cases: list[dict[str, Any]], *, show_json: bool, use_ai: bool, markdown_path: Path \| None=None)` | Run the process for cases. |
| `def` | `parse_args()` | Parse input into structured data for args. |
| `def` | `main()` | Helper for main in the developer utility script. |

## `app/services/budget_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `get_current_month()` | Get data needed for current month. |
| `def` | `normalize_month(month: str \| None=None)` | Normalize and clean input for month. |
| `def` | `normalize_sheet_month_value(value)` | Normalize and clean input for sheet month value. |
| `def` | `format_month_label(month: str)` | Format data into a readable display for month label. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `get_budget_status_emoji(pct_used: float)` | Get data needed for budget status emoji. |
| `def` | `generate_budget_id(month: str, category: str)` | Helper for generate budget id in the finance service layer. |
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `set_budget(category: str, amount: float, month: str=None)` | Set a value for budget. |
| `def` | `get_budget(category: str, month: str=None)` | Get data needed for budget. |
| `def` | `get_all_budgets(month: str=None)` | Get data needed for all budgets. |
| `def` | `get_budget_months()` | Get data needed for budget months. |
| `def` | `budget_transaction_matches_category(record: dict, category: str)` | Helper for budget transaction matches category in the finance service layer. |
| `def` | `calculate_budget_actual_from_transactions(transactions: list[dict])` | Calculate derived values for budget actual from transactions. |
| `def` | `get_actual_expense_breakdown(category: str, month: str=None)` | Get data needed for actual expense breakdown. |
| `def` | `get_actual_expense(category: str, month: str=None)` | Get data needed for actual expense. |
| `def` | `get_budget_summary(month: str=None)` | Get data needed for budget summary. |
| `def` | `check_budget_after_transaction(category: str, month: str=None)` | Helper for check budget after transaction in the finance service layer. |

## `app/services/debt_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `parse_sheet_number(value, default: float=0.0)` | Parse input into structured data for sheet number. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `generate_debt_id()` | Helper for generate debt id in the finance service layer. |
| `def` | `generate_payment_id()` | Helper for generate payment id in the finance service layer. |
| `def` | `normalize_person_name(name: str)` | Normalize and clean input for person name. |
| `def` | `normalize_debt_person_group_name(name: str)` | Normalize and clean input for debt person group name. |
| `def` | `is_settled_value(value)` | Check whether a condition is true for settled value. |
| `def` | `get_debt_row_by_id(debt_id: str)` | Get data needed for debt row by id. |
| `def` | `get_active_debt_exact_person(person_name: str)` | Get data needed for active debt exact person. |
| `def` | `append_debt_mutation(debt_id: str, amount: float, note: str='', mutation_type: str='payment')` | Append data to debt mutation. |
| `def` | `add_debt(debt_type: str, person_name: str, amount: float, description: str='', due_date: str='', source_transaction_id: str='', cashflow_mode: str='', fronting_mode: str='')` | Helper for add debt in the finance service layer. |
| `def` | `get_active_debts(debt_type: str=None)` | Get data needed for active debts. |
| `def` | `get_debt_by_person(person_name: str)` | Get data needed for debt by person. |
| `def` | `add_payment(debt_id: str, amount: float, note: str='')` | Helper for add payment in the finance service layer. |
| `def` | `add_payment_by_person(person_name: str, amount: float, note: str='', target_debt_type: str \| None=None, overpayment_policy: str \| None=None)` | Helper for add payment by person in the finance service layer. |
| `def` | `estimate_payment_outcome(person_name: str, amount: float, target_debt_type: str)` | Helper for estimate payment outcome in the finance service layer. |
| `def` | `format_debt_net_position_lines(person_name: str, remaining_payable: float, remaining_receivable: float)` | Format data into a readable display for debt net position lines. |
| `def` | `offset_debt_by_person(person_name: str, amount: float, description: str='', target_debt_type: str='receivable', resulting_debt_type: str='payable')` | Helper for offset debt by person in the finance service layer. |
| `def` | `_debt_row_sort_key_for_settlement(debt: dict)` | Helper for debt row sort key for settlement in the finance service layer. |
| `def` | `_reduce_debt_remaining_for_settlement(debt: dict, amount: float, note: str, mutation_type: str)` | Helper for reduce debt remaining for settlement in the finance service layer. |
| `def` | `settle_opposite_debts_by_person(person_name: str, amount: float \| None=None, note: str='Netting hutang-piutang')` | Helper for settle opposite debts by person in the finance service layer. |
| `def` | `is_voided_debt(record: dict)` | Check whether a condition is true for voided debt. |
| `def` | `get_debt_person_summary()` | Get data needed for debt person summary. |
| `def` | `get_debt_person_detail(person_name: str, include_settled: bool=True)` | Get data needed for debt person detail. |
| `def` | `get_debt_summary()` | Get data needed for debt summary. |
| `def` | `summarize_debt_rows_for_settlement(debts: list[dict])` | Summarize data for debt rows for settlement. |
| `def` | `settle_selected_debt_ids(person_name: str, debt_ids: list[str], note: str='', overpayment_amount: float=0.0, overpayment_policy: str \| None=None, net_type: str \| None=None)` | Helper for settle selected debt ids in the finance service layer. |
| `def` | `parse_debt_allocation_note(note: str)` | Parse input into structured data for debt allocation note. |
| `def` | `_set_debt_remaining(row_index: int, new_remaining: float, original_amount: float \| None=None)` | Set a value for debt remaining. |
| `def` | `reverse_debt_payment_transaction(txn: dict)` | Helper for reverse debt payment transaction in the finance service layer. |
| `def` | `get_debts_with_row_index(active_only: bool=True)` | Get data needed for debts with row index. |
| `def` | `get_debt_by_id_any_status(debt_id: str)` | Get data needed for debt by id any status. |
| `def` | `build_active_debt_display_map()` | Build the data structure or message text for active debt display map. |
| `def` | `resolve_debt_ref(ref: str, last_debt_map: dict \| None=None)` | Resolve a user input or reference for debt ref. |
| `def` | `expected_initial_cashflow_category(debt: dict)` | Helper for expected initial cashflow category in the finance service layer. |
| `def` | `find_debt_initial_cashflow_candidates(debt: dict)` | Find a record for debt initial cashflow candidates. |
| `def` | `is_debt_without_initial_cashflow(debt: dict)` | Check whether a condition is true for debt without initial cashflow. |
| `def` | `build_debts_index(records: list[dict] \| None=None, active_only: bool=False)` | Build the data structure or message text for debts index. |
| `def` | `get_debts_by_source_transaction_id(transaction_id: str, active_only: bool=True, debt_index: dict \| None=None)` | Get data needed for debts by source transaction id. |
| `def` | `parse_debt_ids_from_transaction_record(txn: dict)` | Parse input into structured data for debt ids from transaction record. |
| `def` | `get_debts_linked_to_transaction_record(txn: dict, active_only: bool=False, debt_index: dict \| None=None)` | Get data needed for debts linked to transaction record. |
| `def` | `get_debt_paid_amount_from_state(debt: dict)` | Get data needed for debt paid amount from state. |
| `def` | `find_overpaid_adjustment_for_debt(debt_id: str, debt_index: dict \| None=None)` | Find a record for overpaid adjustment for debt. |
| `def` | `upsert_overpaid_adjustment(original_debt: dict, overpaid_amount: float, debt_index: dict \| None=None)` | Helper for upsert overpaid adjustment in the finance service layer. |
| `def` | `sync_debt_charges_from_transaction_edit(old_txn: dict, new_txn: dict)` | Helper for sync debt charges from transaction edit in the finance service layer. |
| `def` | `void_debts_for_transaction(transaction_id: str, debt_ids: list[str] \| None=None)` | Helper for void debts for transaction in the finance service layer. |
| `def` | `void_linked_debt_only(debt_id: str, reason: str='Transaksi sumber dihapus')` | Helper for void linked debt only in the finance service layer. |
| `def` | `preview_void_debt(debt_ref: str, last_debt_map: dict \| None=None)` | Helper for preview void debt in the finance service layer. |
| `def` | `resolve_person_debt_targets(person_name: str, detail_ref: str \| None=None)` | Resolve a user input or reference for person debt targets. |
| `def` | `preview_void_debts_by_person(person_name: str, detail_ref: str \| None=None)` | Helper for preview void debts by person in the finance service layer. |
| `def` | `void_debt_ids(debt_ids: list[str])` | Helper for void debt ids in the finance service layer. |
| `def` | `void_debts_by_person(person_name: str, detail_ref: str \| None=None)` | Helper for void debts by person in the finance service layer. |
| `def` | `update_debt(debt_ref: str, updates: dict, last_debt_map: dict \| None=None)` | Update existing data for debt. |
| `def` | `void_debt(debt_ref: str, last_debt_map: dict \| None=None)` | Helper for void debt in the finance service layer. |

## `app/services/finance_insight_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `current_month()` | Helper for current month in the finance service layer. |
| `def` | `normalize_month_arg(value: str \| None=None)` | Normalize and clean input for month arg. |
| `def` | `previous_month(month: str)` | Helper for previous month in the finance service layer. |
| `def` | `month_bounds(month: str)` | Helper for month bounds in the finance service layer. |
| `def` | `parse_period_from_text(text: str)` | Parse input into structured data for period from text. |
| `def` | `normalize_text(value: str)` | Normalize and clean input for text. |
| `def` | `is_date_between(date_value: str, date_from: str \| None, date_to: str \| None)` | Check whether a condition is true for date between. |
| `def` | `filter_records_by_period(records: list[dict], date_from: str \| None, date_to: str \| None)` | Helper for filter records by period in the finance service layer. |
| `def` | `get_month_transactions(month: str)` | Get data needed for month transactions. |
| `def` | `enrich_finance_transactions(records: list[dict])` | Helper for enrich finance transactions in the finance service layer. |
| `def` | `get_effective_expense_amount(record: dict)` | Get data needed for effective expense amount. |
| `def` | `summarize_transactions(records: list[dict])` | Summarize data for transactions. |
| `def` | `add_contribution(items: list[dict], total: float, limit: int=8)` | Helper for add contribution in the finance service layer. |
| `def` | `compact_transaction(r: dict)` | Helper for compact transaction in the finance service layer. |
| `def` | `get_top_transactions(records: list[dict], txn_type: str \| None='expense', limit: int=8)` | Get data needed for top transactions. |
| `def` | `get_budget_status(month: str, transactions: list[dict])` | Get data needed for budget status. |
| `def` | `get_accounts_summary()` | Get data needed for accounts summary. |
| `def` | `get_debt_summary_compact()` | Get data needed for debt summary compact. |
| `def` | `get_net_worth_compact()` | Get data needed for net worth compact. |
| `def` | `detect_anomalies(records: list[dict], month_summary: dict \| None=None)` | Helper for detect anomalies in the finance service layer. |
| `def` | `detect_data_quality_issues(records: list[dict])` | Helper for detect data quality issues in the finance service layer. |
| `def` | `compare_summaries(current: dict, previous: dict)` | Helper for compare summaries in the finance service layer. |
| `def` | `build_monthly_finance_context(month: str \| None=None)` | Build the data structure or message text for monthly finance context. |
| `def` | `extract_keywords(question: str)` | Extract the required part of input for keywords. |
| `def` | `search_relevant_transactions(question: str, date_from: str \| None=None, date_to: str \| None=None, limit: int=12)` | Helper for search relevant transactions in the finance service layer. |
| `def` | `has_explicit_period(question: str)` | Check whether data has explicit period. |
| `def` | `build_ask_finance_context(question: str)` | Build the data structure or message text for ask finance context. |
| `def` | `build_audit_context(month: str \| None=None)` | Build the data structure or message text for audit context. |
| `def` | `build_coach_context(month: str \| None=None, question: str='')` | Build the data structure or message text for coach context. |
| `def` | `should_handle_finance_question(text: str)` | Decide whether the flow should handle finance question. |
| `def` | `route_finance_question_mode(text: str)` | Helper for route finance question mode in the finance service layer. |
| `def` | `deterministic_audit_text(context: dict)` | Helper for deterministic audit text in the finance service layer. |
| `def` | `deterministic_monthly_text(context: dict)` | Helper for deterministic monthly text in the finance service layer. |

## `app/services/net_worth_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the finance service layer. |
| `def` | `today_str()` | Helper for today str in the finance service layer. |
| `def` | `generate_id(prefix: str)` | Helper for generate id in the finance service layer. |
| `def` | `safe_float(value)` | Helper for safe float in the finance service layer. |
| `def` | `safe_float_decimal(value)` | Helper for safe float decimal in the finance service layer. |
| `def` | `parse_human_money(value)` | Parse input into structured data for human money. |
| `def` | `normalize_date_value(value)` | Normalize and clean input for date value. |
| `def` | `calculate_asset_gain(asset: dict)` | Calculate derived values for asset gain. |
| `def` | `parse_price_to_float(value)` | Parse input into structured data for price to float. |
| `def` | `fetch_antam_buyback_price()` | Helper for fetch antam buyback price in the finance service layer. |
| `def` | `is_gold_asset(record: dict)` | Check whether a condition is true for gold asset. |
| `def` | `is_active_record(record: dict)` | Check whether a condition is true for active record. |
| `def` | `build_asset_row(asset: dict)` | Build the data structure or message text for asset row. |
| `def` | `build_liability_row(liability: dict)` | Build the data structure or message text for liability row. |
| `def` | `build_snapshot_row(snapshot: dict)` | Build the data structure or message text for snapshot row. |
| `def` | `add_asset(name: str, current_value: float \| None, category: str='Other Asset', description: str='', asset_type: str='manual', quantity: float \| None=None, unit: str='', price_source: str='', price_per_unit: float \| None=None, purchase_price_per_unit: float \| None=None, purchase_date: str='')` | Helper for add asset in the finance service layer. |
| `def` | `add_liability(name: str, current_balance: float, category: str='Other Liability', description: str='')` | Helper for add liability in the finance service layer. |
| `def` | `refresh_gold_assets(records: list[dict])` | Helper for refresh gold assets in the finance service layer. |
| `def` | `get_assets(active_only: bool=True, refresh_gold: bool=True)` | Get data needed for assets. |
| `def` | `get_liabilities(active_only: bool=True)` | Get data needed for liabilities. |
| `def` | `get_record_by_id(sheet_name: str, record_id: str)` | Get data needed for record by id. |
| `def` | `find_record_row_index(sheet_name: str, record_id: str)` | Find a record for record row index. |
| `def` | `update_record_cells(sheet_name: str, columns: list[str], record_id: str, updates: dict)` | Update existing data for record cells. |
| `def` | `normalize_asset_update_field(field: str)` | Normalize and clean input for asset update field. |
| `def` | `normalize_liability_update_field(field: str)` | Normalize and clean input for liability update field. |
| `def` | `normalize_common_update_value(field: str, value)` | Normalize and clean input for common update value. |
| `def` | `update_asset(asset_id: str, updates: dict)` | Update existing data for asset. |
| `def` | `update_liability(liability_id: str, updates: dict)` | Update existing data for liability. |
| `def` | `deactivate_asset(asset_id: str)` | Helper for deactivate asset in the finance service layer. |
| `def` | `deactivate_liability(liability_id: str)` | Helper for deactivate liability in the finance service layer. |
| `def` | `calculate_net_worth()` | Calculate derived values for net worth. |
| `def` | `create_net_worth_snapshot()` | Create a new data object for net worth snapshot. |
| `def` | `get_net_worth_snapshots(limit: int=12)` | Get data needed for net worth snapshots. |

## `app/services/pending_expense_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the finance service layer. |
| `def` | `today()` | Helper for today in the finance service layer. |
| `def` | `current_month()` | Helper for current month in the finance service layer. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `generate_pending_id()` | Helper for generate pending id in the finance service layer. |
| `def` | `normalize_month(month: str \| None=None)` | Normalize and clean input for month. |
| `def` | `add_months(month: str, delta: int)` | Helper for add months in the finance service layer. |
| `def` | `month_last_day(year: int, month_num: int)` | Helper for month last day in the finance service layer. |
| `def` | `parse_day_current_or_next_month(day_raw: str)` | Parse input into structured data for day current or next month. |
| `def` | `parse_month_only_from_text(text: str)` | Parse input into structured data for month only from text. |
| `def` | `detect_pending_due(text: str)` | Helper for detect pending due in the finance service layer. |
| `def` | `has_past_time_marker(text: str)` | Check whether data has past time marker. |
| `def` | `clean_pending_text(text: str)` | Clean input values for pending text. |
| `def` | `is_pending_expense_text(text: str)` | Check whether a condition is true for pending expense text. |
| `def` | `strip_pending_time_phrases(text: str)` | Helper for strip pending time phrases in the finance service layer. |
| `def` | `infer_category(text: str, parsed: dict \| None=None)` | Helper for infer category in the finance service layer. |
| `def` | `infer_account(text: str, parsed: dict \| None=None)` | Helper for infer account in the finance service layer. |
| `def` | `title_from_description(description: str)` | Helper for title from description in the finance service layer. |
| `def` | `build_pending_row(item: dict)` | Build the data structure or message text for pending row. |
| `def` | `build_pending_expense_from_text(text: str)` | Build the data structure or message text for pending expense from text. |
| `def` | `save_pending_expense(item: dict)` | Save data after validation and confirmation for pending expense. |
| `def` | `add_pending_expense_from_text(text: str)` | Helper for add pending expense from text in the finance service layer. |
| `def` | `get_pending_expenses(period: str \| None=None, active_only: bool=True)` | Get data needed for pending expenses. |
| `def` | `find_pending_by_ref(ref: str)` | Find a record for pending by ref. |
| `def` | `update_pending_status(row_index: int, status: str, paid_transaction_id: str='')` | Update existing data for pending status. |
| `def` | `cancel_pending_expense(ref: str)` | Helper for cancel pending expense in the finance service layer. |
| `def` | `mark_pending_paid(ref: str, account: str \| None=None, paid_date: str \| None=None)` | Mark a record as pending paid. |

## `app/services/recurring_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the finance service layer. |
| `def` | `today_str()` | Helper for today str in the finance service layer. |
| `def` | `generate_recurring_id()` | Helper for generate recurring id in the finance service layer. |
| `def` | `generate_recurring_log_id()` | Helper for generate recurring log id in the finance service layer. |
| `def` | `parse_date(value: str)` | Parse input into structured data for date. |
| `def` | `safe_float(value)` | Helper for safe float in the finance service layer. |
| `def` | `normalize_day_of_month(day)` | Normalize and clean input for day of month. |
| `def` | `normalize_frequency(value: str)` | Normalize and clean input for frequency. |
| `def` | `get_last_day_of_month(year: int, month: int)` | Get data needed for last day of month. |
| `def` | `clamp_day(year: int, month: int, day: int)` | Helper for clamp day in the finance service layer. |
| `def` | `calculate_next_monthly_run(day_of_month: int, from_date: date \| None=None)` | Calculate derived values for next monthly run. |
| `def` | `calculate_next_run_after_execution(rule: dict, run_date: date \| None=None)` | Calculate derived values for next run after execution. |
| `def` | `build_recurring_row(rule: dict)` | Build the data structure or message text for recurring row. |
| `def` | `build_recurring_log_row(log: dict)` | Build the data structure or message text for recurring log row. |
| `def` | `add_recurring_rule(name: str, txn_type: str, amount: float, category: str, account: str, frequency: str, day_of_month: int, description: str \| None=None, subject: str \| None=None, catatan: str \| None=None, tipe_pengeluaran: str \| None=None, to_account: str \| None=None)` | Helper for add recurring rule in the finance service layer. |
| `def` | `get_recurring_rules(active_only: bool=False)` | Get data needed for recurring rules. |
| `def` | `get_due_recurring_rules(target_date: date \| None=None)` | Get data needed for due recurring rules. |
| `def` | `find_recurring_rule_row_index(rule_id: str)` | Find a record for recurring rule row index. |
| `def` | `update_recurring_rule_cells(rule_id: str, updates: dict)` | Update existing data for recurring rule cells. |
| `def` | `disable_recurring_rule(rule_id: str)` | Helper for disable recurring rule in the finance service layer. |
| `def` | `get_recurring_rule_by_id(rule_id: str)` | Get data needed for recurring rule by id. |
| `def` | `normalize_recurring_edit_field(field: str)` | Normalize and clean input for recurring edit field. |
| `def` | `normalize_recurring_edit_value(field: str, value)` | Normalize and clean input for recurring edit value. |
| `def` | `edit_recurring_rule(rule_id: str, updates: dict)` | Helper for edit recurring rule in the finance service layer. |
| `def` | `log_recurring_run(rule_id: str, transaction_id: str \| None, run_date: str, status: str, message: str)` | Helper for log recurring run in the finance service layer. |
| `def` | `build_transaction_from_recurring_rule(rule: dict, run_date: str \| None=None)` | Build the data structure or message text for transaction from recurring rule. |
| `def` | `mark_recurring_rule_paid(rule_id: str, run_date: date \| None=None)` | Mark a record as recurring rule paid. |
| `def` | `process_due_recurring_rules(target_date: date \| None=None)` | Helper for process due recurring rules in the finance service layer. |

## `app/services/report_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `get_transaction_records_for_report()` | Get data needed for transaction records for report. |
| `def` | `format_rupiah(amount: float)` | Format data into a readable display for rupiah. |
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `normalize_category_key(value: str \| None)` | Normalize and clean input for category key. |
| `def` | `normalize_account_key(value: str \| None)` | Normalize and clean input for account key. |
| `def` | `get_known_report_accounts(records: list[dict] \| None=None)` | Get data needed for known report accounts. |
| `def` | `resolve_account_filter(account_query: str \| None, records: list[dict] \| None=None)` | Resolve a user input or reference for account filter. |
| `def` | `is_account_match(value: str \| None, account_key: str \| None)` | Check whether a condition is true for account match. |
| `def` | `is_account_transaction(record: dict, account: str \| None)` | Check whether a condition is true for account transaction. |
| `def` | `split_report_filter_args(value: str \| None, mode: str)` | Helper for split report filter args in the finance service layer. |
| `def` | `split_account_period_arg(value: str \| None)` | Helper for split account period arg in the finance service layer. |
| `def` | `get_known_report_categories(records: list[dict] \| None=None)` | Get data needed for known report categories. |
| `def` | `resolve_category_filter(category_query: str \| None, records: list[dict] \| None=None)` | Resolve a user input or reference for category filter. |
| `def` | `split_report_period_and_category_arg(value: str \| None, mode: str)` | Helper for split report period and category arg in the finance service layer. |
| `def` | `is_truthy_sheet_value(value)` | Check whether a condition is true for truthy sheet value. |
| `def` | `is_voided_debt_record(debt: dict)` | Check whether a condition is true for voided debt record. |
| `def` | `parse_transaction_debt_ids_from_record(txn: dict)` | Parse input into structured data for transaction debt ids from record. |
| `def` | `build_debt_lookup(active_only: bool=True)` | Build the data structure or message text for debt lookup. |
| `def` | `get_linked_debts_for_transaction(txn: dict, lookup: dict)` | Get data needed for linked debts for transaction. |
| `def` | `enrich_transactions_with_debt_info(transactions: list[dict])` | Helper for enrich transactions with debt info in the finance service layer. |
| `def` | `calculate_net_expense_after_receivable(transactions: list[dict])` | Calculate derived values for net expense after receivable. |
| `def` | `calculate_net_expense_by_category(transactions: list[dict])` | Calculate derived values for net expense by category. |
| `def` | `attach_enriched_transactions(summary: dict, transactions: list[dict])` | Helper for attach enriched transactions in the finance service layer. |
| `def` | `build_delta_info(current_value, previous_value, previous_available: bool=True)` | Build the data structure or message text for delta info. |
| `def` | `build_summary_comparison(current: dict, previous: dict, previous_available: bool=True)` | Build the data structure or message text for summary comparison. |
| `def` | `build_category_comparison(current: dict, previous: dict, previous_available: bool=True)` | Build the data structure or message text for category comparison. |
| `def` | `parse_report_date_arg(value: str \| None=None)` | Parse input into structured data for report date arg. |
| `def` | `parse_report_month_arg(value: str \| None=None)` | Parse input into structured data for report month arg. |
| `def` | `get_week_range(reference_date: str \| None=None)` | Get data needed for week range. |
| `def` | `get_month_range(year: int \| None=None, month: int \| None=None)` | Get data needed for month range. |
| `def` | `filter_transactions(records: list[dict], date_from: str \| None=None, date_to: str \| None=None, txn_type: str \| None=None, category: str \| None=None, account: str \| None=None)` | Helper for filter transactions in the finance service layer. |
| `def` | `summarize(transactions: list[dict], account: str \| None=None)` | Helper for summarize in the finance service layer. |
| `def` | `get_daily_report(date_str: str \| None=None, category: str \| None=None, account: str \| None=None)` | Get data needed for daily report. |
| `def` | `get_weekly_report(reference_date: str \| None=None, category: str \| None=None, account: str \| None=None)` | Get data needed for weekly report. |
| `def` | `get_monthly_report(year: int \| None=None, month: int \| None=None, category: str \| None=None, account: str \| None=None)` | Get data needed for monthly report. |
| `def` | `get_account_balance(account_name: str)` | Get data needed for account balance. |
| `def` | `get_account_monthly_report(account: str, month_arg: str \| None=None)` | Get data needed for account monthly report. |
| `def` | `get_account_all_report(account: str)` | Get data needed for account all report. |
| `def` | `get_account_report(account: str, period_arg: str \| None='month')` | Get data needed for account report. |
| `def` | `search_transactions(keyword: str, limit: int=10)` | Helper for search transactions in the finance service layer. |
| `def` | `get_top_expenses(month: str \| None=None, top_n: int=5)` | Get data needed for top expenses. |

## `app/services/transaction_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `get_current_month_str()` | Get data needed for current month str. |
| `def` | `normalize_export_period(period: str \| None=None)` | Normalize and clean input for export period. |
| `def` | `parse_date_safe(value)` | Parse input into structured data for date safe. |
| `def` | `get_transactions_for_export(period: str \| None=None)` | Get data needed for transactions for export. |
| `def` | `is_skip_account_transaction(parsed: dict)` | Check whether a condition is true for skip account transaction. |
| `def` | `generate_transaction_id()` | Helper for generate transaction id in the finance service layer. |
| `def` | `build_transaction_row(parsed: dict, raw_input: str)` | Build the data structure or message text for transaction row. |
| `def` | `update_transaction_debt_relation(transaction_id: str, debt_ids: list[str], tipe_hutang: str='piutang')` | Update existing data for transaction debt relation. |
| `def` | `clear_transaction_debt_relation(transaction_id: str)` | Helper for clear transaction debt relation in the finance service layer. |
| `def` | `validate_transaction(parsed: dict)` | Validate data before it is used by transaction. |
| `def` | `get_account_balance(account_name: str)` | Get data needed for account balance. |
| `def` | `update_account_balance(account_name: str, new_balance: float)` | Update existing data for account balance. |
| `def` | `get_all_accounts()` | Get data needed for all accounts. |
| `def` | `get_account_index_map()` | Get data needed for account index map. |
| `def` | `validate_accounts_exist(account_deltas: dict)` | Validate data before it is used by accounts exist. |
| `def` | `calculate_account_deltas(parsed_items: list[dict])` | Calculate derived values for account deltas. |
| `def` | `apply_account_deltas(account_deltas: dict)` | Apply changes for account deltas. |
| `def` | `save_transaction(parsed: dict, raw_input: str)` | Save data after validation and confirmation for transaction. |
| `def` | `save_transactions_batch(parsed_items: list[dict])` | Save data after validation and confirmation for transactions batch. |
| `def` | `get_transactions_by_month(year: int, month: int)` | Get data needed for transactions by month. |
| `def` | `get_transactions_by_date(date_str: str)` | Get data needed for transactions by date. |
| `def` | `get_expense_by_category(year: int, month: int)` | Get data needed for expense by category. |
| `def` | `is_debt_cashflow_transaction(txn: dict)` | Check whether a condition is true for debt cashflow transaction. |
| `def` | `parse_transaction_date(date_value: str)` | Parse input into structured data for transaction date. |
| `def` | `sort_transactions_sheet_by_date(desc: bool=True)` | Helper for sort transactions sheet by date in the finance service layer. |
| `def` | `get_transactions_with_row_index()` | Get data needed for transactions with row index. |
| `def` | `get_recent_transactions(limit: int=10, period: str \| None=None, month: str \| None=None)` | Get data needed for recent transactions. |
| `def` | `get_transaction_by_id(txn_id: str)` | Get data needed for transaction by id. |
| `def` | `get_transactions_by_ids(txn_ids: list[str])` | Get data needed for transactions by ids. |
| `def` | `get_transactions_by_row_indices(row_indices: list[int])` | Get data needed for transactions by row indices. |
| `def` | `calculate_reverse_deltas_for_delete(transactions: list[dict])` | Calculate derived values for reverse deltas for delete. |
| `def` | `parse_transaction_debt_ids(txn: dict)` | Parse input into structured data for transaction debt ids. |
| `def` | `transaction_has_debt_relation(txn: dict)` | Helper for transaction has debt relation in the finance service layer. |
| `def` | `preview_delete_transactions_by_refs(row_indices: list[int] \| None=None, txn_ids: list[str] \| None=None)` | Helper for preview delete transactions by refs in the finance service layer. |
| `def` | `preview_delete_transactions(txn_ids: list[str])` | Helper for preview delete transactions in the finance service layer. |
| `def` | `delete_transactions_by_ids(txn_ids: list[str])` | Delete data safely for transactions by ids. |
| `def` | `delete_transactions_by_refs(row_indices: list[int] \| None=None, txn_ids: list[str] \| None=None)` | Delete data safely for transactions by refs. |
| `def` | `normalize_edit_field(field: str)` | Normalize and clean input for edit field. |
| `def` | `normalize_edit_updates(updates: dict)` | Normalize and clean input for edit updates. |
| `def` | `get_single_transaction_by_ref(row_index: int \| None=None, txn_id: str \| None=None)` | Get data needed for single transaction by ref. |
| `def` | `build_transaction_row_from_record(txn: dict)` | Build the data structure or message text for transaction row from record. |
| `def` | `calculate_account_effect(txn: dict)` | Calculate derived values for account effect. |
| `def` | `calculate_edit_net_deltas(old_txn: dict, new_txn: dict)` | Calculate derived values for edit net deltas. |
| `def` | `validate_edit_transaction(txn: dict)` | Validate data before it is used by edit transaction. |
| `def` | `preview_edit_transaction_by_ref(updates: dict, row_index: int \| None=None, txn_id: str \| None=None)` | Helper for preview edit transaction by ref in the finance service layer. |
| `def` | `_payment_allocation_note(raw: str, allocations: list[dict], overpayment: float=0.0, policy: str='')` | Helper for payment allocation note in the finance service layer. |
| `def` | `edit_debt_payment_transaction_amount(preview: dict)` | Helper for edit debt payment transaction amount in the finance service layer. |
| `def` | `edit_transaction_by_ref(updates: dict, row_index: int \| None=None, txn_id: str \| None=None)` | Helper for edit transaction by ref in the finance service layer. |

## `app/sheets/client.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `class` | `SheetsAtomicWriteError` | Error raised when a Google Sheets write fails after retries and rollback handling is attempted. |
| `class` | `SheetsTransaction` | Best-effort transaction wrapper for Google Sheets writes. It records successful writes and tries to roll them back if a later write fails. |
| `def` | `sheets_transaction(label: str \| None=None)` | Helper for sheets transaction in the Google Sheets data layer. |
| `def` | `rollback_current_sheets_transaction()` | Helper for rollback current sheets transaction in the Google Sheets data layer. |
| `def` | `get_current_sheets_transaction()` | Get data needed for current sheets transaction. |
| `def` | `_is_quota_or_transient_error(exc: Exception)` | Check whether a condition is true for quota or transient error. |
| `def` | `_call_with_retry(fn, *, max_retries: int \| None=None)` | Helper for call with retry in the Google Sheets data layer. |
| `def` | `_execute_write(fn)` | Helper for execute write in the Google Sheets data layer. |
| `def` | `_execute_read(fn)` | Helper for execute read in the Google Sheets data layer. |
| `def` | `_get_column_letter(col_number: int)` | Get data needed for column letter. |
| `def` | `_extract_updated_row_index(response)` | Extract the required part of input for updated row index. |
| `def` | `_extract_updated_row_range(response)` | Extract the required part of input for updated row range. |
| `def` | `_pad_row(row: list, width: int)` | Helper for pad row in the Google Sheets data layer. |
| `def` | `_clean_header(values: list)` | Clean input values for header. |
| `def` | `_has_data_rows(values: list[list])` | Check whether data has data rows. |
| `def` | `_is_blank_header(header: list[str])` | Check whether a condition is true for blank header. |
| `def` | `_header_has_expected_prefix(header: list[str], expected_header: list[str])` | Helper for header has expected prefix in the Google Sheets data layer. |
| `def` | `_header_is_safe_prefix(header: list[str], expected_header: list[str])` | Helper for header is safe prefix in the Google Sheets data layer. |
| `def` | `_resize_columns_if_needed(sheet, width: int)` | Helper for resize columns if needed in the Google Sheets data layer. |
| `def` | `_write_header(sheet, header: list[str])` | Helper for write header in the Google Sheets data layer. |
| `def` | `_default_rows_for_sheet(sheet_name: str)` | Helper for default rows for sheet in the Google Sheets data layer. |
| `def` | `_seed_default_rows_if_empty(sheet_name: str, sheet, values: list[list])` | Helper for seed default rows if empty in the Google Sheets data layer. |
| `def` | `_get_or_create_worksheet(spreadsheet, sheet_name: str)` | Get data needed for or create worksheet. |
| `def` | `ensure_sheet_schema(sheet_name: str, sheet=None)` | Ensure that setup is ready for sheet schema. |
| `def` | `ensure_spreadsheet_schema()` | Ensure that setup is ready for spreadsheet schema. |
| `def` | `get_spreadsheet()` | Get data needed for spreadsheet. |
| `def` | `get_sheet(sheet_name: str)` | Get data needed for sheet. |
| `def` | `append_row(sheet_name: str, row: list)` | Append data to row. |
| `def` | `append_row_raw(sheet_name: str, row: list)` | Append data to row raw. |
| `def` | `append_rows(sheet_name: str, rows: list[list])` | Append data to rows. |
| `def` | `get_all_records(sheet_name: str)` | Get data needed for all records. |
| `def` | `get_all_values(sheet_name: str)` | Get data needed for all values. |
| `def` | `update_cell(sheet_name: str, row: int, col: int, value)` | Update existing data for cell. |
| `def` | `find_row_index(sheet_name: str, search_col: int, search_value: str)` | Find a record for row index. |
| `def` | `delete_row(sheet_name: str, row_index: int)` | Delete data safely for row. |
| `def` | `delete_rows(sheet_name: str, row_indices: list[int])` | Delete data safely for rows. |
| `def` | `update_row(sheet_name: str, row_index: int, row_values: list)` | Update existing data for row. |
| `def` | `update_range(sheet_name: str, cell_range: str, values: list[list])` | Update existing data for range. |

## `main.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `validate_runtime_config(mode: str=BOT_MODE)` | Validate data before it is used by runtime config. |
| `def` | `ensure_schema_on_startup()` | Ensure that setup is ready for schema on startup. |
| `def` | `start_scheduler_once()` | Helper for start scheduler once in the application. |
| `def` | `shutdown_scheduler_once()` | Helper for shutdown scheduler once in the application. |
| `async def` | `startup()` | Helper for startup in the application. |
| `async def` | `shutdown()` | Helper for shutdown in the application. |
| `async def` | `health_check()` | Helper for health check in the application. |
| `async def` | `test_sheets()` | Helper for test sheets in the application. |
| `async def` | `run_polling_mode()` | Run the process for polling mode. |
| `def` | `run_webhook_mode()` | Run the process for webhook mode. |

## `scripts/ai_command_tester.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_ensure_test_env()` | Ensure that setup is ready for test env. |
| `class` | `_Dummy` | Class used by Dummy in the developer utility script. |
| `class` | `_DummyBadRequest` | Class used by DummyBadRequest in the developer utility script. |
| `def` | `_module_exists(module_name: str)` | Helper for module exists in the developer utility script. |
| `def` | `_install_optional_import_stubs()` | Helper for install optional import stubs in the developer utility script. |
| `class` | `AssertionResult` | Result model for one assertion inside a command test case. |
| `class` | `CommandRun` | Result model for one simulated command or user input run. |
| `def` | `classify_known_route(text: str)` | Helper for classify known route in the developer utility script. |
| `class` | `CommandTester` | Command test runner that loads cases, simulates bot behavior, and produces regression reports. |
| `def` | `get_path(data: Any, path: str)` | Get data needed for path. |
| `def` | `compare_value(actual: Any, expected: Any)` | Helper for compare value in the developer utility script. |
| `def` | `evaluate_expectations(run: CommandRun, expect: dict[str, Any] \| None)` | Helper for evaluate expectations in the developer utility script. |
| `def` | `_has_split_keyword(text: str)` | Check whether data has split keyword. |
| `def` | `_split_has_friend_name(text: str)` | Helper for split has friend name in the developer utility script. |
| `def` | `evaluate_heuristics(run: CommandRun)` | Helper for evaluate heuristics in the developer utility script. |
| `def` | `case_status(assertions: list[AssertionResult])` | Helper for case status in the developer utility script. |
| `def` | `deterministic_diagnosis(run: CommandRun, assertions: list[AssertionResult])` | Helper for deterministic diagnosis in the developer utility script. |
| `def` | `ai_diagnosis(run: CommandRun, assertions: list[AssertionResult])` | Helper for ai diagnosis in the developer utility script. |
| `def` | `command_run_to_dict(run: CommandRun)` | Helper for command run to dict in the developer utility script. |
| `def` | `resolve_input_path(path_text: str)` | Resolve a user input or reference for input path. |
| `def` | `load_cases(path: Path)` | Load data for cases. |
| `def` | `load_text_cases(path: Path, *, decision: str \| None=None)` | Load data for text cases. |
| `def` | `default_sample_cases()` | Helper for default sample cases in the developer utility script. |
| `def` | `write_sample(path: Path)` | Helper for write sample in the developer utility script. |
| `class` | `CaseResult` | Summary model for one test case execution. |
| `def` | `run_one_case(tester: CommandTester, case: dict[str, Any], index: int, *, use_ai: bool)` | Run the process for one case. |
| `def` | `print_case_report(result: CaseResult, *, show_json: bool, use_ai: bool)` | Helper for print case report in the developer utility script. |
| `def` | `make_markdown_report(results: list[CaseResult])` | Helper for make markdown report in the developer utility script. |
| `def` | `run_cases(cases: list[dict[str, Any]], *, show_json: bool, use_ai: bool, markdown_path: Path \| None=None)` | Run the process for cases. |
| `def` | `parse_args()` | Parse input into structured data for args. |
| `def` | `main()` | Helper for main in the developer utility script. |

## `scripts/debug_check.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the developer utility script. |
| `def` | `rupiah(amount)` | Helper for rupiah in the developer utility script. |
| `def` | `add_result(area, name, status, expected, actual='', error='')` | Helper for add result in the developer utility script. |
| `def` | `ok(area, name, expected='OK', actual='OK')` | Helper for ok in the developer utility script. |
| `def` | `warn(area, name, expected='OK', actual='Warning', error='')` | Helper for warn in the developer utility script. |
| `def` | `fail(area, name, expected='OK', actual='Failed', error='')` | Helper for fail in the developer utility script. |
| `def` | `skip(area, name, expected='Available', actual='Skipped', error='')` | Helper for skip in the developer utility script. |
| `def` | `print_header(title)` | Helper for print header in the developer utility script. |
| `def` | `print_summary()` | Helper for print summary in the developer utility script. |
| `def` | `safe_run(area, name, expected, func)` | Helper for safe run in the developer utility script. |
| `def` | `import_module_safe(module_name, area='Import')` | Helper for import module safe in the developer utility script. |
| `def` | `has_function(module, func_name, area)` | Check whether data has function. |
| `def` | `check_environment()` | Helper for check environment in the developer utility script. |
| `def` | `check_imports()` | Helper for check imports in the developer utility script. |
| `def` | `check_config(modules)` | Helper for check config in the developer utility script. |
| `def` | `check_google_sheets(modules)` | Helper for check google sheets in the developer utility script. |
| `def` | `check_nlp(modules)` | Helper for check nlp in the developer utility script. |
| `def` | `check_transaction_service(modules)` | Helper for check transaction service in the developer utility script. |
| `def` | `check_report_service(modules)` | Helper for check report service in the developer utility script. |
| `def` | `check_budget_service(modules)` | Helper for check budget service in the developer utility script. |
| `def` | `check_debt_service(modules)` | Helper for check debt service in the developer utility script. |
| `def` | `check_recurring_service(modules)` | Helper for check recurring service in the developer utility script. |
| `def` | `check_net_worth_service(modules)` | Helper for check net worth service in the developer utility script. |
| `def` | `check_bot_handlers(modules)` | Helper for check bot handlers in the developer utility script. |
| `def` | `check_scheduler(modules)` | Helper for check scheduler in the developer utility script. |
| `def` | `check_regression_commands(modules)` | Helper for check regression commands in the developer utility script. |
| `def` | `main()` | Helper for main in the developer utility script. |

## `scripts/setup_check.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_add(status: str, title: str, detail: str='')` | Helper for add in the developer utility script. |
| `def` | `ok(title: str, detail: str='')` | Helper for ok in the developer utility script. |
| `def` | `warn(title: str, detail: str='')` | Helper for warn in the developer utility script. |
| `def` | `fail(title: str, detail: str='')` | Helper for fail in the developer utility script. |
| `def` | `skip(title: str, detail: str='')` | Helper for skip in the developer utility script. |
| `def` | `mask(value: str)` | Helper for mask in the developer utility script. |
| `def` | `env(name: str, default: str='')` | Helper for env in the developer utility script. |
| `def` | `check_env_file()` | Helper for check env file in the developer utility script. |
| `def` | `check_runtime_env()` | Helper for check runtime env in the developer utility script. |
| `def` | `check_service_account_file()` | Helper for check service account file in the developer utility script. |
| `def` | `check_imports()` | Helper for check imports in the developer utility script. |
| `def` | `check_google_sheets_schema(can_try: bool)` | Helper for check google sheets schema in the developer utility script. |
| `def` | `print_summary()` | Helper for print summary in the developer utility script. |
| `def` | `main()` | Helper for main in the developer utility script. |
