# Split from app/bot/handlers.py for readability.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

def parse_asset_quantity_input(value: str) -> dict | None:
    """
    Deteksi input aset berbasis satuan:
    - 41g / 41 gr / 41 gram
    - 1 buah / 2 unit
    - 41 gram @ 2410000
    - 1 buah @ 8000000

    Return dict {quantity, unit, price_per_unit?} atau None.
    """
    raw = str(value or "").strip().lower()
    raw = raw.replace("@", " @ ")
    raw = re.sub(r"\s+", " ", raw).strip()

    match = re.fullmatch(
        r"(\d+(?:[.,]\d+)?)\s*(g|gr|gram|grams|buah|unit|pcs|pc|lembar|kg|kilogram)(?:\s*@\s*([0-9.,]+)\s*(?:rb|ribu|k|jt|juta)?)?",
        raw,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    quantity = float(match.group(1).replace(",", "."))
    unit = match.group(2).lower()
    unit_aliases = {
        "g": "gram",
        "gr": "gram",
        "grams": "gram",
        "pcs": "buah",
        "pc": "buah",
    }
    unit = unit_aliases.get(unit, unit)

    price_raw = match.group(3)
    price_per_unit = parse_human_amount(price_raw) if price_raw else None

    return {
        "quantity": quantity,
        "unit": unit,
        "price_per_unit": price_per_unit,
    }


def _parse_human_amount_atom(value: str | None) -> float:
    """Parse satu token nominal: 2410000, 2.41jt, 2,41 juta, 91.457k."""
    raw = str(value or "").strip().lower()
    if not raw:
        return 0.0

    multiplier = 1
    if re.search(r"(jt|juta)\b", raw):
        multiplier = 1_000_000
    elif re.search(r"(rb|ribu|k)\b", raw):
        multiplier = 1_000

    raw = re.sub(r"(jt|juta|rb|ribu|k)\b", "", raw).strip()

    # Kalau ada suffix k/juta, titik/koma dianggap desimal: 2.41jt -> 2.41 * 1jt.
    if multiplier != 1:
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)
        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)
        return float(raw or 0) * multiplier

    # Tanpa suffix, titik/koma dianggap pemisah ribuan.
    raw = re.sub(r"[^0-9]", "", raw)
    return float(raw or 0)


