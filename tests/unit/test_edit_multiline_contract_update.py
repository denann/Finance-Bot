import ast
import asyncio
from pathlib import Path
import re
import shlex
import types


SOURCE = Path('app/bot/handler_parts/message_handlers.py').read_text()
TREE = ast.parse(SOURCE)


def _load_function(name, extra_globals=None):
    node = next(n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    ns = {"re": re, "shlex": shlex, "ContextTypes": types.SimpleNamespace(DEFAULT_TYPE=object)}
    ns.update(extra_globals or {})
    exec(compile(module, 'message_handlers.py', 'exec'), ns)
    return ns[name]


def test_multiline_classifier_accepts_bare_or_update_and_rejects_mixed():
    classify = _load_function('classify_bulk_edit_txn_lines')
    mode, parsed, error = classify(['/edit_txn 1', '/edit_txn 3', '/edit_txn 8'])
    assert mode == 'bare' and error is None
    assert [ref for ref, _ in parsed] == ['1', '3', '8']

    mode, _, error = classify(['/edit_txn 1 amount=10', '/edit_txn 3 category=Food'])
    assert mode == 'update' and error is None

    mode, _, error = classify(['/edit_txn 1', '/edit_txn 3 amount=10'])
    assert mode == 'mixed'
    assert 'Jangan campur' in error


def test_duplicate_update_bearing_target_is_rejected_before_write():
    async def run_sheets_read(_name, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def resolve(_context, refs):
        ref = str(refs[0])
        return {"row_indices": [], "txn_ids": ["txn_same" if ref == '2' else f'txn_{ref}'], "invalid_refs": []}

    def parse_updates(args):
        result = {}
        for item in args:
            key, value = item.split('=', 1)
            result[key] = value
        return result

    def preview(**kwargs):
        return {
            "success": True,
            "updates": kwargs.get("updates") or {},
            "old_txn": {"id": kwargs.get("txn_id"), "amount": 100},
            "new_txn": {"id": kwargs.get("txn_id"), "amount": 200},
        }

    service = types.SimpleNamespace(transaction_material_signature=lambda txn: (txn.get('id'), txn.get('amount')))
    parse_entries = _load_function('parse_bulk_edit_txn_entries', {
        'edit_args_contain_split_bill': lambda _args: False,
        'parse_edit_debt_payment_conversion_args': lambda _args: None,
        'resolve_txn_refs_from_last': resolve,
        'parse_edit_updates': parse_updates,
        'run_sheets_read': run_sheets_read,
        'preview_edit_transaction_by_ref': preview,
        'get_edit_category_choice_prompt': lambda _updates, _preview: None,
        'transaction_service': service,
    })

    context = types.SimpleNamespace(user_data={})
    entries, errors, decisions = asyncio.run(parse_entries(
        ['/edit_txn 2 amount=15000', '/edit_txn 2 category=Food'],
        context,
    ))

    assert len(entries) == 1
    assert decisions == []
    assert any('diedit lebih dari sekali' in error for error in errors)


def test_transaksi_month_filter_returns_resolved_refresh_descriptor():
    async def run_sheets_read(_name, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def monthly(year=None, month=None, category=None, account=None):
        assert (year, month, category, account) == (2026, 7, 'Food & Beverage', 'BCA')
        return {
            'month': '2026-07',
            'category_filter': 'Food & Beverage',
            'account_filter': 'BCA',
            'transactions': [{'id': 'txn_1'}],
        }

    parse_period = _load_function('parse_transaksi_period', {
        '_build_transaksi_prefixed_period_arg': lambda first, rest, kind: rest,
        'split_report_filter_args': lambda source, kind: ('2026-07', 'Food & Beverage', 'BCA'),
        'parse_report_month_arg': lambda value: (2026, 7),
        'run_sheets_read': run_sheets_read,
        'get_monthly_report': monthly,
        'build_transaction_filter_title': lambda base, category, account: f'{base} | {category} | {account}',
    })

    title, rows, period_type, account_filter, descriptor = asyncio.run(
        parse_period(['bulan', '2026-07', 'Food', '&', 'Beverage', 'rekening', 'BCA'])
    )
    assert rows == [{'id': 'txn_1'}]
    assert period_type == 'month'
    assert account_filter == 'BCA'
    assert descriptor == {
        'kind': 'month',
        'month': '2026-07',
        'category': 'Food & Beverage',
        'account': 'BCA',
    }
    assert 'Food & Beverage' in title and 'BCA' in title


def test_bulk_confirm_state_preserves_parent_browser_origin():
    build = _load_function('build_bulk_edit_confirm_state')
    state = build([
        {
            'line_no': 1,
            'line': '/edit_txn 3 amount=10',
            'ref': '3',
            'row_index': 7,
            'txn_id': 'txn_3',
            'updates': {'amount': 10},
            'expected_signature': ['sig'],
        }
    ], 'browser-parent')
    assert state['origin_browser_session_id'] == 'browser-parent'
    assert state['entries'][0]['txn_id'] == 'txn_3'
