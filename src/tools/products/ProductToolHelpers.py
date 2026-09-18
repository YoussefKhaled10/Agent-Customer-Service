from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.models.db_schemes.agent_db.schemes.product import Product


def serialize_product(
    product: Product,
    *,
    include_details: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "product_id": product.id,
        "category_id": product.category_id,
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "brand": product.brand,
        "price": format(Decimal(product.price), ".2f"),
        "currency": product.currency,
        "stock": product.stock,
        "reserved_stock": product.reserved_stock,
        "available_stock": product.available_stock,
        "in_stock": product.available_stock > 0,
        "short_description": product.short_description,
        "image_url": product.image_url,
        "is_active": product.is_active,
    }

    if include_details:
        result.update(
            {
                "description": product.description,
                "features": dict(product.features_json or {}),
                "warnings": list(product.warnings_json or []),
            }
        )

    return result
