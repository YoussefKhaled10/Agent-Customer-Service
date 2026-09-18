from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from src.models.Database import database_session
from src.models.OrderModel import OrderModel
from src.models.db_schemes.agent_db.enums import OrderStatus
from src.models.db_schemes.agent_db.schemes.customer import Customer
from src.models.db_schemes.agent_db.schemes.order import Order

@dataclass(frozen=True, slots=True)
class OrderPage:
    orders:list[Order]; total:int; page:int; pages:int; query:str; status:str

class AdminOrderService:
    TRANSITIONS={'pending':{'confirmed','processing','shipped','delivered','cancelled'},'confirmed':{'processing','shipped','delivered','cancelled'},'processing':{'shipped','delivered','cancelled'},'shipped':{'delivered','cancelled'},'delivered':set(),'cancelled':set()}
    def list_orders(self,*,query='',status='all',page=1,per_page=20):
        page=max(1,page); q=query.strip(); valid={x.value for x in OrderStatus}; status=status if status=='all' or status in valid else 'all'; filters=[]
        if q:
            p=f'%{q}%'; filters.append(or_(Order.order_number.ilike(p),Customer.name.ilike(p),Customer.email.ilike(p)))
        if status!='all': filters.append(Order.status==OrderStatus(status))
        with database_session() as db:
            base=select(Order).join(Customer).where(*filters)
            total=int(db.scalar(select(func.count()).select_from(Order).join(Customer).where(*filters)) or 0)
            rows=list(db.scalars(base.options(selectinload(Order.customer),selectinload(Order.items)).order_by(Order.created_at.desc()).offset((page-1)*per_page).limit(per_page)).all())
            for row in rows: db.expunge(row)
        return OrderPage(rows,total,page,max(1,(total+per_page-1)//per_page),q,status)
    def get_order(self,order_id:int):
        with database_session() as db:
            row=db.scalar(select(Order).where(Order.id==order_id).options(selectinload(Order.customer),selectinload(Order.items)))
            if row is None: raise ValueError('Order was not found.')
            db.expunge(row); return row
    def update_status(self,order_id:int,new_status:str):
        with database_session() as db:
            row=db.get(Order,order_id)
            if row is None: raise ValueError('Order was not found.')
            old=row.status.value if hasattr(row.status,'value') else str(row.status)
            valid = {x.value for x in OrderStatus} - {'cancelled'}
            if new_status not in valid: raise ValueError(f'Invalid status: {new_status}. Use the cancel button to cancel.')
            OrderModel.update_status(db,row.order_number,OrderStatus(new_status)); db.flush()
    def cancel(self,order_id:int):
        with database_session() as db:
            row=db.get(Order,order_id)
            if row is None: raise ValueError('Order was not found.')
            OrderModel.cancel_for_customer_id(db,row.order_number,row.customer_id); db.flush()
    def delete_order(self,order_id:int):
        with database_session() as db:
            row=db.get(Order,order_id)
            if row is None: raise ValueError('Order was not found.')
            db.delete(row); db.flush()
