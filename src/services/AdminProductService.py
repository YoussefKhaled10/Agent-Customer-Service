from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, ContextManager

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.ProductModel import ProductModel
from src.models.db_schemes.agent_db.schemes.product import Product


@dataclass(frozen=True, slots=True)
class ProductPage:
    products: list[Product]
    total: int
    page: int
    pages: int
    query: str
    status: str
    category_ids: list[int]


class AdminProductService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    def list_products(
        self,
        *,
        query: str = "",
        status: str = "all",
        page: int = 1,
        per_page: int = 12,
    ) -> ProductPage:
        page = max(1, page)
        per_page = min(max(1, per_page), 100)
        normalized_query = query.strip()
        normalized_status = status if status in {"all", "active", "inactive"} else "all"

        with self.session_factory() as session:
            statement = select(Product)
            count_statement = select(func.count()).select_from(Product)

            filters: list[Any] = []
            if normalized_query:
                pattern = f"%{normalized_query}%"
                filters.append(
                    or_(
                        Product.name.ilike(pattern),
                        Product.sku.ilike(pattern),
                        Product.brand.ilike(pattern),
                        Product.short_description.ilike(pattern),
                    )
                )
            if normalized_status == "active":
                filters.append(Product.is_active.is_(True))
            elif normalized_status == "inactive":
                filters.append(Product.is_active.is_(False))

            if filters:
                statement = statement.where(*filters)
                count_statement = count_statement.where(*filters)

            total = int(session.scalar(count_statement) or 0)
            products = list(
                session.scalars(
                    statement
                    .order_by(Product.updated_at.desc(), Product.id.desc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                ).all()
            )
            category_ids = list(
                session.scalars(
                    select(Product.category_id)
                    .distinct()
                    .order_by(Product.category_id)
                ).all()
            )

        pages = max(1, (total + per_page - 1) // per_page)
        return ProductPage(
            products=products,
            total=total,
            page=page,
            pages=pages,
            query=normalized_query,
            status=normalized_status,
            category_ids=category_ids,
        )

    def create_product(self, payload: dict[str, Any]) -> Product:
        with self.session_factory() as session:
            product = ProductModel.create(
                session,
                category_id=self._positive_int(payload.get("category_id"), "Category ID"),
                name=self._required(payload.get("name"), "Product name"),
                sku=self._required(payload.get("sku"), "SKU"),
                price=self._money(payload.get("price"), "Price"),
                stock=self._non_negative_int(payload.get("stock", 0), "Stock"),
                brand=self._optional(payload.get("brand")),
                slug=self._optional(payload.get("slug")),
                short_description=self._optional(payload.get("short_description")),
                description=self._optional(payload.get("description")),
                image_url=self._optional(payload.get("image_url")),
            )
            product_id = product.id
        return self.get_product(product_id)

    def update_product(self, product_id: int, payload: dict[str, Any]) -> Product:
        with self.session_factory() as session:
            product = ProductModel.get_by_id(session, product_id)
            if product is None:
                raise ValueError("Product was not found.")

            name = self._required(payload.get("name"), "Product name")
            sku = self._required(payload.get("sku"), "SKU").upper()
            duplicate = ProductModel.get_by_sku(session, sku)
            if duplicate is not None and duplicate.id != product_id:
                raise ValueError("Another product already uses this SKU.")

            product.category_id = self._positive_int(payload.get("category_id"), "Category ID")
            product.name = name
            product.sku = sku
            product.slug = ProductModel.normalize_slug(
                self._optional(payload.get("slug")) or name
            )
            product.brand = self._optional(payload.get("brand"))
            product.short_description = self._optional(payload.get("short_description"))
            product.description = self._optional(payload.get("description"))
            product.image_url = self._optional(payload.get("image_url"))
            session.flush()
            ProductModel.update_price(
                session,
                product_id,
                self._money(payload.get("price"), "Price"),
            )
            ProductModel.update_stock(
                session,
                product_id,
                self._non_negative_int(payload.get("stock"), "Stock"),
            )
        return self.get_product(product_id)

    def toggle_product(self, product_id: int) -> Product:
        with self.session_factory() as session:
            product = ProductModel.get_by_id(session, product_id)
            if product is None:
                raise ValueError("Product was not found.")
            ProductModel.set_active_status(session, product_id, not product.is_active)
        return self.get_product(product_id)

    def get_product(self, product_id: int) -> Product:
        with self.session_factory() as session:
            product = ProductModel.get_by_id(session, product_id)
            if product is None:
                raise ValueError("Product was not found.")
            session.expunge(product)
            return product

    @staticmethod
    def _required(value: Any, label: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{label} is required.")
        return normalized

    @staticmethod
    def _optional(value: Any) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @staticmethod
    def _positive_int(value: Any, label: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} must be an integer.") from error
        if parsed <= 0:
            raise ValueError(f"{label} must be greater than zero.")
        return parsed

    @classmethod
    def _non_negative_int(cls, value: Any, label: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} must be an integer.") from error
        if parsed < 0:
            raise ValueError(f"{label} cannot be negative.")
        return parsed

    @staticmethod
    def _money(value: Any, label: str) -> Decimal:
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, TypeError) as error:
            raise ValueError(f"{label} must be a valid number.") from error
        if parsed < 0:
            raise ValueError(f"{label} cannot be negative.")
        return parsed.quantize(Decimal("0.01"))
