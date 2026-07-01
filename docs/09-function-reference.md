# 09. Function Reference

Dokumen ini adalah indeks fungsi dan class top-level per file. Gunakan sebagai peta cepat untuk mencari lokasi logic. Detail perilaku tetap perlu dibaca di file sumber.

## `app/api/webhook.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `set_telegram_app(app: Application)` | - |
| `async def` | `webhook(request: Request, x_telegram_bot_api_secret_token: str=Header(None))` | - |

## `app/bot/application.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `atomic_bot_handler(callback)` | Run each Telegram handler inside one Sheets all-or-nothing operation. |
| `def` | `register_handlers(telegram_app: Application)` | Register all command, message, and callback handlers on an app. |
| `async def` | `scheduled_data_export(context)` | - |
| `def` | `register_job_queue_jobs(telegram_app: Application)` | Register jobs owned by python-telegram-bot JobQueue. |
| `def` | `build_telegram_app()` | Build one fully registered Telegram Application instance. |

## `app/bot/handler_parts/callback_handler.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `is_skip_account_choice(account: str)` | - |
| `def` | `mark_transaction_as_historical(parsed: dict)` | Catat transaksi tanpa mengubah saldo rekening. |
| `def` | `mark_debt_as_historical(debt_parsed: dict)` | Catat debt tanpa membuat cashflow transaksi. |
| `def` | `_split_debt_id_text(value)` | - |
| `def` | `_merge_debt_ids(*values)` | - |
| `def` | `create_fronted_split_receivable_debts(debt_parsed: dict)` | Untuk kasus PTPT: user ditalangin full oleh seseorang, tetapi itemnya |
| `def` | `attach_fronted_split_debt_relations(debt_parsed: dict, debt_result: dict, split_result: dict)` | - |
| `def` | `append_fronted_split_result_lines(lines: list[str], split_result: dict, *, indent: str='')` | - |
| `def` | `build_edit_txn_preview_text_for_callback(preview: dict, split_parsed: dict \| None=None)` | Preview edit transaksi untuk flow split bill di callback_handler. |
| `def` | `parse_debt_ids_from_txn_record_for_edit(txn: dict)` | - |
| `def` | `overpayment_decision_keyboard()` | - |
| `def` | `build_overpayment_decision_text(parsed: dict, outcome: dict)` | - |
| `def` | `resolve_payment_target_type(parsed: dict, debts: list[dict])` | Tentukan arah debt untuk pembayaran by person tanpa memblokir mixed arah. |
| `def` | `clear_parse_clarification_state(context: ContextTypes.DEFAULT_TYPE)` | - |
| `def` | `infer_clarified_payment_target_type(raw: str)` | - |
| `def` | `build_clarified_debt_payment(raw: str, parsed: dict \| None=None)` | - |
| `def` | `build_expense_candidate_raw(raw: str)` | - |
| `def` | `build_clarified_expense(raw: str, parsed: dict \| None=None)` | - |
| `def` | `build_clarified_fronting(raw: str, parsed: dict \| None=None)` | - |
| `async def` | `callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |

## `app/bot/handler_parts/command_handlers.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `async def` | `start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `def` | `add_session_chat_history(context: ContextTypes.DEFAULT_TYPE, role: str, text: str, limit: int=10)` | Simpan riwayat tanya-jawab finance di session Telegram user. |
| `def` | `get_session_chat_history(context: ContextTypes.DEFAULT_TYPE, limit: int=8)` | Ambil beberapa pesan terakhir untuk membantu /ask memahami konteks lanjutan. |
| `def` | `attach_session_history(context: ContextTypes.DEFAULT_TYPE, context_data: dict)` | Tambahkan chat history session ke context JSON yang dikirim ke Gemini. |
| `async def` | `send_finance_insight_reply(update: Update, mode: str, context_data: dict, question: str='', prefix: str='🤖 Insight Gemini', context: ContextTypes.DEFAULT_TYPE \| None=None, remember_history: bool=False)` | - |
| `async def` | `examples_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `insight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /insight [YYYY-MM] — monthly narrative report. |
| `async def` | `audit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /audit [YYYY-MM] — cek data quality dan anomali. |
| `async def` | `ask_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /ask <pertanyaan> — tanya jawab finansial natural. |
| `async def` | `coach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /coach [pertanyaan] — financial coach ringan. |
| `async def` | `handle_natural_finance_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Handle pertanyaan finance natural tanpa command, read-only. |
| `def` | `format_report_delta(delta_info: dict, *, positive_when_up: bool, as_count: bool=False)` | Format delta vs periode sebelumnya dengan indikator hijau/merah berbasis emoji. |
| `def` | `append_report_comparison_lines(lines: list[str], report: dict, label: str)` | - |
| `def` | `get_report_expense_display(report: dict)` | Format total expense report sebagai Net (Gross) jika ada piutang aktif. |
| `def` | `append_report_metric_lines(lines: list[str], report: dict)` | Tambahkan metrik ringkasan; jika filter rekening aktif, transfer dihitung masuk/keluar. |
| `def` | `append_account_report_lines(lines: list[str], report: dict)` | - |
| `def` | `append_recent_account_transaction_lines(lines: list[str], report: dict, limit: int=8)` | - |
| `def` | `append_report_category_breakdown_lines(lines: list[str], report: dict, comparison_label: str)` | - |
| `def` | `build_top_expense_debt_lines(txn: dict, amount: float)` | Compatibility wrapper. Detail debt sekarang diformat oleh build_transaction_display_lines. |
| `def` | `is_category_detail_report(report: dict)` | - |
| `def` | `get_category_list_title(category: str)` | - |
| `def` | `append_category_detail_summary(lines: list[str], report: dict, comparison_label: str)` | - |
| `def` | `append_category_transaction_lines(lines: list[str], report: dict, *, include_date: bool)` | - |
| `async def` | `saldo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `rekening_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /rekening |
| `async def` | `harian_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `mingguan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `bulanan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `cari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `def` | `format_budget_net_gross(net_amount: float, gross_amount: float)` | Format budget realisasi sebagai Bersih (Gross). |
| `async def` | `budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /budget |
| `async def` | `budget_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /budget_history |
| `def` | `build_pending_expense_lines(items: list[dict], title: str, total: float \| None=None)` | - |
| `async def` | `pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /pending [YYYY-MM\|bulan ini\|bulan lalu\|bulan depan\|all\|tanpa tanggal] |
| `async def` | `pending_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /pending_add bayar wifi 285k tgl 30 dari BRI |
| `async def` | `pending_paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /pending_paid pending_id [rekening] |
| `async def` | `pending_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /pending_cancel pending_id |
| `def` | `parse_amount_text(value: str)` | - |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | Ambil nominal asli dari input split bill. |
| `async def` | `set_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Input bebas: |
| `def` | `short_debt_id(debt_id: str)` | - |
| `def` | `parse_debt_void_args(args: list[str])` | Parsing argumen /debt_void yang lebih ramah user. |
| `def` | `build_debt_void_preview_text(preview: dict)` | - |
| `async def` | `debt_void_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /debt_void <nomor\|debt_id\|nama\|nama nomor> |
| `def` | `normalize_debt_edit_type(value: str)` | - |
| `def` | `parse_debt_edit_args(args: list[str])` | - |
| `def` | `build_debt_edit_result_text(result: dict)` | - |
| `async def` | `debt_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /debt_edit <nomor_dari_hutang_atau_debt_id> <field> <value> |
| `def` | `format_debt_created_date_for_display(debt: dict)` | Ambil tanggal dibuat debt/piutang untuk grouping /hutang <nama>. |
| `def` | `debt_detail_sort_key_for_display(debt: dict)` | Urutkan detail /hutang <nama> dari terbaru ke terlama. |
| `def` | `parse_debt_number_selection(selection: str)` | Parse nomor debt dari detail /hutang <nama>. Support: 1-17, 1 2 3, 1,3,5. |
| `def` | `parse_debt_settle_command_args(args: list[str])` | Parse /debt_settle Raka 1-17 amount=337063 account=DANA. |
| `def` | `parse_natural_debt_settle_text(text: str)` | Parse natural: Raka bayar hutang 337063 untuk debt 1-17. |
| `def` | `resolve_selected_debts_from_last_detail(context: ContextTypes.DEFAULT_TYPE, person_name: str, numbers: list[str])` | Pastikan nomor berasal dari hasil terakhir /hutang <person>. |
| `def` | `build_selected_debt_total_text(payload: dict)` | - |
| `def` | `build_selected_debt_settle_preview_text(payload: dict)` | - |
| `def` | `build_selected_settle_catatan(payload: dict, result: dict)` | - |
| `def` | `prepare_selected_debt_settle_payload(context: ContextTypes.DEFAULT_TYPE, parsed: dict)` | - |
| `def` | `selected_debt_settle_overpay_keyboard()` | - |
| `async def` | `debt_settle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `handle_natural_debt_settle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str)` | - |
| `def` | `build_selected_debt_settle_transaction(payload: dict, result: dict)` | - |
| `def` | `_collect_known_debt_person_names()` | Ambil daftar nama orang dari ringkasan debt untuk membersihkan item lama. |
| `def` | `_strip_trailing_known_names_for_summary(text: str, known_names: list[str])` | - |
| `def` | `_clean_debt_description_for_share(desc: str, person: str, known_names: list[str] \| None=None)` | Bersihkan deskripsi debt agar layak dikirim ke teman. |
| `def` | `_format_shareable_date_heading(date_value)` | - |
| `def` | `_group_debts_for_shareable_summary(debts: list[dict], person: str, known_names: list[str])` | - |
| `def` | `build_shareable_debt_summary_text(person_query: str)` | - |
| `async def` | `ringkasan_hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `hutang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |

## `app/bot/handler_parts/command_router.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `build_gemini_low_confidence_text(router_result: dict)` | - |
| `def` | `build_gemini_fallback_text()` | - |
| `def` | `router_args_to_last_filter(args: dict)` | Convert args Gemini ke parameter get_recent_transactions. |
| `def` | `extract_edit_updates_from_router(args: dict)` | - |
| `def` | `format_rupiah(amount: float)` | - |
| `def` | `md_safe(value)` | Escape teks dinamis agar aman untuk Telegram parse_mode='Markdown'. |
| `def` | `clean_command_token(command_text: str)` | Bersihkan command/token user. |
| `def` | `command_description(command_name: str)` | - |
| `def` | `is_destructive_command(command_name: str)` | - |
| `def` | `similarity_score(a: str, b: str)` | - |
| `def` | `get_similarity_candidates(clean_command: str)` | Hitung similarity terhadap command resmi saja. |
| `def` | `resolve_command_local(command_text: str)` | Resolver command lokal yang deterministic. |
| `def` | `build_command_suggestion_text(resolved: dict, original_text: str)` | Bangun response untuk command typo / unknown command. |
| `def` | `maybe_text_is_command_typo(text: str)` | Deteksi typo command pada input tanpa slash. |
| `async def` | `unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle slash command yang tidak dikenali. |
| `def` | `short_txn_id(txn_id: str)` | - |
| `def` | `expand_txn_refs(refs: list[str])` | Expand argumen transaksi. |
| `def` | `resolve_txn_refs_from_last(context: ContextTypes.DEFAULT_TYPE, refs: list[str])` | Resolve argumen /delete_txn. |
| `def` | `build_last_transactions_text(transactions: list[dict], title: str)` | - |
| `def` | `build_delete_preview_text(preview: dict)` | - |
| `def` | `is_authorized(update: Update)` | - |
| `async def` | `reject_unauthorized(update: Update)` | - |

## `app/bot/handler_parts/common_imports.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `format_rupiah(amount: float)` | Format rupiah, termasuk nominal pecahan dari split bill. |
| `def` | `short_debt_id(debt_id: str)` | - |
| `def` | `md_safe(value)` | - |
| `def` | `md_code_text(value)` | Text aman untuk ditaruh di dalam inline code Markdown Telegram. |
| `def` | `short_txn_id(txn_id: str)` | - |
| `def` | `format_indonesian_date_group_label(date_value)` | Format heading grup tanggal: 🗓️ Senin, 30 Juni 2026:. |
| `def` | `_safe_float_for_display(value, default: float=0.0)` | - |
| `def` | `get_transaction_receivable_parts(txn: dict)` | Ambil rincian piutang aktif per orang dari transaksi enriched. |
| `def` | `get_transaction_payable_parts(txn: dict)` | Ambil rincian utang aktif per orang dari transaksi enriched. |
| `def` | `get_net_expense_after_receivable(txn: dict)` | Gross expense dikurangi piutang split bill terkait. |
| `def` | `build_debt_parts_text(parts: list[dict])` | Format: Rp8.000 (Raka), Rp8.000 (Bagas). |
| `def` | `has_expense_transactions(transactions: list[dict] \| None)` | Cek apakah daftar transaksi memiliki minimal satu expense. |
| `def` | `has_net_gross_difference(transactions: list[dict] \| None)` | Cek apakah ada expense yang net-nya berbeda dari gross karena piutang aktif. |
| `def` | `append_net_gross_note(lines: list[str], transactions: list[dict] \| None=None, *, force: bool=False)` | Tambahkan catatan Net (Gross) di awal output yang menampilkan nominal expense. |
| `def` | `format_expense_net_gross(net_amount: float, gross_amount: float, *, always_show_gross: bool=False)` | Format nominal expense: Net (Gross). |
| `def` | `get_transaction_account_text(txn: dict)` | - |
| `def` | `build_transaction_display_lines(txn: dict, *, index: int \| None=None, include_date: bool=True, include_id: bool=False, contribution_pct: float \| None=None, note: str \| None=None)` | Renderer transaksi ringkas yang konsisten untuk report, rekening, dan list transaksi. |
| `def` | `build_transactions_full_text_shared(transactions: list[dict], title: str, account_filter: str \| None=None, *, current_balance: float \| None=None)` | Render daftar transaksi lengkap + ringkasan periode. |
| `def` | `is_authorized(update: Update)` | - |
| `async def` | `reject_unauthorized(update: Update)` | - |
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | - |
| `async def` | `reply_long_markdown(update: Update, text: str)` | - |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | - |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | - |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | - |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | - |
| `def` | `build_progress_bar(pct: float, length: int=10)` | - |
| `def` | `_parse_human_amount_atom(value: str \| None)` | - |
| `def` | `_safe_eval_amount_expression(expr: str)` | - |
| `def` | `parse_human_amount(value: str \| None)` | - |
| `def` | `parse_amount_text(value: str)` | - |
| `def` | `extract_split_bill_total_amount(raw_text: str)` | - |