def _safe_eval_amount_expression(expr: str) -> float:
    """Evaluasi ekspresi nominal sederhana seperti 94k/2 atau 37.5k x 3.

    Hanya operator +, -, *, / yang diizinkan. Tidak memakai eval langsung.
    """
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Num):  # pragma: no cover, compatibility lama
            return float(node.n)
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            right = _eval(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("division by zero")
            return allowed_ops[type(node.op)](_eval(node.left), right)
        raise ValueError("unsafe amount expression")

    tree = ast.parse(expr, mode="eval")
    return float(_eval(tree))


def parse_human_amount(value: str | None) -> float:
    """Parse angka manusia, termasuk ekspresi edit seperti `94k/2`.

    Contoh:
    - `94k/2` -> 47000
    - `37.5k` -> 37500
    - `2.41jt` -> 2410000
    """
    raw = str(value or "").strip().lower()
    if not raw:
        return 0.0

    # Jangan perlakukan tanggal seperti 01-05-2026 sebagai ekspresi matematika.
    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    if has_math_operator:
        # Ubah token nominal bersuffix menjadi angka penuh sebelum dievaluasi.
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        def repl(match: re.Match) -> str:
            token = match.group(0)
            return str(_parse_human_amount_atom(token))

        expr = token_pattern.sub(repl, raw)
        expr = expr.replace("×", "*").replace("x", "*").replace(":", "/")
        expr = re.sub(r"\s+", "", expr)
        if re.fullmatch(r"[0-9.+\-*/()]+", expr):
            try:
                result = _safe_eval_amount_expression(expr)
                if result > 0:
                    return result
            except Exception:
                pass

    return _parse_human_amount_atom(raw)


def guess_asset_category_and_name(name: str, category: str | None = None) -> tuple[str, str]:
    name_clean = str(name or "").strip()
    category_clean = str(category or "").strip()
    low = name_clean.lower()

    if "emas" in low or category_clean.lower() in ["gold", "emas", "precious metal", "logam mulia"]:
        return name_clean or "Emas", category_clean or "Gold"

    return name_clean, category_clean or "Other Asset"


def build_asset_unit_price_prompt(data: dict) -> str:
    return (
        "💰 *Isi harga satuan aset*\n\n"
        f"📦 Nama: *{data.get('name')}*\n"
        f"📁 Kategori: *{data.get('category')}*\n"
        f"🔢 Jumlah: *{data.get('quantity')} {data.get('unit')}*\n\n"
        f"Harga 1 {data.get('unit')} berapa?\n\n"
        "Contoh balasan:\n"
        "`2410000`\n"
        "`2.41 juta`\n"
        "`8000000`"
    )

def parse_pipe_add_args(args: list[str], item_type: str) -> dict:
    """
    Format:
    /asset_add Nama | value | category | description
    /asset_add Emas Antam | 41 gram | Gold | Tabungan emas
    /asset_add Laptop | 1 buah | Electronics | Laptop kerja
    /liability_add Nama | balance | category | description
    """
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh:\n"
            f"`/{item_type}_add Laptop | 8000000 | Electronics | Laptop kerja`"
        )

    parts = [p.strip() for p in raw.split("|")]

    if len(parts) < 2:
        raise ValueError(
            f"Format belum lengkap.\n\n"
            f"Format:\n"
            f"`/{item_type}_add Nama | nominal/jumlah satuan | kategori | deskripsi`"
        )

    name = parts[0]
    amount_raw = parts[1]
    category = parts[2] if len(parts) >= 3 else (
        "Other Asset" if item_type == "asset" else "Other Liability"
    )
    description = parts[3] if len(parts) >= 4 else ""

    if item_type == "asset":
        qty_info = parse_asset_quantity_input(amount_raw)
        if qty_info:
            name, category = guess_asset_category_and_name(name, category)
            asset_type = "gold" if ("emas" in name.lower() or str(category).lower() in ["gold", "emas"]) else "unit"
            return {
                "name": name,
                "amount": None,
                "category": category,
                "description": description,
                "asset_type": asset_type,
                "quantity": qty_info["quantity"],
                "unit": qty_info["unit"],
                "price_source": "manual",
                "price_per_unit": qty_info.get("price_per_unit"),
                "needs_unit_price": not bool(qty_info.get("price_per_unit")),
            }

    amount = parse_human_amount(amount_raw)
    if amount <= 0:
        raise ValueError("Nominal harus angka. Contoh: `8000000`, `2.4 juta`, atau aset satuan `41 gram`.")

    return {
        "name": name,
        "amount": amount,
        "category": category,
        "description": description,
        "asset_type": "manual",
        "quantity": None,
        "unit": "",
        "price_source": "",
        "price_per_unit": None,
        "needs_unit_price": False,
    }


