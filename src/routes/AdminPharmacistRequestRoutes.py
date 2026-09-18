from flask import Blueprint, flash, redirect, render_template, request, url_for
from src.core.AdminAuthorization import admin_page_required
from src.services.AdminSupportMonitoringServices import AdminPharmacistService

def create_admin_pharmacist_blueprint(service=None):
    bp=Blueprint("admin_pharmacist",__name__,url_prefix="/admin/pharmacist-requests"); svc=service or AdminPharmacistService()
    @bp.get("")
    @admin_page_required
    def index():
        data=svc.list(request.args.get("q",""),request.args.get("status","all"),request.args.get("page",1,type=int)); return render_template("admin/pharmacist_requests.html",data=data,active_page="pharmacist")
    @bp.route("/<int:item_id>",methods=["GET","POST"])
    @admin_page_required
    def details(item_id):
        if request.method=="POST":
            try: svc.update(item_id,request.form.get("status",""),request.form.get("assigned_to",""),request.form.get("internal_notes","")); flash("Pharmacist request updated.","success")
            except ValueError as e: flash(str(e),"error")
            return redirect(url_for("admin_pharmacist.details",item_id=item_id))
        try: item=svc.get(item_id)
        except ValueError: return render_template("errors/403.html"),404
        return render_template("admin/pharmacist_request_details.html",item=item,active_page="pharmacist")
    return bp
