"""Handlers for assets and net worth features, including asset creation, updates, deactivation, snapshots, and history."""


# Split from app/bot/handlers.py so the main handler facade stays small.
# Imported by app/bot/handlers.py as a normal Python module.
# Common imports are centralized here; cross-part helpers are imported explicitly when needed.
from app.bot.handler_parts.common_imports import *

# Define parse asset quantity input for callers in this flow.
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

    # Open a multi-line structure for the values below.
    match = re.fullmatch(
        r"(\d+(?:[.,]\d+)?)\s*(g|gr|gram|grams|buah|unit|pcs|pc|lembar|kg|kilogram)(?:\s*@\s*([0-9.,]+)\s*(?:rb|ribu|k|jt|juta)?)?",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Handle the missing or empty match case.
    if not match:
        # Return None to the caller.
        return None

    quantity = float(match.group(1).replace(",", "."))
    # Prepare unit for the next step.
    unit = match.group(2).lower()
    # Open a multi-line structure for the values below.
    unit_aliases = {
        "g": "gram",
        "gr": "gram",
        "grams": "gram",
        "pcs": "buah",
        "pc": "buah",
    # Close the structure that was opened above.
    }
    # Prepare unit for the next step.
    unit = unit_aliases.get(unit, unit)

    # Prepare price raw for the next step.
    price_raw = match.group(3)
    # Prepare price per unit for the next step.
    price_per_unit = parse_human_amount(price_raw) if price_raw else None

    # Return { to the caller.
    return {
        "quantity": quantity,
        "unit": unit,
        "price_per_unit": price_per_unit,
    # Close the structure that was opened above.
    }


# Define parse human amount atom for callers in this flow.
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
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0.0 to the caller.
        return 0.0

    # Prepare multiplier for the next step.
    multiplier = 1
    if re.search(r"(jt|juta)\b", raw):
        # Prepare multiplier for the next step.
        multiplier = 1_000_000
    elif re.search(r"(rb|ribu|k)\b", raw):
        # Prepare multiplier for the next step.
        multiplier = 1_000

    raw = re.sub(r"(jt|juta|rb|ribu|k)\b", "", raw).strip()

    # Implementation section
    if multiplier != 1:
        raw = raw.replace(",", ".")
        raw = re.sub(r"[^0-9.]", "", raw)
        if raw.count(".") > 1:
            first, *rest = raw.split(".")
            raw = first + "." + "".join(rest)
        # Return float(raw or 0) * multiplier to the caller.
        return float(raw or 0) * multiplier

    # Implementation section
    raw = re.sub(r"[^0-9]", "", raw)
    # Return float(raw or 0) to the caller.
    return float(raw or 0)


# Define safe eval amount expression for callers in this flow.
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
    # Open a multi-line structure for the values below.
    allowed_ops = {
        # Include this value in the surrounding collection or call.
        ast.Add: operator.add,
        # Include this value in the surrounding collection or call.
        ast.Sub: operator.sub,
        # Include this value in the surrounding collection or call.
        ast.Mult: operator.mul,
        # Include this value in the surrounding collection or call.
        ast.Div: operator.truediv,
        # Include this value in the surrounding collection or call.
        ast.USub: operator.neg,
        # Include this value in the surrounding collection or call.
        ast.UAdd: operator.pos,
    # Close the structure that was opened above.
    }

    # Define eval for callers in this flow.
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
        # Handle the case where isinstance(node, ast.Expression).
        if isinstance(node, ast.Expression):
            # Return _eval(node.body) to the caller.
            return _eval(node.body)
        # Handle the case where isinstance(node, ast.Constant) and isinstance(node.value, (in....
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            # Return float(node.value) to the caller.
            return float(node.value)
        # Handle the case where isinstance(node, ast.Num): # pragma: no cover, compatibility....
        if isinstance(node, ast.Num):  # pragma: no cover, compatibility lama
            # Return float(node.n) to the caller.
            return float(node.n)
        # Handle the case where isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops.
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            # Return allowed_ops[type(node.op)](_eval(node.operand)) to the caller.
            return allowed_ops[type(node.op)](_eval(node.operand))
        # Handle the case where isinstance(node, ast.BinOp) and type(node.op) in allowed_ops.
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            # Prepare right for the next step.
            right = _eval(node.right)
            # Handle the case where isinstance(node.op, ast.Div) and right == 0.
            if isinstance(node.op, ast.Div) and right == 0:
                raise ValueError("division by zero")
            # Return allowed_ops[type(node.op)](_eval(node.left), right) to the caller.
            return allowed_ops[type(node.op)](_eval(node.left), right)
        raise ValueError("unsafe amount expression")

    tree = ast.parse(expr, mode="eval")
    # Return float(_eval(tree)) to the caller.
    return float(_eval(tree))


# Define parse human amount for callers in this flow.
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
    # Handle the missing or empty raw case.
    if not raw:
        # Return 0.0 to the caller.
        return 0.0

    # Date parsing note: keep explicit and relative Indonesian date formats predictable.
    if re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", raw):
        # Return _parse_human_amount_atom(raw) to the caller.
        return _parse_human_amount_atom(raw)

    has_math_operator = bool(re.search(r"[+*/x×:]|(?<=\s)-(?:\s|\d)", raw))
    # Handle the case where has_math_operator.
    if has_math_operator:
        # Amount parsing note: keep Indonesian numeric formats stable, for example `331.063k` means Rp331.063.
        token_pattern = re.compile(r"\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)?", re.IGNORECASE)

        # Define repl for callers in this flow.
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
            # Prepare token for the next step.
            token = match.group(0)
            # Return str(_parse_human_amount_atom(token)) to the caller.
            return str(_parse_human_amount_atom(token))

        # Prepare expr for the next step.
        expr = token_pattern.sub(repl, raw)
        expr = expr.replace("×", "*").replace("x", "*").replace(":", "/")
        expr = re.sub(r"\s+", "", expr)
        if re.fullmatch(r"[0-9.+\-*/()]+", expr):
            # Run this operation in a guarded block so failures can be handled.
            try:
                # Prepare result for the next step.
                result = _safe_eval_amount_expression(expr)
                # Handle the case where result > 0.
                if result > 0:
                    # Return result to the caller.
                    return result
            # Handle an expected failure from the guarded operation above.
            except Exception:
                # Keep this intentionally empty block valid.
                pass

    # Return _parse_human_amount_atom(raw) to the caller.
    return _parse_human_amount_atom(raw)


# Define parse asset extra fields for callers in this flow.
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
    # Open a multi-line structure for the values below.
    result = {
        "purchase_price_per_unit": None,
        "purchase_date": "",
    # Close the structure that was opened above.
    }

    # Prepare positional for the next step.
    positional = []
    # Process each part in the current collection.
    for part in extra_parts or []:
        raw = str(part or "").strip()
        # Handle the missing or empty raw case.
        if not raw:
            # Skip the rest of this loop iteration after handling this case.
            continue

        if "=" in raw:
            key, value = raw.split("=", 1)
            # Prepare key for the next step.
            key = key.strip().lower()
            # Prepare value for the next step.
            value = value.strip()

            # Handle the case where key in [.
            if key in [
                "purchase_price", "purchase_price_per_unit", "buy_price",
                "harga_beli", "modal", "harga_modal",
            # Close the structure that was opened above.
            ]:
                result["purchase_price_per_unit"] = parse_human_amount(value)
            elif key in ["purchase_date", "buy_date", "tanggal_beli", "tgl_beli"]:
                result["purchase_date"] = value
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Update positional with the current value.
                positional.append(raw)
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Update positional with the current value.
            positional.append(raw)

    if positional and not result.get("purchase_price_per_unit"):
        # Prepare maybe price for the next step.
        maybe_price = parse_human_amount(positional[0])
        # Handle the case where maybe_price > 0.
        if maybe_price > 0:
            result["purchase_price_per_unit"] = maybe_price

    if len(positional) >= 2 and not result.get("purchase_date"):
        result["purchase_date"] = positional[1]

    # Return result to the caller.
    return result


def format_asset_gain_lines(asset: dict, indent: str = "   ") -> list[str]:
    """Format data into a readable display for asset gain lines."""
    # Prepare gain for the next step.
    gain = calculate_asset_gain(asset)
    if not gain.get("has_purchase_info"):
        # Return [] to the caller.
        return []

    unit = asset.get("unit", "unit") or "unit"
    purchase_price = gain.get("purchase_price_per_unit", 0)
    purchase_total = gain.get("purchase_total", 0)
    gain_loss = gain.get("gain_loss", 0)
    gain_pct = gain.get("gain_loss_pct", 0)
    sign = "+" if gain_loss >= 0 else "-"

    # Open a multi-line structure for the values below.
    lines = [
        f"{indent}🧾 Harga beli/{unit}: {format_rupiah(purchase_price)}",
        f"{indent}💼 Modal beli: {format_rupiah(purchase_total)}",
    # Close the structure that was opened above.
    ]

    purchase_date = asset.get("purchase_date")
    # Handle the case where purchase_date.
    if purchase_date:
        lines.append(f"{indent}📆 Tanggal beli: `{purchase_date}`")

    # Open a multi-line structure for the values below.
    lines.append(
        f"{indent}📈 Floating P/L: {sign}{format_rupiah(abs(gain_loss))} ({gain_pct:+.2f}%)"
    # Close the structure that was opened above.
    )
    # Return lines to the caller.
    return lines


# Define guess asset category and name for callers in this flow.
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
    # Prepare low for the next step.
    low = name_clean.lower()

    if "emas" in low or category_clean.lower() in ["gold", "emas", "precious metal", "logam mulia"]:
        return name_clean or "Emas", category_clean or "Gold"

    return name_clean, category_clean or "Other Asset"


# Define build asset unit price prompt for callers in this flow.
def build_asset_unit_price_prompt(data: dict) -> str:
    """Build the data structure or message text for asset unit price prompt."""
    # Return ( to the caller.
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
    # Close the structure that was opened above.
    )

