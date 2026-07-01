# Dipisah dari app/bot/handlers.py agar file utama tidak terlalu besar.
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

    Kembalikan dict {quantity, unit, price_per_unit?} atau None.
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
    """Parsing satu token nominal: 2410000, 2.41jt, 2,41 juta, 91.457k."""
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
    """Parsing angka manusia, termasuk ekspresi edit seperti `94k/2`.

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


def parse_asset_extra_fields(extra_parts: list[str]) -> dict:
    """Parsing field opsional asset add setelah description.

    Mendukung:
    - harga_beli=2559000 | tanggal_beli=2026-06-10
    - buy_price=2.4 juta | buy_date=10/06/2026
    - 2559000 | 2026-06-10  (fallback berdasarkan posisi)
    """
    result = {
        "purchase_price_per_unit": None,
        "purchase_date": "",
    }

    positional = []
    for part in extra_parts or []:
        raw = str(part or "").strip()
        if not raw:
            continue

        if "=" in raw:
            key, value = raw.split("=", 1)
            key = key.strip().lower()
            value = value.strip()

            if key in [
                "purchase_price", "purchase_price_per_unit", "buy_price",
                "harga_beli", "modal", "harga_modal",
            ]:
                result["purchase_price_per_unit"] = parse_human_amount(value)
            elif key in ["purchase_date", "buy_date", "tanggal_beli", "tgl_beli"]:
                result["purchase_date"] = value
            else:
                positional.append(raw)
        else:
            positional.append(raw)

    if positional and not result.get("purchase_price_per_unit"):
        maybe_price = parse_human_amount(positional[0])
        if maybe_price > 0:
            result["purchase_price_per_unit"] = maybe_price

    if len(positional) >= 2 and not result.get("purchase_date"):
        result["purchase_date"] = positional[1]

    return result


def format_asset_gain_lines(asset: dict, indent: str = "   ") -> list[str]:
    gain = calculate_asset_gain(asset)
    if not gain.get("has_purchase_info"):
        return []

    unit = asset.get("unit", "unit") or "unit"
    purchase_price = gain.get("purchase_price_per_unit", 0)
    purchase_total = gain.get("purchase_total", 0)
    gain_loss = gain.get("gain_loss", 0)
    gain_pct = gain.get("gain_loss_pct", 0)
    sign = "+" if gain_loss >= 0 else "-"

    lines = [
        f"{indent}🧾 Harga beli/{unit}: {format_rupiah(purchase_price)}",
        f"{indent}💼 Modal beli: {format_rupiah(purchase_total)}",
    ]

    purchase_date = asset.get("purchase_date")
    if purchase_date:
        lines.append(f"{indent}📆 Tanggal beli: `{purchase_date}`")

    lines.append(
        f"{indent}📈 Floating P/L: {sign}{format_rupiah(abs(gain_loss))} ({gain_pct:+.2f}%)"
    )
    return lines


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
    asset_extra = parse_asset_extra_fields(parts[4:]) if item_type == "asset" else {}

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
                "purchase_price_per_unit": asset_extra.get("purchase_price_per_unit"),
                "purchase_date": asset_extra.get("purchase_date", ""),
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
        "purchase_price_per_unit": asset_extra.get("purchase_price_per_unit"),
        "purchase_date": asset_extra.get("purchase_date", ""),
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
        "purchase_price_per_unit": None,
        "purchase_date": "",
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
    net_worth = summary.get("net_worth", 0)

    accounts = summary.get("accounts", [])
    assets = summary.get("assets", [])

    lines = ["💎 *Net Worth Tracker*\n"]

    lines.append(f"💰 Saldo rekening : *{format_rupiah(total_accounts)}*")
    lines.append(f"📦 Total aset     : *{format_rupiah(total_assets)}*")
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
                gain = calculate_asset_gain(asset)
                gain_suffix = ""
                if gain.get("has_purchase_info"):
                    gl = gain.get("gain_loss", 0)
                    pct = gain.get("gain_loss_pct", 0)
                    sign = "+" if gl >= 0 else "-"
                    gain_suffix = f" | P/L {sign}{format_rupiah(abs(gl))} ({pct:+.2f}%)"

                lines.append(
                    f"• {name} ({qty} {unit}) — "
                    f"{format_rupiah(value)} "
                    f"@ {format_rupiah(price)}/{unit}"
                    f"{gain_suffix}"
                )
            else:
                lines.append(
                    f"• {name} "
                    f"({category}) — "
                    f"{format_rupiah(value)}"
                )


    lines.append(
        "\nCommand:\n"
        "`/asset_add Nama | nominal | kategori | deskripsi`\n"
        "`/asset_update asset_id | value=nominal`\n"
        "`/asset_off asset_id`\n"
        "`/networth_snapshot`"
    )

    return "\n".join(lines)


def build_assets_text(assets: list[dict]) -> str:
    if not assets:
        return (
            "📭 Belum ada aset aktif.\n\n"
            "Tambah aset:\n"
            "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`\n"
            "`/asset_add Emas Antam | 41 gram | Gold | Tabungan emas | harga_beli=2559000 | tanggal_beli=2026-06-10`\n"
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
            block_lines = [
                f"{i}. *{asset.get('name', '-')}*",
                f"   🔢 {quantity} {unit}",
                f"   🏷️ Harga sekarang/{unit}: {format_rupiah(price)}",
                f"   💰 Nilai saat ini: *{format_rupiah(value)}*",
                f"   📅 Harga update: `{last_update}`",
            ]
            block_lines.extend(format_asset_gain_lines(asset))
            block_lines.extend([
                f"   📝 {asset.get('description', '-') or '-'}",
                f"   🔖 `{asset.get('id', '-')}`",
            ])
            lines.append("\n".join(block_lines))
        else:
            block_lines = [
                f"{i}. *{asset.get('name', '-')}*",
                f"   💰 {format_rupiah(value)} | {asset.get('category', '-')}",
            ]
            block_lines.extend(format_asset_gain_lines(asset))
            block_lines.extend([
                f"   📝 {asset.get('description', '-') or '-'}",
                f"   🔖 `{asset.get('id', '-')}`",
            ])
            lines.append("\n".join(block_lines))

    lines.append(f"\n📦 Total aset aktif: *{format_rupiah(total)}*")

    lines.append(
        "\nEdit harga / harga beli:\n"
        "`/asset_update asset_id | unit_price=2420000`\n"
        "`/asset_update asset_id | harga_beli=2559000 | tanggal_beli=2026-06-10`"
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
            f"Aset: {format_rupiah(float(snap.get('total_assets', 0) or 0))}"
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
        lines = [
            "✅ *Aset berhasil ditambahkan!*\n",
            f"📦 Nama: *{asset.get('name')}*",
            f"📁 Kategori: *{asset.get('category')}*",
            f"🔢 Jumlah: *{quantity} {unit}*",
            f"🏷️ Harga sekarang/{unit}: *{format_rupiah(price)}*",
            f"📊 Nilai saat ini: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*",
            f"📅 Update harga: `{asset.get('last_price_update') or '-'}`",
        ]
        lines.extend(format_asset_gain_lines(asset, indent=""))
        lines.extend([
            f"📝 Deskripsi: {asset.get('description') or '-'}",
            f"🔖 ID: `{asset.get('id')}`",
        ])
        return "\n".join(lines)

    lines = [
        "✅ *Aset berhasil ditambahkan!*\n",
        f"📦 Nama: *{asset.get('name')}*",
        f"💰 Nilai: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*",
        f"📁 Kategori: *{asset.get('category')}*",
    ]
    lines.extend(format_asset_gain_lines(asset, indent=""))
    lines.extend([
        f"📝 Deskripsi: {asset.get('description') or '-'}",
        f"🔖 ID: `{asset.get('id')}`",
    ])
    return "\n".join(lines)


def asset_edit_or_continue_keyboard() -> InlineKeyboardMarkup:
    """Keyboard preview aset tanpa import transaction_flow agar tidak terjadi circular import."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit dulu", callback_data="editflow:edit:asset"),
            InlineKeyboardButton("➡️ Lanjut", callback_data="editflow:continue:asset"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:asset")],
    ])


