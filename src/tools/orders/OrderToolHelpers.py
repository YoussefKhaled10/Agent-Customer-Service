from __future__ import annotations

from decimal import Decimal
from typing import Any


def enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def serialize_order_summary(order: Any) -> dict[str, Any]:
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": enum_value(order.status),
        "total_amount": format(Decimal(order.total_amount), ".2f"),
        "currency": order.currency,
        "item_count": len(order.items),
        "created_at": (
            order.created_at.isoformat()
            if getattr(order, "created_at", None) is not None
            else None
        ),
    }


def serialize_order_details(order: Any) -> dict[str, Any]:
    result = serialize_order_summary(order)
    result.update(
        {
            "shipping_address": order.shipping_address,
            "customer_notes": order.customer_notes,
            "updated_at": (
                order.updated_at.isoformat()
                if getattr(order, "updated_at", None) is not None
                else None
            ),
            "items": [
                {
                    "order_item_id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name_snapshot,
                    "product_sku": item.product_sku_snapshot,
                    "quantity": item.quantity,
                    "unit_price": format(Decimal(item.unit_price), ".2f"),
                    "subtotal": format(Decimal(item.subtotal), ".2f"),
                }
                for item in order.items
            ],
        }
    )
    return result
