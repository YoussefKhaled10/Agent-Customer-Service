from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from src.core.AdminAuthorization import admin_page_required
from src.services.AdminCategoryService import AdminCategoryService


def create_admin_category_blueprint(
    category_service: AdminCategoryService | None = None,
) -> Blueprint:
    blueprint = Blueprint(
        "admin_categories",
        __name__,
        url_prefix="/admin/categories",
    )
    service = category_service or AdminCategoryService()

    @blueprint.get("")
    @admin_page_required
    def categories():
        page_data = service.list_categories(
            query=request.args.get("q", ""),
            status=request.args.get("status", "all"),
            page=request.args.get("page", 1, type=int),
            per_page=12,
        )
        return render_template(
            "admin/categories.html",
            categories=page_data.categories,
            product_counts=page_data.product_counts,
            total=page_data.total,
            page=page_data.page,
            total_pages=page_data.pages,
            query=page_data.query,
            status=page_data.status,
        )

    @blueprint.post("")
    @admin_page_required
    def create_category():
        try:
            service.create_category(request.form.to_dict())
            flash("Category created successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_categories.categories"))

    @blueprint.post("/<int:category_id>/update")
    @admin_page_required
    def update_category(category_id: int):
        try:
            service.update_category(category_id, request.form.to_dict())
            flash("Category updated successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_categories.categories"))

    @blueprint.post("/<int:category_id>/toggle")
    @admin_page_required
    def toggle_category(category_id: int):
        try:
            category = service.toggle_category(category_id)
            state = "activated" if category.is_active else "deactivated"
            flash(f"Category {state} successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_categories.categories"))

    @blueprint.get("/<int:category_id>/json")
    @admin_page_required
    def category_json(category_id: int):
        try:
            category = service.get_category(category_id)
        except ValueError as error:
            return jsonify({"error": "not_found", "message": str(error)}), 404
        return jsonify(
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "is_active": category.is_active,
            }
        )

    return blueprint
