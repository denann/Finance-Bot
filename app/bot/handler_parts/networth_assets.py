"""Handlers for assets and net worth features, including asset creation, updates, deactivation, snapshots, and history."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

# Helper for parse asset quantity input.
def parse_asset_quantity_input(value: str) -> dict | None:
    """Parse caller input for the parse asset quantity input workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `dict | None` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower()
    raw = raw.replace("@", " @ ")
    raw = re.sub(r"\s+", " ", raw).strip()

    match = re.fullmatch(
        r"(\d+(?:[.,]\d+)?)\s*(g|gr|gram|grams|buah|unit|pcs|pc|lembar|kg|kilogram)(?:\s*@\s*([0-9.,]+)\s*(?:rb|ribu|k|jt|juta)?)?",
        raw,
        flags=re.IGNORECASE,
    )

    # Validate missing match before continuing.
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

    # Prepare price raw from the incoming input.
    price_raw = match.group(3)
    price_per_unit = parse_human_amount(price_raw) if price_raw else None

    return {
        "quantity": quantity,
        "unit": unit,
        "price_per_unit": price_per_unit,
    }


# Helper for parse human amount atom.
def _parse_human_amount_atom(value: str | None) -> float:
    """Parse caller input for the parse human amount atom workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower()
    # Validate missing raw before continuing.
    if not raw:
        return 0.0

    multiplier = 1
    if re.search(r"(jt|juta)\b", raw):
        multiplier = 1_000_000
    elif re.search(r"(rb|ribu|k)\b", raw):
        multiplier = 1_000

    raw = re.sub(r"(jt|juta|rb|ribu|k)\b", "", raw).strip()

    if multiplier != 1:
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)
        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)
        return float(raw or 0) * multiplier

    raw = re.sub(r"[^0-9]", "", raw)
    return float(raw or 0)


# Helper for safe eval amount expression.
def _safe_eval_amount_expression(expr: str) -> float:
    """Coordinate the safe eval amount expression logic in the Telegram handler layer.

    Args:
        expr: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Helper for eval.
    def _eval(node):
        """Coordinate the eval logic in the Telegram handler layer.

        Args:
            node: Input value supplied by the caller; accepted shape follows the function signature and local validation.

        Returns:
            Value produced by the existing return statements; shape is determined by the current implementation.

        Side effects:
            May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

        Flow constraints:
            Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
        """
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


# Helper for parse human amount.
def parse_human_amount(value: str | None) -> float:
    """Parse caller input for the parse human amount workflow in the Telegram handler layer.

    Args:
        value: Raw value supplied by the caller.

    Returns:
        `float` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = str(value or "").strip().lower()
    # Validate missing raw before continuing.
    if not raw:
        return 0.0

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    if has_math_operator:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        # Helper for repl.
        def repl(match: re.Match) -> str:
            """Coordinate the repl logic in the Telegram handler layer.

            Args:
                match: Input value supplied by the caller; accepted shape follows the function signature and local validation.

            Returns:
                `str` value as defined by the function signature.

            Side effects:
                May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

            Flow constraints:
                Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
            """
            token = match.group(0)
            return str(_parse_human_amount_atom(token))

        expr = token_pattern.sub(repl, raw)
        expr = expr.replace("×", "*").replace("x", "*").replace(":", "/")
        expr = re.sub(r"\s+", "", expr)
        if re.fullmatch(r"[0-9.+\-*/()]+", expr):
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Build result for the response flow.
                result = _safe_eval_amount_expression(expr)
                if result > 0:
                    return result
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass

    return _parse_human_amount_atom(raw)


# Helper for parse asset extra fields.
def parse_asset_extra_fields(extra_parts: list[str]) -> dict:
    """Parse caller input for the parse asset extra fields workflow in the Telegram handler layer.

    Args:
        extra_parts: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    result = {
        "purchase_price_per_unit": None,
        "purchase_date": "",
    }

    positional = []
    # Iterate through each part.
    for part in extra_parts or []:
        raw = str(part or "").strip()
        # Validate missing raw before continuing.
        if not raw:
            # Skip the rest of this loop iteration after handling this case.
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
            # Use the fallback path when no earlier branch matched.
            else:
                # Append the current value to positional.
                positional.append(raw)
        # Use the fallback path when no earlier branch matched.
        else:
            # Append the current value to positional.
            positional.append(raw)

    if positional and not result.get("purchase_price_per_unit"):
        maybe_price = parse_human_amount(positional[0])
        if maybe_price > 0:
            result["purchase_price_per_unit"] = maybe_price

    if len(positional) >= 2 and not result.get("purchase_date"):
        result["purchase_date"] = positional[1]

    return result