def parse_natural_asset_add(text: str) -> dict | None:
    """
    Natural asset input sederhana:
    - add emas 41 gram
    - add laptop 1 buah
    - tambah aset emas 41 gram
    - tambah laptop 1 unit
    """
    raw = str(text or "").strip()
    match = re.fullmatch(
        r"(?:add|tambah)(?:\s+aset)?\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*(g|gr|gram|grams|buah|unit|pcs|pc|lembar|kg|kilogram)",
        raw,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    name_raw = match.group(1).strip()
    qty_raw = f"{match.group(2)} {match.group(3)}"
    qty_info = parse_asset_quantity_input(qty_raw)

    if not qty_info:
        return None

    name = name_raw.title()
    if name.lower() == "emas":
        name = "Emas"

    name, category = guess_asset_category_and_name(name)
    asset_type = "gold" if "emas" in name.lower() else "unit"

    return {
        "name": name,
        "amount": None,
        "category": category,
        "description": "",
        "asset_type": asset_type,
        "quantity": qty_info["quantity"],
        "unit": qty_info["unit"],
        "price_source": "manual",
        "price_per_unit": None,
        "needs_unit_price": True,
    }

def parse_pipe_update_args(args: list[str], command_name: str) -> tuple[str, dict]:
    """
    Format:
    /asset_update asset_xxx | value=9000000 | category=Electronics
    /liability_update liab_xxx | balance=1000000
    """
    raw = " ".join(args).strip()

    if not raw:
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh:\n"
            f"`/{command_name} id_xxx | value=9000000`"
        )

    parts = [p.strip() for p in raw.split("|") if p.strip()]

    if len(parts) < 2:
        raise ValueError(
            f"Format belum lengkap.\n\n"
            f"Contoh:\n"
            f"`/{command_name} id_xxx | value=9000000`"
        )

    record_id = parts[0]
    update_parts = parts[1:]

    updates = {}

    for part in update_parts:
        if "=" not in part:
            raise ValueError(f"Format `{part}` salah. Gunakan field=value.")

        field, value = part.split("=", 1)
        field = field.strip()
        value = value.strip()

        if not field or not value:
            raise ValueError(f"Format `{part}` salah. Field dan value wajib diisi.")

        updates[field] = value

    return record_id, updates


def short_networth_id(record_id: str) -> str:
    record_id = str(record_id or "")
    if len(record_id) <= 18:
        return record_id
    return record_id[:18] + "..."


def build_networth_text(summary: dict) -> str:
    total_accounts = summary.get("total_accounts", 0)
    total_assets = summary.get("total_assets", 0)
    total_liabilities = summary.get("total_liabilities", 0)
    net_worth = summary.get("net_worth", 0)

    accounts = summary.get("accounts", [])
    assets = summary.get("assets", [])
    liabilities = summary.get("liabilities", [])

    lines = ["💎 *Net Worth Tracker*\n"]

    lines.append(f"💰 Saldo rekening : *{format_rupiah(total_accounts)}*")
    lines.append(f"📦 Total aset     : *{format_rupiah(total_assets)}*")
    lines.append(f"💳 Liabilitas     : *{format_rupiah(total_liabilities)}*")
    lines.append(f"🏁 *Net Worth     : {format_rupiah(net_worth)}*\n")

    if accounts:
        lines.append("*Rekening:*")
        for acc in accounts:
            name = acc.get("account_name", "-")
            balance = float(acc.get("balance", 0) or 0)
            lines.append(f"• {name}: {format_rupiah(balance)}")

    if assets:
        lines.append("\n*Aset aktif:*")
        for asset in assets:
            name = asset.get("name", "-")
            category = asset.get("category", "-")
            value = float(asset.get("current_value", 0) or 0)

            if str(asset.get("asset_type", "")).strip().lower() == "gold":
                qty = asset.get("quantity", "-")
                unit = asset.get("unit", "gram") or "gram"
                price = float(asset.get("price_per_unit", 0) or 0)
                lines.append(
                    f"• {name} ({qty} {unit}) — "
                    f"{format_rupiah(value)} "
                    f"@ {format_rupiah(price)}/gram"
                )
            else:
                lines.append(
                    f"• {name} "
                    f"({category}) — "
                    f"{format_rupiah(value)}"
                )

    if liabilities:
        lines.append("\n*Liabilitas aktif:*")
        for liability in liabilities:
            lines.append(
                f"• {liability.get('name', '-')} "
                f"({liability.get('category', '-')}) — "
                f"{format_rupiah(float(liability.get('current_balance', 0) or 0))}"
            )

    lines.append(
        "\nCommand:\n"
        "`/asset_add Nama | nominal | kategori | deskripsi`\n"
        "`/asset_update asset_id | value=nominal`\n"
        "`/asset_off asset_id`\n"
        "`/liability_add Nama | nominal | kategori | deskripsi`\n"
        "`/liability_update liab_id | balance=nominal`\n"
        "`/liability_off liab_id`\n"
        "`/networth_snapshot`"
    )

    return "\n".join(lines)


