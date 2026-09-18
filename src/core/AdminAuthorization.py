from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar, cast

from flask import jsonify, redirect, request, session
from sqlalchemy import select

from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import CustomerRole
from src.models.db_schemes.agent_db.schemes.customer import Customer

F = TypeVar("F", bound=Callable[..., Any])
ADMIN_SESSION_KEY = "admin_customer_id"


def _active_admin(customer_id: int | None) -> Customer | None:
    if customer_id is None:
        return None
    with database_session() as db:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.is_active.is_(True),
                Customer.role == CustomerRole.ADMIN.value,
            )
        )
        if customer is None:
            return None
        db.expunge(customer)
        return customer


def current_admin() -> Customer | None:
    raw_id = session.get(ADMIN_SESSION_KEY)
    try:
        customer_id = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        session.pop(ADMIN_SESSION_KEY, None)
        return None
    customer = _active_admin(customer_id)
    if customer is None:
        session.pop(ADMIN_SESSION_KEY, None)
    return customer


def admin_page_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        admin = current_admin()
        if admin is None:
            return redirect(
                f"/login?next={request.path}"
            )
        return view(*args, **kwargs)

    return cast(F, wrapped)


def admin_api_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        admin = current_admin()
        if admin is None:
            return jsonify(
                {
                    "error": "admin_authorization_required",
                    "message": "Administrator access is required.",
                }
            ), 403
        return view(*args, **kwargs)

    return cast(F, wrapped)