def parse_add_key_value_args(args: list[str], item_type: str) -> dict:
    """Parse one-line add commands that use the project-wide `key=value` style.

    Args:
        args: Command arguments after `/asset_add` or `/liability_add`. Values
            may be quoted, for example `name="Laptop Kerja" amount=8jt`.
        item_type: Supported value is `asset` or `liability`.

    Returns:
        Dict shaped like `parse_pipe_add_args`, ready for preview or service
        calls. Asset dicts include `name`, `amount`, `category`,
        `description`, optional unit fields, purchase metadata, and
        `needs_unit_price`.

    Side effects:
        None.

    Flow constraints:
        Keep old pipe and guided input compatible. This helper only standardizes
        structured one-line add commands and does not write to Google Sheets.
    """
    raw = " ".join(args or []).strip()
    if not raw:
        raise ValueError("Format kosong. Contoh: `/asset_add name=Botol amount=100k category=Barang`")

    # Preserve quoted values and collect continuation words until the next key=value token.
    try:
        tokens = shlex.split(raw)
    except Exception:
        tokens = raw.split()

    values = {}
    i = 0
    while i < len(tokens):
        token = str(tokens[i] or "").strip()
        if "=" not in token:
            raise ValueError(f"Format `{token}` salah. Gunakan field=value.")

        field, value = token.split("=", 1)
        field = field.strip().lower()
        value_parts = [value.strip()] if value.strip() else []
        i += 1

        while i < len(tokens) and "=" not in str(tokens[i] or ""):
            continuation = str(tokens[i] or "").strip()
            if continuation:
                value_parts.append(continuation)
            i += 1

        value = " ".join(value_parts).strip()
        if not field or not value:
            raise ValueError(f"Format `{token}` salah. Field dan value wajib diisi.")
        values[field] = value

    if item_type == "asset":
        # Map user-facing field aliases into the internal asset preview shape.
        name = values.get("name") or values.get("nama")
        if not name:
            raise ValueError("Field `name` wajib diisi. Contoh: `/asset_add name=Laptop amount=8jt`")

        category = values.get("category") or values.get("kategori") or "Other Asset"
        description = values.get("description") or values.get("desc") or values.get("deskripsi") or ""
        quantity_raw = values.get("quantity") or values.get("qty") or values.get("jumlah")
        unit = values.get("unit") or values.get("satuan") or ""
        current_raw = (
            values.get("current_value")
            or values.get("current_price")
            or values.get("amount")
            or values.get("value")
            or values.get("nilai")
            or values.get("nominal")
        )
        unit_price_raw = (
            values.get("unit_price")
            or values.get("price_per_unit")
            or values.get("harga_per_unit")
            or values.get("harga_satuan")
            or values.get("harga_sekarang")
            or values.get("price")
            or values.get("harga")
        )
        purchase_price_raw = (
            values.get("purchase_price")
            or values.get("purchase_price_per_unit")
            or values.get("buy_price")
            or values.get("harga_beli")
            or values.get("modal")
        )
        purchase_date = (
            values.get("purchase_date")
            or values.get("buy_date")
            or values.get("tanggal_beli")
            or values.get("tgl_beli")
            or ""
        )

        quantity = float(str(quantity_raw).replace(",", ".")) if quantity_raw not in [None, ""] else None
        current_value = parse_human_amount(current_raw) if current_raw else 0
        price_per_unit = parse_human_amount(unit_price_raw) if unit_price_raw else None
        purchase_price = parse_human_amount(purchase_price_raw) if purchase_price_raw else None

        if quantity not in [None, ""] or unit:
            if not quantity or quantity <= 0:
                raise ValueError("Field `quantity` harus lebih dari 0 untuk aset satuan.")
            if not str(unit).strip():
                raise ValueError("Field `unit` wajib diisi untuk aset satuan.")
            if not price_per_unit and current_value > 0:
                price_per_unit = current_value / float(quantity)
            name, category = guess_asset_category_and_name(str(name), str(category))
            asset_type = "gold" if ("emas" in str(name).lower() or str(category).lower() in ["gold", "emas"]) else "unit"
            return {
                "name": name,
                "amount": float(quantity) * float(price_per_unit or 0) if price_per_unit else None,
                "category": category,
                "description": description,
                "asset_type": asset_type,
                "quantity": quantity,
                "unit": str(unit).strip(),
                "price_source": "manual",
                "price_per_unit": price_per_unit,
                "purchase_price_per_unit": purchase_price,
                "purchase_date": purchase_date,
                "needs_unit_price": not bool(price_per_unit),
            }

        if current_value <= 0:
            raise ValueError("Field `amount` wajib lebih dari 0. Contoh: `/asset_add name=Laptop amount=8jt`")

        name, category = guess_asset_category_and_name(str(name), str(category))
        return {
            "name": name,
            "amount": current_value,
            "category": category,
            "description": description,
            "asset_type": values.get("asset_type") or values.get("type") or "manual",
            "quantity": None,
            "unit": "",
            "price_source": "",
            "price_per_unit": None,
            "purchase_price_per_unit": purchase_price,
            "purchase_date": purchase_date,
            "needs_unit_price": False,
        }

    if item_type == "liability":
        name = values.get("name") or values.get("nama")
        amount = parse_human_amount(values.get("amount") or values.get("balance") or values.get("nominal"))
        if not name or amount <= 0:
            raise ValueError("Format liability: `/liability_add name=Paylater amount=1200000 category=Paylater`")
        return {
            "name": name,
            "amount": amount,
            "category": values.get("category") or values.get("kategori") or "Other Liability",
            "description": values.get("description") or values.get("desc") or values.get("deskripsi") or "",
        }

    raise ValueError(f"Tipe add tidak dikenal: `{item_type}`")


def format_asset_gain_lines(asset: dict, indent: str = "   ") -> list[str]:
    """Format data into a readable display for asset gain lines."""
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


# Helper for guess asset category and name.
def guess_asset_category_and_name(name: str, category: str | None = None) -> tuple[str, str]:
    """Coordinate the guess asset category and name logic in the Telegram handler layer.

    Args:
        name: Input value supplied by the caller; accepted shape follows the function signature and local validation.
        category: Category name or category-like value from user input or sheet data.

    Returns:
        `tuple[str, str]` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Keep category name, type, symbol, and alias behavior consistent with the documented category flow.
    """
    name_clean = str(name or "").strip()
    category_clean = str(category or "").strip()
    low = name_clean.lower()

    if "emas" in low or category_clean.lower() in ["gold", "emas", "precious metal", "logam mulia"]:
        return name_clean or "Emas", category_clean or "Gold"

    return name_clean, category_clean or "Other Asset"