def build_asset_confirm_preview(data: dict) -> str:
    """Preview tambah aset sebelum disimpan."""
    quantity = data.get("quantity")
    unit = data.get("unit", "") or ""
    price = float(data.get("price_per_unit", 0) or 0)
    purchase_price = float(data.get("purchase_price_per_unit", 0) or 0)
    purchase_date = data.get("purchase_date", "") or ""

    if quantity not in [None, ""] and str(unit).strip():
        current_value = float(data.get("amount") or (float(quantity or 0) * price))
        data["amount"] = current_value

        lines = [
            "📦 *Preview Tambah Aset*\n",
            f"Nama: *{md_safe(data.get('name') or '-')}*",
            f"Kategori: *{md_safe(data.get('category') or 'Other Asset')}*",
            f"Jumlah: *{quantity} {md_safe(unit)}*",
            f"Harga sekarang/{md_safe(unit)}: *{format_rupiah(price)}*",
            f"Nilai saat ini: *{format_rupiah(current_value)}*",
        ]

        if purchase_price > 0:
            modal = float(quantity or 0) * purchase_price
            floating = current_value - modal
            pct = (floating / modal * 100) if modal > 0 else 0
            sign = "+" if floating >= 0 else "-"
            lines.extend([
                f"Harga beli/{md_safe(unit)}: *{format_rupiah(purchase_price)}*",
                f"Modal beli: *{format_rupiah(modal)}*",
                f"Floating P/L: *{sign}{format_rupiah(abs(floating))} ({pct:+.2f}%)*",
            ])

        if purchase_date:
            lines.append(f"Tanggal beli: `{md_safe(purchase_date)}`")

        lines.extend([
            f"Deskripsi: {md_safe(data.get('description') or '-')}",
            "\nSimpan aset ini?",
        ])
        return "\n".join(lines)

    current_value = float(data.get("amount", 0) or 0)
    lines = [
        "📦 *Preview Tambah Aset*\n",
        f"Nama: *{md_safe(data.get('name') or '-')}*",
        f"Kategori: *{md_safe(data.get('category') or 'Other Asset')}*",
        f"Nilai: *{format_rupiah(current_value)}*",
    ]

    if purchase_price > 0:
        lines.append(f"Harga beli/modal: *{format_rupiah(purchase_price)}*")
    if purchase_date:
        lines.append(f"Tanggal beli: `{md_safe(purchase_date)}`")

    lines.extend([
        f"Deskripsi: {md_safe(data.get('description') or '-')}",
        "\nSimpan aset ini?",
    ])
    return "\n".join(lines)


