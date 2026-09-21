from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.models.db_schemes.agent_db.schemes.category import Category

class CategoryModel:
    @staticmethod
    def normalize_slug(value: str) -> str:
        return "-".join(value.strip().lower().split())

    @classmethod
    def get_by_id(cls, session: Session, category_id: int) -> Category | None:
        return session.get(Category, category_id) if category_id > 0 else None

    @classmethod
    def get_by_slug(cls, session: Session, slug: str) -> Category | None:
        return session.scalar(select(Category).where(Category.slug == cls.normalize_slug(slug)))

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Category | None:
        normalized = name.strip()
        if not normalized:
            return None
        return session.scalar(
            select(Category).where(
                func.lower(Category.name) == normalized.lower()
            )
        )

    @classmethod
    def create(cls, session: Session, name: str, slug: str | None = None,
               description: str | None = None) -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Category name is required.")
        normalized_slug = cls.normalize_slug(slug or name)
        if cls.get_by_slug(session, normalized_slug):
            raise ValueError("A category with this slug already exists.")
        category = Category(name=name, slug=normalized_slug,
                            description=description.strip() if description else None,
                            is_active=True)
        session.add(category)
        session.flush()
        return category

    @classmethod
    def list_categories(cls, session: Session, active_only: bool = False) -> list[Category]:
        statement = select(Category)
        if active_only:
            statement = statement.where(Category.is_active.is_(True))
        return list(session.scalars(statement.order_by(Category.name)).all())

    @classmethod
    def set_active_status(cls, session: Session, category_id: int, is_active: bool) -> Category:
        category = cls.get_by_id(session, category_id)
        if category is None:
            raise ValueError("Category was not found.")
        category.is_active = is_active
        session.flush()
        return category