# Define parse pipe add args for callers in this flow.
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

    # Handle the missing or empty raw case.
    if not raw:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh:\n"
            f"`/{item_type}_add Laptop | 8000000 | Electronics | Laptop kerja`"
        # Close the structure that was opened above.
        )

    parts = [p.strip() for p in raw.split("|")]

    # Handle the case where len(parts) < 2.
    if len(parts) < 2:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format belum lengkap.\n\n"
            f"Format:\n"
            f"`/{item_type}_add Nama | nominal/jumlah satuan | kategori | deskripsi`"
        # Close the structure that was opened above.
        )

    # Prepare name for the next step.
    name = parts[0]
    # Prepare amount raw for the next step.
    amount_raw = parts[1]
    # Open a multi-line structure for the values below.
    category = parts[2] if len(parts) >= 3 else (
        "Other Asset" if item_type == "asset" else "Other Liability"
    # Close the structure that was opened above.
    )
    description = parts[3] if len(parts) >= 4 else ""
    asset_extra = parse_asset_extra_fields(parts[4:]) if item_type == "asset" else {}

    if item_type == "asset":
        # Prepare qty info for the next step.
        qty_info = parse_asset_quantity_input(amount_raw)
        # Handle the case where qty_info.
        if qty_info:
            # Run this statement as part of the current workflow.
            name, category = guess_asset_category_and_name(name, category)
            asset_type = "gold" if ("emas" in name.lower() or str(category).lower() in ["gold", "emas"]) else "unit"
            # Return { to the caller.
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
            # Close the structure that was opened above.
            }

    # Prepare amount for the next step.
    amount = parse_human_amount(amount_raw)
    # Handle the case where amount <= 0.
    if amount <= 0:
        raise ValueError("Nominal harus angka. Contoh: `8000000`, `2.4 juta`, atau aset satuan `999 gram`.")

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Define parse natural asset add for callers in this flow.
def parse_natural_asset_add(text: str) -> dict | None:
    """Parse natural asset input before it falls back to expense parsing."""
    raw = str(text or "").strip()

    # Open a multi-line structure for the values below.
    amount_match = re.fullmatch(
        r"(?:(?:catat|catet|add|tambah)\s+aset|aset)\s+(.+?)\s+"
        r"((?:rp\.?\s*)?\d[\d.,]*(?:\s*(?:rb|ribu|k|jt|juta|m|mio))?)",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )
    # Handle the case where amount_match.
    if amount_match:
        # Prepare name raw for the next step.
        name_raw = amount_match.group(1).strip()
        # Prepare amount for the next step.
        amount = parse_human_amount(amount_match.group(2))
        # Handle the case where amount <= 0.
        if amount <= 0:
            # Return None to the caller.
            return None

        # Prepare name for the next step.
        name = name_raw.title()
        if name.lower() == "emas":
            name = "Emas"
        # Run this statement as part of the current workflow.
        name, category = guess_asset_category_and_name(name)
        asset_type = "gold" if "emas" in name.lower() else "unit"

        # Return { to the caller.
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
        # Close the structure that was opened above.
        }

    # Open a multi-line structure for the values below.
    match = re.fullmatch(
        r"(?:add|tambah|catat|catet)(?:\s+aset)?\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*(g|gr|gram|grams|buah|unit|pcs|pc|lembar|kg|kilogram)",
        # Include this value in the surrounding collection or call.
        raw,
        # Prepare flags for the next step.
        flags=re.IGNORECASE,
    # Close the structure that was opened above.
    )

    # Handle the missing or empty match case.
    if not match:
        # Return None to the caller.
        return None

    # Prepare name raw for the next step.
    name_raw = match.group(1).strip()
    qty_raw = f"{match.group(2)} {match.group(3)}"
    # Prepare qty info for the next step.
    qty_info = parse_asset_quantity_input(qty_raw)

    # Handle the missing or empty qty_info case.
    if not qty_info:
        # Return None to the caller.
        return None

    # Prepare name for the next step.
    name = name_raw.title()
    if name.lower() == "emas":
        name = "Emas"

    # Run this statement as part of the current workflow.
    name, category = guess_asset_category_and_name(name)
    asset_type = "gold" if "emas" in name.lower() else "unit"

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }

# Define parse pipe update args for callers in this flow.
def parse_pipe_update_args(args: list[str], command_name: str) -> tuple[str, dict]:
    """Parse update args and support both old pipe format and new key=value format."""
    raw = " ".join(args).strip()

    # Handle the missing or empty raw case.
    if not raw:
        # Raise a clear error so the caller can stop this invalid flow.
        raise ValueError(
            f"Format kosong.\n\n"
            f"Contoh baru: `/{command_name} id_xxx amount=9000000`\n"
            f"Format lama tetap diterima, tapi format utama: `/{command_name} id_xxx amount=9000000`"
        # Close the structure that was opened above.
        )

    if "|" in raw:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        # Handle the case where len(parts) < 2.
        if len(parts) < 2:
            # Raise a clear error so the caller can stop this invalid flow.
            raise ValueError(
                f"Format belum lengkap.\n\n"
                f"Contoh: `/{command_name} id_xxx amount=9000000`"
            # Close the structure that was opened above.
            )
        # Prepare record id for the next step.
        record_id = parts[0]
        # Prepare update tokens for the next step.
        update_tokens = parts[1:]
    # Handle the fallback path after earlier conditions are skipped.
    else:
        # Run this operation in a guarded block so failures can be handled.
        try:
            # Prepare tokens for the next step.
            tokens = shlex.split(raw)
        # Handle an expected failure from the guarded operation above.
        except Exception:
            # Prepare tokens for the next step.
            tokens = raw.split()
        # Handle the case where len(tokens) < 2.
        if len(tokens) < 2:
            # Raise a clear error so the caller can stop this invalid flow.
            raise ValueError(
                f"Format belum lengkap.\n\n"
                f"Contoh: `/{command_name} id_xxx amount=9000000`"
            # Close the structure that was opened above.
            )
        # Prepare record id for the next step.
        record_id = tokens[0]
        # Prepare update tokens for the next step.
        update_tokens = tokens[1:]

    # Prepare updates for the next step.
    updates = {}
    # Prepare i for the next step.
    i = 0
    # Repeat this block while i < len(update_tokens).
    while i < len(update_tokens):
        token = str(update_tokens[i] or "").strip()
        # Handle the missing or empty token case.
        if not token:
            # Run this statement as part of the current workflow.
            i += 1
            # Skip the rest of this loop iteration after handling this case.
            continue
        if "=" not in token:
            raise ValueError(f"Format `{token}` salah. Gunakan field=value.")

        field, value = token.split("=", 1)
        # Prepare field for the next step.
        field = field.strip().lower()
        # Prepare value parts for the next step.
        value_parts = [value.strip()] if value.strip() else []
        # Run this statement as part of the current workflow.
        i += 1

        while i < len(update_tokens) and "=" not in str(update_tokens[i] or ""):
            continuation = str(update_tokens[i] or "").strip()
            # Handle the case where continuation.
            if continuation:
                # Update value parts with the current value.
                value_parts.append(continuation)
            # Run this statement as part of the current workflow.
            i += 1

        value = " ".join(value_parts).strip()
        # Handle the missing or empty field or not value case.
        if not field or not value:
            raise ValueError(f"Format `{token}` salah. Field dan value wajib diisi.")

        if command_name == "asset_update" and field == "amount":
            field = "value"

        # Run this statement as part of the current workflow.
        updates[field] = value

    # Return record_id, updates to the caller.
    return record_id, updates


# Define command args from update for callers in this flow.
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


# Define short networth id for callers in this flow.
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
    # Handle the case where len(record_id) <= 18.
    if len(record_id) <= 18:
        # Return record_id to the caller.
        return record_id
    return record_id[:18] + "..."


# Define build networth text for callers in this flow.
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

    # Handle the case where accounts.
    if accounts:
        lines.append("*Rekening:*")
        # Process each acc in the current collection.
        for acc in accounts:
            name = acc.get("account_name", "-")
            balance = float(acc.get("balance", 0) or 0)
            lines.append(f"• {name}: {format_rupiah(balance)}")

    # Handle the case where assets.
    if assets:
        lines.append("\n*Aset aktif:*")
        # Process each asset in the current collection.
        for asset in assets:
            name = asset.get("name", "-")
            category = asset.get("category", "-")
            value = float(asset.get("current_value", 0) or 0)

            if str(asset.get("asset_type", "")).strip().lower() == "gold":
                qty = asset.get("quantity", "-")
                unit = asset.get("unit", "gram") or "gram"
                price = float(asset.get("price_per_unit", 0) or 0)
                # Prepare gain for the next step.
                gain = calculate_asset_gain(asset)
                gain_suffix = ""
                if gain.get("has_purchase_info"):
                    gl = gain.get("gain_loss", 0)
                    pct = gain.get("gain_loss_pct", 0)
                    sign = "+" if gl >= 0 else "-"
                    gain_suffix = f" | P/L {sign}{format_rupiah(abs(gl))} ({pct:+.2f}%)"

                # Open a multi-line structure for the values below.
                lines.append(
                    f"• {name} ({qty} {unit}) — "
                    f"{format_rupiah(value)} "
                    f"@ {format_rupiah(price)}/{unit}"
                    # Run this statement as part of the current workflow.
                    f"{gain_suffix}"
                # Close the structure that was opened above.
                )
            # Handle the fallback path after earlier conditions are skipped.
            else:
                # Open a multi-line structure for the values below.
                lines.append(
                    f"• {name} "
                    f"({category}) — "
                    # Run this statement as part of the current workflow.
                    f"{format_rupiah(value)}"
                # Close the structure that was opened above.
                )


    # Open a multi-line structure for the values below.
    lines.append(
        "\nCommand:\n"
        "`/asset_add Laptop`\n"
        "`/asset_update asset_id amount=nominal`\n"
        "`/asset_off asset_id`\n"
        "`/networth_snapshot`"
    # Close the structure that was opened above.
    )

    return "\n".join(lines)


