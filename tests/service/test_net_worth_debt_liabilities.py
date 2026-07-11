"""Net worth uses canonical payable debt liabilities."""

from __future__ import annotations

from unittest.mock import patch

from app.services import net_worth_service


def test_active_payable_debt_is_subtracted_from_net_worth() -> None:
    with (
        patch.object(net_worth_service, "get_all_accounts", return_value=[{"balance": 1_000_000}]),
        patch.object(net_worth_service, "get_assets", return_value=[{"current_value": 500_000}]),
        patch.object(
            net_worth_service,
            "get_active_debts",
            return_value=[{"id": "debt_1", "type": "payable", "remaining_amount": 200_000}],
        ) as get_debts,
    ):
        result = net_worth_service.calculate_net_worth()

    get_debts.assert_called_once_with("payable")
    assert result["total_liabilities"] == 200_000
    assert result["net_worth"] == 1_300_000
    assert result["liabilities"][0]["id"] == "debt_1"