ASSET_ADD_FLOW_KEY = "pending_asset_add_flow"
ASSET_ADD_SKIP_WORDS = {"skip", "lewati", "kosong", "-", "tidak", "tidak ada", "ga ada", "gak ada", "nggak ada"}
ASSET_ADD_CANCEL_WORDS = {"cancel", "batal", "/cancel"}


def _asset_flow_is_skip(text: str) -> bool:
    return str(text or "").strip().lower() in ASSET_ADD_SKIP_WORDS


def _asset_flow_is_cancel(text: str) -> bool:
    return str(text or "").strip().lower() in ASSET_ADD_CANCEL_WORDS


def _asset_flow_prompt(step: str, data: dict | None = None) -> str:
    data = data or {}

    prompts = {
        "name": (
            "📦 *Tambah Aset — Step 1/7*\n\n"
            "Asetnya apa?\n\n"
            "Contoh:\n"
            "`Emas Antam`\n"
            "`Laptop Kerja`"
        ),
        "quantity": (
            "🔢 *Tambah Aset — Step 2/7*\n\n"
            f"Aset: *{md_safe(data.get('name') or '-')}*\n\n"
            "Berapa jumlah/unitnya?\n\n"
            "Contoh aset satuan:\n"
            "`41 gram`\n"
            "`1 buah`\n\n"
            "Kalau aset tidak berbasis unit, ketik nilai saat ini langsung:\n"
            "`8000000`"
        ),
        "purchase_price": (
            "🧾 *Tambah Aset — Step 3/7*\n\n"
            "Harga belinya berapa?\n\n"
            "Untuk aset satuan, isi harga beli per unit.\n"
            "Contoh:\n"
            "`2559000`\n"
            "`2.55 juta`\n\n"
            "Kalau belum mau diisi, ketik `lewati`."
        ),
        "purchase_date": (
            "📆 *Tambah Aset — Step 4/7*\n\n"
            "Tanggal belinya kapan?\n\n"
            "Contoh:\n"
            "`2026-06-10`\n"
            "`10/06/2026`\n"
            "`kemarin`\n\n"
            "Kalau tidak tahu / tidak mau isi, ketik `lewati`."
        ),
        "current_price": (
            "🏷️ *Tambah Aset — Step 5/7*\n\n"
            f"Jumlah: *{data.get('quantity')} {md_safe(data.get('unit') or '')}*\n\n"
            "Harga saat ini per unit berapa?\n\n"
            "Contoh:\n"
            "`2594000`\n"
            "`2.594 juta`"
        ),
        "category": (
            "📁 *Tambah Aset — Step 6/7*\n\n"
            "Kategorinya apa?\n\n"
            "Contoh:\n"
            "`Gold`\n"
            "`Electronics`\n"
            "`Investment`\n\n"
            "Kalau mau otomatis, ketik `lewati`."
        ),
        "description": (
            "📝 *Tambah Aset — Step 7/7*\n\n"
            "Deskripsinya apa?\n\n"
            "Contoh:\n"
            "`Tabungan emas`\n"
            "`Laptop kerja`\n\n"
            "Kalau kosong, ketik `lewati`."
        ),
    }

    return prompts.get(step, "Input tidak dikenali. Ketik `batal` untuk membatalkan.") + "\n\nTekan tombol ❌ Batal atau ketik `batal` untuk cancel."