## `app/bot/handler_parts/core.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `split_long_message(text: str, max_len: int=TELEGRAM_SAFE_MESSAGE_LIMIT)` | Split pesan panjang Telegram menjadi beberapa bagian aman. |
| `async def` | `reply_long_markdown(update: Update, text: str)` | Kirim Markdown panjang dengan fallback plain text kalau Markdown error. |
| `async def` | `reply_message_safely(message, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Kirim pesan biasa secara aman, termasuk pesan panjang dan Markdown error. |
| `async def` | `reply_update_safely(update: Update, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | - |
| `async def` | `safe_edit_message(query, text: str, parse_mode: str \| None=None, reply_markup=None, **kwargs)` | Edit pesan callback secara aman. |
| `async def` | `show_callback_loading(query, text: str='⏳ *Memproses pilihan...*')` | Tampilkan loading singkat dan hapus inline keyboard agar tombol tidak double-click. |
| `async def` | `error_handler(update: object, context: ContextTypes.DEFAULT_TYPE)` | Error handler global agar exception callback tetap diberi tahu ke Telegram. |

## `app/bot/handler_parts/health_recurring_export.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `health_status_icon(ok: bool)` | - |
| `def` | `health_warn_icon(ok: bool)` | - |
| `def` | `safe_health_check(label: str, check_func)` | Jalankan satu health check dengan aman. |
| `def` | `check_google_sheets_connection()` | - |
| `def` | `check_sheet_readable(sheet_name: str)` | - |
| `def` | `check_wispybite()` | - |
| `def` | `check_wispybite_port()` | - |
| `def` | `check_gemini_config()` | - |
| `def` | `check_environment_config()` | - |
| `def` | `build_health_report_text(results: list[dict])` | - |
| `async def` | `health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /health — cek status komponen utama bot. |
| `def` | `parse_recurring_add_args(args: list[str])` | Format: |
| `def` | `parse_recurring_edit_args(args: list[str])` | Format: |
| `def` | `build_recurring_edit_result_text(result: dict)` | - |
| `async def` | `recurring_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /recurring_edit <rule_id> \| field=value \| field=value |
| `def` | `short_rule_id(rule_id: str)` | - |
| `def` | `build_recurring_rules_text(rules: list[dict])` | - |
| `def` | `build_recurring_run_text(result: dict)` | - |
| `async def` | `recurring_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /recurring — list recurring rules |
| `async def` | `recurring_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /recurring_add Nama \| type \| amount \| category \| account \| monthly \| day \| description |
| `async def` | `recurring_run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /recurring_run — jalankan recurring yang jatuh tempo secara manual |
| `async def` | `recurring_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /recurring_off <rule_id> |
| `def` | `write_transactions_to_csv(records: list[dict], file_path: str)` | Tulis records transaksi ke file CSV. |
| `def` | `build_export_caption(export_result: dict)` | - |
| `async def` | `export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /download_data |
| `async def` | `scheduled_export_transactions(bot, chat_id: int, period=None)` | Auto export transaksi untuk scheduler. |

## `app/bot/handler_parts/message_handlers.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `async def` | `send_parse_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE, raw: str, parsed: dict \| None, assessment: dict)` | Kirim prompt klarifikasi tanpa menyimpan apa pun. |
| `def` | `try_gemini_draft_for_parse_safety(raw: str, fallback_parsed: dict, assessment: dict)` | Ambil draft Gemini untuk non-sensitive review. Kalau gagal, tetap pakai regex + warning. |
| `async def` | `debt_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle input debt dari pesan bebas. |
| `async def` | `handle_gemini_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Jalankan hasil Gemini intent router. |
| `def` | `normalize_text_command(text: str)` | - |
| `async def` | `handle_local_natural_intent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Handle natural command sederhana secara lokal tanpa Gemini. |
| `async def` | `image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | Handle foto struk/nota/screenshot transaksi. |
| `async def` | `message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | - |
| `def` | `build_transactions_full_text(transactions: list[dict], title: str, account_filter: str \| None=None)` | - |
| `def` | `build_transaction_filter_title(base_title: str, category_filter: str \| None=None, account_filter: str \| None=None)` | - |
| `def` | `_build_transaksi_prefixed_period_arg(first: str, rest: str, mode: str)` | Bangun argumen periode+filter untuk /transaksi dengan prefix hari/minggu/bulan. |
| `def` | `parse_transaksi_period(args: list[str])` | Parse command /transaksi untuk full list hari/minggu/bulan/rekening tertentu. |
| `async def` | `transaksi_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | List transaksi full untuk hari/minggu/bulan tertentu. |
| `async def` | `last_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /last |
| `async def` | `delete_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /delete_txn 1 |
| `def` | `parse_edit_updates(args: list[str])` | Parse argumen edit. |
| `def` | `edit_args_contain_split_bill(args: list[str])` | - |
| `def` | `_normalize_edit_arg_token(token: str)` | - |
| `def` | `parse_edit_debt_payment_conversion_args(args: list[str])` | Parse /edit_txn untuk mengubah transaksi biasa menjadi pembayaran debt. |
| `def` | `build_debt_payment_conversion_updates(conversion: dict, old_txn: dict \| None=None)` | - |
| `def` | `validate_edit_debt_payment_conversion(conversion: dict, amount: float)` | - |
| `def` | `build_edit_debt_payment_preview_text(preview: dict, conversion: dict, debt_check: dict)` | - |
| `def` | `build_edit_split_preview_text(preview: dict, split_parsed: dict \| None=None)` | - |
| `def` | `build_edit_preview_text(preview: dict)` | - |
| `def` | `extract_bulk_edit_txn_lines(raw_text: str)` | Ambil baris /edit_txn dari pesan multi-line. |
| `def` | `_format_bulk_edit_value(value)` | - |
| `def` | `build_bulk_edit_preview_text(entries: list[dict])` | - |
| `def` | `build_bulk_edit_error_text(errors: list[str])` | - |
| `def` | `parse_bulk_edit_txn_entries(lines: list[str], context: ContextTypes.DEFAULT_TYPE)` | - |
| `async def` | `bulk_edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, lines: list[str])` | - |
| `async def` | `edit_txn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /edit_txn 2 amount=15000 |

## `app/bot/handler_parts/networth_assets.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `parse_asset_quantity_input(value: str)` | Deteksi input aset berbasis satuan: |
| `def` | `_parse_human_amount_atom(value: str \| None)` | Parse satu token nominal: 2410000, 2.41jt, 2,41 juta, 91.457k. |
| `def` | `_safe_eval_amount_expression(expr: str)` | Evaluasi ekspresi nominal sederhana seperti 94k/2 atau 37.5k x 3. |
| `def` | `parse_human_amount(value: str \| None)` | Parse angka manusia, termasuk ekspresi edit seperti `94k/2`. |
| `def` | `parse_asset_extra_fields(extra_parts: list[str])` | Parse optional asset add fields after description. |
| `def` | `format_asset_gain_lines(asset: dict, indent: str='   ')` | - |
| `def` | `guess_asset_category_and_name(name: str, category: str \| None=None)` | - |
| `def` | `build_asset_unit_price_prompt(data: dict)` | - |
| `def` | `parse_pipe_add_args(args: list[str], item_type: str)` | Format: |
| `def` | `parse_natural_asset_add(text: str)` | Natural asset input sederhana: |
| `def` | `parse_pipe_update_args(args: list[str], command_name: str)` | Format: |
| `def` | `short_networth_id(record_id: str)` | - |
| `def` | `build_networth_text(summary: dict)` | - |
| `def` | `build_assets_text(assets: list[dict])` | - |
| `def` | `build_liabilities_text(liabilities: list[dict])` | - |
| `def` | `build_update_result_text(result: dict, label: str)` | - |
| `def` | `build_snapshots_text(snapshots: list[dict])` | - |
| `async def` | `networth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /networth — lihat net worth summary |
| `async def` | `assets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /assets — lihat daftar aset aktif |
| `async def` | `liabilities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /liabilities — lihat daftar liabilitas aktif |
| `def` | `build_asset_added_text(asset: dict)` | - |
| `def` | `asset_edit_or_continue_keyboard()` | Keyboard preview aset tanpa import transaction_flow agar tidak circular. |
| `def` | `build_asset_confirm_preview(data: dict)` | Preview tambah aset sebelum disimpan. |
| `def` | `_asset_flow_is_skip(text: str)` | - |
| `def` | `_asset_flow_is_cancel(text: str)` | - |
| `def` | `_asset_flow_prompt(step: str, data: dict \| None=None)` | - |
| `def` | `start_asset_add_flow(context: ContextTypes.DEFAULT_TYPE)` | - |
| `def` | `_build_asset_data_from_flow(data: dict)` | - |
| `async def` | `handle_pending_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | - |
| `async def` | `asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /asset_add Nama \| nominal \| kategori \| deskripsi |
| `async def` | `liability_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /liability_add Nama \| nominal \| kategori \| deskripsi |
| `async def` | `asset_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /asset_update asset_id \| value=9000000 \| category=Electronics |
| `async def` | `liability_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /liability_update liab_id \| balance=1000000 |
| `async def` | `asset_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /asset_off asset_id |
| `async def` | `liability_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /liability_off liab_id |
| `async def` | `networth_snapshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /networth_snapshot — simpan snapshot net worth hari ini |
| `async def` | `networth_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE)` | /networth_history — lihat snapshot terakhir |

## `app/bot/handler_parts/transaction_flow.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `parse_input(text: str)` | Coba regex dulu, fallback ke Gemini. |
| `def` | `build_progress_bar(pct: float, length: int=10)` | Buat progress bar teks. Contoh: [████░░░░░░] 40% |
| `def` | `split_user_inputs(text: str)` | Pecah input user menjadi beberapa item. |
| `def` | `needs_account(parsed: dict)` | Transaksi expense/income wajib punya account. |
| `def` | `is_debt_item(parsed: dict)` | - |
| `def` | `is_transaction_item(parsed: dict)` | - |
| `def` | `build_mixed_preview(mixed_items: list[dict])` | Preview untuk campuran transaksi biasa + debt. |
| `def` | `parse_income_missing_amount(line: str)` | Deteksi income masuk dari orang yang belum punya nominal. |
| `def` | `build_missing_amount_prompt(raw: str, parsed: dict, current: int \| None=None, total: int \| None=None)` | - |
| `def` | `finalize_missing_amount_item(item: dict, amount: float)` | - |
| `async def` | `continue_after_missing_amount_mixed(update: Update, context: ContextTypes.DEFAULT_TYPE, mixed_items: list[dict])` | - |
| `async def` | `handle_pending_missing_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | - |
| `def` | `parse_mixed_item(line: str)` | Parse satu item sebagai debt dulu, lalu transaksi biasa. |
| `def` | `mixed_needs_account(mixed_items: list[dict])` | - |
| `def` | `edit_or_continue_keyboard(scope: str)` | Keyboard setelah preview: edit dulu atau lanjut ke rekening/simpan. |
| `def` | `build_parse_safety_notice(assessment: dict, mode: str='warning')` | Header warning/AI review untuk ditempel di atas preview existing. |
| `def` | `build_preview_with_parse_safety(parsed: dict, assessment: dict, mode: str='warning')` | - |
| `def` | `build_pending_expense_confirm_preview(item: dict, include_question: bool=True)` | Preview pending expense sebelum user lanjut ke confirm save. |
| `def` | `parse_clarification_keyboard()` | - |
| `def` | `build_parse_clarification_prompt(raw: str, assessment: dict \| None=None)` | - |
| `def` | `parse_participant_count(value: str)` | - |
| `def` | `build_account_delta_summary_from_transaction_items(items: list[dict])` | Ringkasan dampak saldo per rekening dari item transaksi yang sudah punya account. |
| `def` | `build_mixed_short_summary(mixed_items: list[dict])` | Ringkasan pendek untuk transisi setelah preview panjang sudah pernah ditampilkan. |
| `def` | `build_single_short_summary(parsed: dict)` | Ringkasan pendek untuk single transaction setelah preview awal sudah tampil. |
| `def` | `build_updated_item_summary(item: dict, index: int \| None=None)` | Ringkasan pendek item yang baru diedit. |
| `def` | `build_preview_edit_help(scope: str='single')` | - |
| `def` | `build_mixed_edit_choose_prompt(mixed_items: list[dict])` | - |
| `def` | `parse_preview_edit_updates(text: str)` | Parse update sederhana untuk preview sebelum simpan. |
| `def` | `apply_preview_edit_updates_to_parsed(parsed: dict, updates: dict)` | - |
| `async def` | `proceed_after_preview_edit(query, context: ContextTypes.DEFAULT_TYPE, scope: str)` | Lanjutkan flow setelah user memilih 'Lanjut'. |
| `async def` | `handle_pending_preview_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str)` | Handle balasan user untuk edit preview sebelum pilih rekening/simpan. |
| `def` | `format_split_bill_preview_line(parsed: dict)` | - |
| `def` | `build_preview(parsed: dict)` | Buat teks preview transaksi sebelum disimpan. |
| `def` | `build_batch_preview(parsed_items: list[dict])` | Buat preview untuk banyak transaksi sekaligus. |
| `def` | `strip_split_bill_phrase(text: str)` | - |
| `def` | `strip_trailing_split_person_names(text: str, person_names: list[str])` | Buang rangkaian nama teman split bill yang bocor di akhir deskripsi/subject. |
| `def` | `split_split_bill_person_names(name_text: str)` | Ambil daftar nama teman dari frasa split bill. |
| `def` | `strip_split_bill_name_tail(name_text: str)` | Potong bagian setelah nama teman, misalnya tanggal/status pembayaran. |
| `def` | `is_split_bill_allocation_token(value: str)` | - |
| `def` | `parse_split_bill_share_value(value: str, base_share: float)` | Parse nilai share teman: 100%, 80%, 125k, 100000, dst. |
| `def` | `parse_split_bill_people_and_shares(name_text: str, total_amount: float, participants: int)` | Parse nama teman split bill plus custom share opsional. |
| `def` | `format_split_bill_person_shares(split_bill: dict)` | - |
| `def` | `clean_split_person_name(name: str)` | - |
| `def` | `build_split_bill_item_description_from_raw(raw: str, fallback: str='')` | Ambil nama item split bill dari raw input, bukan dari sisa parser. |
| `def` | `detect_split_bill(parsed: dict, raw: str)` | Deteksi input split bill sederhana. |
| `def` | `attach_split_bill_if_any(parsed: dict, raw: str)` | - |
| `def` | `split_bill_needs_decision(parsed: dict)` | - |
| `def` | `mixed_split_bill_needs_decision(mixed_items: list[dict])` | - |
| `def` | `split_bill_keyboard(scope: str='single', item_index: int \| None=None)` | Keyboard keputusan split bill. |
| `def` | `mixed_split_bill_keyboard(mixed_items: list[dict])` | Keyboard split bill mixed dengan index item aktif di callback_data. |
| `def` | `build_split_bill_prompt_from_parsed(parsed: dict)` | - |
| `def` | `build_mixed_split_bill_prompt(mixed_items: list[dict])` | - |
| `def` | `get_mixed_split_bill_indexes(mixed_items: list[dict])` | Return index item transaksi mixed yang memiliki split bill. |
| `def` | `get_next_mixed_split_bill_index(mixed_items: list[dict])` | Return index split bill pertama yang belum dipilih paid/unpaid. |
| `def` | `build_mixed_split_bill_queue_prompt(mixed_items: list[dict])` | Prompt split bill untuk bulk input, tapi ditanya satu-per-satu. |
| `def` | `apply_split_bill_decision_to_current_mixed(mixed_items: list[dict], status: str)` | Terapkan paid/unpaid hanya ke split bill mixed yang sedang aktif. |
| `def` | `apply_split_bill_decision_to_mixed_index(mixed_items: list[dict], item_index: int, status: str)` | Terapkan paid/unpaid ke index split bill tertentu. |
| `def` | `apply_split_bill_decision_to_parsed(parsed: dict, status: str)` | Terapkan keputusan split bill ke transaksi. |
| `def` | `apply_split_bill_decision_to_mixed(mixed_items: list[dict], status: str)` | - |
| `def` | `create_split_bill_debt(parsed: dict, raw: str='', source_transaction_id: str='')` | - |
| `def` | `format_split_debt_result_lines(debt_result: dict)` | Format hasil create_split_bill_debt untuk output Telegram. |
| `def` | `summarize_saved_transaction_items(items: list[dict])` | - |
| `def` | `append_saved_summary_lines(lines: list[str], items: list[dict], title: str='Ringkasan tersimpan')` | - |
| `def` | `_clean_fronting_item_text(text: str, person: str='')` | Bersihkan nama item ditalangin dari nominal, nama penalang, dan frasa split. |
| `def` | `_fronting_expense_description(debt_parsed: dict)` | Ambil nama item untuk ditalangin agar report tidak tampil sebagai label debt. |
| `def` | `_fronting_expense_category(debt_parsed: dict)` | Infer kategori expense untuk ditalangin dari raw input bila memungkinkan. |
| `def` | `is_ditalangin_expense_without_balance(debt_parsed: dict)` | Ditalangin = expense sudah terjadi, tapi saldo rekening user belum berubah. |
| `def` | `normalize_slash_split_syntax(raw: str)` | Ubah shorthand 46k/4 menjadi 46k dibagi 4 agar parser split bill lama bisa menangkapnya. |
| `def` | `enrich_ditalangin_split_bill_if_any(debt_parsed: dict, raw: str \| None=None)` | Support kasus PTPT: user ditalangin orang lain, tetapi itemnya tetap |
| `def` | `_debt_payment_catatan(debt_parsed: dict, raw: str)` | - |
| `def` | `build_debt_cashflow_transaction(debt_parsed: dict, account: str, debt_type_for_payment: str \| None=None)` | Ubah aktivitas utang/piutang menjadi transaksi cashflow/fact table. |
| `def` | `debt_uses_cashflow(debt_parsed: dict)` | Return True kalau aktivitas debt perlu dicatat juga sebagai cashflow. |
| `def` | `build_debt_only_confirm_preview(debt_parsed: dict)` | Preview untuk debt tanpa update saldo rekening. |
| `def` | `build_debt_initial_preview(debt_parsed: dict)` | Preview awal debt sebelum user lanjut ke pilih rekening/konfirmasi. |
| `def` | `build_debt_short_summary(debt_parsed: dict)` | Ringkasan pendek debt untuk transisi setelah edit/preview. |
| `def` | `build_debt_account_prompt(debt_parsed: dict)` | Preview debt sebelum memilih rekening. |
| `def` | `build_debt_confirm_preview(debt_parsed: dict, account: str, debt_type_for_payment: str \| None=None)` | Preview debt setelah rekening dipilih, sebelum disimpan. |
| `def` | `build_debt_batch_confirm_preview(debt_items: list[dict], account: str)` | Preview batch debt setelah rekening dipilih, sebelum disimpan. |
| `def` | `build_debt_batch_account_prompt(debt_items: list[dict])` | Preview batch debt sebelum memilih rekening. |

## `app/bot/keyboards.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `account_keyboard(prefix: str='acc', include_skip: bool=True)` | Keyboard pilihan rekening. |
| `def` | `confirm_keyboard(txn_id: str)` | Keyboard konfirmasi setelah transaksi ditampilkan. |
| `def` | `cancel_keyboard()` | Keyboard batalkan saja. |