def build_assets_text(assets: list[dict]) -> str:
    if not assets:
        return (
            "📭 Belum ada aset aktif.\n\n"
            "Tambah aset:\n"
            "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`\n"
            "`/asset_add Emas Antam | 41 gram | Gold | Tabungan emas`\n"
            "atau natural: `add emas 41 gram`"
        )

    lines = ["📦 *Daftar Aset Aktif*\n"]

    total = 0

    for i, asset in enumerate(assets, 1):
        value = float(asset.get("current_value", 0) or 0)
        total += value

        quantity = asset.get("quantity", "")
        unit = asset.get("unit", "")
        price = float(asset.get("price_per_unit", 0) or 0)
        has_unit_info = bool(str(quantity or "").strip()) and bool(str(unit or "").strip())

        if has_unit_info:
            last_update = asset.get("last_price_update", "-") or "-"
            lines.append(
                f"{i}. *{asset.get('name', '-')}*\n"
                f"   🔢 {quantity} {unit}\n"
                f"   🏷️ Harga/{unit}: {format_rupiah(price)}\n"
                f"   💰 Nilai saat ini: *{format_rupiah(value)}*\n"
                f"   📅 Harga update: `{last_update}`\n"
                f"   📝 {asset.get('description', '-') or '-'}\n"
                f"   🔖 `{asset.get('id', '-')}`"
            )
        else:
            lines.append(
                f"{i}. *{asset.get('name', '-')}*\n"
                f"   💰 {format_rupiah(value)} | {asset.get('category', '-')}\n"
                f"   📝 {asset.get('description', '-') or '-'}\n"
                f"   🔖 `{asset.get('id', '-')}`"
            )

    lines.append(f"\n📦 Total aset aktif: *{format_rupiah(total)}*")

    lines.append(
        "\nEdit harga satuan:\n"
        "`/asset_update asset_id | unit_price=2420000`"
    )

    return "\n".join(lines)

def build_liabilities_text(liabilities: list[dict]) -> str:
    if not liabilities:
        return (
            "📭 Belum ada liabilitas aktif.\n\n"
            "Tambah liabilitas:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`"
        )

    lines = ["💳 *Daftar Liabilitas Aktif*\n"]

    total = 0

    for i, liability in enumerate(liabilities, 1):
        balance = float(liability.get("current_balance", 0) or 0)
        total += balance

        lines.append(
            f"{i}. *{liability.get('name', '-')}*\n"
            f"   💰 {format_rupiah(balance)} | {liability.get('category', '-')}\n"
            f"   📝 {liability.get('description', '-') or '-'}\n"
            f"   🔖 `{liability.get('id', '-')}`"
        )

    lines.append(f"\n💳 Total liabilitas aktif: *{format_rupiah(total)}*")

    return "\n".join(lines)