# Define build assets text for callers in this flow.
def build_assets_text(assets: list[dict]) -> str:
    """Build the data structure or message text for assets text."""
    # Handle the missing or empty assets case.
    if not assets:
        # Return ( to the caller.
        return (
            "📭 Belum ada aset aktif.\n\n"
            "Tambah aset:\n"
            "`/asset_add Laptop`\n"
            "`catet aset hp 10 juta`\n"
            "atau natural: `add emas 999 gram`"
        # Close the structure that was opened above.
        )

    lines = ["📦 *Daftar Aset Aktif*\n"]

    # Prepare total for the next step.
    total = 0

    # Process each i, asset in the current collection.
    for i, asset in enumerate(assets, 1):
        value = float(asset.get("current_value", 0) or 0)
        # Run this statement as part of the current workflow.
        total += value

        quantity = asset.get("quantity", "")
        unit = asset.get("unit", "")
        price = float(asset.get("price_per_unit", 0) or 0)
        has_unit_info = bool(str(quantity or "").strip()) and bool(str(unit or "").strip())

        # Handle the case where has_unit_info.
        if has_unit_info:
            last_update = asset.get("last_price_update", "-") or "-"
            # Open a multi-line structure for the values below.
            block_lines = [
                f"{i}. *{asset.get('name', '-')}*",
                f"   🔢 {quantity} {unit}",
                f"   🏷️ Harga sekarang/{unit}: {format_rupiah(price)}",
                f"   💰 Nilai saat ini: *{format_rupiah(value)}*",
                f"   📅 Harga update: `{last_update}`",
            # Close the structure that was opened above.
            ]
            # Update block lines with the current value.
            block_lines.extend(format_asset_gain_lines(asset))
            # Open a multi-line structure for the values below.
            block_lines.extend([
                f"   📝 {asset.get('description', '-') or '-'}",
                f"   🔖 `{asset.get('id', '-')}`",
            # Close the structure that was opened above.
            ])
            lines.append("\n".join(block_lines))
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Open a multi-line structure for the values below.
            block_lines = [
                f"{i}. *{asset.get('name', '-')}*",
                f"   💰 {format_rupiah(value)} | {asset.get('category', '-')}",
            # Close the structure that was opened above.
            ]
            # Update block lines with the current value.
            block_lines.extend(format_asset_gain_lines(asset))
            # Open a multi-line structure for the values below.
            block_lines.extend([
                f"   📝 {asset.get('description', '-') or '-'}",
                f"   🔖 `{asset.get('id', '-')}`",
            # Close the structure that was opened above.
            ])
            lines.append("\n".join(block_lines))

    lines.append(f"\n📦 Total aset aktif: *{format_rupiah(total)}*")

    # Open a multi-line structure for the values below.
    lines.append(
        "\nEdit harga / harga beli:\n"
        "`/asset_update asset_id unit_price=2420000`\n"
        "`/asset_update asset_id harga_beli=2559000 tanggal_beli=2026-06-10`"
    # Close the structure that was opened above.
    )

    return "\n".join(lines)

# Define build liabilities text for callers in this flow.
def build_liabilities_text(liabilities: list[dict]) -> str:
    """Build the data structure or message text for liabilities text."""
    # Handle the missing or empty liabilities case.
    if not liabilities:
        # Return ( to the caller.
        return (
            "📭 Belum ada liabilitas aktif.\n\n"
            "Tambah liabilitas:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`"
        # Close the structure that was opened above.
        )

    lines = ["💳 *Daftar Liabilitas Aktif*\n"]

    # Prepare total for the next step.
    total = 0

    # Process each i, liability in the current collection.
    for i, liability in enumerate(liabilities, 1):
        balance = float(liability.get("current_balance", 0) or 0)
        # Run this statement as part of the current workflow.
        total += balance

        # Open a multi-line structure for the values below.
        lines.append(
            f"{i}. *{liability.get('name', '-')}*\n"
            f"   💰 {format_rupiah(balance)} | {liability.get('category', '-')}\n"
            f"   📝 {liability.get('description', '-') or '-'}\n"
            f"   🔖 `{liability.get('id', '-')}`"
        # Close the structure that was opened above.
        )

    lines.append(f"\n💳 Total liabilitas aktif: *{format_rupiah(total)}*")

    return "\n".join(lines)


# Define build update result text for callers in this flow.
def build_update_result_text(result: dict, label: str) -> str:
    """Build the data structure or message text for update result text."""
    before = result.get("before", {}) or {}
    after = result.get("after", {}) or {}
    updates = result.get("updates", {}) or {}

    lines = [f"✅ {label} berhasil diupdate!\n"]

    lines.append(f"Nama: {after.get('name') or before.get('name') or '-'}")
    lines.append(f"ID: {after.get('id') or before.get('id') or '-'}")

    lines.append("\nField yang berubah:")

    # Process each field in the current collection.
    for field in updates:
        if field == "updated_at":
            # Skip the rest of this loop iteration after handling this case.
            continue

        old_value = before.get(field, "-")
        new_value = after.get(field, updates.get(field, "-"))

        lines.append(f"- {field}: {old_value} → {new_value}")

    return "\n".join(lines)


# Define build snapshots text for callers in this flow.
def build_snapshots_text(snapshots: list[dict]) -> str:
    """Build the data structure or message text for snapshots text."""
    # Handle the missing or empty snapshots case.
    if not snapshots:
        return "📭 Belum ada snapshot net worth."

    lines = ["📈 *Riwayat Net Worth Snapshot*\n"]

    # Process each snap in the current collection.
    for snap in snapshots:
        # Open a multi-line structure for the values below.
        lines.append(
            f"• `{snap.get('snapshot_date', '-')}` — "
            f"*{format_rupiah(float(snap.get('net_worth', 0) or 0))}*\n"
            f"  Rekening: {format_rupiah(float(snap.get('total_accounts', 0) or 0))} | "
            f"Aset: {format_rupiah(float(snap.get('total_assets', 0) or 0))}"
        # Close the structure that was opened above.
        )

    return "\n".join(lines)

# Handle the asynchronous networth handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare summary for the next step.
    summary = calculate_net_worth()

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_networth_text(summary),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Handle the asynchronous assets handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare assets for the next step.
    assets = get_assets(active_only=True)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_assets_text(assets),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Handle the asynchronous liabilities handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare liabilities for the next step.
    liabilities = get_liabilities(active_only=True)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_liabilities_text(liabilities),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Define build asset added text for callers in this flow.
def build_asset_added_text(asset: dict) -> str:
    """Build the data structure or message text for asset added text."""
    quantity = asset.get("quantity", "")
    unit = asset.get("unit", "")
    price = float(asset.get("price_per_unit", 0) or 0)
    has_unit_info = bool(str(quantity or "").strip()) and bool(str(unit or "").strip())

    # Handle the case where has_unit_info.
    if has_unit_info:
        # Open a multi-line structure for the values below.
        lines = [
            "✅ *Aset berhasil ditambahkan!*\n",
            f"📦 Nama: *{asset.get('name')}*",
            f"📁 Kategori: *{asset.get('category')}*",
            f"🔢 Jumlah: *{quantity} {unit}*",
            f"🏷️ Harga sekarang/{unit}: *{format_rupiah(price)}*",
            f"📊 Nilai saat ini: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*",
            f"📅 Update harga: `{asset.get('last_price_update') or '-'}`",
        # Close the structure that was opened above.
        ]
        lines.extend(format_asset_gain_lines(asset, indent=""))
        # Open a multi-line structure for the values below.
        lines.extend([
            f"📝 Deskripsi: {asset.get('description') or '-'}",
            f"🔖 ID: `{asset.get('id')}`",
        # Close the structure that was opened above.
        ])
        return "\n".join(lines)

    # Open a multi-line structure for the values below.
    lines = [
        "✅ *Aset berhasil ditambahkan!*\n",
        f"📦 Nama: *{asset.get('name')}*",
        f"💰 Nilai: *{format_rupiah(float(asset.get('current_value', 0) or 0))}*",
        f"📁 Kategori: *{asset.get('category')}*",
    # Close the structure that was opened above.
    ]
    lines.extend(format_asset_gain_lines(asset, indent=""))
    # Open a multi-line structure for the values below.
    lines.extend([
        f"📝 Deskripsi: {asset.get('description') or '-'}",
        f"🔖 ID: `{asset.get('id')}`",
    # Close the structure that was opened above.
    ])
    return "\n".join(lines)


