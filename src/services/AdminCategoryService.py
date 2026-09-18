from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, ContextManager

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.Database import database_session
from src.models.CategoryModel import CategoryModel
from src.models.db_schemes.agent_db.schemes.category import Category


@dataclass(frozen=True, slots=True)
class CategoryPage:
    categories: list[Category]
    product_counts: dict[int, int]
    total: int
    page: int
    pages: int
    query: str
    status: str


class AdminCategoryService:
    def __init__(
        self,
        session_factory: Callable[[], ContextManager[Session]] = database_session,
    ) -> None:
        self.session_factory = session_factory

    def list_categories(
        self,
        *,
        query: str = "",
        status: str = "all",
        page: int = 1,
        per_page: int = 12,
    ) -> CategoryPage:
        page = max(1, int(page))
        per_page = min(max(1, int(per_page)), 100)
        query = query.strip()
        status = status if status in {"all", "active", "inactive"} else "all"

        with self.session_factory() as session:
            statement = select(Category)
            count_statement = select(func.count(Category.id))
            filters: list[Any] = []
            if query:
                pattern = f"%{query}%"
                filters.append(
                    or_(
                        Category.name.ilike(pattern),
                        Category.slug.ilike(pattern),
                        Category.description.ilike(pattern),
                    )
                )
            if status == "active":
                filters.append(Category.is_active.is_(True))
            elif status == "inactive":
                filters.append(Category.is_active.is_(False))
            if filters:
                statement = statement.where(*filters)
                count_statement = count_statement.where(*filters)

            total = int(session.scalar(count_statement) or 0)
            categories = list(
                session.scalars(
                    statement
                    .order_by(Category.name.asc(), Category.id.asc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                ).all()
            )
            product_counts = {
                category.id: len(category.products)
                for category in categories
            }

        return CategoryPage(
            categories=categories,
            product_counts=product_counts,
            total=total,
            page=page,
            pages=max(1, (total + per_page - 1) // per_page),
            query=query,
            status=status,
        )

    def active_categories(self) -> list[Category]:
        with self.session_factory() as session:
            values = list(
                session.scalars(
                    select(Category)
                    .where(Category.is_active.is_(True))
                    .order_by(Category.name.asc())
                ).all()
            )
            for value in values:
                session.expunge(value)
            return values

    def get_category(self, category_id: int) -> Category:
        with self.session_factory() as session:
            category = CategoryModel.get_by_id(session, category_id)
            if category is None:
                raise ValueError("Category was not found.")
            session.expunge(category)
            return category

    def create_category(self, payload: dict[str, Any]) -> Category:
        name = self._required(payload.get("name"), "Category name")
        slug = self._slug(payload.get("slug") or name)
        description = self._optional(payload.get("description"))
        with self.session_factory() as session:
            if self._duplicate_exists(session, name=name, slug=slug):
                raise ValueError("A category with this name or slug already exists.")
            category = CategoryModel.create(
                session,
                name=name,
                slug=slug,
                description=description,
            )
            category_id = category.id
        return self.get_category(category_id)

    def update_category(self, category_id: int, payload: dict[str, Any]) -> Category:
        name = self._required(payload.get("name"), "Category name")
        slug = self._slug(payload.get("slug") or name)
        description = self._optional(payload.get("description"))
        with self.session_factory() as session:
            category = CategoryModel.get_by_id(session, category_id)
            if category is None:
                raise ValueError("Category was not found.")
            if self._duplicate_exists(
                session,
                name=name,
                slug=slug,
                exclude_id=category_id,
            ):
                raise ValueError("A category with this name or slug already exists.")
            category.name = name
            category.slug = slug
            category.description = description
            session.flush()
        return self.get_category(category_id)

    def toggle_category(self, category_id: int) -> Category:
        with self.session_factory() as session:
            category = CategoryModel.get_by_id(session, category_id)
            if category is None:
                raise ValueError("Category was not found.")
            CategoryModel.set_active_status(
                session,
                category_id,
                not category.is_active,
            )
        return self.get_category(category_id)

    @staticmethod
    def _duplicate_exists(
        session: Session,
        *,
        name: str,
        slug: str,
        exclude_id: int | None = None,
    ) -> bool:
        statement = select(Category.id).where(
            or_(
                func.lower(Category.name) == name.lower(),
                func.lower(Category.slug) == slug.lower(),
            )
        )
        if exclude_id is not None:
            statement = statement.where(Category.id != exclude_id)
        return session.scalar(statement.limit(1)) is not None

    @staticmethod
    def _required(value: Any, label: str) -> str:
        value = str(value or "").strip()
        if not value:
            raise ValueError(f"{label} is required.")
        return value

    @staticmethod
    def _optional(value: Any) -> str | None:
        value = str(value or "").strip()
        return value or None

    @staticmethod
    def _slug(value: Any) -> str:
        value = str(value or "").strip().lower()
        value = "-".join(value.replace("_", " ").split())
        if not value:
            raise ValueError("Category slug is required.")
        return value
