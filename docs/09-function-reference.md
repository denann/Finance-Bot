# 09. Function Reference

This file is a quick index of top-level functions and classes. Use it as a map to find the right logic location. For detailed behavior, read the source file directly.

## `app/api/webhook.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `set_telegram_app(app: Application)` | Helper for set telegram app in the API and webhook layer. |
| `async def` | `webhook(request: Request, x_telegram_bot_api_secret_token: str=Header(None))` | Helper for webhook in the API and webhook layer. |

## `app/bot/application.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `atomic_bot_handler(callback)` | Wrap a Telegram handler in a Sheets transaction so failed writes can be rolled back. |
| `def` | `register_handlers(telegram_app: Application)` | Register all command, message, callback, and error handlers in one place. |
| `async def` | `scheduled_data_export(context)` | Run the scheduled transaction export job from the Telegram JobQueue. |
| `def` | `register_job_queue_jobs(telegram_app: Application)` | Register daily jobs managed by python-telegram-bot JobQueue. |
| `def` | `build_telegram_app()` | Build the Telegram Application with all handlers and scheduled jobs. |

## `app/bot/handler_parts/callback_handler.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `is_skip_account_choice(account: str)` | Check a boolean condition for is skip account choice. |
| `def` | `mark_transaction_as_historical(parsed: dict)` | Mark a record as transaction as historical. |
| `def` | `mark_debt_as_historical(debt_parsed: dict)` | Mark a record as debt as historical. |
| `def` | `_split_debt_id_text(value)` | Helper for split debt id text in the Telegram bot flow. |
| `def` | `_merge_debt_ids(*values)` | Helper for merge debt ids in the Telegram bot flow. |
| `def` | `create_fronted_split_receivable_debts(debt_parsed: dict)` | Create a new record or object for fronted split receivable debts. |
| `def` | `attach_fronted_split_debt_relations(debt_parsed: dict, debt_result: dict, split_result: dict)` | Helper for attach fronted split debt relations in the Telegram bot flow. |
| `def` | `append_fronted_split_result_lines(lines: list[str], split_result: dict, *, indent: str='')` | Append data or text to fronted split result lines. |
| `def` | `build_edit_txn_preview_text_for_callback(preview: dict, split_parsed: dict \| None=None)` | Handle Telegram inline-button callbacks for the Telegram bot flow. |
| `def` | `parse_debt_ids_from_txn_record_for_edit(txn: dict)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `overpayment_decision_keyboard()` | Helper for overpayment decision keyboard in the Telegram bot flow. |
| `def` | `build_overpayment_decision_text(parsed: dict, outcome: dict)` | Build the data structure or message text for overpayment decision text. |
| `def` | `resolve_payment_target_type(parsed: dict, debts: list[dict])` | Resolve the final value for payment target type from possible inputs. |
| `def` | `clear_parse_clarification_state(context: ContextTypes.DEFAULT_TYPE)` | Clear or reset parse clarification state. |
| `def` | `infer_clarified_payment_target_type(raw: str)` | Helper for infer clarified payment target type in the Telegram bot flow. |
| `def` | `build_clarified_debt_payment(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified debt payment. |
| `def` | `build_expense_candidate_raw(raw: str)` | Build the data structure or message text for expense candidate raw. |
| `def` | `build_clarified_expense(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified expense. |
| `def` | `build_clarified_fronting(raw: str, parsed: dict \| None=None)` | Build the data structure or message text for clarified fronting. |
| `async def` | `callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for callback. |

## `app/bot/handler_parts/command_handlers.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `async def` | `start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for start. |
| `async def` | `help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for help. |
| `def` | `add_session_chat_history(context: ContextTypes.DEFAULT_TYPE, role: str, text: str, limit: int=10)` | Helper for add session chat history in the Telegram bot flow. |
| `def` | `get_session_chat_history(context: ContextTypes.DEFAULT_TYPE, limit: int=8)` | Retrieve data needed for session chat history. |
| `def` | `attach_session_history(context: ContextTypes.DEFAULT_TYPE, context_data: dict)` | Helper for attach session history in the Telegram bot flow. |
| `async def` | `send_finance_insight_reply(update: Update, mode: str, context_data: dict, question: str='', prefix: str='🤖 Insight Gemini', context: ContextTypes.DEFAULT_TYPE \| None=None, remember_history: bool=False)` | Send a Telegram response for send finance insight reply. |
| `async def` | `examples_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for examples. |
| `async def` | `insight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for insight. |
| `async def` | `audit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for audit. |
| `async def` | `ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for ask. |
| `async def` | `coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for coach. |
| `async def` | `handle_natural_finance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle natural finance question in the Telegram bot flow. |
| `def` | `format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool=False)` | Format report delta into readable text. |
| `def` | `append_report_comparison_lines(lines: list[str], report: dict, label: str)` | Append data or text to report comparison lines. |
| `def` | `get_report_expense_display(report: dict)` | Retrieve data needed for report expense display. |
| `def` | `append_report_metric_lines(lines: list[str], report: dict)` | Append data or text to report metric lines. |
| `def` | `append_account_report_lines(lines: list[str], report: dict)` | Append data or text to account report lines. |
| `def` | `append_recent_account_transaction_lines(lines: list[str], report: dict, limit: int=8)` | Append data or text to recent account transaction lines. |
| `def` | `append_report_category_breakdown_lines(lines: list[str], report: dict, comparison_label: str)` | Append data or text to report category breakdown lines. |
| `def` | `build_top_expense_debt_lines(txn: dict, amount: float)` | Build the data structure or message text for top expense debt lines. |
| `def` | `is_category_detail_report(report: dict)` | Check a boolean condition for is category detail report. |
| `def` | `get_category_list_title(category: str)` | Retrieve data needed for category list title. |
| `def` | `append_category_detail_summary(lines: list[str], report: dict, comparison_label: str)` | Append data or text to category detail summary. |
| `def` | `append_category_transaction_lines(lines: list[str], report: dict, *, include_date: bool)` | Append data or text to category transaction lines. |
| `async def` | `saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for saldo. |
| `async def` | `rekening_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for rekening. |
| `async def` | `harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for harian. |
| `async def` | `mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for mingguan. |
| `async def` | `bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for bulanan. |
| `async def` | `cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for cari. |
| `def` | `format_budget_net_gross(net_amount: float, gross_amount: float)` | Format budget net gross into readable text. |
| `async def` | `budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for budget. |
| `async def` | `budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for budget history. |
| `def` | `build_pending_expense_lines(items: list[dict], title: str, total: float \| None=None)` | Build the data structure or message text for pending expense lines. |
| `async def` | `pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending. |
| `async def` | `pending_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending add. |
| `async def` | `pending_paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending paid. |
| `async def` | `pending_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for pending cancel. |
| `def` | `parse_amount_text(value: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Extract the important part of the input for split bill total amount. |
| `async def` | `set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for set budget. |
| `def` | `short_debt_id(debt_id: str)` | Helper for short debt id in the Telegram bot flow. |
| `def` | `parse_debt_void_args(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_debt_void_preview_text(preview: dict)` | Build the data structure or message text for debt void preview text. |
| `async def` | `debt_void_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt void. |
| `def` | `normalize_debt_edit_type(value: str)` | Clean and standardize normalize debt edit type. |
| `def` | `parse_debt_edit_args(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_debt_edit_result_text(result: dict)` | Build the data structure or message text for debt edit result text. |
| `async def` | `debt_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt edit. |
| `def` | `format_debt_created_date_for_display(debt: dict)` | Format debt created date for display into readable text. |
| `def` | `debt_detail_sort_key_for_display(debt: dict)` | Helper for debt detail sort key for display in the Telegram bot flow. |
| `def` | `parse_debt_number_selection(selection: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_debt_settle_command_args(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_natural_debt_settle_text(text: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `resolve_selected_debts_from_last_detail(context: ContextTypes.DEFAULT_TYPE, person_name: str, numbers: list[str])` | Resolve the final value for selected debts from last detail from possible inputs. |
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
| `def` | `_clean_debt_description_for_share(desc: str, person: str, known_names: list[str] \| None=None)` | Clean and standardize clean debt description for share. |
| `def` | `_format_shareable_date_heading(date_value)` | Format shareable date heading into readable text. |
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
| `def` | `extract_edit_updates_from_router(args: dict)` | Extract the important part of the input for edit updates from router. |
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `md_safe(value)` | Helper for md safe in the Telegram bot flow. |
| `def` | `clean_command_token(command_text: str)` | Clean and standardize clean command token. |
| `def` | `command_description(command_name: str)` | Helper for command description in the Telegram bot flow. |
| `def` | `is_destructive_command(command_name: str)` | Check a boolean condition for is destructive command. |
| `def` | `similarity_score(a: str, b: str)` | Helper for similarity score in the Telegram bot flow. |
| `def` | `get_similarity_candidates(clean_command: str)` | Retrieve data needed for similarity candidates. |
| `def` | `resolve_command_local(command_text: str)` | Resolve the final value for command local from possible inputs. |
| `def` | `build_command_suggestion_text(resolved: dict, original_text: str)` | Build the data structure or message text for command suggestion text. |
| `def` | `maybe_text_is_command_typo(text: str)` | Try to detect text is command typo without forcing a final decision. |
| `async def` | `unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for unknown command. |
| `def` | `short_txn_id(txn_id: str)` | Helper for short txn id in the Telegram bot flow. |
| `def` | `expand_txn_refs(refs: list[str])` | Helper for expand txn refs in the Telegram bot flow. |
| `def` | `resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str])` | Resolve the final value for txn refs from last from possible inputs. |
| `def` | `build_last_transactions_text(transactions: list[dict], title: str)` | Build the data structure or message text for last transactions text. |
| `def` | `build_delete_preview_text(preview: dict)` | Build the data structure or message text for delete preview text. |
| `def` | `is_authorized(update: Update)` | Check a boolean condition for is authorized. |
| `async def` | `reject_unauthorized(update: Update)` | Helper for reject unauthorized in the Telegram bot flow. |

## `app/bot/handler_parts/common_imports.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `short_debt_id(debt_id: str)` | Helper for short debt id in the Telegram bot flow. |
| `def` | `md_safe(value)` | Helper for md safe in the Telegram bot flow. |
| `def` | `md_code_text(value)` | Helper for md code text in the Telegram bot flow. |
| `def` | `short_txn_id(txn_id: str)` | Helper for short txn id in the Telegram bot flow. |
| `def` | `format_indonesian_date_group_label(date_value)` | Format indonesian date group label into readable text. |
| `def` | `_safe_float_for_display(value, default: float=0.0)` | Helper for safe float for display in the Telegram bot flow. |
| `def` | `get_transaction_receivable_parts(txn: dict)` | Retrieve data needed for transaction receivable parts. |
| `def` | `get_transaction_payable_parts(txn: dict)` | Retrieve data needed for transaction payable parts. |
| `def` | `get_net_expense_after_receivable(txn: dict)` | Retrieve data needed for net expense after receivable. |
| `def` | `build_debt_parts_text(parts: list[dict])` | Build the data structure or message text for debt parts text. |
| `def` | `has_expense_transactions(transactions: list[dict] \| None)` | Check a boolean condition for has expense transactions. |
| `def` | `has_net_gross_difference(transactions: list[dict] \| None)` | Check a boolean condition for has net gross difference. |
| `def` | `append_net_gross_note(lines: list[str], transactions: list[dict] \| None=None, *, force: bool=False)` | Append data or text to net gross note. |
| `def` | `format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool=False)` | Format expense net gross into readable text. |
| `def` | `get_transaction_account_text(txn: dict)` | Retrieve data needed for transaction account text. |
| `def` | `build_transaction_display_lines(txn: dict, *, index: int \| None=None, include_date: bool=True, include_id: bool=False, contribution_pct: float \| None=None, note: str \| None=None)` | Build the data structure or message text for transaction display lines. |
| `def` | `build_transactions_full_text_shared(transactions: list[dict], title: str, account_filter: str \| None=None, *, current_balance: float \| None=None)` | Build the data structure or message text for transactions full text shared. |
| `def` | `is_authorized(update: Update)` | Check a boolean condition for is authorized. |
| `async def` | `reject_unauthorized(update: Update)` | Helper for reject unauthorized in the Telegram bot flow. |
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | Helper for split long message in the Telegram bot flow. |
| `async def` | `reply_long_markdown(update: Update, text: str)` | Send a Telegram response for reply long markdown. |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram response for reply message safely. |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram response for reply update safely. |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Helper for safe edit message in the Telegram bot flow. |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | Handle Telegram inline-button callbacks for the Telegram bot flow. |
| `def` | `build_progress_bar(pct: float, length: int=10)` | Build the data structure or message text for progress bar. |
| `def` | `_parse_human_amount_atom(value: str \| None)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `_safe_eval_amount_expression(expr: str)` | Helper for safe eval amount expression in the Telegram bot flow. |
| `def` | `parse_human_amount(value: str \| None)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_amount_text(value: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Extract the important part of the input for split bill total amount. |

## `app/bot/handler_parts/core.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | Helper for split long message in the Telegram bot flow. |
| `async def` | `reply_long_markdown(update: Update, text: str)` | Send a Telegram response for reply long markdown. |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram response for reply message safely. |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Send a Telegram response for reply update safely. |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Helper for safe edit message in the Telegram bot flow. |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | Handle Telegram inline-button callbacks for the Telegram bot flow. |
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
| `def` | `parse_recurring_add_args(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_recurring_edit_args(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
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
| `async def` | `send_parse_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str, parsed: dict \| None, assessment: dict)` | Send a Telegram response for send parse clarification. |
| `def` | `try_gemini_draft_for_parse_safety(raw: str, fallback_parsed: dict, assessment: dict)` | Helper for try gemini draft for parse safety in the Telegram bot flow. |
| `async def` | `debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for debt message. |
| `async def` | `handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle gemini intent in the Telegram bot flow. |
| `def` | `normalize_text_command(text: str)` | Clean and standardize normalize text command. |
| `async def` | `handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle local natural intent in the Telegram bot flow. |
| `async def` | `image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for image. |
| `async def` | `message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for message. |
| `def` | `build_transactions_full_text(transactions: list[dict], title: str, account_filter: str \| None=None)` | Build the data structure or message text for transactions full text. |
| `def` | `build_transaction_filter_title(base_title: str, category_filter: str \| None=None, account_filter: str \| None=None)` | Build the data structure or message text for transaction filter title. |
| `def` | `_build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str)` | Build the data structure or message text for transaksi prefixed period arg. |
| `def` | `parse_transaksi_period(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `async def` | `transaksi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for transaksi. |
| `async def` | `last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for last. |
| `async def` | `delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for delete txn. |
| `def` | `parse_edit_updates(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `edit_args_contain_split_bill(args: list[str])` | Helper for edit args contain split bill in the Telegram bot flow. |
| `def` | `_normalize_edit_arg_token(token: str)` | Clean and standardize normalize edit arg token. |
| `def` | `parse_edit_debt_payment_conversion_args(args: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_debt_payment_conversion_updates(conversion: dict, old_txn: dict \| None=None)` | Build the data structure or message text for debt payment conversion updates. |
| `def` | `validate_edit_debt_payment_conversion(conversion: dict, amount: float)` | Validate data before it is used by the Telegram bot flow. |
| `def` | `build_edit_debt_payment_preview_text(preview: dict, conversion: dict, debt_check: dict)` | Build the data structure or message text for edit debt payment preview text. |
| `def` | `build_edit_split_preview_text(preview: dict, split_parsed: dict \| None=None)` | Build the data structure or message text for edit split preview text. |
| `def` | `build_edit_preview_text(preview: dict)` | Build the data structure or message text for edit preview text. |
| `def` | `extract_bulk_edit_txn_lines(raw_text: str)` | Extract the important part of the input for bulk edit txn lines. |
| `def` | `_format_bulk_edit_value(value)` | Format bulk edit value into readable text. |
| `def` | `build_bulk_edit_preview_text(entries: list[dict])` | Build the data structure or message text for bulk edit preview text. |
| `def` | `build_bulk_edit_error_text(errors: list[str])` | Build the data structure or message text for bulk edit error text. |
| `def` | `parse_bulk_edit_txn_entries(lines: list[str], context: ContextTypes.DEFAULT_TYPE)` | Parse input into structured data for the Telegram bot flow. |
| `async def` | `bulk_edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str])` | Handle the Telegram request for bulk edit txn. |
| `async def` | `edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle the Telegram request for edit txn. |

## `app/bot/handler_parts/networth_assets.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `parse_asset_quantity_input(value: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `_parse_human_amount_atom(value: str \| None)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `_safe_eval_amount_expression(expr: str)` | Helper for safe eval amount expression in the Telegram bot flow. |
| `def` | `parse_human_amount(value: str \| None)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_asset_extra_fields(extra_parts: list[str])` | Parse input into structured data for the Telegram bot flow. |
| `def` | `format_asset_gain_lines(asset: dict, indent: str='   ')` | Format asset gain lines into readable text. |
| `def` | `guess_asset_category_and_name(name: str, category: str \| None=None)` | Helper for guess asset category and name in the Telegram bot flow. |
| `def` | `build_asset_unit_price_prompt(data: dict)` | Build the data structure or message text for asset unit price prompt. |
| `def` | `parse_pipe_add_args(args: list[str], item_type: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_natural_asset_add(text: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_pipe_update_args(args: list[str], command_name: str)` | Parse input into structured data for the Telegram bot flow. |
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
| `def` | `parse_input(text: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_progress_bar(pct: float, length: int=10)` | Build the data structure or message text for progress bar. |
| `def` | `split_user_inputs(text: str)` | Helper for split user inputs in the Telegram bot flow. |
| `def` | `needs_account(parsed: dict)` | Helper for needs account in the Telegram bot flow. |
| `def` | `is_debt_item(parsed: dict)` | Check a boolean condition for is debt item. |
| `def` | `is_transaction_item(parsed: dict)` | Check a boolean condition for is transaction item. |
| `def` | `build_mixed_preview(mixed_items: list[dict])` | Build the data structure or message text for mixed preview. |
| `def` | `parse_income_missing_amount(line: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_missing_amount_prompt(raw: str, parsed: dict, current: int \| None=None, total: int \| None=None)` | Build the data structure or message text for missing amount prompt. |
| `def` | `finalize_missing_amount_item(item: dict, amount: float)` | Helper for finalize missing amount item in the Telegram bot flow. |
| `async def` | `continue_after_missing_amount_mixed(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict])` | Helper for continue after missing amount mixed in the Telegram bot flow. |
| `async def` | `handle_pending_missing_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle pending missing amount in the Telegram bot flow. |
| `def` | `parse_mixed_item(line: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `mixed_needs_account(mixed_items: list[dict])` | Helper for mixed needs account in the Telegram bot flow. |
| `def` | `edit_or_continue_keyboard(scope: str)` | Helper for edit or continue keyboard in the Telegram bot flow. |
| `def` | `build_parse_safety_notice(assessment: dict, mode: str='warning')` | Build the data structure or message text for parse safety notice. |
| `def` | `build_preview_with_parse_safety(parsed: dict, assessment: dict, mode: str='warning')` | Build the data structure or message text for preview with parse safety. |
| `def` | `build_pending_expense_confirm_preview(item: dict, include_question: bool=True)` | Build the data structure or message text for pending expense confirm preview. |
| `def` | `parse_clarification_keyboard()` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_parse_clarification_prompt(raw: str, assessment: dict \| None=None)` | Build the data structure or message text for parse clarification prompt. |
| `def` | `parse_participant_count(value: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `build_account_delta_summary_from_transaction_items(items: list[dict])` | Build the data structure or message text for account delta summary from transaction items. |
| `def` | `build_mixed_short_summary(mixed_items: list[dict])` | Build the data structure or message text for mixed short summary. |
| `def` | `build_single_short_summary(parsed: dict)` | Build the data structure or message text for single short summary. |
| `def` | `build_updated_item_summary(item: dict, index: int \| None=None)` | Build the data structure or message text for updated item summary. |
| `def` | `build_preview_edit_help(scope: str='single')` | Build the data structure or message text for preview edit help. |
| `def` | `build_mixed_edit_choose_prompt(mixed_items: list[dict])` | Build the data structure or message text for mixed edit choose prompt. |
| `def` | `parse_preview_edit_updates(text: str)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `apply_preview_edit_updates_to_parsed(parsed: dict, updates: dict)` | Apply changes for preview edit updates to parsed. |
| `async def` | `proceed_after_preview_edit(query, context: ContextTypes.DEFAULT_TYPE, scope: str)` | Helper for proceed after preview edit in the Telegram bot flow. |
| `async def` | `handle_pending_preview_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Helper for handle pending preview edit in the Telegram bot flow. |
| `def` | `format_split_bill_preview_line(parsed: dict)` | Format split bill preview line into readable text. |
| `def` | `build_preview(parsed: dict)` | Build the data structure or message text for preview. |
| `def` | `build_batch_preview(parsed_items: list[dict])` | Build the data structure or message text for batch preview. |
| `def` | `strip_split_bill_phrase(text: str)` | Helper for strip split bill phrase in the Telegram bot flow. |
| `def` | `strip_trailing_split_person_names(text: str, person_names: list[str])` | Helper for strip trailing split person names in the Telegram bot flow. |
| `def` | `split_split_bill_person_names(name_text: str)` | Helper for split split bill person names in the Telegram bot flow. |
| `def` | `strip_split_bill_name_tail(name_text: str)` | Helper for strip split bill name tail in the Telegram bot flow. |
| `def` | `is_split_bill_allocation_token(value: str)` | Check a boolean condition for is split bill allocation token. |
| `def` | `parse_split_bill_share_value(value: str, base_share: float)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `parse_split_bill_people_and_shares(name_text: str, total_amount: float, participants: int)` | Parse input into structured data for the Telegram bot flow. |
| `def` | `format_split_bill_person_shares(split_bill: dict)` | Format split bill person shares into readable text. |
| `def` | `clean_split_person_name(name: str)` | Clean and standardize clean split person name. |
| `def` | `build_split_bill_item_description_from_raw(raw: str, fallback: str='')` | Build the data structure or message text for split bill item description from raw. |
| `def` | `detect_split_bill(parsed: dict, raw: str)` | Helper for detect split bill in the Telegram bot flow. |
| `def` | `attach_split_bill_if_any(parsed: dict, raw: str)` | Helper for attach split bill if any in the Telegram bot flow. |
| `def` | `split_bill_needs_decision(parsed: dict)` | Helper for split bill needs decision in the Telegram bot flow. |
| `def` | `mixed_split_bill_needs_decision(mixed_items: list[dict])` | Helper for mixed split bill needs decision in the Telegram bot flow. |
| `def` | `split_bill_keyboard(scope: str='single', item_index: int \| None=None)` | Helper for split bill keyboard in the Telegram bot flow. |
| `def` | `mixed_split_bill_keyboard(mixed_items: list[dict])` | Helper for mixed split bill keyboard in the Telegram bot flow. |
| `def` | `build_split_bill_prompt_from_parsed(parsed: dict)` | Build the data structure or message text for split bill prompt from parsed. |
| `def` | `build_mixed_split_bill_prompt(mixed_items: list[dict])` | Build the data structure or message text for mixed split bill prompt. |
| `def` | `get_mixed_split_bill_indexes(mixed_items: list[dict])` | Retrieve data needed for mixed split bill indexes. |
| `def` | `get_next_mixed_split_bill_index(mixed_items: list[dict])` | Retrieve data needed for next mixed split bill index. |
| `def` | `build_mixed_split_bill_queue_prompt(mixed_items: list[dict])` | Build the data structure or message text for mixed split bill queue prompt. |
| `def` | `apply_split_bill_decision_to_current_mixed(mixed_items: list[dict], status: str)` | Apply changes for split bill decision to current mixed. |
| `def` | `apply_split_bill_decision_to_mixed_index(mixed_items: list[dict], item_index: int, status: str)` | Apply changes for split bill decision to mixed index. |
| `def` | `apply_split_bill_decision_to_parsed(parsed: dict, status: str)` | Apply changes for split bill decision to parsed. |
| `def` | `apply_split_bill_decision_to_mixed(mixed_items: list[dict], status: str)` | Apply changes for split bill decision to mixed. |
| `def` | `create_split_bill_debt(parsed: dict, raw: str='', source_transaction_id: str='')` | Create a new record or object for split bill debt. |
| `def` | `format_split_debt_result_lines(debt_result: dict)` | Format split debt result lines into readable text. |
| `def` | `summarize_saved_transaction_items(items: list[dict])` | Build a concise summary for the Telegram bot flow. |
| `def` | `append_saved_summary_lines(lines: list[str], items: list[dict], title: str='Ringkasan tersimpan')` | Append data or text to saved summary lines. |
| `def` | `_clean_fronting_item_text(text: str, person: str='')` | Clean and standardize clean fronting item text. |
| `def` | `_fronting_expense_description(debt_parsed: dict)` | Helper for fronting expense description in the Telegram bot flow. |
| `def` | `_fronting_expense_category(debt_parsed: dict)` | Helper for fronting expense category in the Telegram bot flow. |
| `def` | `is_ditalangin_expense_without_balance(debt_parsed: dict)` | Check a boolean condition for is ditalangin expense without balance. |
| `def` | `normalize_slash_split_syntax(raw: str)` | Clean and standardize normalize slash split syntax. |
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

## `app/config.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_parse_int_env(name: str, default: int \| None=None)` | Read an environment variable and convert it to integer with a safe fallback. |

## `app/nlp/gemini_finance_insight.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_json_dumps(data: dict)` | Helper for json dumps in the parser and NLP layer. |
| `def` | `build_finance_insight_prompt(mode: str, context: dict, question: str='')` | Build the data structure or message text for finance insight prompt. |
| `def` | `generate_finance_insight(mode: str, context: dict, question: str='')` | Helper for generate finance insight in the parser and NLP layer. |

## `app/nlp/gemini_image_parser.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `clean_gemini_json(raw_text: str)` | Clean and standardize clean gemini json. |
| `def` | `build_image_prompt(caption: str='')` | Build the data structure or message text for image prompt. |
| `def` | `normalize_item(item: dict)` | Clean and standardize normalize item. |
| `def` | `parse_transactions_from_image(image_bytes: bytes, mime_type: str='image/jpeg', caption: str='')` | Parse input into structured data for the parser and NLP layer. |

## `app/nlp/gemini_intent_router.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `should_try_gemini_intent_router(text: str)` | Check a boolean condition for should try gemini intent router. |
| `def` | `extract_json_object(text: str)` | Extract the important part of the input for json object. |
| `def` | `normalize_router_result(data: dict)` | Clean and standardize normalize router result. |
| `def` | `route_intent_with_gemini(user_text: str)` | Helper for route intent with gemini in the parser and NLP layer. |

## `app/nlp/gemini_langchain_client.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_require_api_key()` | Helper for require api key in the parser and NLP layer. |
| `def` | `get_gemini_llm(model_name: str, temperature: float=0.0)` | Retrieve data needed for gemini llm. |
| `def` | `_extract_text(response: Any)` | Extract the important part of the input for text. |
| `def` | `generate_text_with_gemini(prompt: str, *, model_name: str \| None=None, temperature: float=0.0)` | Helper for generate text with gemini in the parser and NLP layer. |
| `def` | `_make_data_url(image_bytes: bytes, mime_type: str)` | Helper for make data url in the parser and NLP layer. |
| `def` | `generate_text_from_image_with_gemini(prompt: str, image_bytes: bytes, *, mime_type: str='image/jpeg', model_name: str \| None=None, temperature: float=0.0)` | Helper for generate text from image with gemini in the parser and NLP layer. |

## `app/nlp/gemini_parser.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `build_prompt(user_input: str)` | Build the data structure or message text for prompt. |
| `def` | `clean_gemini_json(raw_text: str)` | Clean and standardize clean gemini json. |
| `def` | `parse_with_gemini(user_input: str)` | Parse input into structured data for the parser and NLP layer. |
| `def` | `parse_with_pending_fallback(user_input: str)` | Parse input into structured data for the parser and NLP layer. |

## `app/nlp/normalizer.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `normalize_amount(text: str)` | Clean and standardize normalize amount. |
| `def` | `normalize_text(text: str)` | Clean and standardize normalize text. |
| `def` | `parse_amount_value(number_str: str, unit: str='')` | Parse input into structured data for the parser and NLP layer. |
| `def` | `extract_amount_from_text(text: str)` | Extract the important part of the input for amount from text. |
| `def` | `apply_split_operation(text: str, base_amount: int)` | Apply changes for split operation. |

## `app/nlp/parse_safety.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_has_amount(clean: str)` | Check a boolean condition for has amount. |
| `def` | `_has_debt_keyword(clean: str)` | Check a boolean condition for has debt keyword. |
| `def` | `_has_account(clean: str)` | Check a boolean condition for has account. |
| `def` | `_first_token(value: str)` | Helper for first token in the parser and NLP layer. |
| `def` | `_looks_like_person(value: str)` | Helper for looks like person in the parser and NLP layer. |
| `def` | `_append_unique(items: list[str], value: str)` | Append data or text to unique. |
| `def` | `_add_reason(reasons: list[str], reason: str)` | Helper for add reason in the parser and NLP layer. |
| `def` | `extract_person_candidate(text: str)` | Extract the important part of the input for person candidate. |
| `def` | `detect_pre_parse_clarification_flags(text: str)` | Helper for detect pre parse clarification flags in the parser and NLP layer. |
| `def` | `detect_post_parse_flags(text: str, parsed: dict[str, Any] \| None)` | Helper for detect post parse flags in the parser and NLP layer. |
| `def` | `assess_parse_safety(text: str, parsed: dict \| None)` | Assess parser output and choose the safest next action: preview, warning, Gemini draft, or clarification. |

## `app/nlp/regex_parser.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `display_account_name(account: str)` | Helper for display account name in the parser and NLP layer. |
| `def` | `parse_debt_input(text: str)` | Parse input into structured data for the parser and NLP layer. |
| `def` | `detect_type(text: str)` | Helper for detect type in the parser and NLP layer. |
| `def` | `detect_category(text: str, transaction_type: str)` | Helper for detect category in the parser and NLP layer. |
| `def` | `detect_account(text: str)` | Helper for detect account in the parser and NLP layer. |
| `def` | `detect_transfer_accounts(text: str)` | Helper for detect transfer accounts in the parser and NLP layer. |
| `def` | `parse_explicit_date(date_text: str)` | Parse input into structured data for the parser and NLP layer. |
| `def` | `parse_day_only_date(day_text: str)` | Parse input into structured data for the parser and NLP layer. |
| `def` | `strip_date_phrases(text: str)` | Helper for strip date phrases in the parser and NLP layer. |
| `def` | `parse_relative_number(value: str)` | Parse input into structured data for the parser and NLP layer. |
| `def` | `detect_relative_date(text: str)` | Helper for detect relative date in the parser and NLP layer. |
| `def` | `detect_date(text: str)` | Helper for detect date in the parser and NLP layer. |
| `def` | `extract_description(text: str, amount=None)` | Extract the important part of the input for description. |
| `def` | `detect_subject(text: str, transaction_type: str, category: str, description: str)` | Helper for detect subject in the parser and NLP layer. |
| `def` | `extract_note(text: str)` | Extract the important part of the input for note. |
| `def` | `detect_spending_type(text: str, category: str, transaction_type: str)` | Helper for detect spending type in the parser and NLP layer. |
| `def` | `parse_with_regex(text: str)` | Parse a natural finance input with local deterministic rules before using AI fallback. |

## `app/scheduler/jobs.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `async def` | `job_recurring_run()` | Helper for job recurring run in the scheduled job layer. |
| `async def` | `send_message(text: str, parse_mode: str \| None='Markdown', reply_markup=None)` | Send a Telegram response for send message. |
| `async def` | `job_daily_summary()` | Helper for job daily summary in the scheduled job layer. |
| `async def` | `job_weekly_summary()` | Helper for job weekly summary in the scheduled job layer. |
| `async def` | `job_monthly_summary()` | Helper for job monthly summary in the scheduled job layer. |
| `async def` | `job_debt_reminder()` | Helper for job debt reminder in the scheduled job layer. |
| `def` | `create_scheduler()` | Create a new record or object for scheduler. |

## `app/services/budget_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `get_current_month()` | Retrieve data needed for current month. |
| `def` | `normalize_month(month: str \| None=None)` | Clean and standardize normalize month. |
| `def` | `normalize_sheet_month_value(value)` | Clean and standardize normalize sheet month value. |
| `def` | `format_month_label(month: str)` | Format month label into readable text. |
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `get_budget_status_emoji(pct_used: float)` | Retrieve data needed for budget status emoji. |
| `def` | `generate_budget_id(month: str, category: str)` | Helper for generate budget id in the finance service layer. |
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `set_budget(category: str, amount: float, month: str=None)` | Helper for set budget in the finance service layer. |
| `def` | `get_budget(category: str, month: str=None)` | Retrieve data needed for budget. |
| `def` | `get_all_budgets(month: str=None)` | Retrieve data needed for all budgets. |
| `def` | `get_budget_months()` | Retrieve data needed for budget months. |
| `def` | `budget_transaction_matches_category(record: dict, category: str)` | Helper for budget transaction matches category in the finance service layer. |
| `def` | `calculate_budget_actual_from_transactions(transactions: list[dict])` | Calculate derived values for calculate budget actual from transactions. |
| `def` | `get_actual_expense_breakdown(category: str, month: str=None)` | Retrieve data needed for actual expense breakdown. |
| `def` | `get_actual_expense(category: str, month: str=None)` | Retrieve data needed for actual expense. |
| `def` | `get_budget_summary(month: str=None)` | Retrieve data needed for budget summary. |
| `def` | `check_budget_after_transaction(category: str, month: str=None)` | Helper for check budget after transaction in the finance service layer. |

## `app/services/debt_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `parse_sheet_number(value, default: float=0.0)` | Parse input into structured data for the finance service layer. |
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `generate_debt_id()` | Helper for generate debt id in the finance service layer. |
| `def` | `generate_payment_id()` | Helper for generate payment id in the finance service layer. |
| `def` | `normalize_person_name(name: str)` | Clean and standardize normalize person name. |
| `def` | `normalize_debt_person_group_name(name: str)` | Clean and standardize normalize debt person group name. |
| `def` | `is_settled_value(value)` | Check a boolean condition for is settled value. |
| `def` | `get_debt_row_by_id(debt_id: str)` | Retrieve data needed for debt row by id. |
| `def` | `get_active_debt_exact_person(person_name: str)` | Retrieve data needed for active debt exact person. |
| `def` | `append_debt_mutation(debt_id: str, amount: float, note: str='', mutation_type: str='payment')` | Append data or text to debt mutation. |
| `def` | `add_debt(debt_type: str, person_name: str, amount: float, description: str='', due_date: str='', source_transaction_id: str='', cashflow_mode: str='', fronting_mode: str='')` | Create a granular debt record and register its mutation history. |
| `def` | `get_active_debts(debt_type: str=None)` | Retrieve data needed for active debts. |
| `def` | `get_debt_by_person(person_name: str)` | Retrieve data needed for debt by person. |
| `def` | `add_payment(debt_id: str, amount: float, note: str='')` | Helper for add payment in the finance service layer. |
| `def` | `add_payment_by_person(person_name: str, amount: float, note: str='', target_debt_type: str \| None=None, overpayment_policy: str \| None=None)` | Helper for add payment by person in the finance service layer. |
| `def` | `estimate_payment_outcome(person_name: str, amount: float, target_debt_type: str)` | Helper for estimate payment outcome in the finance service layer. |
| `def` | `format_debt_net_position_lines(person_name: str, remaining_payable: float, remaining_receivable: float)` | Format debt net position lines into readable text. |
| `def` | `offset_debt_by_person(person_name: str, amount: float, description: str='', target_debt_type: str='receivable', resulting_debt_type: str='payable')` | Helper for offset debt by person in the finance service layer. |
| `def` | `_debt_row_sort_key_for_settlement(debt: dict)` | Helper for debt row sort key for settlement in the finance service layer. |
| `def` | `_reduce_debt_remaining_for_settlement(debt: dict, amount: float, note: str, mutation_type: str)` | Helper for reduce debt remaining for settlement in the finance service layer. |
| `def` | `settle_opposite_debts_by_person(person_name: str, amount: float \| None=None, note: str='Netting hutang-piutang')` | Helper for settle opposite debts by person in the finance service layer. |
| `def` | `is_voided_debt(record: dict)` | Check a boolean condition for is voided debt. |
| `def` | `get_debt_person_summary()` | Retrieve data needed for debt person summary. |
| `def` | `get_debt_person_detail(person_name: str, include_settled: bool=True)` | Retrieve data needed for debt person detail. |
| `def` | `get_debt_summary()` | Retrieve data needed for debt summary. |
| `def` | `summarize_debt_rows_for_settlement(debts: list[dict])` | Build a concise summary for the finance service layer. |
| `def` | `settle_selected_debt_ids(person_name: str, debt_ids: list[str], note: str='', overpayment_amount: float=0.0, overpayment_policy: str \| None=None, net_type: str \| None=None)` | Helper for settle selected debt ids in the finance service layer. |
| `def` | `parse_debt_allocation_note(note: str)` | Parse input into structured data for the finance service layer. |
| `def` | `_set_debt_remaining(row_index: int, new_remaining: float, original_amount: float \| None=None)` | Helper for set debt remaining in the finance service layer. |
| `def` | `reverse_debt_payment_transaction(txn: dict)` | Helper for reverse debt payment transaction in the finance service layer. |
| `def` | `get_debts_with_row_index(active_only: bool=True)` | Retrieve data needed for debts with row index. |
| `def` | `get_debt_by_id_any_status(debt_id: str)` | Retrieve data needed for debt by id any status. |
| `def` | `build_active_debt_display_map()` | Build the data structure or message text for active debt display map. |
| `def` | `resolve_debt_ref(ref: str, last_debt_map: dict \| None=None)` | Resolve the final value for debt ref from possible inputs. |
| `def` | `expected_initial_cashflow_category(debt: dict)` | Helper for expected initial cashflow category in the finance service layer. |
| `def` | `find_debt_initial_cashflow_candidates(debt: dict)` | Helper for find debt initial cashflow candidates in the finance service layer. |
| `def` | `is_debt_without_initial_cashflow(debt: dict)` | Check a boolean condition for is debt without initial cashflow. |
| `def` | `build_debts_index(records: list[dict] \| None=None, active_only: bool=False)` | Build the data structure or message text for debts index. |
| `def` | `get_debts_by_source_transaction_id(transaction_id: str, active_only: bool=True, debt_index: dict \| None=None)` | Retrieve data needed for debts by source transaction id. |
| `def` | `parse_debt_ids_from_transaction_record(txn: dict)` | Parse input into structured data for the finance service layer. |
| `def` | `get_debts_linked_to_transaction_record(txn: dict, active_only: bool=False, debt_index: dict \| None=None)` | Retrieve data needed for debts linked to transaction record. |
| `def` | `get_debt_paid_amount_from_state(debt: dict)` | Retrieve data needed for debt paid amount from state. |
| `def` | `find_overpaid_adjustment_for_debt(debt_id: str, debt_index: dict \| None=None)` | Helper for find overpaid adjustment for debt in the finance service layer. |
| `def` | `upsert_overpaid_adjustment(original_debt: dict, overpaid_amount: float, debt_index: dict \| None=None)` | Helper for upsert overpaid adjustment in the finance service layer. |
| `def` | `sync_debt_charges_from_transaction_edit(old_txn: dict, new_txn: dict)` | Helper for sync debt charges from transaction edit in the finance service layer. |
| `def` | `void_debts_for_transaction(transaction_id: str, debt_ids: list[str] \| None=None)` | Helper for void debts for transaction in the finance service layer. |
| `def` | `void_linked_debt_only(debt_id: str, reason: str='Transaksi sumber dihapus')` | Helper for void linked debt only in the finance service layer. |
| `def` | `preview_void_debt(debt_ref: str, last_debt_map: dict \| None=None)` | Helper for preview void debt in the finance service layer. |
| `def` | `resolve_person_debt_targets(person_name: str, detail_ref: str \| None=None)` | Resolve the final value for person debt targets from possible inputs. |
| `def` | `preview_void_debts_by_person(person_name: str, detail_ref: str \| None=None)` | Helper for preview void debts by person in the finance service layer. |
| `def` | `void_debt_ids(debt_ids: list[str])` | Helper for void debt ids in the finance service layer. |
| `def` | `void_debts_by_person(person_name: str, detail_ref: str \| None=None)` | Helper for void debts by person in the finance service layer. |
| `def` | `update_debt(debt_ref: str, updates: dict, last_debt_map: dict \| None=None)` | Update debt while keeping related data consistent. |
| `def` | `void_debt(debt_ref: str, last_debt_map: dict \| None=None)` | Helper for void debt in the finance service layer. |

## `app/services/finance_insight_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `current_month()` | Helper for current month in the finance service layer. |
| `def` | `normalize_month_arg(value: str \| None=None)` | Clean and standardize normalize month arg. |
| `def` | `previous_month(month: str)` | Helper for previous month in the finance service layer. |
| `def` | `month_bounds(month: str)` | Helper for month bounds in the finance service layer. |
| `def` | `parse_period_from_text(text: str)` | Parse input into structured data for the finance service layer. |
| `def` | `normalize_text(value: str)` | Clean and standardize normalize text. |
| `def` | `is_date_between(date_value: str, date_from: str \| None, date_to: str \| None)` | Check a boolean condition for is date between. |
| `def` | `filter_records_by_period(records: list[dict], date_from: str \| None, date_to: str \| None)` | Helper for filter records by period in the finance service layer. |
| `def` | `get_month_transactions(month: str)` | Retrieve data needed for month transactions. |
| `def` | `enrich_finance_transactions(records: list[dict])` | Helper for enrich finance transactions in the finance service layer. |
| `def` | `get_effective_expense_amount(record: dict)` | Retrieve data needed for effective expense amount. |
| `def` | `summarize_transactions(records: list[dict])` | Build a concise summary for the finance service layer. |
| `def` | `add_contribution(items: list[dict], total: float, limit: int=8)` | Helper for add contribution in the finance service layer. |
| `def` | `compact_transaction(r: dict)` | Helper for compact transaction in the finance service layer. |
| `def` | `get_top_transactions(records: list[dict], txn_type: str \| None='expense', limit: int=8)` | Retrieve data needed for top transactions. |
| `def` | `get_budget_status(month: str, transactions: list[dict])` | Retrieve data needed for budget status. |
| `def` | `get_accounts_summary()` | Retrieve data needed for accounts summary. |
| `def` | `get_debt_summary_compact()` | Retrieve data needed for debt summary compact. |
| `def` | `get_net_worth_compact()` | Retrieve data needed for net worth compact. |
| `def` | `detect_anomalies(records: list[dict], month_summary: dict \| None=None)` | Helper for detect anomalies in the finance service layer. |
| `def` | `detect_data_quality_issues(records: list[dict])` | Helper for detect data quality issues in the finance service layer. |
| `def` | `compare_summaries(current: dict, previous: dict)` | Helper for compare summaries in the finance service layer. |
| `def` | `build_monthly_finance_context(month: str \| None=None)` | Build the data structure or message text for monthly finance context. |
| `def` | `extract_keywords(question: str)` | Extract the important part of the input for keywords. |
| `def` | `search_relevant_transactions(question: str, date_from: str \| None=None, date_to: str \| None=None, limit: int=12)` | Helper for search relevant transactions in the finance service layer. |
| `def` | `has_explicit_period(question: str)` | Check a boolean condition for has explicit period. |
| `def` | `build_ask_finance_context(question: str)` | Build the most relevant finance context for a natural /ask question. |
| `def` | `build_audit_context(month: str \| None=None)` | Build the data structure or message text for audit context. |
| `def` | `build_coach_context(month: str \| None=None, question: str='')` | Build the data structure or message text for coach context. |
| `def` | `should_handle_finance_question(text: str)` | Check a boolean condition for should handle finance question. |
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
| `def` | `parse_human_money(value)` | Parse input into structured data for the finance service layer. |
| `def` | `normalize_date_value(value)` | Clean and standardize normalize date value. |
| `def` | `calculate_asset_gain(asset: dict)` | Calculate derived values for calculate asset gain. |
| `def` | `parse_price_to_float(value)` | Parse input into structured data for the finance service layer. |
| `def` | `fetch_antam_buyback_price()` | Helper for fetch antam buyback price in the finance service layer. |
| `def` | `is_gold_asset(record: dict)` | Check a boolean condition for is gold asset. |
| `def` | `is_active_record(record: dict)` | Check a boolean condition for is active record. |
| `def` | `build_asset_row(asset: dict)` | Build the data structure or message text for asset row. |
| `def` | `build_liability_row(liability: dict)` | Build the data structure or message text for liability row. |
| `def` | `build_snapshot_row(snapshot: dict)` | Build the data structure or message text for snapshot row. |
| `def` | `add_asset(name: str, current_value: float \| None, category: str='Other Asset', description: str='', asset_type: str='manual', quantity: float \| None=None, unit: str='', price_source: str='', price_per_unit: float \| None=None, purchase_price_per_unit: float \| None=None, purchase_date: str='')` | Helper for add asset in the finance service layer. |
| `def` | `add_liability(name: str, current_balance: float, category: str='Other Liability', description: str='')` | Helper for add liability in the finance service layer. |
| `def` | `refresh_gold_assets(records: list[dict])` | Helper for refresh gold assets in the finance service layer. |
| `def` | `get_assets(active_only: bool=True, refresh_gold: bool=True)` | Retrieve data needed for assets. |
| `def` | `get_liabilities(active_only: bool=True)` | Retrieve data needed for liabilities. |
| `def` | `get_record_by_id(sheet_name: str, record_id: str)` | Retrieve data needed for record by id. |
| `def` | `find_record_row_index(sheet_name: str, record_id: str)` | Helper for find record row index in the finance service layer. |
| `def` | `update_record_cells(sheet_name: str, columns: list[str], record_id: str, updates: dict)` | Update record cells while keeping related data consistent. |
| `def` | `normalize_asset_update_field(field: str)` | Clean and standardize normalize asset update field. |
| `def` | `normalize_liability_update_field(field: str)` | Clean and standardize normalize liability update field. |
| `def` | `normalize_common_update_value(field: str, value)` | Clean and standardize normalize common update value. |
| `def` | `update_asset(asset_id: str, updates: dict)` | Update asset while keeping related data consistent. |
| `def` | `update_liability(liability_id: str, updates: dict)` | Update liability while keeping related data consistent. |
| `def` | `deactivate_asset(asset_id: str)` | Helper for deactivate asset in the finance service layer. |
| `def` | `deactivate_liability(liability_id: str)` | Helper for deactivate liability in the finance service layer. |
| `def` | `calculate_net_worth()` | Calculate derived values for calculate net worth. |
| `def` | `create_net_worth_snapshot()` | Create a new record or object for net worth snapshot. |
| `def` | `get_net_worth_snapshots(limit: int=12)` | Retrieve data needed for net worth snapshots. |

## `app/services/pending_expense_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the finance service layer. |
| `def` | `today()` | Helper for today in the finance service layer. |
| `def` | `current_month()` | Helper for current month in the finance service layer. |
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `generate_pending_id()` | Helper for generate pending id in the finance service layer. |
| `def` | `normalize_month(month: str \| None=None)` | Clean and standardize normalize month. |
| `def` | `add_months(month: str, delta: int)` | Helper for add months in the finance service layer. |
| `def` | `month_last_day(year: int, month_num: int)` | Helper for month last day in the finance service layer. |
| `def` | `parse_day_current_or_next_month(day_raw: str)` | Parse input into structured data for the finance service layer. |
| `def` | `parse_month_only_from_text(text: str)` | Parse input into structured data for the finance service layer. |
| `def` | `detect_pending_due(text: str)` | Helper for detect pending due in the finance service layer. |
| `def` | `has_past_time_marker(text: str)` | Check a boolean condition for has past time marker. |
| `def` | `clean_pending_text(text: str)` | Clean and standardize clean pending text. |
| `def` | `is_pending_expense_text(text: str)` | Check a boolean condition for is pending expense text. |
| `def` | `strip_pending_time_phrases(text: str)` | Helper for strip pending time phrases in the finance service layer. |
| `def` | `infer_category(text: str, parsed: dict \| None=None)` | Helper for infer category in the finance service layer. |
| `def` | `infer_account(text: str, parsed: dict \| None=None)` | Helper for infer account in the finance service layer. |
| `def` | `title_from_description(description: str)` | Helper for title from description in the finance service layer. |
| `def` | `build_pending_row(item: dict)` | Build the data structure or message text for pending row. |
| `def` | `build_pending_expense_from_text(text: str)` | Build the data structure or message text for pending expense from text. |
| `def` | `save_pending_expense(item: dict)` | Save pending expense after validation and confirmation. |
| `def` | `add_pending_expense_from_text(text: str)` | Helper for add pending expense from text in the finance service layer. |
| `def` | `get_pending_expenses(period: str \| None=None, active_only: bool=True)` | Retrieve data needed for pending expenses. |
| `def` | `find_pending_by_ref(ref: str)` | Helper for find pending by ref in the finance service layer. |
| `def` | `update_pending_status(row_index: int, status: str, paid_transaction_id: str='')` | Update pending status while keeping related data consistent. |
| `def` | `cancel_pending_expense(ref: str)` | Helper for cancel pending expense in the finance service layer. |
| `def` | `mark_pending_paid(ref: str, account: str \| None=None, paid_date: str \| None=None)` | Mark a record as pending paid. |

## `app/services/recurring_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the finance service layer. |
| `def` | `today_str()` | Helper for today str in the finance service layer. |
| `def` | `generate_recurring_id()` | Helper for generate recurring id in the finance service layer. |
| `def` | `generate_recurring_log_id()` | Helper for generate recurring log id in the finance service layer. |
| `def` | `parse_date(value: str)` | Parse input into structured data for the finance service layer. |
| `def` | `safe_float(value)` | Helper for safe float in the finance service layer. |
| `def` | `normalize_day_of_month(day)` | Clean and standardize normalize day of month. |
| `def` | `normalize_frequency(value: str)` | Clean and standardize normalize frequency. |
| `def` | `get_last_day_of_month(year: int, month: int)` | Retrieve data needed for last day of month. |
| `def` | `clamp_day(year: int, month: int, day: int)` | Helper for clamp day in the finance service layer. |
| `def` | `calculate_next_monthly_run(day_of_month: int, from_date: date \| None=None)` | Calculate derived values for calculate next monthly run. |
| `def` | `calculate_next_run_after_execution(rule: dict, run_date: date \| None=None)` | Calculate derived values for calculate next run after execution. |
| `def` | `build_recurring_row(rule: dict)` | Build the data structure or message text for recurring row. |
| `def` | `build_recurring_log_row(log: dict)` | Build the data structure or message text for recurring log row. |
| `def` | `add_recurring_rule(name: str, txn_type: str, amount: float, category: str, account: str, frequency: str, day_of_month: int, description: str \| None=None, subject: str \| None=None, catatan: str \| None=None, tipe_pengeluaran: str \| None=None, to_account: str \| None=None)` | Helper for add recurring rule in the finance service layer. |
| `def` | `get_recurring_rules(active_only: bool=False)` | Retrieve data needed for recurring rules. |
| `def` | `get_due_recurring_rules(target_date: date \| None=None)` | Retrieve data needed for due recurring rules. |
| `def` | `find_recurring_rule_row_index(rule_id: str)` | Helper for find recurring rule row index in the finance service layer. |
| `def` | `update_recurring_rule_cells(rule_id: str, updates: dict)` | Update recurring rule cells while keeping related data consistent. |
| `def` | `disable_recurring_rule(rule_id: str)` | Helper for disable recurring rule in the finance service layer. |
| `def` | `get_recurring_rule_by_id(rule_id: str)` | Retrieve data needed for recurring rule by id. |
| `def` | `normalize_recurring_edit_field(field: str)` | Clean and standardize normalize recurring edit field. |
| `def` | `normalize_recurring_edit_value(field: str, value)` | Clean and standardize normalize recurring edit value. |
| `def` | `edit_recurring_rule(rule_id: str, updates: dict)` | Helper for edit recurring rule in the finance service layer. |
| `def` | `log_recurring_run(rule_id: str, transaction_id: str \| None, run_date: str, status: str, message: str)` | Helper for log recurring run in the finance service layer. |
| `def` | `build_transaction_from_recurring_rule(rule: dict, run_date: str \| None=None)` | Build the data structure or message text for transaction from recurring rule. |
| `def` | `mark_recurring_rule_paid(rule_id: str, run_date: date \| None=None)` | Mark a record as recurring rule paid. |
| `def` | `process_due_recurring_rules(target_date: date \| None=None)` | Helper for process due recurring rules in the finance service layer. |

## `app/services/report_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `get_transaction_records_for_report()` | Retrieve data needed for transaction records for report. |
| `def` | `format_rupiah(amount: float)` | Format rupiah into readable text. |
| `def` | `safe_float(value, default: float=0.0)` | Helper for safe float in the finance service layer. |
| `def` | `normalize_category_key(value: str \| None)` | Clean and standardize normalize category key. |
| `def` | `normalize_account_key(value: str \| None)` | Clean and standardize normalize account key. |
| `def` | `get_known_report_accounts(records: list[dict] \| None=None)` | Retrieve data needed for known report accounts. |
| `def` | `resolve_account_filter(account_query: str \| None, records: list[dict] \| None=None)` | Resolve the final value for account filter from possible inputs. |
| `def` | `is_account_match(value: str \| None, account_key: str \| None)` | Check a boolean condition for is account match. |
| `def` | `is_account_transaction(record: dict, account: str \| None)` | Check a boolean condition for is account transaction. |
| `def` | `split_report_filter_args(value: str \| None, mode: str)` | Helper for split report filter args in the finance service layer. |
| `def` | `split_account_period_arg(value: str \| None)` | Helper for split account period arg in the finance service layer. |
| `def` | `get_known_report_categories(records: list[dict] \| None=None)` | Retrieve data needed for known report categories. |
| `def` | `resolve_category_filter(category_query: str \| None, records: list[dict] \| None=None)` | Resolve the final value for category filter from possible inputs. |
| `def` | `split_report_period_and_category_arg(value: str \| None, mode: str)` | Helper for split report period and category arg in the finance service layer. |
| `def` | `is_truthy_sheet_value(value)` | Check a boolean condition for is truthy sheet value. |
| `def` | `is_voided_debt_record(debt: dict)` | Check a boolean condition for is voided debt record. |
| `def` | `parse_transaction_debt_ids_from_record(txn: dict)` | Parse input into structured data for the finance service layer. |
| `def` | `build_debt_lookup(active_only: bool=True)` | Build the data structure or message text for debt lookup. |
| `def` | `get_linked_debts_for_transaction(txn: dict, lookup: dict)` | Retrieve data needed for linked debts for transaction. |
| `def` | `enrich_transactions_with_debt_info(transactions: list[dict])` | Helper for enrich transactions with debt info in the finance service layer. |
| `def` | `calculate_net_expense_after_receivable(transactions: list[dict])` | Calculate derived values for calculate net expense after receivable. |
| `def` | `calculate_net_expense_by_category(transactions: list[dict])` | Calculate derived values for calculate net expense by category. |
| `def` | `attach_enriched_transactions(summary: dict, transactions: list[dict])` | Helper for attach enriched transactions in the finance service layer. |
| `def` | `build_delta_info(current_value, previous_value, previous_available: bool=True)` | Build the data structure or message text for delta info. |
| `def` | `build_summary_comparison(current: dict, previous: dict, previous_available: bool=True)` | Build the data structure or message text for summary comparison. |
| `def` | `build_category_comparison(current: dict, previous: dict, previous_available: bool=True)` | Build the data structure or message text for category comparison. |
| `def` | `parse_report_date_arg(value: str \| None=None)` | Parse input into structured data for the finance service layer. |
| `def` | `parse_report_month_arg(value: str \| None=None)` | Parse input into structured data for the finance service layer. |
| `def` | `get_week_range(reference_date: str \| None=None)` | Retrieve data needed for week range. |
| `def` | `get_month_range(year: int \| None=None, month: int \| None=None)` | Retrieve data needed for month range. |
| `def` | `filter_transactions(records: list[dict], date_from: str \| None=None, date_to: str \| None=None, txn_type: str \| None=None, category: str \| None=None, account: str \| None=None)` | Helper for filter transactions in the finance service layer. |
| `def` | `summarize(transactions: list[dict], account: str \| None=None)` | Build a concise summary for the finance service layer. |
| `def` | `get_daily_report(date_str: str \| None=None, category: str \| None=None, account: str \| None=None)` | Retrieve data needed for daily report. |
| `def` | `get_weekly_report(reference_date: str \| None=None, category: str \| None=None, account: str \| None=None)` | Retrieve data needed for weekly report. |
| `def` | `get_monthly_report(year: int \| None=None, month: int \| None=None, category: str \| None=None, account: str \| None=None)` | Retrieve data needed for monthly report. |
| `def` | `get_account_balance(account_name: str)` | Retrieve data needed for account balance. |
| `def` | `get_account_monthly_report(account: str, month_arg: str \| None=None)` | Retrieve data needed for account monthly report. |
| `def` | `get_account_all_report(account: str)` | Retrieve data needed for account all report. |
| `def` | `get_account_report(account: str, period_arg: str \| None='month')` | Retrieve data needed for account report. |
| `def` | `search_transactions(keyword: str, limit: int=10)` | Helper for search transactions in the finance service layer. |
| `def` | `get_top_expenses(month: str \| None=None, top_n: int=5)` | Retrieve data needed for top expenses. |

## `app/services/transaction_service.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `get_current_month_str()` | Retrieve data needed for current month str. |
| `def` | `normalize_export_period(period: str \| None=None)` | Clean and standardize normalize export period. |
| `def` | `parse_date_safe(value)` | Parse input into structured data for the finance service layer. |
| `def` | `get_transactions_for_export(period: str \| None=None)` | Retrieve data needed for transactions for export. |
| `def` | `is_skip_account_transaction(parsed: dict)` | Check a boolean condition for is skip account transaction. |
| `def` | `generate_transaction_id()` | Helper for generate transaction id in the finance service layer. |
| `def` | `build_transaction_row(parsed: dict, raw_input: str)` | Build the data structure or message text for transaction row. |
| `def` | `update_transaction_debt_relation(transaction_id: str, debt_ids: list[str], tipe_hutang: str='piutang')` | Update transaction debt relation while keeping related data consistent. |
| `def` | `clear_transaction_debt_relation(transaction_id: str)` | Clear or reset transaction debt relation. |
| `def` | `validate_transaction(parsed: dict)` | Validate data before it is used by the finance service layer. |
| `def` | `get_account_balance(account_name: str)` | Retrieve data needed for account balance. |
| `def` | `update_account_balance(account_name: str, new_balance: float)` | Update account balance while keeping related data consistent. |
| `def` | `get_all_accounts()` | Retrieve data needed for all accounts. |
| `def` | `get_account_index_map()` | Retrieve data needed for account index map. |
| `def` | `validate_accounts_exist(account_deltas: dict)` | Validate data before it is used by the finance service layer. |
| `def` | `calculate_account_deltas(parsed_items: list[dict])` | Calculate derived values for calculate account deltas. |
| `def` | `apply_account_deltas(account_deltas: dict)` | Apply changes for account deltas. |
| `def` | `save_transaction(parsed: dict, raw_input: str)` | Validate and save one transaction, then update related account balances. |
| `def` | `save_transactions_batch(parsed_items: list[dict])` | Save multiple transactions in one batch and apply account balance changes safely. |
| `def` | `get_transactions_by_month(year: int, month: int)` | Retrieve data needed for transactions by month. |
| `def` | `get_transactions_by_date(date_str: str)` | Retrieve data needed for transactions by date. |
| `def` | `get_expense_by_category(year: int, month: int)` | Retrieve data needed for expense by category. |
| `def` | `is_debt_cashflow_transaction(txn: dict)` | Check a boolean condition for is debt cashflow transaction. |
| `def` | `parse_transaction_date(date_value: str)` | Parse input into structured data for the finance service layer. |
| `def` | `sort_transactions_sheet_by_date(desc: bool=True)` | Helper for sort transactions sheet by date in the finance service layer. |
| `def` | `get_transactions_with_row_index()` | Retrieve data needed for transactions with row index. |
| `def` | `get_recent_transactions(limit: int=10, period: str \| None=None, month: str \| None=None)` | Retrieve data needed for recent transactions. |
| `def` | `get_transaction_by_id(txn_id: str)` | Retrieve data needed for transaction by id. |
| `def` | `get_transactions_by_ids(txn_ids: list[str])` | Retrieve data needed for transactions by ids. |
| `def` | `get_transactions_by_row_indices(row_indices: list[int])` | Retrieve data needed for transactions by row indices. |
| `def` | `calculate_reverse_deltas_for_delete(transactions: list[dict])` | Calculate derived values for calculate reverse deltas for delete. |
| `def` | `parse_transaction_debt_ids(txn: dict)` | Parse input into structured data for the finance service layer. |
| `def` | `transaction_has_debt_relation(txn: dict)` | Helper for transaction has debt relation in the finance service layer. |
| `def` | `preview_delete_transactions_by_refs(row_indices: list[int] \| None=None, txn_ids: list[str] \| None=None)` | Helper for preview delete transactions by refs in the finance service layer. |
| `def` | `preview_delete_transactions(txn_ids: list[str])` | Helper for preview delete transactions in the finance service layer. |
| `def` | `delete_transactions_by_ids(txn_ids: list[str])` | Delete transactions by ids with validation for related data. |
| `def` | `delete_transactions_by_refs(row_indices: list[int] \| None=None, txn_ids: list[str] \| None=None)` | Delete transactions by refs with validation for related data. |
| `def` | `normalize_edit_field(field: str)` | Clean and standardize normalize edit field. |
| `def` | `normalize_edit_updates(updates: dict)` | Clean and standardize normalize edit updates. |
| `def` | `get_single_transaction_by_ref(row_index: int \| None=None, txn_id: str \| None=None)` | Retrieve data needed for single transaction by ref. |
| `def` | `build_transaction_row_from_record(txn: dict)` | Build the data structure or message text for transaction row from record. |
| `def` | `calculate_account_effect(txn: dict)` | Calculate derived values for calculate account effect. |
| `def` | `calculate_edit_net_deltas(old_txn: dict, new_txn: dict)` | Calculate derived values for calculate edit net deltas. |
| `def` | `validate_edit_transaction(txn: dict)` | Validate data before it is used by the finance service layer. |
| `def` | `preview_edit_transaction_by_ref(updates: dict, row_index: int \| None=None, txn_id: str \| None=None)` | Helper for preview edit transaction by ref in the finance service layer. |
| `def` | `_payment_allocation_note(raw: str, allocations: list[dict], overpayment: float=0.0, policy: str='')` | Helper for payment allocation note in the finance service layer. |
| `def` | `edit_debt_payment_transaction_amount(preview: dict)` | Helper for edit debt payment transaction amount in the finance service layer. |
| `def` | `edit_transaction_by_ref(updates: dict, row_index: int \| None=None, txn_id: str \| None=None)` | Helper for edit transaction by ref in the finance service layer. |

## `app/sheets/client.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `class` | `SheetsAtomicWriteError` | Raised when a Google Sheets write fails after retry and rollback handling is needed. |
| `class` | `SheetsTransaction` | Best-effort transaction wrapper for Google Sheets operations. |
| `def` | `sheets_transaction(label: str \| None=None)` | Create a best-effort transaction context for multiple Google Sheets writes. |
| `def` | `rollback_current_sheets_transaction()` | Helper for rollback current sheets transaction in the Google Sheets data layer. |
| `def` | `get_current_sheets_transaction()` | Retrieve data needed for current sheets transaction. |
| `def` | `_is_quota_or_transient_error(exc: Exception)` | Check a boolean condition for is quota or transient error. |
| `def` | `_call_with_retry(fn, *, max_retries: int \| None=None)` | Helper for call with retry in the Google Sheets data layer. |
| `def` | `_execute_write(fn)` | Helper for execute write in the Google Sheets data layer. |
| `def` | `_execute_read(fn)` | Helper for execute read in the Google Sheets data layer. |
| `def` | `_get_column_letter(col_number: int)` | Retrieve data needed for column letter. |
| `def` | `_extract_updated_row_index(response)` | Extract the important part of the input for updated row index. |
| `def` | `_extract_updated_row_range(response)` | Extract the important part of the input for updated row range. |
| `def` | `_pad_row(row: list, width: int)` | Helper for pad row in the Google Sheets data layer. |
| `def` | `_clean_header(values: list)` | Clean and standardize clean header. |
| `def` | `_has_data_rows(values: list[list])` | Check a boolean condition for has data rows. |
| `def` | `_is_blank_header(header: list[str])` | Check a boolean condition for is blank header. |
| `def` | `_header_has_expected_prefix(header: list[str], expected_header: list[str])` | Helper for header has expected prefix in the Google Sheets data layer. |
| `def` | `_header_is_safe_prefix(header: list[str], expected_header: list[str])` | Helper for header is safe prefix in the Google Sheets data layer. |
| `def` | `_resize_columns_if_needed(sheet, width: int)` | Helper for resize columns if needed in the Google Sheets data layer. |
| `def` | `_write_header(sheet, header: list[str])` | Helper for write header in the Google Sheets data layer. |
| `def` | `_default_rows_for_sheet(sheet_name: str)` | Helper for default rows for sheet in the Google Sheets data layer. |
| `def` | `_seed_default_rows_if_empty(sheet_name: str, sheet, values: list[list])` | Helper for seed default rows if empty in the Google Sheets data layer. |
| `def` | `_get_or_create_worksheet(spreadsheet, sheet_name: str)` | Retrieve data needed for or create worksheet. |
| `def` | `ensure_sheet_schema(sheet_name: str, sheet=None)` | Ensure one worksheet has the expected header without rewriting existing data unsafely. |
| `def` | `ensure_spreadsheet_schema()` | Ensure all required worksheets exist and have compatible headers. |
| `def` | `get_spreadsheet()` | Retrieve data needed for spreadsheet. |
| `def` | `get_sheet(sheet_name: str)` | Retrieve data needed for sheet. |
| `def` | `append_row(sheet_name: str, row: list)` | Append data or text to row. |
| `def` | `append_row_raw(sheet_name: str, row: list)` | Append data or text to row raw. |
| `def` | `append_rows(sheet_name: str, rows: list[list])` | Append data or text to rows. |
| `def` | `get_all_records(sheet_name: str)` | Retrieve data needed for all records. |
| `def` | `get_all_values(sheet_name: str)` | Retrieve data needed for all values. |
| `def` | `update_cell(sheet_name: str, row: int, col: int, value)` | Update cell while keeping related data consistent. |
| `def` | `find_row_index(sheet_name: str, search_col: int, search_value: str)` | Helper for find row index in the Google Sheets data layer. |
| `def` | `delete_row(sheet_name: str, row_index: int)` | Delete row with validation for related data. |
| `def` | `delete_rows(sheet_name: str, row_indices: list[int])` | Delete rows with validation for related data. |
| `def` | `update_row(sheet_name: str, row_index: int, row_values: list)` | Update row while keeping related data consistent. |
| `def` | `update_range(sheet_name: str, cell_range: str, values: list[list])` | Update range while keeping related data consistent. |

## `main.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `validate_runtime_config(mode: str=BOT_MODE)` | Validate required environment variables for the selected runtime mode. |
| `def` | `ensure_schema_on_startup()` | Prepare Google Sheets tabs and headers during application startup. |
| `def` | `start_scheduler_once()` | Start the scheduler only if it is not already running. |
| `def` | `shutdown_scheduler_once()` | Stop the scheduler safely if it is running. |
| `async def` | `startup()` | FastAPI startup hook used when webhook mode is active. |
| `async def` | `shutdown()` | FastAPI shutdown hook that stops the Telegram app and scheduler safely. |
| `async def` | `health_check()` | Return a simple runtime health status for deployment checks. |
| `async def` | `test_sheets()` | Run a quick Google Sheets connectivity and schema check. |
| `async def` | `run_polling_mode()` | Run the bot using Telegram polling for local usage and simple 24/7 deployment. |
| `def` | `run_webhook_mode()` | Run the FastAPI server for advanced webhook deployment. |

## `scripts/ai_command_tester.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_ensure_test_env()` | Ensure test env is ready before continuing. |
| `class` | `_Dummy` | Dummy object used to replace optional external dependencies during lightweight local tests. |
| `class` | `_DummyBadRequest` | Dummy exception that mimics Telegram BadRequest when the real dependency is unavailable. |
| `def` | `_module_exists(module_name: str)` | Helper for module exists in the utility script. |
| `def` | `_install_optional_import_stubs()` | Helper for install optional import stubs in the utility script. |
| `class` | `AssertionResult` | Result model for one assertion in a command test case. |
| `class` | `CommandRun` | Result model for one simulated command or input run. |
| `def` | `classify_known_route(text: str)` | Helper for classify known route in the utility script. |
| `class` | `CommandTester` | Main runner that loads test cases, executes parser/handler logic, and reports results. |
| `def` | `get_path(data: Any, path: str)` | Retrieve data needed for path. |
| `def` | `compare_value(actual: Any, expected: Any)` | Helper for compare value in the utility script. |
| `def` | `evaluate_expectations(run: CommandRun, expect: dict[str, Any] \| None)` | Helper for evaluate expectations in the utility script. |
| `def` | `_has_split_keyword(text: str)` | Check a boolean condition for has split keyword. |
| `def` | `_split_has_friend_name(text: str)` | Helper for split has friend name in the utility script. |
| `def` | `evaluate_heuristics(run: CommandRun)` | Helper for evaluate heuristics in the utility script. |
| `def` | `case_status(assertions: list[AssertionResult])` | Helper for case status in the utility script. |
| `def` | `deterministic_diagnosis(run: CommandRun, assertions: list[AssertionResult])` | Helper for deterministic diagnosis in the utility script. |
| `def` | `ai_diagnosis(run: CommandRun, assertions: list[AssertionResult])` | Helper for ai diagnosis in the utility script. |
| `def` | `command_run_to_dict(run: CommandRun)` | Helper for command run to dict in the utility script. |
| `def` | `resolve_input_path(path_text: str)` | Resolve the final value for input path from possible inputs. |
| `def` | `load_cases(path: Path)` | Load data for cases. |
| `def` | `load_text_cases(path: Path, *, decision: str \| None=None)` | Load data for text cases. |
| `def` | `default_sample_cases()` | Helper for default sample cases in the utility script. |
| `def` | `write_sample(path: Path)` | Helper for write sample in the utility script. |
| `class` | `CaseResult` | Summary model for one test case result. |
| `def` | `run_one_case(tester: CommandTester, case: dict[str, Any], index: int, *, use_ai: bool)` | Run the one case process. |
| `def` | `print_case_report(result: CaseResult, *, show_json: bool, use_ai: bool)` | Helper for print case report in the utility script. |
| `def` | `make_markdown_report(results: list[CaseResult])` | Helper for make markdown report in the utility script. |
| `def` | `run_cases(cases: list[dict[str, Any]], *, show_json: bool, use_ai: bool, markdown_path: Path \| None=None)` | Run the cases process. |
| `def` | `parse_args()` | Parse input into structured data for the utility script. |
| `def` | `main()` | Helper for main in the utility script. |

## `scripts/debug_check.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `now_str()` | Helper for now str in the utility script. |
| `def` | `rupiah(amount)` | Helper for rupiah in the utility script. |
| `def` | `add_result(area, name, status, expected, actual='', error='')` | Helper for add result in the utility script. |
| `def` | `ok(area, name, expected='OK', actual='OK')` | Helper for ok in the utility script. |
| `def` | `warn(area, name, expected='OK', actual='Warning', error='')` | Helper for warn in the utility script. |
| `def` | `fail(area, name, expected='OK', actual='Failed', error='')` | Helper for fail in the utility script. |
| `def` | `skip(area, name, expected='Available', actual='Skipped', error='')` | Helper for skip in the utility script. |
| `def` | `print_header(title)` | Helper for print header in the utility script. |
| `def` | `print_summary()` | Helper for print summary in the utility script. |
| `def` | `safe_run(area, name, expected, func)` | Helper for safe run in the utility script. |
| `def` | `import_module_safe(module_name, area='Import')` | Helper for import module safe in the utility script. |
| `def` | `has_function(module, func_name, area)` | Check a boolean condition for has function. |
| `def` | `check_environment()` | Helper for check environment in the utility script. |
| `def` | `check_imports()` | Helper for check imports in the utility script. |
| `def` | `check_config(modules)` | Helper for check config in the utility script. |
| `def` | `check_google_sheets(modules)` | Helper for check google sheets in the utility script. |
| `def` | `check_nlp(modules)` | Helper for check nlp in the utility script. |
| `def` | `check_transaction_service(modules)` | Helper for check transaction service in the utility script. |
| `def` | `check_report_service(modules)` | Helper for check report service in the utility script. |
| `def` | `check_budget_service(modules)` | Helper for check budget service in the utility script. |
| `def` | `check_debt_service(modules)` | Helper for check debt service in the utility script. |
| `def` | `check_recurring_service(modules)` | Helper for check recurring service in the utility script. |
| `def` | `check_net_worth_service(modules)` | Helper for check net worth service in the utility script. |
| `def` | `check_bot_handlers(modules)` | Helper for check bot handlers in the utility script. |
| `def` | `check_scheduler(modules)` | Helper for check scheduler in the utility script. |
| `def` | `check_regression_commands(modules)` | Helper for check regression commands in the utility script. |
| `def` | `main()` | Helper for main in the utility script. |

## `scripts/setup_check.py`

| Type | Name / Signature | Purpose |
|---|---|---|
| `def` | `_add(status: str, title: str, detail: str='')` | Helper for add in the utility script. |
| `def` | `ok(title: str, detail: str='')` | Helper for ok in the utility script. |
| `def` | `warn(title: str, detail: str='')` | Helper for warn in the utility script. |
| `def` | `fail(title: str, detail: str='')` | Helper for fail in the utility script. |
| `def` | `skip(title: str, detail: str='')` | Helper for skip in the utility script. |
| `def` | `mask(value: str)` | Helper for mask in the utility script. |
| `def` | `env(name: str, default: str='')` | Helper for env in the utility script. |
| `def` | `check_env_file()` | Helper for check env file in the utility script. |
| `def` | `check_runtime_env()` | Helper for check runtime env in the utility script. |
| `def` | `check_service_account_file()` | Helper for check service account file in the utility script. |
| `def` | `check_imports()` | Helper for check imports in the utility script. |
| `def` | `check_google_sheets_schema(can_try: bool)` | Helper for check google sheets schema in the utility script. |
| `def` | `print_summary()` | Helper for print summary in the utility script. |
| `def` | `main()` | Helper for main in the utility script. |
