from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from src.core.AdminAuthorization import admin_page_required

from src.services.AdminProductService import AdminProductService
from src.services.AdminCategoryService import AdminCategoryService


def create_admin_product_blueprint(
    product_service: AdminProductService | None = None,
) -> Blueprint:
    blueprint = Blueprint("admin_products", __name__, url_prefix="/admin/products")
    service = product_service or AdminProductService()
    category_service = AdminCategoryService()

    @blueprint.get("")
    @admin_page_required
    def products():
        page_data = service.list_products(
            query=request.args.get("q", ""),
            status=request.args.get("status", "all"),
            page=request.args.get("page", 1, type=int),
            per_page=12,
        )
        return render_template(
            "admin/products.html",
            products=page_data.products,
            total=page_data.total,
            page=page_data.page,
            total_pages=page_data.pages,
            query=page_data.query,
            status=page_data.status,
            category_ids=page_data.category_ids,
            categories=category_service.active_categories(),
        )

    @blueprint.post("")
    @admin_page_required
    def create_product():
        try:
            service.create_product(request.form.to_dict())
            flash("Product created successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_products.products"))

    @blueprint.post("/<int:product_id>/update")
    @admin_page_required
    def update_product(product_id: int):
        try:
            service.update_product(product_id, request.form.to_dict())
            flash("Product updated successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_products.products"))

    @blueprint.post("/<int:product_id>/toggle")
    @admin_page_required
    def toggle_product(product_id: int):
        try:
            product = service.toggle_product(product_id)
            state = "activated" if product.is_active else "deactivated"
            flash(f"Product {state} successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_products.products"))

    @blueprint.get("/<int:product_id>/json")
    @admin_page_required
    def product_json(product_id: int):
        try:
            product = service.get_product(product_id)
        except ValueError as error:
            return jsonify({"error": "not_found", "message": str(error)}), 404
        return jsonify(
            {
                "id": product.id,
                "category_id": product.category_id,
                "name": product.name,
                "slug": product.slug,
                "sku": product.sku,
                "brand": product.brand,
                "price": str(product.price),
                "currency": product.currency,
                "stock": product.stock,
                "reserved_stock": product.reserved_stock,
                "available_stock": product.available_stock,
                "short_description": product.short_description,
                "description": product.description,
                "image_url": product.image_url,
                "is_active": product.is_active,
            }
        )

    return blueprint
