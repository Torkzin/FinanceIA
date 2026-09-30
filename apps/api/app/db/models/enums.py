from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    FINANCE = "finance"
    MANAGER = "manager"


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class InvoiceStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    OVERDUE = "overdue"
    REJECTED = "rejected"


class InvoiceSource(StrEnum):
    MANUAL = "manual"
    DOCUMENT = "document"
    ERP = "erp"