# Helper for build asset unit price prompt.
def build_asset_unit_price_prompt(data: dict) -> str:
    """Build the data structure or message text for asset unit price prompt."""
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

# Helper for parse pipe add args.
def parse_pipe_add_args(args: list[str], item_type: str) -> dict:
    """Parse caller input for the parse pipe add args workflow in the Telegram handler layer.

    Args:
        args: Command argument list or parsed argument values supplied by the caller.
        item_type: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    raw = " ".join(args).strip()

    # Validate missing raw before continuing.
    if not raw:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh:\n"
            f"`/{item_type}_add Laptop | 8000000 | Electronics | Laptop kerja`"
        )

    parts = [p.strip() for p in raw.split("|")]

    if len(parts) < 2:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format belum lengkap.\n\n"
            f"Format:\n"
            f"`/{item_type}_add Nama | nominal/jumlah satuan | kategori | deskripsi`"
        )

    name = parts[0]
    # Extract amount raw for validation.
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

    # Extract amount for validation.
    amount = parse_human_amount(amount_raw)
    if amount <= 0:
        raise ValueError("Nominal harus angka. Contoh: `8000000`, `2.4 juta`, atau aset satuan `999 gram`.")

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


# Helper for parse natural asset add.
def parse_natural_asset_add(text: str) -> dict | None:
    """Parse natural asset input before it falls back to expense parsing."""
    raw = str(text or "").strip()

    amount_match = re.fullmatch(
        r"(?:(?:catat|catet|add|tambah)\s+aset|aset)\s+(.+?)\s+"
        r"((?:rp\.?\s*)?\d[\d.,]*(?:\s*(?:rb|ribu|k|jt|juta|m|mio))?)",
        raw,
        flags=re.IGNORECASE,
    )
    if amount_match:
        # Prepare name raw from the incoming input.
        name_raw = amount_match.group(1).strip()
        # Extract amount for validation.
        amount = parse_human_amount(amount_match.group(2))
        if amount <= 0:
            return None

        name = name_raw.title()
        if name.lower() == "emas":
            name = "Emas"
        name, category = guess_asset_category_and_name(name)
        asset_type = "gold" if "emas" in name.lower() else "unit"

        return {
            "name": name,
            "amount": amount,
            "category": category,
            "description": "",
            "asset_type": asset_type,
            "quantity": 1,
            "unit": "unit",
            "price_source": "manual",
            "price_per_unit": amount,
            "purchase_price_per_unit": amount,
            "purchase_date": "",
            "needs_unit_price": False,
        }

    match = re.fullmatch(
        r"(?:add|tambah|catat|catet)(?:\s+aset)?\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*(g|gr|gram|grams|buah|unit|pcs|pc|lembar|kg|kilogram)",
        raw,
        flags=re.IGNORECASE,
    )

    # Validate missing match before continuing.
    if not match:
        return None

    # Prepare name raw from the incoming input.
    name_raw = match.group(1).strip()
    qty_raw = f"{match.group(2)} {match.group(3)}"
    qty_info = parse_asset_quantity_input(qty_raw)

    # Validate missing qty info before continuing.
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

# Helper for parse pipe update args.
def parse_pipe_update_args(args: list[str], command_name: str) -> tuple[str, dict]:
    """Parse update args and support both old pipe format and new key=value format."""
    raw = " ".join(args).strip()

    # Validate missing raw before continuing.
    if not raw:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh baru: `/{command_name} id_xxx amount=9000000`\n"
            f"Format lama tetap diterima, tapi format utama: `/{command_name} id_xxx amount=9000000`"
        )

    if "|" in raw:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        if len(parts) < 2:
            # Raise a clear error so the caller can stop this invalid flow.
            raise ValueError(
                f"Format belum lengkap.\n\n"
                f"Contoh: `/{command_name} id_xxx amount=9000000`"
            )
        record_id = parts[0]
        # Extract update tokens for validation.
        update_tokens = parts[1:]
    # Use the fallback path when no earlier branch matched.
    else:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare tokens from the incoming input.
            tokens = shlex.split(raw)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Prepare tokens from the incoming input.
            tokens = raw.split()
        if len(tokens) < 2:
            # Raise a clear error so the caller can stop this invalid flow.
            raise ValueError(
                f"Format belum lengkap.\n\n"
                f"Contoh: `/{command_name} id_xxx amount=9000000`"
            )
        record_id = tokens[0]
        # Extract update tokens for validation.
        update_tokens = tokens[1:]

    # Extract updates for validation.
    updates = {}
    i = 0
    # Repeat this block while i < len(update_tokens).
    while i < len(update_tokens):
        token = str(update_tokens[i] or "").strip()
        # Validate missing token before continuing.
        if not token:
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue
        if "=" not in token:
            raise ValueError(f"Format `{token}` salah. Gunakan field=value.")

        field, value = token.split("=", 1)
        field = field.strip().lower()
        # Prepare value parts from the incoming input.
        value_parts = [value.strip()] if value.strip() else []
        i += 1

        while i < len(update_tokens) and "=" not in str(update_tokens[i] or ""):
            continuation = str(update_tokens[i] or "").strip()
            if continuation:
                # Append the current value to value parts.
                value_parts.append(continuation)
            i += 1

        value = " ".join(value_parts).strip()
        # Validate missing field or not value before continuing.
        if not field or not value:
            raise ValueError(f"Format `{token}` salah. Field dan value wajib diisi.")

        if command_name == "asset_update" and field == "amount":
            field = "value"

        updates[field] = value

    return record_id, updates


# Helper for command args from update.
def _command_args_from_update(update: Update, context: ContextTypes.DEFAULT_TYPE, command_name: str) -> list[str]:
    """Read slash command arguments from the original Telegram message.

    Args:
        update: Telegram update from `CommandHandler` or fallback regex routing.
        context: Telegram callback context. `context.args` is used when the
            original message text does not match the requested command.
        command_name: Slash command without `/`, for example `asset_update`.

    Returns:
        Command arguments as a list. When reading from the original text, the
        command tail is returned as one item so quoted key=value text remains
        intact for downstream parsers.

    Side effects:
        None. This helper only reads the incoming Telegram update.

    Flow constraints:
        Keep asset flows preview-before-save and do not mutate Google Sheets.
    """
    message = getattr(update, "message", None)
    text = str(getattr(message, "text", "") or "").strip()
    pattern = rf"^/{re.escape(command_name)}(?:@\w+)?(?:\s+(.*))?$"
    match = re.match(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    # Prefer the original command tail so quoted values survive fallback routing.
    if match:
        raw_tail = str(match.group(1) or "").strip()
        return [raw_tail] if raw_tail else []
    # Fall back to context args for normal CommandHandler calls.
    return list(getattr(context, "args", None) or [])


# Helper for short networth id.
def short_networth_id(record_id: str) -> str:
    """Coordinate the short networth id logic in the Telegram handler layer.

    Args:
        record_id: Input value supplied by the caller; accepted shape follows the function signature and local validation.

    Returns:
        `str` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    record_id = str(record_id or "")
    if len(record_id) <= 18:
        return record_id
    return record_id[:18] + "..."


