from flask import Blueprint,flash,redirect,render_template,request,url_for
from src.core.AdminAuthorization import admin_page_required,current_admin
from src.services.AdminCustomerService import AdminCustomerService

def create_admin_customer_blueprint(service=None):
    bp=Blueprint('admin_customers',__name__,url_prefix='/admin/customers'); service=service or AdminCustomerService()
    @bp.get('')
    @admin_page_required
    def customers():
        page,orders,conversations=service.list_customers(query=request.args.get('q',''),status=request.args.get('status','all'),role=request.args.get('role','all'),page=request.args.get('page',1,type=int))
        return render_template('admin/customers.html',page_data=page,order_counts=orders,conversation_counts=conversations,active_page='customers')
    @bp.get('/<int:customer_id>')
    @admin_page_required
    def customer_details(customer_id):
        try: customer,orders=service.get_customer(customer_id)
        except ValueError as e: flash(str(e),'error'); return redirect(url_for('admin_customers.customers'))
        return render_template('admin/customer_details.html',customer=customer,orders=orders,active_page='customers')
    @bp.post('/<int:customer_id>/toggle')
    @admin_page_required
    def toggle_customer(customer_id):
        try:
            admin=current_admin(); state=service.toggle(customer_id,admin.id); flash(f"Customer {'activated' if state else 'deactivated'} successfully.",'success')
        except ValueError as e: flash(str(e),'error')
        return redirect(request.referrer or url_for('admin_customers.customers'))
    return bp