## `app/config.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `_parse_int_env(name: str, default: int \| None=None)` | - |

## `app/nlp/gemini_finance_insight.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `_json_dumps(data: dict)` | - |
| `def` | `build_finance_insight_prompt(mode: str, context: dict, question: str='')` | - |
| `def` | `generate_finance_insight(mode: str, context: dict, question: str='')` | Generate insight text. Falls back to deterministic text if Gemini fails. |

## `app/nlp/gemini_image_parser.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `clean_gemini_json(raw_text: str)` | - |
| `def` | `build_image_prompt(caption: str='')` | - |
| `def` | `normalize_item(item: dict)` | - |
| `def` | `parse_transactions_from_image(image_bytes: bytes, mime_type: str='image/jpeg', caption: str='')` | Parse foto struk/nota/screenshot transaksi menjadi item transaksi bot. |

## `app/nlp/gemini_intent_router.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `should_try_gemini_intent_router(text: str)` | Rule trigger Gemini intent router. |
| `def` | `extract_json_object(text: str)` | Ambil JSON object dari response Gemini. |
| `def` | `normalize_router_result(data: dict)` | Normalisasi output Gemini supaya selalu punya struktur aman. |
| `def` | `route_intent_with_gemini(user_text: str)` | Gemini natural-language intent router. |