# Helper for build networth text.
def build_networth_text(summary: dict) -> str:
    """Build the data structure or message text for networth text."""
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
        # Iterate through each acc.
        for acc in accounts:
            name = acc.get("account_name", "-")
            balance = float(acc.get("balance", 0) or 0)
            lines.append(f"• {name}: {format_rupiah(balance)}")

    if assets:
        lines.append("\n*Aset aktif:*")
        # Iterate through each asset.
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
            # Use the fallback path when no earlier branch matched.
            else:
                lines.append(
                    f"• {name} "
                    f"({category}) — "
                    f"{format_rupiah(value)}"
                )


    lines.append(
        "\nCommand:\n"
        "`/asset_add name=Laptop amount=8jt category=Electronics`\n"
        "`/asset_add Laptop`\n"
        "`/asset_update asset_id amount=nominal`\n"
        "`/asset_off asset_id`\n"
        "`/networth_snapshot`"
    )

    return "\n".join(lines)


# Helper for build assets text.
def build_assets_text(assets: list[dict]) -> str:
    """Build the data structure or message text for assets text."""
    # Validate missing assets before continuing.
    if not assets:
        return (
            "📭 Belum ada aset aktif.\n\n"
            "Tambah aset:\n"
            "`/asset_add Laptop`\n"
            "`catet aset hp 10 juta`\n"
            "atau natural: `add emas 999 gram`"
        )

    lines = ["📦 *Daftar Aset Aktif*\n"]

    total = 0

    # Iterate through each i, asset.
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
            # Append the current value to block lines.
            block_lines.extend(format_asset_gain_lines(asset))
            block_lines.extend([
                f"   📝 {asset.get('description', '-') or '-'}",
                f"   🔖 `{asset.get('id', '-')}`",
            ])
            lines.append("\n".join(block_lines))
        # Use the fallback path when no earlier branch matched.
        else:
            block_lines = [
                f"{i}. *{asset.get('name', '-')}*",
                f"   💰 {format_rupiah(value)} | {asset.get('category', '-')}",
            ]
            # Append the current value to block lines.
            block_lines.extend(format_asset_gain_lines(asset))
            block_lines.extend([
                f"   📝 {asset.get('description', '-') or '-'}",
                f"   🔖 `{asset.get('id', '-')}`",
            ])
            lines.append("\n".join(block_lines))

    lines.append(f"\n📦 Total aset aktif: *{format_rupiah(total)}*")

    lines.append(
        "\nEdit harga / harga beli:\n"
        "`/asset_update asset_id unit_price=2420000`\n"
        "`/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`"
    )

    return "\n".join(lines)

# Helper for build liabilities text.
def build_liabilities_text(liabilities: list[dict]) -> str:
    """Build the data structure or message text for liabilities text."""
    # Validate missing liabilities before continuing.
    if not liabilities:
        return (
            "📭 Belum ada liabilitas aktif.\n\n"
            "Tambah liabilitas:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`"
        )

    lines = ["💳 *Daftar Liabilitas Aktif*\n"]

    total = 0

    # Iterate through each i, liability.
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


# Helper for build update result text.
def build_update_result_text(result: dict, label: str) -> str:
    """Build the data structure or message text for update result text."""
    before = result.get("before", {}) or {}
    after = result.get("after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = [f"✅ {label} berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    # Iterate through each field.
    for field in updates:
        if field == "updated_at":
            # Skip the rest of this loop iteration after handling this case.
            continue

        old_value = before.get(field, "-")
        new_value = after.get(field, updates.get(field, "-"))

        lines.append(f"- {field}: {old_value} → {new_value}")

    return "\n".join(lines)


# Helper for build snapshots text.
def build_snapshots_text(snapshots: list[dict]) -> str:
    """Build the data structure or message text for snapshots text."""
    # Validate missing snapshots before continuing.
    if not snapshots:
        return "📭 Belum ada snapshot net worth."

    lines = ["📈 *Riwayat Net Worth Snapshot*\n"]

    # Iterate through each snap.
    for snap in snapshots:
        lines.append(
            f"• `{snap.get('snapshot_date', '-')}` — "
            f"*{format_rupiah(float(snap.get('net_worth', 0) or 0))}*\n"
            f"  Rekening: {format_rupiah(float(snap.get('total_accounts', 0) or 0))} | "
            f"Aset: {format_rupiah(float(snap.get('total_assets', 0) or 0))}"
        )

    return "\n".join(lines)

async def networth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous networth handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Build summary for the response flow.
    summary = calculate_net_worth()

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_networth_text(summary),
        parse_mode="Markdown",
    )


