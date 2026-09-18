from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from src.core.AdminAuthorization import admin_page_required
from src.services.AdminKnowledgeService import AdminKnowledgeService


def create_admin_knowledge_blueprint(service: AdminKnowledgeService | None = None) -> Blueprint:
    bp=Blueprint("admin_knowledge",__name__,url_prefix="/admin/knowledge")
    svc=service or AdminKnowledgeService()

    @bp.get("")
    @admin_page_required
    def index():
        data=svc.list_documents(query=request.args.get("q",""),status=request.args.get("status","all"),active=request.args.get("active","all"),page=request.args.get("page",1,type=int))
        return render_template("admin/knowledge.html",data=data,categories=svc.category_choices(),active_page="knowledge")

    @bp.post("/upload")
    @admin_page_required
    def upload():
        try:
            result=svc.upload(file_storage=request.files.get("file"),title=request.form.get("title",""),category=request.form.get("category","general"),tags=request.form.get("tags",""))
            flash(f"Document indexed successfully with {result.chunks_created} chunks.","success")
            return redirect(url_for("admin_knowledge.details",document_id=result.document_id))
        except Exception as error:
            flash(str(error),"error"); return redirect(url_for("admin_knowledge.index"))

    @bp.get("/<int:document_id>")
    @admin_page_required
    def details(document_id:int):
        try: doc=svc.get_document(document_id)
        except ValueError: return "Knowledge document not found.",404
        return render_template("admin/knowledge_details.html",doc=doc,active_page="knowledge")

    @bp.post("/<int:document_id>/edit")
    @admin_page_required
    def edit(document_id: int):
        try:
            svc.edit_metadata(
                document_id,
                title=request.form.get("title", ""),
                category=request.form.get("category", "general"),
                tags=request.form.get("tags", "")
            )
            flash("Metadata updated successfully.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("admin_knowledge.details", document_id=document_id))

    @bp.post("/<int:document_id>/replace")
    @admin_page_required
    def replace(document_id: int):
        try:
            result = svc.replace_pdf(document_id, file_storage=request.files.get("file"))
            flash(f"Document replaced and indexed successfully with {result.chunks_created} chunks.", "success")
        except Exception as error:
            flash(str(error), "error")
        return redirect(url_for("admin_knowledge.details", document_id=document_id))

    @bp.get("/<int:document_id>/chunks")
    @admin_page_required
    def chunks(document_id:int):
        try: doc=svc.get_document(document_id)
        except ValueError: return "Knowledge document not found.",404
        return render_template("admin/knowledge_chunks.html",doc=doc,active_page="knowledge")

    @bp.post("/<int:document_id>/toggle")
    @admin_page_required
    def toggle(document_id:int):
        try: active=svc.set_active(document_id); flash(f"Document {'activated' if active else 'deactivated'}.","success")
        except ValueError as error: flash(str(error),"error")
        return redirect(url_for("admin_knowledge.details",document_id=document_id))

    @bp.post("/<int:document_id>/reindex")
    @admin_page_required
    def reindex(document_id:int):
        try: result=svc.reindex(document_id); flash(f"Re-indexed with {result.chunks_created} chunks.","success")
        except Exception as error: flash(str(error),"error")
        return redirect(url_for("admin_knowledge.details",document_id=document_id))

    @bp.post("/<int:document_id>/delete")
    @admin_page_required
    def delete(document_id:int):
        try: svc.delete_document(document_id); flash("Knowledge document deleted.","success"); return redirect(url_for("admin_knowledge.index"))
        except ValueError as error: flash(str(error),"error"); return redirect(url_for("admin_knowledge.details",document_id=document_id))

    return bp