## `app/nlp/gemini_langchain_client.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `_require_api_key()` | - |
| `def` | `get_gemini_llm(model_name: str, temperature: float=0.0)` | Centralized LangChain Gemini client. |
| `def` | `_extract_text(response: Any)` | Ambil text dari AIMessage LangChain secara aman. |
| `def` | `generate_text_with_gemini(prompt: str, *, model_name: str \| None=None, temperature: float=0.0)` | Generate text via Gemini using LangChain. |
| `def` | `_make_data_url(image_bytes: bytes, mime_type: str)` | - |
| `def` | `generate_text_from_image_with_gemini(prompt: str, image_bytes: bytes, *, mime_type: str='image/jpeg', model_name: str \| None=None, temperature: float=0.0)` | Generate text from image via Gemini Vision using LangChain. |

## `app/nlp/gemini_parser.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `build_prompt(user_input: str)` | - |
| `def` | `clean_gemini_json(raw_text: str)` | - |
| `def` | `parse_with_gemini(user_input: str)` | - |
| `def` | `parse_with_pending_fallback(user_input: str)` | - |

## `app/nlp/normalizer.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `normalize_amount(text: str)` | Mengubah berbagai format nominal ke integer. |
| `def` | `normalize_text(text: str)` | Lowercase, strip, dan hapus karakter tidak perlu. |
| `def` | `parse_amount_value(number_str: str, unit: str='')` | Parse satu token nominal menjadi integer. |
| `def` | `extract_amount_from_text(text: str)` | Cari dan ekstrak nominal dari kalimat penuh. |
| `def` | `apply_split_operation(text: str, base_amount: int)` | Deteksi pola pembagian dan aplikasikan ke amount. |

## `app/nlp/parse_safety.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `_has_amount(clean: str)` | - |
| `def` | `_has_debt_keyword(clean: str)` | - |
| `def` | `_has_account(clean: str)` | - |
| `def` | `_first_token(value: str)` | - |
| `def` | `_looks_like_person(value: str)` | - |
| `def` | `_append_unique(items: list[str], value: str)` | - |
| `def` | `_add_reason(reasons: list[str], reason: str)` | - |
| `def` | `extract_person_candidate(text: str)` | Best-effort person extraction for clarification callbacks. |
| `def` | `detect_pre_parse_clarification_flags(text: str)` | Flags that must be caught before debt/parser execution. |
| `def` | `detect_post_parse_flags(text: str, parsed: dict[str, Any] \| None)` | Return (info_flags, warning_flags, gemini_flags, reasons). |
| `def` | `assess_parse_safety(text: str, parsed: dict \| None)` | Assess parsing safety and choose routing action. |

## `app/nlp/regex_parser.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `display_account_name(account: str)` | - |
| `def` | `parse_debt_input(text: str)` | - |
| `def` | `detect_type(text: str)` | - |
| `def` | `detect_category(text: str, transaction_type: str)` | - |
| `def` | `detect_account(text: str)` | - |
| `def` | `detect_transfer_accounts(text: str)` | Deteksi rekening asal dan tujuan untuk transaksi transfer/top up. |
| `def` | `parse_explicit_date(date_text: str)` | Parse tanggal eksplisit ke format YYYY-MM-DD. |
| `def` | `parse_day_only_date(day_text: str)` | Parse tanggal hanya angka hari dan gunakan bulan/tahun hari ini. |
| `def` | `strip_date_phrases(text: str)` | Hapus frasa tanggal dari deskripsi. |
| `def` | `parse_relative_number(value: str)` | Parse angka relative date. |
| `def` | `detect_relative_date(text: str)` | Deteksi tanggal relatif. |
| `def` | `detect_date(text: str)` | Deteksi tanggal transaksi. |
| `def` | `extract_description(text: str, amount=None)` | - |
| `def` | `detect_subject(text: str, transaction_type: str, category: str, description: str)` | - |
| `def` | `extract_note(text: str)` | Ambil catatan tambahan. |
| `def` | `detect_spending_type(text: str, category: str, transaction_type: str)` | - |
| `def` | `parse_with_regex(text: str)` | - |