# Define asset edit or continue keyboard for callers in this flow.
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
    # Return InlineKeyboardMarkup([ to the caller.
    return InlineKeyboardMarkup([
        # Open a multi-line structure for the values below.
        [
            InlineKeyboardButton("✅ Simpan", callback_data="confirm:asset"),
            InlineKeyboardButton("✏️ Edit dulu", callback_data="editflow:edit:asset"),
        # Close the structure that was opened above.
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel:asset")],
    # Close the structure that was opened above.
    ])


# Define build asset confirm preview for callers in this flow.
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

        # Open a multi-line structure for the values below.
        lines = [
            "📦 *Preview Tambah Aset*\n",
            f"Nama: *{md_safe(data.get('name') or '-')}*",
            f"Kategori: *{md_safe(data.get('category') or 'Other Asset')}*",
            f"Jumlah: *{quantity} {md_safe(unit)}*",
            f"Harga sekarang/{md_safe(unit)}: *{format_rupiah(price)}*",
            f"Nilai saat ini: *{format_rupiah(current_value)}*",
        # Close the structure that was opened above.
        ]

        # Handle the case where purchase_price > 0.
        if purchase_price > 0:
            # Prepare modal for the next step.
            modal = float(quantity or 0) * purchase_price
            # Prepare floating for the next step.
            floating = current_value - modal
            # Prepare pct for the next step.
            pct = (floating / modal * 100) if modal > 0 else 0
            sign = "+" if floating >= 0 else "-"
            # Open a multi-line structure for the values below.
            lines.extend([
                f"Harga beli/{md_safe(unit)}: *{format_rupiah(purchase_price)}*",
                f"Modal beli: *{format_rupiah(modal)}*",
                f"Floating P/L: *{sign}{format_rupiah(abs(floating))} ({pct:+.2f}%)*",
            # Close the structure that was opened above.
            ])

        # Handle the case where purchase_date.
        if purchase_date:
            lines.append(f"Tanggal beli: `{md_safe(purchase_date)}`")

        # Open a multi-line structure for the values below.
        lines.extend([
            f"Deskripsi: {md_safe(data.get('description') or '-')}",
            "\nSimpan aset ini?",
        # Close the structure that was opened above.
        ])
        return "\n".join(lines)

    current_value = float(data.get("amount", 0) or 0)
    # Open a multi-line structure for the values below.
    lines = [
        "📦 *Preview Tambah Aset*\n",
        f"Nama: *{md_safe(data.get('name') or '-')}*",
        f"Kategori: *{md_safe(data.get('category') or 'Other Asset')}*",
        f"Nilai: *{format_rupiah(current_value)}*",
    # Close the structure that was opened above.
    ]

    # Handle the case where purchase_price > 0.
    if purchase_price > 0:
        lines.append(f"Harga beli/modal: *{format_rupiah(purchase_price)}*")
    # Handle the case where purchase_date.
    if purchase_date:
        lines.append(f"Tanggal beli: `{md_safe(purchase_date)}`")

    # Open a multi-line structure for the values below.
    lines.extend([
        f"Deskripsi: {md_safe(data.get('description') or '-')}",
        "\nSimpan aset ini?",
    # Close the structure that was opened above.
    ])
    return "\n".join(lines)


ASSET_ADD_FLOW_KEY = "pending_asset_add_flow"
ASSET_ADD_PROMPT_MESSAGE_KEY = "pending_asset_add_prompt_message_id"
ASSET_ADD_SKIP_WORDS = {"skip", "lewati", "kosong", "-", "tidak", "tidak ada", "ga ada", "gak ada", "nggak ada"}
ASSET_ADD_CANCEL_WORDS = {"cancel", "batal", "/cancel"}
ASSET_ADD_OPTIONAL_STEPS = {"purchase_price", "purchase_date", "category", "description"}
# Prepare ASSET ADD MIN MANUAL VALUE for the next step.
ASSET_ADD_MIN_MANUAL_VALUE = 1_000


# Define asset flow is skip for callers in this flow.
def _asset_flow_is_skip(text: str) -> bool:
    """Check whether user wants to skip an optional asset wizard field."""
    return str(text or "").strip().lower() in ASSET_ADD_SKIP_WORDS


# Define asset flow is cancel for callers in this flow.
def _asset_flow_is_cancel(text: str) -> bool:
    """Check whether user wants to cancel the asset wizard."""
    return str(text or "").strip().lower() in ASSET_ADD_CANCEL_WORDS


# Define asset add step keyboard for callers in this flow.
def asset_add_step_keyboard(step: str) -> InlineKeyboardMarkup:
    """Build the inline keyboard for one asset_add wizard step."""
    # Prepare rows for the next step.
    rows = []
    # Handle the case where step in ASSET_ADD_OPTIONAL_STEPS.
    if step in ASSET_ADD_OPTIONAL_STEPS:
        rows.append([InlineKeyboardButton("⏭️ Lewati", callback_data="asset_add:skip")])
    rows.append([InlineKeyboardButton("🚫 Batal", callback_data="cancel:asset_add")])
    # Return InlineKeyboardMarkup(rows) to the caller.
    return InlineKeyboardMarkup(rows)


# Define asset flow prompt for callers in this flow.
def _asset_flow_prompt(step: str, data: dict | None = None) -> str:
    """Build one prompt text for the asset_add wizard."""
    # Prepare data for the next step.
    data = data or {}

    # Open a multi-line structure for the values below.
    prompts = {
        "name": (
            "📦 *Tambah Aset — Step 1/7*\n\n"
            "Asetnya apa?\n\n"
            "Contoh:\n"
            "`Emas Antam`\n"
            "`Laptop Kerja`"
        # Close the structure that was opened above.
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
        # Close the structure that was opened above.
        ),
        "purchase_price": (
            "🧾 *Tambah Aset — Step 3/7*\n\n"
            "Harga belinya berapa?\n\n"
            "Untuk aset satuan, isi harga beli per unit.\n"
            "Contoh:\n"
            "`2559000`\n"
            "`2.55 juta`\n\n"
            "Kalau belum mau diisi, klik *Lewati* atau ketik `lewati`."
        # Close the structure that was opened above.
        ),
        "purchase_date": (
            "📆 *Tambah Aset — Step 4/7*\n\n"
            "Tanggal belinya kapan?\n\n"
            "Contoh:\n"
            "`2026-06-10`\n"
            "`10/06/2026`\n"
            "`kemarin`\n\n"
            "Kalau tidak tahu / tidak mau isi, klik *Lewati* atau ketik `lewati`."
        # Close the structure that was opened above.
        ),
        "current_price": (
            "🏷️ *Tambah Aset — Step 5/7*\n\n"
            f"Jumlah: *{data.get('quantity')} {md_safe(data.get('unit') or '')}*\n\n"
            "Harga saat ini per unit berapa?\n\n"
            "Contoh:\n"
            "`2594000`\n"
            "`2.594 juta`"
        # Close the structure that was opened above.
        ),
        "category": (
            "📁 *Tambah Aset — Step 6/7*\n\n"
            "Kategorinya apa?\n\n"
            "Contoh:\n"
            "`Gold`\n"
            "`Electronics`\n"
            "`Investment`\n\n"
            "Kalau mau otomatis, klik *Lewati* atau ketik `lewati`."
        # Close the structure that was opened above.
        ),
        "description": (
            "📝 *Tambah Aset — Step 7/7*\n\n"
            "Deskripsinya apa?\n\n"
            "Contoh:\n"
            "`Tabungan emas`\n"
            "`Laptop kerja`\n\n"
            "Kalau kosong, klik *Lewati* atau ketik `lewati`."
        # Close the structure that was opened above.
        ),
    # Close the structure that was opened above.
    }

    return prompts.get(step, "Input tidak dikenali. Ketik `batal` untuk membatalkan.")


# Handle the asynchronous send asset add step prompt workflow.
async def send_asset_add_step_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, step: str, data: dict | None = None):
    """Send one asset wizard prompt and track its inline keyboard for later cleanup."""
    # Return await reply_tracked_inline_keyboard( to the caller.
    return await reply_tracked_inline_keyboard(
        # Include this value in the surrounding collection or call.
        update,
        # Include this value in the surrounding collection or call.
        context,
        # Include this value in the surrounding collection or call.
        _asset_flow_prompt(step, data),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=asset_add_step_keyboard(step),
        # Prepare state key for the next step.
        state_key=ASSET_ADD_PROMPT_MESSAGE_KEY,
    # Close the structure that was opened above.
    )


