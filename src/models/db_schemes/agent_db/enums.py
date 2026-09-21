from enum import StrEnum

class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class InquiryStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class InquiryPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class PharmacistRequestStatus(StrEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    CONTACTED = "contacted"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ContactMethod(StrEnum):
    PHONE = "phone"
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class KnowledgeCategory(StrEnum):
    POLICY = "policy"
    FAQ = "faq"
    PRODUCT_GUIDE = "product_guide"
    SHIPPING = "shipping"
    RETURNS = "returns"
    WARRANTY = "warranty"
    GENERAL = "general"


class IndexStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolExecutionStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class CustomerRole(StrEnum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    SUPPORT = "support"
    PHARMACIST = "pharmacist"