## `app/scheduler/jobs.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `async def` | `job_recurring_run()` | Kirim reminder recurring yang jatuh tempo. |
| `async def` | `send_message(text: str, parse_mode: str \| None='Markdown', reply_markup=None)` | Kirim pesan ke user via bot. |
| `async def` | `job_daily_summary()` | Kirim ringkasan harian setiap jam 21:00. |
| `async def` | `job_weekly_summary()` | Kirim ringkasan mingguan setiap Senin jam 08:00. |
| `async def` | `job_monthly_summary()` | Kirim laporan bulanan setiap tanggal 1 jam 07:00. |
| `async def` | `job_debt_reminder()` | Cek hutang yang mendekati jatuh tempo. |
| `def` | `create_scheduler()` | Buat dan konfigurasi scheduler. |

## `app/services/budget_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `get_current_month()` | Return bulan ini dalam format YYYY-MM. |
| `def` | `normalize_month(month: str \| None=None)` | Normalize bulan ke format YYYY-MM. |
| `def` | `normalize_sheet_month_value(value)` | Normalisasi nilai month dari Google Sheets ke format YYYY-MM. |
| `def` | `format_month_label(month: str)` | Ubah YYYY-MM menjadi label singkat. |
| `def` | `format_rupiah(amount: float)` | - |
| `def` | `get_budget_status_emoji(pct_used: float)` | - |
| `def` | `generate_budget_id(month: str, category: str)` | - |
| `def` | `safe_float(value, default: float=0.0)` | - |
| `def` | `set_budget(category: str, amount: float, month: str=None)` | Set atau update budget untuk kategori tertentu pada bulan tertentu. |
| `def` | `get_budget(category: str, month: str=None)` | Ambil budget untuk kategori tertentu di bulan tertentu. |
| `def` | `get_all_budgets(month: str=None)` | Ambil semua budget di bulan tertentu. |
| `def` | `get_budget_months()` | Ambil daftar bulan yang punya budget. |
| `def` | `budget_transaction_matches_category(record: dict, category: str)` | Cek apakah transaksi masuk ke budget category tertentu. |
| `def` | `calculate_budget_actual_from_transactions(transactions: list[dict])` | Hitung realisasi budget sebagai Bersih (Gross). |
| `def` | `get_actual_expense_breakdown(category: str, month: str=None)` | Hitung total pengeluaran bersih dan gross untuk kategori budget. |
| `def` | `get_actual_expense(category: str, month: str=None)` | Return realisasi budget bersih untuk kategori tertentu. |
| `def` | `get_budget_summary(month: str=None)` | Ambil ringkasan budget vs realisasi semua kategori pada bulan tertentu. |
| `def` | `check_budget_after_transaction(category: str, month: str=None)` | Dipanggil setiap kali ada transaksi expense masuk. |

## `app/services/debt_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `parse_sheet_number(value, default: float=0.0)` | Parse angka dari Google Sheets dengan aman. |
| `def` | `format_rupiah(amount: float)` | Format rupiah tanpa menghilangkan pecahan split bill. |
| `def` | `generate_debt_id()` | - |
| `def` | `generate_payment_id()` | - |
| `def` | `normalize_person_name(name: str)` | Normalisasi nama supaya 'budi', 'Budi', '  budi  ' dianggap orang yang sama. |
| `def` | `normalize_debt_person_group_name(name: str)` | Normalisasi nama untuk tampilan agregat debt. |
| `def` | `is_settled_value(value)` | - |
| `def` | `get_debt_row_by_id(debt_id: str)` | Cari debt berdasarkan ID. |
| `def` | `get_active_debt_exact_person(person_name: str)` | Ambil 1 debt aktif berdasarkan nama orang secara exact setelah normalisasi. |
| `def` | `append_debt_mutation(debt_id: str, amount: float, note: str='', mutation_type: str='payment')` | Catat mutasi debt ke sheet debt_payments. |
| `def` | `add_debt(debt_type: str, person_name: str, amount: float, description: str='', due_date: str='', source_transaction_id: str='', cashflow_mode: str='', fronting_mode: str='')` | Tambah utang/piutang sebagai baris granular per input. |
| `def` | `get_active_debts(debt_type: str=None)` | Ambil semua utang/piutang yang belum lunas. |
| `def` | `get_debt_by_person(person_name: str)` | Cari utang/piutang aktif berdasarkan nama orang. |
| `def` | `add_payment(debt_id: str, amount: float, note: str='')` | Catat pembayaran/pengurangan debt tertentu. |
| `def` | `add_payment_by_person(person_name: str, amount: float, note: str='', target_debt_type: str \| None=None, overpayment_policy: str \| None=None)` | Alokasikan pembayaran debt per orang dengan basis posisi net. |
| `def` | `estimate_payment_outcome(person_name: str, amount: float, target_debt_type: str)` | Hitung preview pembayaran global per orang berbasis saldo net. |
| `def` | `format_debt_net_position_lines(person_name: str, remaining_payable: float, remaining_receivable: float)` | Format posisi akhir hutang-piutang global per orang. |
| `def` | `offset_debt_by_person(person_name: str, amount: float, description: str='', target_debt_type: str='receivable', resulting_debt_type: str='payable')` | Kompensasi / potong silang hutang-piutang tanpa cashflow rekening. |
| `def` | `_debt_row_sort_key_for_settlement(debt: dict)` | Urutan stabil untuk alokasi settlement/netting debt. |
| `def` | `_reduce_debt_remaining_for_settlement(debt: dict, amount: float, note: str, mutation_type: str)` | Kurangi remaining_amount suatu debt tanpa menyentuh transaksi sumber. |
| `def` | `settle_opposite_debts_by_person(person_name: str, amount: float \| None=None, note: str='Netting hutang-piutang')` | Saling hapus payable dan receivable aktif milik orang yang sama. |
| `def` | `is_voided_debt(record: dict)` | True kalau debt ditandai void, bukan pembayaran/lunas normal. |
| `def` | `get_debt_person_summary()` | Ringkasan /hutang berbasis orang, bukan baris granular. |
| `def` | `get_debt_person_detail(person_name: str, include_settled: bool=True)` | Detail debt per orang untuk /hutang <nama>. |
| `def` | `get_debt_summary()` | Hitung total utang dan piutang aktif. |
| `def` | `summarize_debt_rows_for_settlement(debts: list[dict])` | Hitung total debt terpilih tanpa membaca ulang sheet. |
| `def` | `settle_selected_debt_ids(person_name: str, debt_ids: list[str], note: str='', overpayment_amount: float=0.0, overpayment_policy: str \| None=None, net_type: str \| None=None)` | Settle hanya debt_id yang dipilih dari /hutang <nama>. |
| `def` | `parse_debt_allocation_note(note: str)` | Parse catatan transaksi: debt_allocations=debt_id:amount;debt_id:amount. |
| `def` | `_set_debt_remaining(row_index: int, new_remaining: float, original_amount: float \| None=None)` | - |
| `def` | `reverse_debt_payment_transaction(txn: dict)` | Balikkan efek pembayaran debt dari transaksi yang akan dihapus. |
| `def` | `get_debts_with_row_index(active_only: bool=True)` | Ambil debt + _row_index Google Sheets. |
| `def` | `get_debt_by_id_any_status(debt_id: str)` | Cari debt berdasarkan ID, termasuk yang sudah settled/void. |
| `def` | `build_active_debt_display_map()` | Bangun mapping nomor debt berdasarkan urutan tampilan /hutang. |
| `def` | `resolve_debt_ref(ref: str, last_debt_map: dict \| None=None)` | Resolve argumen /debt_void. |
| `def` | `expected_initial_cashflow_category(debt: dict)` | - |
| `def` | `find_debt_initial_cashflow_candidates(debt: dict)` | Cari transaksi cashflow awal yang terkait debt. |
| `def` | `is_debt_without_initial_cashflow(debt: dict)` | Deteksi debt yang memang dibuat tanpa transaksi cashflow awal. |
| `def` | `build_debts_index(records: list[dict] \| None=None, active_only: bool=False)` | Bangun index debts sekali baca untuk menghindari get_all_records berulang. |
| `def` | `get_debts_by_source_transaction_id(transaction_id: str, active_only: bool=True, debt_index: dict \| None=None)` | Cari debt granular yang dibuat dari source_transaction_id tertentu. |
| `def` | `parse_debt_ids_from_transaction_record(txn: dict)` | Ambil daftar debt_id dari kolom transactions.hutang_id. |
| `def` | `get_debts_linked_to_transaction_record(txn: dict, active_only: bool=False, debt_index: dict \| None=None)` | Cari semua debt yang terhubung ke sebuah transaksi. |
| `def` | `get_debt_paid_amount_from_state(debt: dict)` | Paid amount = original_amount - remaining_amount. |
| `def` | `find_overpaid_adjustment_for_debt(debt_id: str, debt_index: dict \| None=None)` | Cari debt adjustment auto untuk overpaid dari debt tertentu. |
| `def` | `upsert_overpaid_adjustment(original_debt: dict, overpaid_amount: float, debt_index: dict \| None=None)` | Buat/update adjustment debt saat payment melebihi charge baru. |
| `def` | `sync_debt_charges_from_transaction_edit(old_txn: dict, new_txn: dict)` | Sync debt charge yang berasal dari transaksi setelah transaksi diedit. |
| `def` | `void_debts_for_transaction(transaction_id: str, debt_ids: list[str] \| None=None)` | Void semua debt yang terhubung ke transaksi. |
| `def` | `void_linked_debt_only(debt_id: str, reason: str='Transaksi sumber dihapus')` | Void debt yang terhubung ke transaksi yang sedang dihapus. |
| `def` | `preview_void_debt(debt_ref: str, last_debt_map: dict \| None=None)` | Preview pembatalan debt. |
| `def` | `resolve_person_debt_targets(person_name: str, detail_ref: str \| None=None)` | Resolve target debt dari nama orang. |
| `def` | `preview_void_debts_by_person(person_name: str, detail_ref: str \| None=None)` | Preview void berdasarkan nama orang. |
| `def` | `void_debt_ids(debt_ids: list[str])` | Void beberapa debt_id secara berurutan. |
| `def` | `void_debts_by_person(person_name: str, detail_ref: str \| None=None)` | Eksekusi void berdasarkan nama orang setelah lolos preview. |
| `def` | `update_debt(debt_ref: str, updates: dict, last_debt_map: dict \| None=None)` | Edit debt/piutang aktif dengan aman. |
| `def` | `void_debt(debt_ref: str, last_debt_map: dict \| None=None)` | Batalkan debt yang salah input dengan aman: |