def build_update_result_text(result: dict, label: str) -> str:
    before = result.get("before", {}) or {}
    after = result.get("after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = [f"✅ {label} berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    for field in updates:
        if field == "updated_at":
            continue

        old_value = before.get(field, "-")
        new_value = after.get(field, updates.get(field, "-"))

        lines.append(f"- {field}: {old_value} → {new_value}")

    return "\n".join(lines)


def build_snapshots_text(snapshots: list[dict]) -> str:
    if not snapshots:
        return "📭 Belum ada snapshot net worth."

    lines = ["📈 *Riwayat Net Worth Snapshot*\n"]

    for snap in snapshots:
        lines.append(
            f"• `{snap.get('snapshot_date', '-')}` — "
            f"*{format_rupiah(float(snap.get('net_worth', 0) or 0))}*\n"
            f"  Rekening: {format_rupiah(float(snap.get('total_accounts', 0) or 0))} | "
            f"Aset: {format_rupiah(float(snap.get('total_assets', 0) or 0))} | "
            f"Liabilitas: {format_rupiah(float(snap.get('total_liabilities', 0) or 0))}"
        )

    return "\n".join(lines)

async def networth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /networth — lihat net worth summary
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    summary = calculate_net_worth()

    await update.message.reply_text(
        build_networth_text(summary),
        parse_mode="Markdown",
    )


async def assets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /assets — lihat daftar aset aktif
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    assets = get_assets(active_only=True)

    await update.message.reply_text(
        build_assets_text(assets),
        parse_mode="Markdown",
    )


async def liabilities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liabilities — lihat daftar liabilitas aktif
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    liabilities = get_liabilities(active_only=True)

    await update.message.reply_text(
        build_liabilities_text(liabilities),
        parse_mode="Markdown",
    )


def build_asset_added_text(asset: dict) -> str:
    quantity = asset.get("quantity", "")
    unit = asset.get("unit", "")
    price = float(asset.get("price_per_unit", 0) or 0)
    has_unit_info = bool(str(quantity or "").strip()) and bool(str(unit or "").strip())

    if has_unit_info:
        return (
            "✅ *Aset berhasil ditambahkan!*\n\n"
            f"📦 Nama: *{asset.get('name')}*\n"
            f"📁 Kategori: *{asset.get('category')}*\n"
            f"🔢 Jumlah: *{quantity} {unit}*\n"
            f"🏷️ Harga/{unit}: *{format_rupiah(price)}*\n"
            f"📊 Nilai saat ini: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*\n"
            f"📅 Update harga: `{asset.get('last_price_update') or '-'}`\n"
            f"📝 Deskripsi: {asset.get('description') or '-'}\n"
            f"🔖 ID: `{asset.get('id')}`"
        )

    return (
        "✅ *Aset berhasil ditambahkan!*\n\n"
        f"📦 Nama: *{asset.get('name')}*\n"
        f"💰 Nilai: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*\n"
        f"📁 Kategori: *{asset.get('category')}*\n"
        f"📝 Deskripsi: {asset.get('description') or '-'}\n"
        f"🔖 ID: `{asset.get('id')}`"
    )


def build_asset_confirm_preview(data: dict) -> str:
    """Preview tambah aset sebelum disimpan."""
    quantity = data.get("quantity")
    unit = data.get("unit", "") or ""
    price = float(data.get("price_per_unit", 0) or 0)

    if quantity not in [None, ""] and str(unit).strip():
        current_value = float(data.get("amount") or (float(quantity or 0) * price))
        data["amount"] = current_value

        return (
            "📦 *Preview Tambah Aset*\n\n"
            f"Nama: *{md_safe(data.get('name') or '-')}*\n"
            f"Kategori: *{md_safe(data.get('category') or 'Other Asset')}*\n"
            f"Jumlah: *{quantity} {md_safe(unit)}*\n"
            f"Harga/{md_safe(unit)}: *{format_rupiah(price)}*\n"
            f"Nilai saat ini: *{format_rupiah(current_value)}*\n"
            f"Deskripsi: {md_safe(data.get('description') or '-')}\n\n"
            "Simpan aset ini?"
        )

    current_value = float(data.get("amount", 0) or 0)
    return (
        "📦 *Preview Tambah Aset*\n\n"
        f"Nama: *{md_safe(data.get('name') or '-')}*\n"
        f"Kategori: *{md_safe(data.get('category') or 'Other Asset')}*\n"
        f"Nilai: *{format_rupiah(current_value)}*\n"
        f"Deskripsi: {md_safe(data.get('description') or '-')}\n\n"
        "Simpan aset ini?"
    )


async def asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_add Nama | nominal | kategori | deskripsi
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        data = parse_pipe_add_args(context.args, "asset")

        if data.get("needs_unit_price"):
            context.user_data["pending_asset_price"] = data
            await update.message.reply_text(
                build_asset_unit_price_prompt(data),
                parse_mode="Markdown",
            )
            return

        context.user_data["pending_asset_confirm"] = data
        context.user_data.pop("pending_asset_price", None)

        await update.message.reply_text(
            build_asset_confirm_preview(data),
            parse_mode="Markdown",
            reply_markup=confirm_keyboard("asset"),
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal tambah aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`\n"
            "`/asset_add Emas Antam | 41 gram | Gold | Tabungan emas`\n"
            "`/asset_add Laptop | 1 buah | Electronics | Laptop kerja`",
            parse_mode="Markdown",
        )


async def liability_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liability_add Nama | nominal | kategori | deskripsi
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        data = parse_pipe_add_args(context.args, "liability")

        liability = add_liability(
            name=data["name"],
            current_balance=data["amount"],
            category=data["category"],
            description=data["description"],
        )

        await update.message.reply_text(
            "✅ *Liabilitas berhasil ditambahkan!*\n\n"
            f"💳 Nama: *{liability.get('name')}*\n"
            f"💰 Nominal: *{format_rupiah(float(liability.get('current_balance', 0) or 0))}*\n"
            f"📁 Kategori: *{liability.get('category')}*\n"
            f"📝 Deskripsi: {liability.get('description') or '-'}\n"
            f"🔖 ID: `{liability.get('id')}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal tambah liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`",
            parse_mode="Markdown",
        )


async def asset_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_update asset_id | value=9000000 | category=Electronics
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        asset_id, updates = parse_pipe_update_args(context.args, "asset_update")
        result = update_asset(asset_id, updates)

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/assets`",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_update_result_text(result, "Aset")
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal update aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_update asset_xxx | value=9000000`\n"
            "`/asset_update asset_xxx | unit_price=2420000`\n"
            "`/asset_update asset_xxx | name=Laptop Baru | category=Electronics`",
            parse_mode="Markdown",
        )


async def liability_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liability_update liab_id | balance=1000000
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        liability_id, updates = parse_pipe_update_args(context.args, "liability_update")
        result = update_liability(liability_id, updates)

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/liabilities`",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text(
            build_update_result_text(result, "Liabilitas")
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal update liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_update liab_xxx | balance=1000000`\n"
            "`/liability_update liab_xxx | name=Paylater Shopee | balance=500000`",
            parse_mode="Markdown",
        )


async def asset_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_off asset_id
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan asset ID.\n\n"
            "Contoh:\n"
            "`/asset_off asset_xxx`",
            parse_mode="Markdown",
        )
        return

    asset_id = context.args[0].strip()
    success = deactivate_asset(asset_id)

    if not success:
        await update.message.reply_text("❌ Asset tidak ditemukan.")
        return

    await update.message.reply_text(
        f"✅ Asset berhasil dinonaktifkan:\n`{asset_id}`",
        parse_mode="Markdown",
    )


async def liability_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /liability_off liab_id
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Masukkan liability ID.\n\n"
            "Contoh:\n"
            "`/liability_off liab_xxx`",
            parse_mode="Markdown",
        )
        return

    liability_id = context.args[0].strip()
    success = deactivate_liability(liability_id)

    if not success:
        await update.message.reply_text("❌ Liability tidak ditemukan.")
        return

    await update.message.reply_text(
        f"✅ Liability berhasil dinonaktifkan:\n`{liability_id}`",
        parse_mode="Markdown",
    )


async def networth_snapshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /networth_snapshot — simpan snapshot net worth hari ini
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        snapshot = create_net_worth_snapshot()

        await update.message.reply_text(
            "✅ *Snapshot Net Worth berhasil disimpan!*\n\n"
            f"📅 Tanggal: `{snapshot.get('snapshot_date')}`\n"
            f"💰 Rekening: *{format_rupiah(float(snapshot.get('total_accounts', 0) or 0))}*\n"
            f"📦 Aset: *{format_rupiah(float(snapshot.get('total_assets', 0) or 0))}*\n"
            f"💳 Liabilitas: *{format_rupiah(float(snapshot.get('total_liabilities', 0) or 0))}*\n"
            f"🏁 Net Worth: *{format_rupiah(float(snapshot.get('net_worth', 0) or 0))}*",
            parse_mode="Markdown",
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Gagal menyimpan snapshot net worth: {str(e)}"
        )


async def networth_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /networth_history — lihat snapshot terakhir
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    snapshots = get_net_worth_snapshots(limit=12)

    await update.message.reply_text(
        build_snapshots_text(snapshots),
        parse_mode="Markdown",
    )

