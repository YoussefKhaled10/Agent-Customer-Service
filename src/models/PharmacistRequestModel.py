from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.db_schemes.agent_db.enums import ContactMethod, PharmacistRequestStatus
from src.models.db_schemes.agent_db.schemes.pharmacist_request import PharmacistRequest

class PharmacistRequestModel:
    @classmethod
    def create(cls, session: Session, *, customer_name: str, phone: str,
               question_summary: str, email: str | None = None,
               customer_id: int | None = None, related_product_id: int | None = None,
               preferred_contact_method: ContactMethod = ContactMethod.PHONE) -> PharmacistRequest:
        if not customer_name.strip() or not phone.strip() or not question_summary.strip():
            raise ValueError("Name, phone, and question summary are required.")
        request = PharmacistRequest(customer_id=customer_id, related_product_id=related_product_id,
            customer_name=customer_name.strip(), email=email.strip().lower() if email else None,
            phone=phone.strip(), preferred_contact_method=preferred_contact_method,
            question_summary=question_summary.strip(), status=PharmacistRequestStatus.PENDING)
        session.add(request)
        session.flush()
        return request

    @classmethod
    def list(cls, session: Session, status: PharmacistRequestStatus | None = None) -> list[PharmacistRequest]:
        statement = select(PharmacistRequest)
        if status:
            statement = statement.where(PharmacistRequest.status == status)
        return list(session.scalars(statement.order_by(PharmacistRequest.created_at.desc())).all())

    @classmethod
    def update_status(cls, session: Session, request_id: int,
                      status: PharmacistRequestStatus, assigned_to: str | None = None) -> PharmacistRequest:
        request = session.get(PharmacistRequest, request_id)
        if request is None:
            raise ValueError("Pharmacist request was not found.")
        request.status = status
        if assigned_to is not None:
            request.assigned_to = assigned_to.strip() or None
        session.flush()
        return request