## `app/services/finance_insight_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `safe_float(value, default: float=0.0)` | Parse angka rupiah dari Google Sheets tanpa mengalikan numeric float. |
| `def` | `format_rupiah(amount: float)` | - |
| `def` | `current_month()` | - |
| `def` | `normalize_month_arg(value: str \| None=None)` | Support None, YYYY-MM, YYYY/MM, bulan angka, bulan ini. |
| `def` | `previous_month(month: str)` | - |
| `def` | `month_bounds(month: str)` | - |
| `def` | `parse_period_from_text(text: str)` | - |
| `def` | `normalize_text(value: str)` | - |
| `def` | `is_date_between(date_value: str, date_from: str \| None, date_to: str \| None)` | - |
| `def` | `filter_records_by_period(records: list[dict], date_from: str \| None, date_to: str \| None)` | - |
| `def` | `get_month_transactions(month: str)` | - |
| `def` | `enrich_finance_transactions(records: list[dict])` | Attach debt metadata so AI finance sees expense as Net, not Gross. |
| `def` | `get_effective_expense_amount(record: dict)` | Nominal expense untuk analisis AI = net setelah piutang split bill. |
| `def` | `summarize_transactions(records: list[dict])` | - |
| `def` | `add_contribution(items: list[dict], total: float, limit: int=8)` | - |
| `def` | `compact_transaction(r: dict)` | - |
| `def` | `get_top_transactions(records: list[dict], txn_type: str \| None='expense', limit: int=8)` | - |
| `def` | `get_budget_status(month: str, transactions: list[dict])` | - |
| `def` | `get_accounts_summary()` | - |
| `def` | `get_debt_summary_compact()` | - |
| `def` | `get_net_worth_compact()` | - |
| `def` | `detect_anomalies(records: list[dict], month_summary: dict \| None=None)` | - |
| `def` | `detect_data_quality_issues(records: list[dict])` | - |
| `def` | `compare_summaries(current: dict, previous: dict)` | - |
| `def` | `build_monthly_finance_context(month: str \| None=None)` | - |
| `def` | `extract_keywords(question: str)` | - |
| `def` | `search_relevant_transactions(question: str, date_from: str \| None=None, date_to: str \| None=None, limit: int=12)` | - |
| `def` | `has_explicit_period(question: str)` | - |
| `def` | `build_ask_finance_context(question: str)` | - |
| `def` | `build_audit_context(month: str \| None=None)` | - |
| `def` | `build_coach_context(month: str \| None=None, question: str='')` | - |
| `def` | `should_handle_finance_question(text: str)` | - |
| `def` | `route_finance_question_mode(text: str)` | - |
| `def` | `deterministic_audit_text(context: dict)` | - |
| `def` | `deterministic_monthly_text(context: dict)` | - |

## `app/services/net_worth_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `now_str()` | - |
| `def` | `today_str()` | - |
| `def` | `generate_id(prefix: str)` | - |
| `def` | `safe_float(value)` | - |
| `def` | `safe_float_decimal(value)` | Parse decimal values such as 41, 41.5, 41,5 without treating dot as thousands. |
| `def` | `parse_human_money(value)` | Parse 2420000, 2.42 juta, 2,42jt, 91.457k for manual asset prices. |
| `def` | `normalize_date_value(value)` | Normalize common Indonesian date inputs to YYYY-MM-DD when possible. |
| `def` | `calculate_asset_gain(asset: dict)` | Return acquisition cost, gain/loss, and gain percentage for one asset. |
| `def` | `parse_price_to_float(value)` | Parse Indonesian price strings like Rp 2,594,000 or 2.594.000. |
| `def` | `fetch_antam_buyback_price()` | Fetch latest Antam buyback price per gram from Logam Mulia. |
| `def` | `is_gold_asset(record: dict)` | - |
| `def` | `is_active_record(record: dict)` | - |
| `def` | `build_asset_row(asset: dict)` | - |
| `def` | `build_liability_row(liability: dict)` | - |
| `def` | `build_snapshot_row(snapshot: dict)` | - |
| `def` | `add_asset(name: str, current_value: float \| None, category: str='Other Asset', description: str='', asset_type: str='manual', quantity: float \| None=None, unit: str='', price_source: str='', price_per_unit: float \| None=None, purchase_price_per_unit: float \| None=None, purchase_date: str='')` | - |
| `def` | `add_liability(name: str, current_balance: float, category: str='Other Liability', description: str='')` | Deprecated: liabilities tidak lagi dipakai dalam konsep net worth bot. |
| `def` | `refresh_gold_assets(records: list[dict])` | Deprecated auto-refresh hook. |
| `def` | `get_assets(active_only: bool=True, refresh_gold: bool=True)` | - |
| `def` | `get_liabilities(active_only: bool=True)` | Deprecated: liabilities sudah tidak menjadi sheet aktif. |
| `def` | `get_record_by_id(sheet_name: str, record_id: str)` | - |
| `def` | `find_record_row_index(sheet_name: str, record_id: str)` | - |
| `def` | `update_record_cells(sheet_name: str, columns: list[str], record_id: str, updates: dict)` | - |
| `def` | `normalize_asset_update_field(field: str)` | - |
| `def` | `normalize_liability_update_field(field: str)` | - |
| `def` | `normalize_common_update_value(field: str, value)` | - |
| `def` | `update_asset(asset_id: str, updates: dict)` | - |
| `def` | `update_liability(liability_id: str, updates: dict)` | Deprecated: liabilities tidak lagi dipakai dalam konsep net worth bot. |
| `def` | `deactivate_asset(asset_id: str)` | - |
| `def` | `deactivate_liability(liability_id: str)` | Deprecated: liabilities tidak lagi dipakai dalam konsep net worth bot. |
| `def` | `calculate_net_worth()` | - |
| `def` | `create_net_worth_snapshot()` | - |
| `def` | `get_net_worth_snapshots(limit: int=12)` | - |

## `app/services/pending_expense_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `now_str()` | - |
| `def` | `today()` | - |
| `def` | `current_month()` | - |
| `def` | `format_rupiah(amount: float)` | - |
| `def` | `safe_float(value, default: float=0.0)` | - |
| `def` | `generate_pending_id()` | - |
| `def` | `normalize_month(month: str \| None=None)` | - |
| `def` | `add_months(month: str, delta: int)` | - |
| `def` | `month_last_day(year: int, month_num: int)` | - |
| `def` | `parse_day_current_or_next_month(day_raw: str)` | - |
| `def` | `parse_month_only_from_text(text: str)` | - |
| `def` | `detect_pending_due(text: str)` | Return due_date, month, due_precision. |
| `def` | `has_past_time_marker(text: str)` | True kalau teks jelas merujuk waktu yang sudah lewat. |
| `def` | `clean_pending_text(text: str)` | - |
| `def` | `is_pending_expense_text(text: str)` | Deteksi input natural untuk pending expense. |
| `def` | `strip_pending_time_phrases(text: str)` | - |
| `def` | `infer_category(text: str, parsed: dict \| None=None)` | - |
| `def` | `infer_account(text: str, parsed: dict \| None=None)` | - |
| `def` | `title_from_description(description: str)` | - |
| `def` | `build_pending_row(item: dict)` | - |
| `def` | `build_pending_expense_from_text(text: str)` | Parse input pending expense menjadi item, tanpa menyimpan ke Google Sheets. |
| `def` | `save_pending_expense(item: dict)` | Simpan item pending expense yang sudah dipreview/di-confirm user. |
| `def` | `add_pending_expense_from_text(text: str)` | Parse dan langsung simpan pending expense. |
| `def` | `get_pending_expenses(period: str \| None=None, active_only: bool=True)` | - |
| `def` | `find_pending_by_ref(ref: str)` | - |
| `def` | `update_pending_status(row_index: int, status: str, paid_transaction_id: str='')` | - |
| `def` | `cancel_pending_expense(ref: str)` | - |
| `def` | `mark_pending_paid(ref: str, account: str \| None=None, paid_date: str \| None=None)` | - |

