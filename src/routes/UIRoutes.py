from __future__ import annotations
from src.core.AdminAuthorization import admin_page_required

from flask import Blueprint, render_template

from src.services.AdminDashboardService import AdminDashboardService


def create_ui_blueprint(
    dashboard_service: AdminDashboardService | None = None,
) -> Blueprint:
    blueprint = Blueprint("ui", __name__)
    active_dashboard = dashboard_service or AdminDashboardService()

    @blueprint.get("/")
    @blueprint.get("/chat")
    def chat():
        return render_template("customer/chat.html")

    @blueprint.get("/admin")
    @admin_page_required
    def admin():
        overview = active_dashboard.get_overview()
        return render_template(
            "admin/dashboard.html",
            metrics=overview.metrics,
            recent_orders=overview.recent_orders,
            knowledge_documents=overview.knowledge_documents,
            tool_success_rate=overview.tool_success_rate,
            agent_requests=overview.agent_requests,
        )

    return blueprint