async def assets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous assets handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    assets = get_assets(active_only=True)

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_assets_text(assets),
        parse_mode="Markdown",
    )


async def liabilities_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous liabilities handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    liabilities = get_liabilities(active_only=True)

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_liabilities_text(liabilities),
        parse_mode="Markdown",
    )


# Helper for build asset added text.
def build_asset_added_text(asset: dict) -> str:
    """Build the data structure or message text for asset added text."""
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


# Helper for asset edit or continue keyboard.
def asset_edit_or_continue_keyboard() -> InlineKeyboardMarkup:
    """Coordinate the asset edit or continue keyboard logic in the Telegram handler layer.

    Args:
        None.

    Returns:
        `InlineKeyboardMarkup` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Simpan", callback_data="confirm:asset"),
            InlineKeyboardButton("✏️ Edit dulu", callback_data="editflow:edit:asset"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:asset")],
    ])


# Helper for build asset confirm preview.
def build_asset_confirm_preview(data: dict) -> str:
    """Build the data structure or message text for asset confirm preview."""
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
ASSET_ADD_PROMPT_MESSAGE_KEY = "pending_asset_add_prompt_message_id"
ASSET_ADD_SKIP_WORDS = {"skip", "lewati", "kosong", "-", "tidak", "tidak ada", "ga ada", "gak ada", "nggak ada"}
ASSET_ADD_CANCEL_WORDS = {"cancel", "batal", "/cancel"}
ASSET_ADD_OPTIONAL_STEPS = {"purchase_price", "purchase_date", "category", "description"}
ASSET_ADD_MIN_MANUAL_VALUE = 1_000


# Helper for asset flow is skip.
def _asset_flow_is_skip(text: str) -> bool:
    """Check whether user wants to skip an optional asset wizard field."""
    return str(text or "").strip().lower() in ASSET_ADD_SKIP_WORDS


# Helper for asset flow is cancel.
def _asset_flow_is_cancel(text: str) -> bool:
    """Check whether user wants to cancel the asset wizard."""
    return str(text or "").strip().lower() in ASSET_ADD_CANCEL_WORDS


# Helper for asset add step keyboard.
def asset_add_step_keyboard(step: str) -> InlineKeyboardMarkup:
    """Build the inline keyboard for one asset_add wizard step."""
    # Load rows for the current calculation.
    rows = []
    if step in ASSET_ADD_OPTIONAL_STEPS:
        rows.append([InlineKeyboardButton("⏭️ Lewati", callback_data="asset_add:skip")])
    rows.append([InlineKeyboardButton("🚫 Batal", callback_data="cancel:asset_add")])
    return InlineKeyboardMarkup(rows)


# Helper for asset flow prompt.
def _asset_flow_prompt(step: str, data: dict | None = None) -> str:
    """Build one prompt text for the asset_add wizard."""
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
            "`999 gram`\n"
            "`1 buah`\n\n"
            "Kalau aset tidak berbasis unit, ketik nilai saat ini langsung:\n"
            "`8000000`\n"
            "`8 juta`\n\n"
            "Catatan: kalau kamu menulis `1`, bot akan minta konfirmasi ulang karena rawan salah maksud."
        ),
        "purchase_price": (
            "🧾 *Tambah Aset — Step 3/7*\n\n"
            "Harga belinya berapa?\n\n"
            "Untuk aset satuan, isi harga beli per unit.\n"
            "Contoh:\n"
            "`2559000`\n"
            "`2.55 juta`\n\n"
            "Kalau belum mau diisi, klik *Lewati* atau ketik `lewati`."
        ),
        "purchase_date": (
            "📆 *Tambah Aset — Step 4/7*\n\n"
            "Tanggal belinya kapan?\n\n"
            "Contoh:\n"
            "`2026-06-10`\n"
            "`10/06/2026`\n"
            "`kemarin`\n\n"
            "Kalau tidak tahu / tidak mau isi, klik *Lewati* atau ketik `lewati`."
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
            "Kalau mau otomatis, klik *Lewati* atau ketik `lewati`."
        ),
        "description": (
            "📝 *Tambah Aset — Step 7/7*\n\n"
            "Deskripsinya apa?\n\n"
            "Contoh:\n"
            "`Tabungan emas`\n"
            "`Laptop kerja`\n\n"
            "Kalau kosong, klik *Lewati* atau ketik `lewati`."
        ),
    }

    return prompts.get(step, "Input tidak dikenali. Ketik `batal` untuk membatalkan.")


# Handle the asynchronous send asset add step prompt workflow.
async def send_asset_add_step_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict | None = None):
    """Send one asset wizard prompt and track its inline keyboard for later cleanup."""
    return await reply_tracked_inline_keyboard(
        update,
        context,
        _asset_flow_prompt(step, data),
        parse_mode="Markdown",
        reply_markup=asset_add_step_keyboard(step),
        state_key=ASSET_ADD_PROMPT_MESSAGE_KEY,
    )


# Handle the asynchronous clear asset add step keyboard workflow.
async def clear_asset_add_step_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the old asset wizard keyboard after the user answers."""
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    # Await clear tracked inline keyboard before continuing.
    await clear_tracked_inline_keyboard(context, chat_id, ASSET_ADD_PROMPT_MESSAGE_KEY)