def start_asset_add_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("pending_asset_price", None)
    context.user_data.pop("pending_asset_confirm", None)
    context.user_data[ASSET_ADD_FLOW_KEY] = {
        "step": "name",
        "data": {},
    }


def _build_asset_data_from_flow(data: dict) -> dict:
    name = str(data.get("name") or "").strip()
    category = str(data.get("category") or "").strip()
    name, category = guess_asset_category_and_name(name, category)

    quantity = data.get("quantity")
    unit = data.get("unit", "") or ""
    price_per_unit = data.get("price_per_unit")
    current_value = data.get("amount")

    if quantity not in [None, ""] and str(unit).strip():
        asset_type = "gold" if ("emas" in name.lower() or category.lower() in ["gold", "emas"]) else "unit"
        amount = float(quantity or 0) * float(price_per_unit or 0)
    else:
        asset_type = "manual"
        amount = float(current_value or 0)
        quantity = None
        unit = ""
        price_per_unit = None

    return {
        "name": name,
        "amount": amount,
        "category": category,
        "description": str(data.get("description") or "").strip(),
        "asset_type": asset_type,
        "quantity": quantity,
        "unit": unit,
        "price_source": "manual" if price_per_unit else "",
        "price_per_unit": price_per_unit,
        "purchase_price_per_unit": data.get("purchase_price_per_unit"),
        "purchase_date": data.get("purchase_date", "") or "",
        "needs_unit_price": False,
    }