## `app/services/recurring_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `now_str()` | - |
| `def` | `today_str()` | - |
| `def` | `generate_recurring_id()` | - |
| `def` | `generate_recurring_log_id()` | - |
| `def` | `parse_date(value: str)` | - |
| `def` | `safe_float(value)` | - |
| `def` | `normalize_day_of_month(day)` | - |
| `def` | `normalize_frequency(value: str)` | - |
| `def` | `get_last_day_of_month(year: int, month: int)` | - |
| `def` | `clamp_day(year: int, month: int, day: int)` | - |
| `def` | `calculate_next_monthly_run(day_of_month: int, from_date: date \| None=None)` | Hitung next_run_date untuk monthly recurring. |
| `def` | `calculate_next_run_after_execution(rule: dict, run_date: date \| None=None)` | - |
| `def` | `build_recurring_row(rule: dict)` | - |
| `def` | `build_recurring_log_row(log: dict)` | - |
| `def` | `add_recurring_rule(name: str, txn_type: str, amount: float, category: str, account: str, frequency: str, day_of_month: int, description: str \| None=None, subject: str \| None=None, catatan: str \| None=None, tipe_pengeluaran: str \| None=None, to_account: str \| None=None)` | - |
| `def` | `get_recurring_rules(active_only: bool=False)` | - |
| `def` | `get_due_recurring_rules(target_date: date \| None=None)` | - |
| `def` | `find_recurring_rule_row_index(rule_id: str)` | - |
| `def` | `update_recurring_rule_cells(rule_id: str, updates: dict)` | - |
| `def` | `disable_recurring_rule(rule_id: str)` | - |
| `def` | `get_recurring_rule_by_id(rule_id: str)` | - |
| `def` | `normalize_recurring_edit_field(field: str)` | - |
| `def` | `normalize_recurring_edit_value(field: str, value)` | - |
| `def` | `edit_recurring_rule(rule_id: str, updates: dict)` | Edit recurring rule by ID. |
| `def` | `log_recurring_run(rule_id: str, transaction_id: str \| None, run_date: str, status: str, message: str)` | - |
| `def` | `build_transaction_from_recurring_rule(rule: dict, run_date: str \| None=None)` | - |
| `def` | `mark_recurring_rule_paid(rule_id: str, run_date: date \| None=None)` | Tandai recurring sudah dibayar untuk periode jatuh tempo saat ini. |
| `def` | `process_due_recurring_rules(target_date: date \| None=None)` | - |

## `app/services/report_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `get_transaction_records_for_report()` | Ambil semua transaksi untuk laporan. |
| `def` | `format_rupiah(amount: float)` | - |
| `def` | `safe_float(value, default: float=0.0)` | Parse amount dari number/string Google Sheets secara aman. |
| `def` | `normalize_category_key(value: str \| None)` | Normalisasi nama kategori untuk matching yang toleran spasi/simbol. |
| `def` | `normalize_account_key(value: str \| None)` | Normalisasi nama rekening untuk matching yang toleran spasi/simbol. |
| `def` | `get_known_report_accounts(records: list[dict] \| None=None)` | Gabungkan rekening dari sheet accounts dan transaksi. |
| `def` | `resolve_account_filter(account_query: str \| None, records: list[dict] \| None=None)` | Resolve input rekening user ke nama rekening canonical jika memungkinkan. |
| `def` | `is_account_match(value: str \| None, account_key: str \| None)` | - |
| `def` | `is_account_transaction(record: dict, account: str \| None)` | Cek apakah transaksi menyentuh rekening tertentu. |
| `def` | `split_report_filter_args(value: str \| None, mode: str)` | Pisahkan argumen report menjadi periode, kategori, dan rekening. |
| `def` | `split_account_period_arg(value: str \| None)` | Parse argumen /rekening. |
| `def` | `get_known_report_categories(records: list[dict] \| None=None)` | Gabungkan kategori default dan kategori yang benar-benar ada di sheet transaksi. |
| `def` | `resolve_category_filter(category_query: str \| None, records: list[dict] \| None=None)` | Resolve input kategori user ke nama kategori canonical jika memungkinkan. |
| `def` | `split_report_period_and_category_arg(value: str \| None, mode: str)` | Pisahkan argumen report menjadi periode dan kategori. |
| `def` | `is_truthy_sheet_value(value)` | - |
| `def` | `is_voided_debt_record(debt: dict)` | Void beda dengan settled/lunas. Settled tetap dihitung untuk Net (Gross). |
| `def` | `parse_transaction_debt_ids_from_record(txn: dict)` | Ambil daftar debt id dari kolom transactions.hutang_id. |
| `def` | `build_debt_lookup(active_only: bool=True)` | Index debts berdasarkan id dan source_transaction_id untuk laporan. |
| `def` | `get_linked_debts_for_transaction(txn: dict, lookup: dict)` | Cari debt aktif yang terhubung ke transaksi dari hutang_id atau source_transaction_id. |
| `def` | `enrich_transactions_with_debt_info(transactions: list[dict])` | Tambahkan ringkasan debt ke transaksi. |
| `def` | `calculate_net_expense_after_receivable(transactions: list[dict])` | Total pengeluaran bersih: gross expense dikurangi piutang aktif terkait transaksi. |
| `def` | `calculate_net_expense_by_category(transactions: list[dict])` | Breakdown pengeluaran bersih per kategori. |
| `def` | `attach_enriched_transactions(summary: dict, transactions: list[dict])` | Attach transaksi enriched + total pengeluaran bersih ke summary report. |
| `def` | `build_delta_info(current_value, previous_value, previous_available: bool=True)` | Buat metadata delta yang aman saat data periode sebelumnya belum ada. |
| `def` | `build_summary_comparison(current: dict, previous: dict, previous_available: bool=True)` | Buat delta current vs periode sebelumnya. |
| `def` | `build_category_comparison(current: dict, previous: dict, previous_available: bool=True)` | Buat delta pengeluaran per kategori vs periode sebelumnya. |
| `def` | `parse_report_date_arg(value: str \| None=None)` | Normalize argumen tanggal laporan ke YYYY-MM-DD. |
| `def` | `parse_report_month_arg(value: str \| None=None)` | Normalize argumen bulan laporan ke (year, month). |
| `def` | `get_week_range(reference_date: str \| None=None)` | Return (monday, sunday) minggu dari reference_date dalam format YYYY-MM-DD. |
| `def` | `get_month_range(year: int \| None=None, month: int \| None=None)` | Return (first_day, last_day) bulan dalam format YYYY-MM-DD. |
| `def` | `filter_transactions(records: list[dict], date_from: str \| None=None, date_to: str \| None=None, txn_type: str \| None=None, category: str \| None=None, account: str \| None=None)` | Filter transaksi berdasarkan rentang tanggal, tipe, kategori, dan/atau rekening. |
| `def` | `summarize(transactions: list[dict], account: str \| None=None)` | Hitung total income, expense, transfer, net, dan breakdown per kategori. |
| `def` | `get_daily_report(date_str: str \| None=None, category: str \| None=None, account: str \| None=None)` | Laporan harian untuk tanggal tertentu. Default: hari ini. |
| `def` | `get_weekly_report(reference_date: str \| None=None, category: str \| None=None, account: str \| None=None)` | Laporan mingguan — Senin sampai Minggu dari reference_date. |
| `def` | `get_monthly_report(year: int \| None=None, month: int \| None=None, category: str \| None=None, account: str \| None=None)` | Laporan bulanan. |
| `def` | `get_account_balance(account_name: str)` | Ambil saldo rekening dari sheet accounts. |
| `def` | `get_account_monthly_report(account: str, month_arg: str \| None=None)` | Ringkasan rekening untuk bulan tertentu. |
| `def` | `get_account_all_report(account: str)` | Ringkasan rekening untuk seluruh histori transaksi. |
| `def` | `get_account_report(account: str, period_arg: str \| None='month')` | Dispatcher ringkasan rekening untuk /rekening. |
| `def` | `search_transactions(keyword: str, limit: int=10)` | Cari transaksi berdasarkan keyword di kolom description, subject, category, atau raw_input. |
| `def` | `get_top_expenses(month: str \| None=None, top_n: int=5)` | Ambil N transaksi expense terbesar dalam sebulan. |