def start_asset_add_flow(context: ContextTypes.DEFAULT_TYPE, initial_data: dict | None = None, step: str = "name") -> None:
    """Start asset add wizard without discarding fields already known from command args."""
    context.user_data.pop("pending_asset_price", None)
    context.user_data.pop("pending_asset_confirm", None)
    context.user_data[ASSET_ADD_FLOW_KEY] = {
        "step": step or "name",
        "data": dict(initial_data or {}),
    }


# Helper for asset manual value too small.
def _asset_manual_value_too_small(amount: float, raw_text: str) -> bool:
    """Guard accidental Rp1/Rp2 asset values that usually mean the user misunderstood the field."""
    raw = str(raw_text or "").strip().lower()
    # Handle amount >= ASSET ADD MIN MANUAL VALUE.
    if amount >= ASSET_ADD_MIN_MANUAL_VALUE:
        return False
    return bool(re.fullmatch(r"(?:rp\.?\s*)?\d+(?:[.,]0+)?", raw))


# Helper for build asset data from flow.
def _build_asset_data_from_flow(data: dict) -> dict:
    """Build structured output for the build asset data from flow workflow in the Telegram handler layer.

    Args:
        data: Structured input data used by the current flow.

    Returns:
        `dict` value as defined by the function signature.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    name = str(data.get("name") or "").strip()
    category = str(data.get("category") or "").strip()
    name, category = guess_asset_category_and_name(name, category)

    quantity = data.get("quantity")
    unit = data.get("unit", "") or ""
    price_per_unit = data.get("price_per_unit")
    current_value = data.get("amount")

    if quantity not in [None, ""] and str(unit).strip():
        asset_type = "gold" if ("emas" in name.lower() or category.lower() in ["gold", "emas"]) else "unit"
        # Extract amount for validation.
        amount = float(quantity or 0) * float(price_per_unit or 0)
    # Use the fallback path when no earlier branch matched.
    else:
        asset_type = "manual"
        # Extract amount for validation.
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


# Handle the asynchronous finish asset add flow workflow.
async def _finish_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> bool:
    """Move completed asset wizard state into confirmation preview."""
    asset_data = _build_asset_data_from_flow(data)
    context.user_data["pending_asset_confirm"] = asset_data
    context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
    context.user_data.pop(ASSET_ADD_PROMPT_MESSAGE_KEY, None)

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        f"{build_asset_confirm_preview(asset_data)}\n\nMau simpan, edit dulu, atau batal?",
        parse_mode="Markdown",
        reply_markup=asset_edit_or_continue_keyboard(),
    )
    return True


# Handle the asynchronous handle pending asset add flow workflow.
async def handle_pending_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle one text answer for the asset_add wizard."""
    flow = context.user_data.get(ASSET_ADD_FLOW_KEY)
    # Validate missing flow before continuing.
    if not flow:
        return False

    text = str(user_text or "").strip()
    # Await clear asset add step keyboard before continuing.
    await clear_asset_add_step_keyboard(update, context)

    if _asset_flow_is_cancel(text):
        context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
        context.user_data.pop("pending_asset_price", None)
        context.user_data.pop("pending_asset_confirm", None)
        await update.message.reply_text("🚫 Tambah aset dibatalkan. Tidak ada data yang disimpan.")
        return True

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    if step == "name":
        # Validate missing text before continuing.
        if not text:
            await send_asset_add_step_prompt(update, context, "name", data)
            return True
        data["name"] = text
        flow["step"] = "quantity"
        await send_asset_add_step_prompt(update, context, "quantity", data)
        return True

    if step == "quantity":
        qty_info = parse_asset_quantity_input(text)
        if qty_info:
            data["quantity"] = qty_info["quantity"]
            data["unit"] = qty_info["unit"]
            if qty_info.get("price_per_unit"):
                data["price_per_unit"] = qty_info.get("price_per_unit")
            flow["step"] = "purchase_price"
            await send_asset_add_step_prompt(update, context, "purchase_price", data)
            return True

        # Extract amount for validation.
        amount = parse_human_amount(text)
        if amount > 0:
            if _asset_manual_value_too_small(amount, text):
                # Send the Telegram response before continuing.
                await update.message.reply_text(
                    "⚠️ Nilai aset terlihat terlalu kecil. Kalau maksudnya 1 juta, tulis `1 juta`.\n"
                    "Kalau ini aset berbasis unit, tulis seperti `1 buah` atau `999 gram`.",
                    parse_mode="Markdown",
                )
                await send_asset_add_step_prompt(update, context, "quantity", data)
                return True
            data["amount"] = amount
            data["quantity"] = None
            data["unit"] = ""
            data["price_per_unit"] = None
            flow["step"] = "purchase_price"
            await send_asset_add_step_prompt(update, context, "purchase_price", data)
            return True

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Jumlah/nilai aset belum valid.\n\nContoh: `999 gram`, `1 buah`, `8000000`, atau `8 juta`.",
            parse_mode="Markdown",
        )
        await send_asset_add_step_prompt(update, context, "quantity", data)
        return True

    if step == "purchase_price":
        if _asset_flow_is_skip(text):
            data["purchase_price_per_unit"] = None
        # Use the fallback path when no earlier branch matched.
        else:
            purchase_price = parse_human_amount(text)
            if purchase_price <= 0:
                # Send the Telegram response before continuing.
                await update.message.reply_text(
                    "❌ Harga beli belum valid. Contoh: `2559000`, `2.55 juta`, atau klik *Lewati*.",
                    parse_mode="Markdown",
                )
                await send_asset_add_step_prompt(update, context, "purchase_price", data)
                return True
            data["purchase_price_per_unit"] = purchase_price

        flow["step"] = "purchase_date"
        await send_asset_add_step_prompt(update, context, "purchase_date", data)
        return True

    if step == "purchase_date":
        if _asset_flow_is_skip(text):
            data["purchase_date"] = ""
        # Use the fallback path when no earlier branch matched.
        else:
            data["purchase_date"] = detect_date(text)

        if data.get("quantity") not in [None, ""] and str(data.get("unit") or "").strip() and not data.get("price_per_unit"):
            flow["step"] = "current_price"
            await send_asset_add_step_prompt(update, context, "current_price", data)
            return True

        flow["step"] = "category"
        await send_asset_add_step_prompt(update, context, "category", data)
        return True

    if step == "current_price":
        current_price = parse_human_amount(text)
        if current_price <= 0:
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                "❌ Harga saat ini belum valid. Contoh: `2594000` atau `2.594 juta`.",
                parse_mode="Markdown",
            )
            await send_asset_add_step_prompt(update, context, "current_price", data)
            return True
        data["price_per_unit"] = current_price
        data["amount"] = float(data.get("quantity") or 0) * current_price
        flow["step"] = "category"
        await send_asset_add_step_prompt(update, context, "category", data)
        return True

    if step == "category":
        data["category"] = "" if _asset_flow_is_skip(text) else text
        flow["step"] = "description"
        await send_asset_add_step_prompt(update, context, "description", data)
        return True

    if step == "description":
        data["description"] = "" if _asset_flow_is_skip(text) else text
        return await _finish_asset_add_flow(update, context, data)

    context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
    context.user_data.pop(ASSET_ADD_PROMPT_MESSAGE_KEY, None)
    await update.message.reply_text("❌ Sesi tambah aset tidak valid. Coba ulangi `/asset_add`.", parse_mode="Markdown")
    return True


