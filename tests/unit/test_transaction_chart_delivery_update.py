import asyncio
import importlib
import sys
import types
from contextlib import contextmanager


class InputFile:
    def __init__(self, obj, filename=None):
        self.obj = obj
        self.filename = filename


_MISSING = object()


@contextmanager
def _temporary_modules(replacements):
    saved = {}
    attrs = {}
    try:
        for name, module in replacements.items():
            saved[name] = sys.modules.get(name, _MISSING)
            parent_name, _, attr = name.rpartition(".")
            if parent_name:
                parent = importlib.import_module(parent_name)
                attrs[name] = (parent, getattr(parent, attr, _MISSING))
                setattr(parent, attr, module)
            sys.modules[name] = module
        yield
    finally:
        for name in reversed(tuple(replacements)):
            parent_info = attrs.get(name)
            if parent_info:
                parent, old = parent_info
                attr = name.rpartition(".")[2]
                if old is _MISSING:
                    if getattr(parent, attr, _MISSING) is replacements[name]:
                        delattr(parent, attr)
                else:
                    setattr(parent, attr, old)
            old = saved[name]
            if old is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def _load_chart_module(builder=None):
    telegram = types.ModuleType("telegram")
    telegram.InputFile = InputFile
    chart_service = types.ModuleType("app.services.chart_service")
    chart_service.build_transaction_timeseries_png_bytes = builder or (lambda rows, title: b"\x89PNG\r\n\x1a\nchart")
    name = "app.bot.handler_parts.transaction_chart"
    old = sys.modules.pop(name, None)
    try:
        with _temporary_modules({"telegram": telegram, "app.services.chart_service": chart_service}):
            module = importlib.import_module(name)
    finally:
        if old is not None:
            sys.modules[name] = old
        else:
            sys.modules.pop(name, None)
    return module


def test_actual_chart_delivery_helper_requires_telegram_photo_response():
    captured = {}
    chart = _load_chart_module(lambda rows, title: (captured.update(ids=[r["id"] for r in rows], title=title) or b"\x89PNG\r\n\x1a\nvisible"))

    class Bot:
        async def send_photo(self, **kwargs):
            captured["send"] = kwargs
            assert kwargs["chat_id"] == 123
            assert kwargs["photo"].filename == "grafik-transaksi-timeseries.png"
            assert kwargs["photo"].obj.startswith(b"\x89PNG\r\n\x1a\n")
            return types.SimpleNamespace(photo=[types.SimpleNamespace(file_id="photo-1")])

    ok, error = asyncio.run(chart.send_transaction_timeseries_chart_message(
        Bot(), 123,
        [{"id": "txn_a", "type": "expense", "amount": 10000, "net": 8000}],
        "Transaksi Bulan 2026-07",
    ))

    assert ok is True and error == ""
    assert captured["ids"] == ["txn_a"]
    assert captured["title"] == "Time Series - Transaksi Bulan 2026-07"
    assert "Basis angka: pengeluaran net" in captured["send"]["caption"]


def test_actual_chart_delivery_helper_rejects_non_photo_telegram_response():
    chart = _load_chart_module()

    class Bot:
        async def send_photo(self, **kwargs):
            return types.SimpleNamespace(photo=[])

    ok, error = asyncio.run(chart.send_transaction_timeseries_chart_message(Bot(), 123, [{"id": "txn_a"}], "X"))
    assert ok is False
    assert "tidak mengembalikan pesan foto" in error.lower()


def test_actual_chart_delivery_helper_returns_truthful_generation_failure():
    chart = _load_chart_module(lambda rows, title: (_ for _ in ()).throw(RuntimeError("chart boom")))

    class Bot:
        async def send_photo(self, **kwargs):
            raise AssertionError("photo must not be sent when chart generation fails")

    ok, error = asyncio.run(chart.send_transaction_timeseries_chart_message(Bot(), 123, [], "X"))
    assert ok is False
    assert "chart boom" in error


def test_actual_chart_delivery_helper_bounds_send_failure():
    chart = _load_chart_module()

    class Bot:
        async def send_photo(self, **kwargs):
            raise RuntimeError("telegram photo send boom")

    ok, error = asyncio.run(chart.send_transaction_timeseries_chart_message(Bot(), 123, [{"id": "txn_a"}], "X"))
    assert ok is False
    assert "telegram photo send boom" in error


def test_actual_chart_delivery_helper_rejects_invalid_png_before_send():
    chart = _load_chart_module(lambda rows, title: b"not-a-png")

    class Bot:
        async def send_photo(self, **kwargs):
            raise AssertionError("invalid PNG must not reach Telegram")

    ok, error = asyncio.run(chart.send_transaction_timeseries_chart_message(Bot(), 123, [{"id": "txn_a"}], "X"))
    assert ok is False
    assert "png" in error.lower()


def test_actual_chart_renderer_flows_into_photo_delivery_seam():
    """Use the real chart renderer, not a mocked PNG builder."""
    telegram = types.ModuleType("telegram")
    telegram.InputFile = InputFile
    name = "app.bot.handler_parts.transaction_chart"
    old = sys.modules.pop(name, _MISSING)
    parent = importlib.import_module("app.bot.handler_parts")
    old_attr = getattr(parent, "transaction_chart", _MISSING)
    if old_attr is not _MISSING:
        delattr(parent, "transaction_chart")
    loaded = _MISSING
    try:
        with _temporary_modules({"telegram": telegram}):
            loaded = importlib.import_module(name)
    finally:
        if old is _MISSING:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old
        if old_attr is _MISSING:
            if getattr(parent, "transaction_chart", _MISSING) is loaded:
                delattr(parent, "transaction_chart")
        else:
            parent.transaction_chart = old_attr

    captured = {}
    class Bot:
        async def send_photo(self, **kwargs):
            captured.update(kwargs)
            assert kwargs["photo"].obj.startswith(b"\x89PNG\r\n\x1a\n")
            assert len(kwargs["photo"].obj) > 1000
            return types.SimpleNamespace(photo=[types.SimpleNamespace(file_id="real-render")])

    ok, error = asyncio.run(loaded.send_transaction_timeseries_chart_message(
        Bot(), 321,
        [{"id": "txn_real", "date": "2026-08-01", "type": "expense", "amount": 10000, "net": 8000}],
        "Transaksi Bulan 2026-08",
    ))
    assert ok is True and error == ""
    assert captured["chat_id"] == 321
