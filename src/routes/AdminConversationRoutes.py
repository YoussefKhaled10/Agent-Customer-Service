from flask import Blueprint, flash, redirect, render_template, request, url_for
from src.core.AdminAuthorization import admin_page_required
from src.services.AdminSupportMonitoringServices import AdminConversationService

def create_admin_conversation_blueprint(service=None):
    bp=Blueprint("admin_conversations",__name__,url_prefix="/admin/conversations"); svc=service or AdminConversationService()
    @bp.get("")
    @admin_page_required
    def index():
        data=svc.list(request.args.get("q",""),request.args.get("status","all"),request.args.get("page",1,type=int)); return render_template("admin/conversations.html",data=data,active_page="conversations")
    @bp.get("/<int:item_id>")
    @admin_page_required
    def details(item_id):
        try: item=svc.get(item_id)
        except ValueError: return render_template("errors/403.html"),404
        return render_template("admin/conversation_details.html",item=item,active_page="conversations")
    @bp.post("/<int:item_id>/clear-pending")
    @admin_page_required
    def clear_pending(item_id):
        try: svc.clear_pending(item_id); flash("Pending action cleared.","success")
        except ValueError as e: flash(str(e),"error")
        return redirect(url_for("admin_conversations.details",item_id=item_id))
    return bp