async def handle_pending_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    flow = context.user_data.get(ASSET_ADD_FLOW_KEY)
    if not flow:
        return False

    text = str(user_text or "").strip()

    if _asset_flow_is_cancel(text):
        context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
        context.user_data.pop("pending_asset_price", None)
        context.user_data.pop("pending_asset_confirm", None)
        await update.message.reply_text("❌ Tambah aset dibatalkan.")
        return True

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    if step == "name":
        if not text:
            await update.message.reply_text(_asset_flow_prompt("name", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
            return True
        data["name"] = text
        flow["step"] = "quantity"
        await update.message.reply_text(_asset_flow_prompt("quantity", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
        return True

    if step == "quantity":
        qty_info = parse_asset_quantity_input(text)
        if qty_info:
            data["quantity"] = qty_info["quantity"]
            data["unit"] = qty_info["unit"]
            if qty_info.get("price_per_unit"):
                data["price_per_unit"] = qty_info.get("price_per_unit")
            flow["step"] = "purchase_price"
            await update.message.reply_text(_asset_flow_prompt("purchase_price", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
            return True

        amount = parse_human_amount(text)
        if amount > 0:
            data["amount"] = amount
            data["quantity"] = None
            data["unit"] = ""
            data["price_per_unit"] = None
            flow["step"] = "purchase_price"
            await update.message.reply_text(_asset_flow_prompt("purchase_price", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
            return True

        await update.message.reply_text(
            "❌ Jumlah/nilai aset belum valid.\n\n"
            "Contoh: `41 gram`, `1 buah`, atau `8000000`.",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return True

    if step == "purchase_price":
        if _asset_flow_is_skip(text):
            data["purchase_price_per_unit"] = None
        else:
            purchase_price = parse_human_amount(text)
            if purchase_price <= 0:
                await update.message.reply_text(
                    "❌ Harga beli belum valid. Contoh: `2559000`, `2.55 juta`, atau ketik `lewati`.",
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard(),
                )
                return True
            data["purchase_price_per_unit"] = purchase_price

        flow["step"] = "purchase_date"
        await update.message.reply_text(_asset_flow_prompt("purchase_date", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
        return True

    if step == "purchase_date":
        if _asset_flow_is_skip(text):
            data["purchase_date"] = ""
        else:
            data["purchase_date"] = detect_date(text)

        if data.get("quantity") not in [None, ""] and str(data.get("unit") or "").strip() and not data.get("price_per_unit"):
            flow["step"] = "current_price"
            await update.message.reply_text(_asset_flow_prompt("current_price", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
            return True

        flow["step"] = "category"
        await update.message.reply_text(_asset_flow_prompt("category", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
        return True

    if step == "current_price":
        current_price = parse_human_amount(text)
        if current_price <= 0:
            await update.message.reply_text(
                "❌ Harga saat ini belum valid. Contoh: `2594000` atau `2.594 juta`.",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard(),
            )
            return True
        data["price_per_unit"] = current_price
        data["amount"] = float(data.get("quantity") or 0) * current_price
        flow["step"] = "category"
        await update.message.reply_text(_asset_flow_prompt("category", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
        return True

    if step == "category":
        data["category"] = "" if _asset_flow_is_skip(text) else text
        flow["step"] = "description"
        await update.message.reply_text(_asset_flow_prompt("description", data), parse_mode="Markdown", reply_markup=cancel_keyboard())
        return True

    if step == "description":
        data["description"] = "" if _asset_flow_is_skip(text) else text
        asset_data = _build_asset_data_from_flow(data)
        context.user_data["pending_asset_confirm"] = asset_data
        context.user_data.pop(ASSET_ADD_FLOW_KEY, None)

        await update.message.reply_text(
            f"{build_asset_confirm_preview(asset_data)}\n\nMau edit dulu atau lanjut ke simpan?",
            parse_mode="Markdown",
            reply_markup=asset_edit_or_continue_keyboard(),
        )
        return True

    context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
    await update.message.reply_text("❌ Sesi tambah aset tidak valid. Coba ulangi `/asset_add`.", parse_mode="Markdown")
    return True


async def asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /asset_add Nama | nominal | kategori | deskripsi
    """
    if not is_authorized(update):
        await reject_unauthorized(update)
        return

    try:
        if not context.args:
            start_asset_add_flow(context)
            await update.message.reply_text(
                _asset_flow_prompt("name", {}),
                parse_mode="Markdown",
                reply_markup=cancel_keyboard(),
            )
            return

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
            f"{build_asset_confirm_preview(data)}\n\nMau edit dulu atau lanjut ke simpan?",
            parse_mode="Markdown",
            reply_markup=asset_edit_or_continue_keyboard(),
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ Gagal tambah aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_add Laptop | 8000000 | Electronics | Laptop kerja`\n"
            "`/asset_add Emas Antam | 41 gram | Gold | Tabungan emas | harga_beli=2559000 | tanggal_beli=2026-06-10`\n"
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
            "`/asset_update asset_xxx | harga_beli=2559000 | tanggal_beli=2026-06-10`\n"
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

