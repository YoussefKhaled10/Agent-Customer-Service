from __future__ import annotations

from flask import Blueprint, jsonify, session
from sqlalchemy import select

from src.core.AdminAuthorization import ADMIN_SESSION_KEY, current_admin
from src.core.AuthenticationDependencies import optional_customer_id
from src.models.Database import database_session
from src.models.db_schemes.agent_db.enums import CustomerRole
from src.models.db_schemes.agent_db.schemes.customer import Customer


def create_admin_authorization_blueprint() -> Blueprint:
    blueprint = Blueprint("admin_authorization", __name__, url_prefix="/api/admin")

    @blueprint.post("/session")
    def create_admin_session():
        customer_id, auth_error = optional_customer_id()
        if auth_error is not None:
            return auth_error
        if customer_id is None:
            return jsonify(
                {"error": "authentication_required", "message": "Sign in first."}
            ), 401

        with database_session() as db:
            customer = db.scalar(
                select(Customer).where(Customer.id == customer_id)
            )
            if customer is None or not customer.is_active:
                return jsonify(
                    {"error": "inactive_or_missing_customer", "message": "Account is unavailable."}
                ), 403
            if customer.role != CustomerRole.ADMIN.value:
                session.pop(ADMIN_SESSION_KEY, None)
                return jsonify(
                    {"error": "admin_forbidden", "message": "Administrator access is required."}
                ), 403
            session[ADMIN_SESSION_KEY] = customer.id
            session.permanent = True
            return jsonify(
                {
                    "authorized": True,
                    "admin": {
                        "id": customer.id,
                        "name": customer.name,
                        "email": customer.email,
                        "role": customer.role,
                    },
                }
            )

    @blueprint.get("/session")
    def inspect_admin_session():
        admin = current_admin()
        if admin is None:
            return jsonify({"authorized": False}), 401
        return jsonify(
            {
                "authorized": True,
                "admin": {
                    "id": admin.id,
                    "name": admin.name,
                    "email": admin.email,
                    "role": admin.role,
                },
            }
        )

    @blueprint.delete("/session")
    def delete_admin_session():
        session.pop(ADMIN_SESSION_KEY, None)
        return jsonify({"authorized": False})

    return blueprint
