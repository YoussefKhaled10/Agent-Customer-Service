from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.models.CustomerModel import CustomerModel
from src.models.db_schemes.agent_db.enums import OrderStatus
from src.models.db_schemes.agent_db.schemes.order import Order, OrderItem
from src.models.db_schemes.agent_db.schemes.product import Product




class OrderModel:
    @classmethod
    def get_by_number(cls, session: Session, order_number: str) -> Order | None:
        statement = select(Order).options(selectinload(Order.items)).where(Order.order_number == order_number.strip().upper())
        return session.scalar(statement)

    @classmethod
    def get_status(cls, session: Session, order_number: str, customer_email: str) -> Order:
        order = cls.get_by_number(session, order_number)
        if order is None or order.customer.email.lower() != customer_email.strip().lower():
            raise ValueError("Order was not found for this customer.")
        return order

    @classmethod
    def create(cls, session: Session, *, customer_name: str, customer_email: str,
               phone: str | None, shipping_address: str, items: list[dict],
               idempotency_key: str, customer_notes: str | None = None) -> Order:
        if not shipping_address.strip():
            raise ValueError("Shipping address is required.")
        if not items:
            raise ValueError("At least one order item is required.")
        existing = session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if existing:
            return existing
        customer, _ = CustomerModel.get_or_create(session, customer_name, customer_email, phone, shipping_address)
        order = Order(order_number=f"PC-{uuid4().hex[:10].upper()}", customer_id=customer.id,
                      total_amount=Decimal("0.00"), currency="EGP", status=OrderStatus.PENDING,
                      shipping_address=shipping_address.strip(), customer_notes=customer_notes,
                      idempotency_key=idempotency_key)
        session.add(order)
        session.flush()
        total = Decimal("0.00")
        for requested in items:
            product_id, quantity = int(requested["product_id"]), int(requested["quantity"])
            if quantity < 1:
                raise ValueError("Quantity must be positive.")
            product = session.execute(select(Product).where(Product.id == product_id).with_for_update()).scalar_one_or_none()
            if product is None or not product.is_active:
                raise ValueError(f"Product {product_id} is unavailable.")
            if product.available_stock < quantity:
                raise ValueError(f"Insufficient stock for {product.name}.")
            subtotal = product.price * quantity
            session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=quantity,
                                  unit_price=product.price, subtotal=subtotal,
                                  product_name_snapshot=product.name, product_sku_snapshot=product.sku))
            product.stock -= quantity
            total += subtotal
        order.total_amount = total
        session.flush()
        return order

    @classmethod
    def update_status(cls, session: Session, order_number: str, status: OrderStatus) -> Order:
        order = cls.get_by_number(session, order_number)
        if order is None:
            raise ValueError("Order was not found.")
        order.status = status
        session.flush()
        return order

    @classmethod
    def get_for_customer_id(
        cls,
        session: Session,
        order_number: str,
        customer_id: int,
    ) -> Order | None:
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.order_number == order_number.strip().upper(),
                Order.customer_id == customer_id,
            )
        )
        return session.scalar(statement)

    @classmethod
    def list_by_customer_id(
        cls,
        session: Session,
        customer_id: int,
        *,
        status: OrderStatus | None = None,
        limit: int = 20,
    ) -> list[Order]:
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == customer_id)
        )
        if status is not None:
            statement = statement.where(Order.status == status)
        statement = statement.order_by(Order.created_at.desc()).limit(limit)
        return list(session.scalars(statement).all())
    
    @classmethod
    def create_for_customer_id(
        cls,
        session: Session,
        *,
        customer_id: int,
        items: list[dict],
        idempotency_key: str,
        shipping_address: str | None = None,
        customer_notes: str | None = None,
    ) -> Order:
        customer = CustomerModel.get_by_id(session, customer_id)
        if customer is None or not customer.is_active:
            raise ValueError("Authenticated customer was not found or is inactive.")

        selected_address = (
            shipping_address.strip()
            if shipping_address and shipping_address.strip()
            else (customer.default_shipping_address or "").strip()
        )
        if not selected_address:
            raise ValueError(
                "Shipping address is required because the customer has no default address."
            )

        return cls.create(
            session,
            customer_name=customer.name,
            customer_email=customer.email,
            phone=customer.phone,
            shipping_address=selected_address,
            items=items,
            idempotency_key=idempotency_key.strip(),
            customer_notes=customer_notes,
        )

    @classmethod
    def cancel_for_customer_id(
        cls,
        session: Session,
        *,
        order_number: str,
        customer_id: int,
    ) -> tuple[Order | None, bool]:
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(
                Order.order_number == order_number.strip().upper(),
                Order.customer_id == customer_id,
            )
            .with_for_update()
        )
        order = session.scalar(statement)
        if order is None:
            return None, False

        if order.status == OrderStatus.CANCELLED:
            return order, True

        cancellable = {
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
        }
        if order.status not in cancellable:
            raise ValueError(
                f"Order in status '{order.status.value}' cannot be cancelled."
            )

        product_ids = [item.product_id for item in order.items]
        products = {
            product.id: product
            for product in session.scalars(
                select(Product)
                .where(Product.id.in_(product_ids))
                .with_for_update()
            ).all()
        }

        for item in order.items:
            product = products.get(item.product_id)
            if product is None:
                raise ValueError(
                    f"Product {item.product_id} required for stock restoration was not found."
                )
            product.stock += item.quantity

        order.status = OrderStatus.CANCELLED
        session.flush()
        return order, False

