from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.db_schemes.agent_db.enums import InquiryPriority, InquiryStatus
from src.models.db_schemes.agent_db.schemes.customer_inquiry import CustomerInquiry

class InquiryModel:
    @classmethod
    def create(cls, session: Session, *, customer_name: str, email: str, subject: str,
               content: str, phone: str | None = None, customer_id: int | None = None,
               priority: InquiryPriority = InquiryPriority.NORMAL) -> CustomerInquiry:
        if not all([customer_name.strip(), email.strip(), subject.strip(), content.strip()]):
            raise ValueError("Name, email, subject, and content are required.")
        inquiry = CustomerInquiry(customer_id=customer_id, customer_name=customer_name.strip(),
            email=email.strip().lower(), phone=phone.strip() if phone else None,
            subject=subject.strip(), content=content.strip(), priority=priority,
            status=InquiryStatus.OPEN)
        session.add(inquiry); session.flush(); return inquiry

    @classmethod
    def list(cls, session: Session, status: InquiryStatus | None = None) -> list[CustomerInquiry]:
        statement = select(CustomerInquiry)
        if status: statement = statement.where(CustomerInquiry.status == status)
        return list(session.scalars(statement.order_by(CustomerInquiry.created_at.desc())).all())

    @classmethod
    def update_status(cls, session: Session, inquiry_id: int, status: InquiryStatus) -> CustomerInquiry:
        inquiry = session.get(CustomerInquiry, inquiry_id)
        if inquiry is None: raise ValueError("Inquiry was not found.")
        inquiry.status = status; session.flush(); return inquiry
