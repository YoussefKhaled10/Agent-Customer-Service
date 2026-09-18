from flask import Blueprint,flash,redirect,render_template,request,url_for
from src.core.AdminAuthorization import admin_page_required
from src.models.db_schemes.agent_db.enums import OrderStatus
from src.services.AdminOrderService import AdminOrderService

def create_admin_order_blueprint(service=None):
    bp=Blueprint('admin_orders',__name__,url_prefix='/admin/orders'); service=service or AdminOrderService()
    @bp.get('')
    @admin_page_required
    def orders():
        page=service.list_orders(query=request.args.get('q',''),status=request.args.get('status','all'),page=request.args.get('page',1,type=int))
        return render_template('admin/orders.html',page_data=page,statuses=[x.value for x in OrderStatus],active_page='orders')
    @bp.get('/<int:order_id>')
    @admin_page_required
    def order_details(order_id):
        try: order=service.get_order(order_id)
        except ValueError as e: flash(str(e),'error'); return redirect(url_for('admin_orders.orders'))
        current=order.status.value if hasattr(order.status,'value') else str(order.status)
        next_statuses=sorted({x.value for x in OrderStatus} - {current, 'cancelled'})
        return render_template('admin/order_details.html',order=order,current_status=current,next_statuses=next_statuses,active_page='orders')
    @bp.post('/<int:order_id>/status')
    @admin_page_required
    def update_status(order_id):
        try: service.update_status(order_id,request.form.get('status','')); flash('Order status updated.','success')
        except ValueError as e: flash(str(e),'error')
        return redirect(url_for('admin_orders.order_details',order_id=order_id))
    @bp.post('/<int:order_id>/cancel')
    @admin_page_required
    def cancel(order_id):
        try: service.cancel(order_id); flash('Order cancelled and stock restored.','success')
        except ValueError as e: flash(str(e),'error')
        return redirect(url_for('admin_orders.order_details',order_id=order_id))
    @bp.post('/<int:order_id>/delete')
    @admin_page_required
    def delete(order_id):
        try: service.delete_order(order_id); flash('Order deleted completely.','success')
        except ValueError as e: flash(str(e),'error')
        return redirect(url_for('admin_orders.orders'))
    return bp