# Handle the asynchronous handle asset add skip callback workflow.
async def handle_asset_add_skip_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Lewati button for optional asset_add wizard steps."""
    flow = context.user_data.get(ASSET_ADD_FLOW_KEY)
    # Validate missing flow before continuing.
    if not flow:
        await safe_edit_message(query, "❌ Sesi tambah aset expired. Jalankan `/asset_add` lagi.", parse_mode="Markdown")
        return

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    # Handle step not in ASSET ADD OPTIONAL STEPS.
    if step not in ASSET_ADD_OPTIONAL_STEPS:
        await safe_edit_message(query, "ℹ️ Step ini wajib diisi, jadi tidak bisa dilewati.", parse_mode="Markdown")
        return

    if step == "purchase_price":
        data["purchase_price_per_unit"] = None
        next_step = "purchase_date"
    elif step == "purchase_date":
        data["purchase_date"] = ""
        next_step = "current_price" if data.get("quantity") not in [None, ""] and str(data.get("unit") or "").strip() and not data.get("price_per_unit") else "category"
    elif step == "category":
        data["category"] = ""
        next_step = "description"
    # Use the fallback path when no earlier branch matched.
    else:
        data["description"] = ""
        asset_data = _build_asset_data_from_flow(data)
        context.user_data["pending_asset_confirm"] = asset_data
        context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
        context.user_data.pop(ASSET_ADD_PROMPT_MESSAGE_KEY, None)
        # Send the Telegram response before continuing.
        await safe_edit_message(
            query,
            f"{build_asset_confirm_preview(asset_data)}\n\nMau simpan, edit dulu, atau batal?",
            parse_mode="Markdown",
            reply_markup=asset_edit_or_continue_keyboard(),
        )
        return

    flow["step"] = next_step
    # Send the Telegram response before continuing.
    await safe_edit_message(
        query,
        _asset_flow_prompt(next_step, data),
        parse_mode="Markdown",
        reply_markup=asset_add_step_keyboard(next_step),
    )
    context.user_data[ASSET_ADD_PROMPT_MESSAGE_KEY] = getattr(query.message, "message_id", None)


async def asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /asset_add as a guided wizard, while keeping old pipe format compatible."""
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _command_args_from_update(update, context, "asset_add")
        # Start the wizard when the command has no inline arguments.
        if not command_args:
            start_asset_add_flow(context)
            await send_asset_add_step_prompt(update, context, "name", {})
            return

        raw_arg = " ".join(command_args).strip()
        if "|" in raw_arg:
            data = parse_pipe_add_args(command_args, "asset")
        elif "=" in raw_arg:
            data = parse_add_key_value_args(command_args, "asset")
        else:
            start_asset_add_flow(context, {"name": raw_arg}, step="quantity")
            await send_asset_add_step_prompt(update, context, "quantity", {"name": raw_arg})
            return

        if data.get("needs_unit_price"):
            context.user_data["pending_asset_price"] = data
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                build_asset_unit_price_prompt(data),
                parse_mode="Markdown",
                reply_markup=cancel_keyboard("asset_price"),
            )
            return

        context.user_data["pending_asset_confirm"] = data
        context.user_data.pop("pending_asset_price", None)

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"{build_asset_confirm_preview(data)}\n\nMau simpan, edit dulu, atau batal?",
            parse_mode="Markdown",
            reply_markup=asset_edit_or_continue_keyboard(),
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Gagal tambah aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_add name=Laptop amount=8jt category=Electronics desc=\"Laptop kerja\"`\n"
            "`/asset_add name=\"Emas Antam\" quantity=10 unit=gram price=1.5jt category=Emas`\n"
            "`/asset_add Laptop`\n"
            "`catet aset hp 10 juta`\n"
            "`tambah aset laptop 8 juta`",
            parse_mode="Markdown",
        )