## `app/services/transaction_service.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `get_current_month_str()` | - |
| `def` | `normalize_export_period(period: str \| None=None)` | Normalize argumen /download_data. |
| `def` | `parse_date_safe(value)` | - |
| `def` | `get_transactions_for_export(period: str \| None=None)` | Ambil transaksi untuk export CSV. |
| `def` | `is_skip_account_transaction(parsed: dict)` | True jika transaksi dicatat tanpa mengubah saldo rekening. |
| `def` | `generate_transaction_id()` | Generate transaction ID yang unik. |
| `def` | `build_transaction_row(parsed: dict, raw_input: str)` | Build row transaksi sesuai header Google Sheets: |
| `def` | `update_transaction_debt_relation(transaction_id: str, debt_ids: list[str], tipe_hutang: str='piutang')` | Update kolom hutang_id dan tipe_hutang di sheet transactions. |
| `def` | `clear_transaction_debt_relation(transaction_id: str)` | Kosongkan hutang_id/tipe_hutang transaksi setelah split bill lama dibatalkan/lunas. |
| `def` | `validate_transaction(parsed: dict)` | - |
| `def` | `get_account_balance(account_name: str)` | Ambil saldo rekening berdasarkan nama. |
| `def` | `update_account_balance(account_name: str, new_balance: float)` | Update saldo rekening di sheet accounts. |
| `def` | `get_all_accounts()` | Ambil semua rekening beserta saldonya. |
| `def` | `get_account_index_map()` | Ambil semua account sekali saja. |
| `def` | `validate_accounts_exist(account_deltas: dict)` | Validasi semua rekening yang akan terdampak sebelum operasi write. |
| `def` | `calculate_account_deltas(parsed_items: list[dict])` | Hitung perubahan saldo per rekening dari banyak transaksi. |
| `def` | `apply_account_deltas(account_deltas: dict)` | Update saldo rekening berdasarkan total delta per account. |
| `def` | `save_transaction(parsed: dict, raw_input: str)` | Simpan satu transaksi ke Google Sheets dan update saldo rekening. |
| `def` | `save_transactions_batch(parsed_items: list[dict])` | Simpan banyak transaksi sekaligus. |
| `def` | `get_transactions_by_month(year: int, month: int)` | Ambil semua transaksi dalam satu bulan. |
| `def` | `get_transactions_by_date(date_str: str)` | Ambil semua transaksi di tanggal tertentu. Format: YYYY-MM-DD |
| `def` | `get_expense_by_category(year: int, month: int)` | Hitung total pengeluaran per kategori dalam satu bulan. |
| `def` | `is_debt_cashflow_transaction(txn: dict)` | - |
| `def` | `parse_transaction_date(date_value: str)` | - |
| `def` | `sort_transactions_sheet_by_date(desc: bool=True)` | Sort tab transactions berdasarkan kolom date. |
| `def` | `get_transactions_with_row_index()` | Ambil semua transaksi + _row_index Google Sheets. |
| `def` | `get_recent_transactions(limit: int=10, period: str \| None=None, month: str \| None=None)` | Ambil transaksi terbaru. |
| `def` | `get_transaction_by_id(txn_id: str)` | - |
| `def` | `get_transactions_by_ids(txn_ids: list[str])` | - |
| `def` | `get_transactions_by_row_indices(row_indices: list[int])` | - |
| `def` | `calculate_reverse_deltas_for_delete(transactions: list[dict])` | Balik efek saldo dari transaksi yang akan dihapus. |
| `def` | `parse_transaction_debt_ids(txn: dict)` | Ambil debt/hutang id dari kolom transactions.hutang_id, support comma-separated. |
| `def` | `transaction_has_debt_relation(txn: dict)` | - |
| `def` | `preview_delete_transactions_by_refs(row_indices: list[int] \| None=None, txn_ids: list[str] \| None=None)` | Preview delete berdasarkan: |
| `def` | `preview_delete_transactions(txn_ids: list[str])` | Validasi dan preview transaksi yang akan dihapus. |
| `def` | `delete_transactions_by_ids(txn_ids: list[str])` | Hapus banyak transaksi sekaligus dan reverse saldo rekening. |
| `def` | `delete_transactions_by_refs(row_indices: list[int] \| None=None, txn_ids: list[str] \| None=None)` | Delete transaksi berdasarkan row_index dan/atau transaction_id. |
| `def` | `normalize_edit_field(field: str)` | - |
| `def` | `normalize_edit_updates(updates: dict)` | - |
| `def` | `get_single_transaction_by_ref(row_index: int \| None=None, txn_id: str \| None=None)` | - |
| `def` | `build_transaction_row_from_record(txn: dict)` | Bentuk ulang row sesuai header transactions. |
| `def` | `calculate_account_effect(txn: dict)` | Hitung efek saldo asli dari sebuah transaksi. |
| `def` | `calculate_edit_net_deltas(old_txn: dict, new_txn: dict)` | Net delta saldo untuk edit transaksi. |
| `def` | `validate_edit_transaction(txn: dict)` | - |
| `def` | `preview_edit_transaction_by_ref(updates: dict, row_index: int \| None=None, txn_id: str \| None=None)` | Preview edit transaksi. |
| `def` | `_payment_allocation_note(raw: str, allocations: list[dict], overpayment: float=0.0, policy: str='')` | - |
| `def` | `edit_debt_payment_transaction_amount(preview: dict)` | Edit nominal transaksi pembayaran debt sambil sync sheet debts. |
| `def` | `edit_transaction_by_ref(updates: dict, row_index: int \| None=None, txn_id: str \| None=None)` | Edit transaksi: |

## `app/sheets/client.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `class` | `SheetsAtomicWriteError` | Error write Sheets yang sudah melewati retry dan memicu rollback. |
| `class` | `SheetsTransaction` | Best-effort transaction wrapper untuk operasi Google Sheets. |
| `def` | `sheets_transaction(label: str \| None=None)` | Aktifkan rollback otomatis untuk semua write Sheets di dalam blok ini. |
| `def` | `rollback_current_sheets_transaction()` | Rollback transaksi Sheets aktif, dipakai untuk logical failure non-exception. |
| `def` | `get_current_sheets_transaction()` | - |
| `def` | `_is_quota_or_transient_error(exc: Exception)` | - |
| `def` | `_call_with_retry(fn, *, max_retries: int \| None=None)` | - |
| `def` | `_execute_write(fn)` | - |
| `def` | `_execute_read(fn)` | - |
| `def` | `_get_column_letter(col_number: int)` | - |
| `def` | `_extract_updated_row_index(response)` | - |
| `def` | `_extract_updated_row_range(response)` | - |
| `def` | `_pad_row(row: list, width: int)` | - |
| `def` | `_clean_header(values: list)` | - |
| `def` | `_has_data_rows(values: list[list])` | - |
| `def` | `_is_blank_header(header: list[str])` | - |
| `def` | `_header_has_expected_prefix(header: list[str], expected_header: list[str])` | - |
| `def` | `_header_is_safe_prefix(header: list[str], expected_header: list[str])` | - |
| `def` | `_resize_columns_if_needed(sheet, width: int)` | - |
| `def` | `_write_header(sheet, header: list[str])` | - |
| `def` | `_default_rows_for_sheet(sheet_name: str)` | - |
| `def` | `_seed_default_rows_if_empty(sheet_name: str, sheet, values: list[list])` | - |
| `def` | `_get_or_create_worksheet(spreadsheet, sheet_name: str)` | - |
| `def` | `ensure_sheet_schema(sheet_name: str, sheet=None)` | Pastikan tab dan header Google Sheets siap dipakai bot. |
| `def` | `ensure_spreadsheet_schema()` | Buat semua tab wajib dan header jika spreadsheet masih kosong/belum siap. |
| `def` | `get_spreadsheet()` | Singleton pattern — koneksi dibuat sekali, dipakai ulang. |
| `def` | `get_sheet(sheet_name: str)` | Ambil worksheet berdasarkan nama tab. |
| `def` | `append_row(sheet_name: str, row: list)` | Tambah satu baris baru di akhir sheet dengan retry + rollback. |
| `def` | `append_row_raw(sheet_name: str, row: list)` | Tambah satu baris baru tanpa auto-format Google Sheets. |
| `def` | `append_rows(sheet_name: str, rows: list[list])` | Tambah banyak baris sekaligus. |
| `def` | `get_all_records(sheet_name: str)` | Ambil semua data sebagai list of dict (header = key). |
| `def` | `get_all_values(sheet_name: str)` | - |
| `def` | `update_cell(sheet_name: str, row: int, col: int, value)` | Update satu cell berdasarkan posisi row & col (1-indexed). |
| `def` | `find_row_index(sheet_name: str, search_col: int, search_value: str)` | Cari index baris berdasarkan nilai di kolom tertentu. |
| `def` | `delete_row(sheet_name: str, row_index: int)` | Hapus satu baris dari worksheet. |
| `def` | `delete_rows(sheet_name: str, row_indices: list[int])` | Hapus banyak baris dari worksheet. |
| `def` | `update_row(sheet_name: str, row_index: int, row_values: list)` | Update satu baris penuh di worksheet. |
| `def` | `update_range(sheet_name: str, cell_range: str, values: list[list])` | Update range worksheet dengan snapshot rollback. |

## `main.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `validate_runtime_config(mode: str=BOT_MODE)` | Validate required env variables for the selected runtime mode. |
| `def` | `ensure_schema_on_startup()` | Prepare Google Sheets schema if credentials and access are ready. |
| `def` | `start_scheduler_once()` | - |
| `def` | `shutdown_scheduler_once()` | - |
| `async def` | `startup()` | - |
| `async def` | `shutdown()` | - |
| `async def` | `health_check()` | - |
| `async def` | `test_sheets()` | - |
| `async def` | `run_polling_mode()` | Run bot using Telegram long polling for simple local setup. |
| `def` | `run_webhook_mode()` | Run FastAPI app for webhook deployment. |

## `scripts/debug_check.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `now_str()` | - |
| `def` | `rupiah(amount)` | - |
| `def` | `add_result(area, name, status, expected, actual='', error='')` | - |
| `def` | `ok(area, name, expected='OK', actual='OK')` | - |
| `def` | `warn(area, name, expected='OK', actual='Warning', error='')` | - |
| `def` | `fail(area, name, expected='OK', actual='Failed', error='')` | - |
| `def` | `skip(area, name, expected='Available', actual='Skipped', error='')` | - |
| `def` | `print_header(title)` | - |
| `def` | `print_summary()` | - |
| `def` | `safe_run(area, name, expected, func)` | - |
| `def` | `import_module_safe(module_name, area='Import')` | - |
| `def` | `has_function(module, func_name, area)` | - |
| `def` | `check_environment()` | - |
| `def` | `check_imports()` | - |
| `def` | `check_config(modules)` | - |
| `def` | `check_google_sheets(modules)` | - |
| `def` | `check_nlp(modules)` | - |
| `def` | `check_transaction_service(modules)` | - |
| `def` | `check_report_service(modules)` | - |
| `def` | `check_budget_service(modules)` | - |
| `def` | `check_debt_service(modules)` | - |
| `def` | `check_recurring_service(modules)` | - |
| `def` | `check_net_worth_service(modules)` | - |
| `def` | `check_bot_handlers(modules)` | - |
| `def` | `check_scheduler(modules)` | - |
| `def` | `check_regression_commands(modules)` | - |
| `def` | `main()` | - |

## `scripts/setup_check.py`

| Type | Name / Signature | Keterangan singkat |
|---|---|---|
| `def` | `_add(status: str, title: str, detail: str='')` | - |
| `def` | `ok(title: str, detail: str='')` | - |
| `def` | `warn(title: str, detail: str='')` | - |
| `def` | `fail(title: str, detail: str='')` | - |
| `def` | `skip(title: str, detail: str='')` | - |
| `def` | `mask(value: str)` | - |
| `def` | `env(name: str, default: str='')` | - |
| `def` | `check_env_file()` | - |
| `def` | `check_runtime_env()` | - |
| `def` | `check_service_account_file()` | - |
| `def` | `check_imports()` | - |
| `def` | `check_google_sheets_schema(can_try: bool)` | - |
| `def` | `print_summary()` | - |
| `def` | `main()` | - |