# Handle the asynchronous clear asset add step keyboard workflow.
async def clear_asset_add_step_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the old asset wizard keyboard after the user answers."""
    chat = getattr(update, "effective_chat", None)
    chat_id = getattr(chat, "id", None) or getattr(getattr(update, "message", None), "chat_id", None)
    # Wait for clear_tracked_inline_keyboard before continuing this flow.
    await clear_tracked_inline_keyboard(context, chat_id, ASSET_ADD_PROMPT_MESSAGE_KEY)


def start_asset_add_flow(context: ContextTypes.DEFAULT_TYPE, initial_data: dict | None = None, step: str = "name") -> None:
    """Start asset add wizard without discarding fields already known from command args."""
    context.user_data.pop("pending_asset_price", None)
    context.user_data.pop("pending_asset_confirm", None)
    # Open a multi-line structure for the values below.
    context.user_data[ASSET_ADD_FLOW_KEY] = {
        "step": step or "name",
        "data": dict(initial_data or {}),
    # Close the structure that was opened above.
    }


# Define asset manual value too small for callers in this flow.
def _asset_manual_value_too_small(amount: float, raw_text: str) -> bool:
    """Guard accidental Rp1/Rp2 asset values that usually mean the user misunderstood the field."""
    raw = str(raw_text or "").strip().lower()
    # Handle the case where amount >= ASSET_ADD_MIN_MANUAL_VALUE.
    if amount >= ASSET_ADD_MIN_MANUAL_VALUE:
        # Return False to the caller.
        return False
    return bool(re.fullmatch(r"(?:rp\.?\s*)?\d+(?:[.,]0+)?", raw))


# Define build asset data from flow for callers in this flow.
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
    # Run this statement as part of the current workflow.
    name, category = guess_asset_category_and_name(name, category)

    quantity = data.get("quantity")
    unit = data.get("unit", "") or ""
    price_per_unit = data.get("price_per_unit")
    current_value = data.get("amount")

    if quantity not in [None, ""] and str(unit).strip():
        asset_type = "gold" if ("emas" in name.lower() or category.lower() in ["gold", "emas"]) else "unit"
        # Prepare amount for the next step.
        amount = float(quantity or 0) * float(price_per_unit or 0)
    # Handle the fallback path after earlier conditions are skipped.
    else:
        asset_type = "manual"
        # Prepare amount for the next step.
        amount = float(current_value or 0)
        # Prepare quantity for the next step.
        quantity = None
        unit = ""
        # Prepare price per unit for the next step.
        price_per_unit = None

    # Return { to the caller.
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
    # Close the structure that was opened above.
    }


# Handle the asynchronous finish asset add flow workflow.
async def _finish_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> bool:
    """Move completed asset wizard state into confirmation preview."""
    # Prepare asset data for the next step.
    asset_data = _build_asset_data_from_flow(data)
    context.user_data["pending_asset_confirm"] = asset_data
    # Run this statement as part of the current workflow.
    context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
    # Run this statement as part of the current workflow.
    context.user_data.pop(ASSET_ADD_PROMPT_MESSAGE_KEY, None)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        f"{build_asset_confirm_preview(asset_data)}\n\nMau simpan, edit dulu, atau batal?",
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=asset_edit_or_continue_keyboard(),
    # Close the structure that was opened above.
    )
    # Return True to the caller.
    return True


# Handle the asynchronous handle pending asset add flow workflow.
async def handle_pending_asset_add_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> bool:
    """Handle one text answer for the asset_add wizard."""
    # Prepare flow for the next step.
    flow = context.user_data.get(ASSET_ADD_FLOW_KEY)
    # Handle the missing or empty flow case.
    if not flow:
        # Return False to the caller.
        return False

    text = str(user_text or "").strip()
    # Wait for clear_asset_add_step_keyboard before continuing this flow.
    await clear_asset_add_step_keyboard(update, context)

    # Handle the case where _asset_flow_is_cancel(text).
    if _asset_flow_is_cancel(text):
        # Run this statement as part of the current workflow.
        context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
        context.user_data.pop("pending_asset_price", None)
        context.user_data.pop("pending_asset_confirm", None)
        await update.message.reply_text("🚫 Tambah aset dibatalkan. Tidak ada data yang disimpan.")
        # Return True to the caller.
        return True

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    if step == "name":
        # Handle the missing or empty text case.
        if not text:
            await send_asset_add_step_prompt(update, context, "name", data)
            # Return True to the caller.
            return True
        data["name"] = text
        flow["step"] = "quantity"
        await send_asset_add_step_prompt(update, context, "quantity", data)
        # Return True to the caller.
        return True

    if step == "quantity":
        # Prepare qty info for the next step.
        qty_info = parse_asset_quantity_input(text)
        # Handle the case where qty_info.
        if qty_info:
            data["quantity"] = qty_info["quantity"]
            data["unit"] = qty_info["unit"]
            if qty_info.get("price_per_unit"):
                data["price_per_unit"] = qty_info.get("price_per_unit")
            flow["step"] = "purchase_price"
            await send_asset_add_step_prompt(update, context, "purchase_price", data)
            # Return True to the caller.
            return True

        # Prepare amount for the next step.
        amount = parse_human_amount(text)
        # Handle the case where amount > 0.
        if amount > 0:
            # Handle the case where _asset_manual_value_too_small(amount, text).
            if _asset_manual_value_too_small(amount, text):
                # Wait for update.message.reply_text before continuing this flow.
                await update.message.reply_text(
                    "⚠️ Nilai aset terlihat terlalu kecil. Kalau maksudnya 1 juta, tulis `1 juta`.\n"
                    "Kalau ini aset berbasis unit, tulis seperti `1 buah` atau `999 gram`.",
                    parse_mode="Markdown",
                # Close the structure that was opened above.
                )
                await send_asset_add_step_prompt(update, context, "quantity", data)
                # Return True to the caller.
                return True
            data["amount"] = amount
            data["quantity"] = None
            data["unit"] = ""
            data["price_per_unit"] = None
            flow["step"] = "purchase_price"
            await send_asset_add_step_prompt(update, context, "purchase_price", data)
            # Return True to the caller.
            return True

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Jumlah/nilai aset belum valid.\n\nContoh: `999 gram`, `1 buah`, `8000000`, atau `8 juta`.",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        await send_asset_add_step_prompt(update, context, "quantity", data)
        # Return True to the caller.
        return True

    if step == "purchase_price":
        # Handle the case where _asset_flow_is_skip(text).
        if _asset_flow_is_skip(text):
            data["purchase_price_per_unit"] = None
        # Handle the fallback path after earlier conditions are skipped.
        else:
            # Prepare purchase price for the next step.
            purchase_price = parse_human_amount(text)
            # Handle the case where purchase_price <= 0.
            if purchase_price <= 0:
                # Wait for update.message.reply_text before continuing this flow.
                await update.message.reply_text(
                    "❌ Harga beli belum valid. Contoh: `2559000`, `2.55 juta`, atau klik *Lewati*.",
                    parse_mode="Markdown",
                # Close the structure that was opened above.
                )
                await send_asset_add_step_prompt(update, context, "purchase_price", data)
                # Return True to the caller.
                return True
            data["purchase_price_per_unit"] = purchase_price

        flow["step"] = "purchase_date"
        await send_asset_add_step_prompt(update, context, "purchase_date", data)
        # Return True to the caller.
        return True

    if step == "purchase_date":
        # Handle the case where _asset_flow_is_skip(text).
        if _asset_flow_is_skip(text):
            data["purchase_date"] = ""
        # Handle the fallback path after earlier conditions are skipped.
        else:
            data["purchase_date"] = detect_date(text)

        if data.get("quantity") not in [None, ""] and str(data.get("unit") or "").strip() and not data.get("price_per_unit"):
            flow["step"] = "current_price"
            await send_asset_add_step_prompt(update, context, "current_price", data)
            # Return True to the caller.
            return True

        flow["step"] = "category"
        await send_asset_add_step_prompt(update, context, "category", data)
        # Return True to the caller.
        return True

    if step == "current_price":
        # Prepare current price for the next step.
        current_price = parse_human_amount(text)
        # Handle the case where current_price <= 0.
        if current_price <= 0:
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                "❌ Harga saat ini belum valid. Contoh: `2594000` atau `2.594 juta`.",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            await send_asset_add_step_prompt(update, context, "current_price", data)
            # Return True to the caller.
            return True
        data["price_per_unit"] = current_price
        data["amount"] = float(data.get("quantity") or 0) * current_price
        flow["step"] = "category"
        await send_asset_add_step_prompt(update, context, "category", data)
        # Return True to the caller.
        return True

    if step == "category":
        data["category"] = "" if _asset_flow_is_skip(text) else text
        flow["step"] = "description"
        await send_asset_add_step_prompt(update, context, "description", data)
        # Return True to the caller.
        return True

    if step == "description":
        data["description"] = "" if _asset_flow_is_skip(text) else text
        # Return await _finish_asset_add_flow(update, context, data) to the caller.
        return await _finish_asset_add_flow(update, context, data)

    # Run this statement as part of the current workflow.
    context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
    # Run this statement as part of the current workflow.
    context.user_data.pop(ASSET_ADD_PROMPT_MESSAGE_KEY, None)
    await update.message.reply_text("❌ Sesi tambah aset tidak valid. Coba ulangi `/asset_add`.", parse_mode="Markdown")
    # Return True to the caller.
    return True


# Handle the asynchronous handle asset add skip callback workflow.
async def handle_asset_add_skip_callback(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Lewati button for optional asset_add wizard steps."""
    # Prepare flow for the next step.
    flow = context.user_data.get(ASSET_ADD_FLOW_KEY)
    # Handle the missing or empty flow case.
    if not flow:
        await safe_edit_message(query, "❌ Sesi tambah aset expired. Jalankan `/asset_add` lagi.", parse_mode="Markdown")
        # Return control to the caller.
        return

    step = flow.get("step", "name")
    data = flow.setdefault("data", {})

    # Handle the case where step not in ASSET_ADD_OPTIONAL_STEPS.
    if step not in ASSET_ADD_OPTIONAL_STEPS:
        await safe_edit_message(query, "ℹ️ Step ini wajib diisi, jadi tidak bisa dilewati.", parse_mode="Markdown")
        # Return control to the caller.
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
    # Handle the fallback path after earlier conditions are skipped.
    else:
        data["description"] = ""
        # Prepare asset data for the next step.
        asset_data = _build_asset_data_from_flow(data)
        context.user_data["pending_asset_confirm"] = asset_data
        # Run this statement as part of the current workflow.
        context.user_data.pop(ASSET_ADD_FLOW_KEY, None)
        # Run this statement as part of the current workflow.
        context.user_data.pop(ASSET_ADD_PROMPT_MESSAGE_KEY, None)
        # Wait for safe_edit_message before continuing this flow.
        await safe_edit_message(
            # Include this value in the surrounding collection or call.
            query,
            f"{build_asset_confirm_preview(asset_data)}\n\nMau simpan, edit dulu, atau batal?",
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=asset_edit_or_continue_keyboard(),
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    flow["step"] = next_step
    # Wait for safe_edit_message before continuing this flow.
    await safe_edit_message(
        # Include this value in the surrounding collection or call.
        query,
        # Include this value in the surrounding collection or call.
        _asset_flow_prompt(next_step, data),
        parse_mode="Markdown",
        # Prepare reply markup for the next step.
        reply_markup=asset_add_step_keyboard(next_step),
    # Close the structure that was opened above.
    )
    context.user_data[ASSET_ADD_PROMPT_MESSAGE_KEY] = getattr(query.message, "message_id", None)


# Handle the asynchronous asset add handler workflow.
async def asset_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /asset_add as a guided wizard, while keeping old pipe format compatible."""
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _command_args_from_update(update, context, "asset_add")
        # Start the wizard when the command has no inline arguments.
        if not command_args:
            # Run this statement as part of the current workflow.
            start_asset_add_flow(context)
            await send_asset_add_step_prompt(update, context, "name", {})
            # Return control to the caller.
            return

        raw_arg = " ".join(command_args).strip()
        if "|" not in raw_arg:
            start_asset_add_flow(context, {"name": raw_arg}, step="quantity")
            await send_asset_add_step_prompt(update, context, "quantity", {"name": raw_arg})
            # Return control to the caller.
            return

        data = parse_pipe_add_args(command_args, "asset")

        if data.get("needs_unit_price"):
            context.user_data["pending_asset_price"] = data
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                # Include this value in the surrounding collection or call.
                build_asset_unit_price_prompt(data),
                parse_mode="Markdown",
                reply_markup=cancel_keyboard("asset_price"),
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        context.user_data["pending_asset_confirm"] = data
        context.user_data.pop("pending_asset_price", None)

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"{build_asset_confirm_preview(data)}\n\nMau simpan, edit dulu, atau batal?",
            parse_mode="Markdown",
            # Prepare reply markup for the next step.
            reply_markup=asset_edit_or_continue_keyboard(),
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Gagal tambah aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_add Laptop`\n"
            "`/asset_add Laptop`\n"
            "`catet aset hp 10 juta`\n"
            "`tambah aset laptop 8 juta`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )


# Handle the asynchronous liability add handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        data = parse_pipe_add_args(context.args, "liability")

        # Open a multi-line structure for the values below.
        liability = add_liability(
            name=data["name"],
            current_balance=data["amount"],
            category=data["category"],
            description=data["description"],
        # Close the structure that was opened above.
        )

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "✅ *Liabilitas berhasil ditambahkan!*\n\n"
            f"💳 Nama: *{liability.get('name')}*\n"
            f"💰 Nominal: *{format_rupiah(float(liability.get('current_balance', 0) or 0))}*\n"
            f"📁 Kategori: *{liability.get('category')}*\n"
            f"📝 Deskripsi: {liability.get('description') or '-'}\n"
            f"🔖 ID: `{liability.get('id')}`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Gagal tambah liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_add Paylater | 1200000 | Paylater | Cicilan aktif`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )


# Handle the asynchronous asset update handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Read args from the original text so fallback routing keeps quoted values intact.
        command_args = _command_args_from_update(update, context, "asset_update")
        asset_id, updates = parse_pipe_update_args(command_args, "asset_update")
        # Prepare result for the next step.
        result = update_asset(asset_id, updates)

        if not result.get("success"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/assets`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_update_result_text(result, "Aset")
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Gagal update aset.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/asset_update asset_xxx amount=9000000`\n"
            "`/asset_update asset_xxx unit_price=2420000`\n"
            "`/asset_update asset_xxx harga_beli=2559000 tanggal_beli=2026-06-10`\n"
            "`/asset_update asset_xxx name=\"Laptop Baru\" category=Electronics`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )


# Handle the asynchronous liability update handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        liability_id, updates = parse_pipe_update_args(context.args, "liability_update")
        # Prepare result for the next step.
        result = update_liability(liability_id, updates)

        if not result.get("success"):
            # Wait for update.message.reply_text before continuing this flow.
            await update.message.reply_text(
                f"❌ {result.get('message')}\n\n"
                "Cek ID dengan command:\n"
                "`/liabilities`",
                parse_mode="Markdown",
            # Close the structure that was opened above.
            )
            # Return control to the caller.
            return

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            build_update_result_text(result, "Liabilitas")
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Gagal update liabilitas.\n\n"
            f"{str(e)}\n\n"
            "Contoh:\n"
            "`/liability_update liab_xxx | balance=1000000`\n"
            "`/liability_update liab_xxx | name=Paylater Shopee | balance=500000`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )


# Handle the asynchronous asset off handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Handle the missing or empty context.args case.
    if not context.args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan asset ID.\n\n"
            "Contoh:\n"
            "`/asset_off asset_xxx`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare asset id for the next step.
    asset_id = context.args[0].strip()
    # Prepare success for the next step.
    success = deactivate_asset(asset_id)

    # Handle the missing or empty success case.
    if not success:
        await update.message.reply_text("❌ Asset tidak ditemukan.")
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        f"✅ Asset berhasil dinonaktifkan:\n`{asset_id}`",
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Handle the asynchronous liability off handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Handle the missing or empty context.args case.
    if not context.args:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "❌ Masukkan liability ID.\n\n"
            "Contoh:\n"
            "`/liability_off liab_xxx`",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )
        # Return control to the caller.
        return

    # Prepare liability id for the next step.
    liability_id = context.args[0].strip()
    # Prepare success for the next step.
    success = deactivate_liability(liability_id)

    # Handle the missing or empty success case.
    if not success:
        await update.message.reply_text("❌ Liability tidak ditemukan.")
        # Return control to the caller.
        return

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        f"✅ Liability berhasil dinonaktifkan:\n`{liability_id}`",
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )


# Handle the asynchronous networth snapshot handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Run this operation in a guarded block so failures can be handled.
    try:
        # Prepare snapshot for the next step.
        snapshot = create_net_worth_snapshot()

        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            "✅ *Snapshot Net Worth berhasil disimpan!*\n\n"
            f"📅 Tanggal: `{snapshot.get('snapshot_date')}`\n"
            f"💰 Rekening: *{format_rupiah(float(snapshot.get('total_accounts', 0) or 0))}*\n"
            f"📦 Aset: *{format_rupiah(float(snapshot.get('total_assets', 0) or 0))}*\n"
            f"🏁 Net Worth: *{format_rupiah(float(snapshot.get('net_worth', 0) or 0))}*",
            parse_mode="Markdown",
        # Close the structure that was opened above.
        )

    # Handle an expected failure from the guarded operation above.
    except Exception as e:
        # Wait for update.message.reply_text before continuing this flow.
        await update.message.reply_text(
            f"❌ Gagal menyimpan snapshot net worth: {str(e)}"
        # Close the structure that was opened above.
        )


# Handle the asynchronous networth history handler workflow.
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
    # Handle the missing or empty is_authorized(update) case.
    if not is_authorized(update):
        # Wait for reject_unauthorized before continuing this flow.
        await reject_unauthorized(update)
        # Return control to the caller.
        return

    # Prepare snapshots for the next step.
    snapshots = get_net_worth_snapshots(limit=12)

    # Wait for update.message.reply_text before continuing this flow.
    await update.message.reply_text(
        # Include this value in the surrounding collection or call.
        build_snapshots_text(snapshots),
        parse_mode="Markdown",
    # Close the structure that was opened above.
    )