async def liability_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous liability add handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        raw_arg = " ".join(context.args or []).strip()
        data = parse_pipe_add_args(context.args, "liability") if "|" in raw_arg else parse_add_key_value_args(context.args, "liability")

        liability = add_liability(
            name=data["name"],
            current_balance=data["amount"],
            category=data["category"],
            description=data["description"],
        )

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "✅ *Liabilitas berhasil ditambahkan!*\n\n"
            f"💳 Nama: *{liability.get('name')}*\n"
            f"💰 Nominal: *{format_rupiah(float(liability.get('current_balance', 0) or 0))}*\n"
            f"📁 Kategori: *{liability.get('category')}*\n"
            f"📝 Deskripsi: {liability.get('description') or '-'}\n"
            f"🔖 ID: `{liability.get('id')}`",
            parse_mode="Markdown",
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Gagal tambah liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_add name=Paylater amount=1200000 category=Paylater desc=\"Cicilan aktif\"`",
            parse_mode="Markdown",
        )


async def asset_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous asset update handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _command_args_from_update(update, context, "asset_update")
        asset_id, updates = parse_pipe_update_args(command_args, "asset_update")
        # Build result for the response flow.
        result = update_asset(asset_id, updates)

        if not result.get("success"):
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/assets`",
                parse_mode="Markdown",
            )
            return

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_update_result_text(result, "Aset")
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Gagal update aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_update asset_xxx amount=9000000`\n"
            "`/asset_update asset_xxx unit_price=2420000`\n"
            "`/asset_update asset_xxx harga_beli=2559000 tanggal_beli=2026-06-10`\n"
            "`/asset_update asset_xxx name=\"Laptop Baru\" category=Electronics`",
            parse_mode="Markdown",
        )


async def liability_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous liability update handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        liability_id, updates = parse_pipe_update_args(context.args, "liability_update")
        # Build result for the response flow.
        result = update_liability(liability_id, updates)

        if not result.get("success"):
            # Send the Telegram response before continuing.
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/liabilities`",
                parse_mode="Markdown",
            )
            return

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            build_update_result_text(result, "Liabilitas")
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Gagal update liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_update liab_xxx | balance=1000000`\n"
            "`/liability_update liab_xxx | name=Paylater Shopee | balance=500000`",
            parse_mode="Markdown",
        )


async def asset_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous asset off handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Validate missing context.args before continuing.
    if not context.args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Masukkan asset ID.\n\n"
            "Contoh:\n"
            "`/asset_off asset_xxx`",
            parse_mode="Markdown",
        )
        return

    asset_id = context.args[0].strip()
    success = deactivate_asset(asset_id)

    # Validate missing success before continuing.
    if not success:
        await update.message.reply_text("❌ Asset tidak ditemukan.")
        return

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        f"✅ Asset berhasil dinonaktifkan:\n`{asset_id}`",
        parse_mode="Markdown",
    )


async def liability_off_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous liability off handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Validate missing context.args before continuing.
    if not context.args:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "❌ Masukkan liability ID.\n\n"
            "Contoh:\n"
            "`/liability_off liab_xxx`",
            parse_mode="Markdown",
        )
        return

    liability_id = context.args[0].strip()
    success = deactivate_liability(liability_id)

    # Validate missing success before continuing.
    if not success:
        await update.message.reply_text("❌ Liability tidak ditemukan.")
        return

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        f"✅ Liability berhasil dinonaktifkan:\n`{liability_id}`",
        parse_mode="Markdown",
    )


async def networth_snapshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous networth snapshot handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        snapshot = create_net_worth_snapshot()

        # Send the Telegram response before continuing.
        await update.message.reply_text(
            "✅ *Snapshot Net Worth berhasil disimpan!*\n\n"
            f"📅 Tanggal: `{snapshot.get('snapshot_date')}`\n"
            f"💰 Rekening: *{format_rupiah(float(snapshot.get('total_accounts', 0) or 0))}*\n"
            f"📦 Aset: *{format_rupiah(float(snapshot.get('total_assets', 0) or 0))}*\n"
            f"🏁 Net Worth: *{format_rupiah(float(snapshot.get('net_worth', 0) or 0))}*",
            parse_mode="Markdown",
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Send the Telegram response before continuing.
        await update.message.reply_text(
            f"❌ Gagal menyimpan snapshot net worth: {str(e)}"
        )


async def networth_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the asynchronous networth history handler flow in the Telegram handler layer.

    Args:
        update: Telegram Update object supplied by python-telegram-bot.
        context: Telegram callback context containing args, bot data, user data, and job data.

    Returns:
        Awaitable result from the async flow. Most Telegram handlers return `None` after sending a response.

    Side effects:
        May send or edit Telegram messages and may update `context.user_data` according to the active conversation flow.

    Flow constraints:
        Preserve the existing Telegram flow, including preview-before-save and Batal handling where cancellation is possible.
    """
    # Validate missing is authorized(update) before continuing.
    if not is_authorized(update):
        # Await reject unauthorized before continuing.
        await reject_unauthorized(update)
        return

    snapshots = get_net_worth_snapshots(limit=12)

    # Send the Telegram response before continuing.
    await update.message.reply_text(
        build_snapshots_text(snapshots),
        parse_mode="Markdown",
    )

