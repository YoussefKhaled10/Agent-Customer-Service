from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from src.models.Database import database_session
from src.models.db_schemes.agent_db.schemes.customer import Customer
from src.models.db_schemes.agent_db.schemes.order import Order
from src.models.db_schemes.agent_db.schemes.conversation import Conversation

@dataclass(frozen=True, slots=True)
class CustomerPage:
    customers: list[Customer]; total: int; page: int; pages: int; query: str; status: str; role: str

class AdminCustomerService:
    def list_customers(self, *, query='', status='all', role='all', page=1, per_page=20):
        page=max(1,page); q=query.strip(); status=status if status in {'all','active','inactive'} else 'all'; role=role if role in {'all','customer','admin','support','pharmacist'} else 'all'
        filters=[]
        if q:
            p=f'%{q}%'; filters.append(or_(Customer.name.ilike(p),Customer.email.ilike(p),Customer.phone.ilike(p)))
        if status=='active': filters.append(Customer.is_active.is_(True))
        elif status=='inactive': filters.append(Customer.is_active.is_(False))
        if role!='all': filters.append(Customer.role==role)
        with database_session() as db:
            total=int(db.scalar(select(func.count()).select_from(Customer).where(*filters)) or 0)
            rows=list(db.scalars(select(Customer).where(*filters).order_by(Customer.created_at.desc(),Customer.id.desc()).offset((page-1)*per_page).limit(per_page)).all())
            ids=[c.id for c in rows]
            order_counts=dict(db.execute(select(Order.customer_id,func.count(Order.id)).where(Order.customer_id.in_(ids)).group_by(Order.customer_id)).all()) if ids else {}
            conv_counts=dict(db.execute(select(Conversation.customer_id,func.count(Conversation.id)).where(Conversation.customer_id.in_(ids)).group_by(Conversation.customer_id)).all()) if ids else {}
            for c in rows: db.expunge(c)
        return CustomerPage(rows,total,page,max(1,(total+per_page-1)//per_page),q,status,role),order_counts,conv_counts
    def get_customer(self, customer_id:int):
        with database_session() as db:
            customer=db.get(Customer,customer_id)
            if customer is None: raise ValueError('Customer was not found.')
            orders=list(db.scalars(select(Order).where(Order.customer_id==customer_id).order_by(Order.created_at.desc()).limit(10)).all())
            db.expunge(customer)
            for row in orders: db.expunge(row)
            return customer,orders
    def toggle(self, customer_id:int, current_admin_id:int):
        if customer_id==current_admin_id: raise ValueError('You cannot deactivate your own admin account.')
        with database_session() as db:
            customer=db.get(Customer,customer_id)
            if customer is None: raise ValueError('Customer was not found.')
            customer.is_active=not customer.is_active; state=customer.is_active; db.flush()
        return state
