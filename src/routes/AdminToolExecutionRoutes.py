from flask import Blueprint, flash, redirect, render_template, request, url_for
from src.core.AdminAuthorization import admin_page_required
from src.services.AdminSupportMonitoringServices import AdminToolExecutionService

def create_admin_tool_execution_blueprint(service=None):
    bp=Blueprint("admin_tool_executions",__name__,url_prefix="/admin/tool-executions"); svc=service or AdminToolExecutionService()
    @bp.get("")
    @admin_page_required
    def index():
        data=svc.list(request.args.get("q",""),request.args.get("status","all"),request.args.get("page",1,type=int)); return render_template("admin/tool_executions.html",data=data,active_page="tools")
    @bp.get("/<int:item_id>")
    @admin_page_required
    def details(item_id):
        try: item=svc.get(item_id)
        except ValueError: return render_template("errors/403.html"),404
        return render_template("admin/tool_execution_details.html",item=item,active_page="tools")
    return bp
