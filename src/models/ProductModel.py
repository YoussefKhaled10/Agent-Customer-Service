from decimal import Decimal
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from src.models.CategoryModel import CategoryModel
from src.models.db_schemes.agent_db.schemes.product import Product

class ProductModel:
    @staticmethod
    def normalize_slug(value: str) -> str:
        return "-".join(value.strip().lower().split())

    @classmethod
    def get_by_id(cls, session: Session, product_id: int) -> Product | None:
        return session.get(Product, product_id) if product_id > 0 else None

    @classmethod
    def get_by_sku(cls, session: Session, sku: str) -> Product | None:
        return session.scalar(select(Product).where(func.lower(Product.sku) == sku.strip().lower()))

    @classmethod
    def create(cls, session: Session, *, category_id: int, name: str, sku: str,
               price: Decimal | str, stock: int = 0, brand: str | None = None,
               slug: str | None = None, short_description: str | None = None,
               description: str | None = None, features_json: dict[str, Any] | None = None,
               warnings_json: list[str] | None = None, image_url: str | None = None) -> Product:
        name, sku = name.strip(), sku.strip().upper()
        price_value = Decimal(str(price))
        if not name or not sku:
            raise ValueError("Product name and SKU are required.")
        if price_value < 0 or stock < 0:
            raise ValueError("Price and stock cannot be negative.")
        if cls.get_by_sku(session, sku):
            raise ValueError("A product with this SKU already exists.")
        product = Product(category_id=category_id, name=name,
            slug=cls.normalize_slug(slug or name), sku=sku,
            brand=brand.strip() if brand else None, price=price_value,
            currency="EGP", stock=stock, reserved_stock=0,
            short_description=short_description, description=description,
            features_json=features_json or {}, warnings_json=warnings_json or [],
            image_url=image_url, is_active=True)
        session.add(product)
        session.flush()
        return product

    @classmethod
    def search(cls, session: Session, query: str | None = None,
               category_id: int | None = None, category_slug: str | None = None,
               category_name: str | None = None, min_price: Decimal | None = None,
               max_price: Decimal | None = None, in_stock_only: bool = True,
               limit: int = 20) -> list[Product]:
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100.")
        resolved_category_id = category_id
        if category_slug:
            category = CategoryModel.get_by_slug(session, category_slug)
            if category is None or not category.is_active:
                raise ValueError("Category was not found or is inactive.")
            resolved_category_id = category.id
        elif category_name:
            category = CategoryModel.get_by_name(session, category_name)
            if category is None or not category.is_active:
                raise ValueError("Category was not found or is inactive.")
            resolved_category_id = category.id

        statement = select(Product).where(Product.is_active.is_(True))
        search_terms = cls.search_terms(query)
        if search_terms:
            searchable_columns = (
                Product.name,
                Product.brand,
                Product.sku,
                Product.short_description,
                Product.description,
            )
            statement = statement.where(
                or_(*(
                    column.ilike(f"%{term}%")
                    for term in search_terms
                    for column in searchable_columns
                ))
            )
        if resolved_category_id:
            statement = statement.where(Product.category_id == resolved_category_id)
        if min_price is not None:
            statement = statement.where(Product.price >= min_price)
        if max_price is not None:
            statement = statement.where(Product.price <= max_price)
        if in_stock_only:
            statement = statement.where((Product.stock - Product.reserved_stock) > 0)
        return list(session.scalars(statement.order_by(Product.price, Product.id).limit(limit)).all())

    @staticmethod
    def search_terms(query: str | None) -> list[str]:
        if not query or not query.strip():
            return []
        return list(dict.fromkeys(
            term.casefold()
            for term in query.split()
            if term.strip()
        ))

    @classmethod
    def update_stock(cls, session: Session, product_id: int, stock: int) -> Product:
        if stock < 0:
            raise ValueError("Stock cannot be negative.")
        product = cls.get_by_id(session, product_id)
        if product is None:
            raise ValueError("Product was not found.")
        if stock < product.reserved_stock:
            raise ValueError("Stock cannot be below reserved stock.")
        product.stock = stock
        session.flush()
        return product

    @classmethod
    def update_price(cls, session: Session, product_id: int, price: Decimal | str) -> Product:
        value = Decimal(str(price))
        if value < 0:
            raise ValueError("Price cannot be negative.")
        product = cls.get_by_id(session, product_id)
        if product is None:
            raise ValueError("Product was not found.")
        product.price = value
        session.flush()
        return product

    @classmethod
    def set_active_status(cls, session: Session, product_id: int, is_active: bool) -> Product:
        product = cls.get_by_id(session, product_id)
        if product is None:
            raise ValueError("Product was not found.")
        product.is_active = is_active
        session.flush()
        return product
