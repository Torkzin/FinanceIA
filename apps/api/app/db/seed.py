import asyncio
import random
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import Company, CostCenter, Invoice, Supplier, User
from app.db.models.enums import InvoiceSource, InvoiceStatus, SupplierStatus, UserRole
from app.db.session import async_session_factory

COMPANY_SLUG = "aurora-tech-demo"

SUPPLIERS = [
    ("Amazon Web Services Brasil", "83.274.448/0001-08", "Cloud"),
    ("Microsoft Tecnologia", "62.401.384/0001-07", "Software"),
    ("Google Cloud Brasil", "19.685.423/0001-10", "Cloud"),
    ("Salesforce Sistemas", "01.983.304/0001-45", "Software"),
    ("Atlassian Brasil", "36.212.845/0001-09", "Software"),
    ("Alfa Telecom", "05.436.771/0001-26", "Telecom"),
    ("Norte Energia", "48.625.107/0001-63", "Utilities"),
    ("Água Clara Serviços", "70.914.238/0001-51", "Utilities"),
    ("Horizonte Contabilidade", "26.803.147/0001-80", "Professional Services"),
    ("Ponto Legal Advocacia", "14.597.362/0001-04", "Professional Services"),
    ("Vértice Marketing", "93.175.420/0001-38", "Marketing"),
    ("Estúdio Criativo Sul", "57.302.816/0001-95", "Marketing"),
    ("Mobi Transportes", "31.749.205/0001-17", "Logistics"),
    ("Rota Express", "68.015.934/0001-42", "Logistics"),
    ("Office Mais", "22.638.590/0001-73", "Office"),
    ("Café Central", "45.190.267/0001-31", "Office"),
    ("Talento RH", "79.426.813/0001-60", "Human Resources"),
    ("Academia Corporativa", "17.054.689/0001-22", "Training"),
    ("Seguro Forte", "52.861.309/0001-54", "Insurance"),
    ("Viagem Fácil", "08.319.746/0001-86", "Travel"),
]

COST_CENTERS = [
    ("TEC", "Technology", "Engineering, cloud infrastructure, and software"),
    ("MKT", "Marketing", "Demand generation, brand, and communications"),
    ("OPS", "Operations", "Facilities, logistics, and general operations"),
    ("FIN", "Finance", "Finance, legal, accounting, and insurance"),
    ("PEO", "People", "People operations, benefits, and training"),
]


def stable_id(resource: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"https://finance-ai.local/demo/{resource}")


def shift_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def build_invoices(
    company_id: UUID,
    suppliers: list[Supplier],
    cost_centers: list[CostCenter],
    today: date,
) -> list[Invoice]:
    rng = random.Random(20260930)
    first_current_month = today.replace(day=1)
    period_start = shift_months(first_current_month, -5)
    period_days = max((today - period_start).days, 1)
    invoices: list[Invoice] = []

    for index in range(100):
        supplier = suppliers[index % len(suppliers)]
        cost_center = cost_centers[index % len(cost_centers)]
        issue_date = period_start + timedelta(days=(index * period_days) // 100)
        due_date = issue_date + timedelta(days=rng.choice([10, 15, 20, 30]))
        base_amount = Decimal(450 + (index % 20) * 185)
        variation = Decimal(str(rng.uniform(0.88, 1.18)))
        amount = (base_amount * variation).quantize(Decimal("0.01"))

        if index in {37, 82}:
            amount = (amount * Decimal("3.25")).quantize(Decimal("0.01"))

        if due_date < today:
            status = InvoiceStatus.OVERDUE if index % 13 == 0 else InvoiceStatus.PAID
        else:
            status = InvoiceStatus.APPROVED if index % 3 == 0 else InvoiceStatus.PENDING

        category = SUPPLIERS[index % len(SUPPLIERS)][2]
        source = [InvoiceSource.MANUAL, InvoiceSource.DOCUMENT, InvoiceSource.ERP][index % 3]
        invoices.append(
            Invoice(
                id=stable_id(f"invoice/{index + 1}"),
                company_id=company_id,
                supplier_id=supplier.id,
                cost_center_id=cost_center.id,
                invoice_number=f"DEMO-{issue_date:%Y%m}-{index + 1:04d}",
                description=f"Demo expense for {supplier.name}",
                category=category,
                issue_date=issue_date,
                due_date=due_date,
                amount=amount,
                currency="BRL",
                status=status,
                source=source,
                ai_confidence=Decimal("0.9300") if source == InvoiceSource.DOCUMENT else None,
            )
        )

    return invoices


async def seed_database() -> None:
    async with async_session_factory() as session:
        existing_company = await session.scalar(select(Company).where(Company.slug == COMPANY_SLUG))
        if existing_company:
            existing_users = list(
                await session.scalars(select(User).where(User.company_id == existing_company.id))
            )
            password_was_upgraded = False
            for user in existing_users:
                if user.password_hash.startswith("!"):
                    user.password_hash = hash_password(
                        settings.demo_user_password.get_secret_value()
                    )
                    password_was_upgraded = True
            if password_was_upgraded:
                await session.commit()
            invoice_count = await session.scalar(
                select(func.count(Invoice.id)).where(Invoice.company_id == existing_company.id)
            )
            print(
                f"Demo data already exists for {existing_company.name} "
                f"({invoice_count or 0} invoices)."
            )
            return

        company = Company(
            id=stable_id("company/aurora-tech"),
            name="Aurora Tecnologia Ltda.",
            slug=COMPANY_SLUG,
        )
        session.add(company)

        users = [
            User(
                id=stable_id(f"user/{role}"),
                company_id=company.id,
                full_name=name,
                email=email,
                password_hash=hash_password(settings.demo_user_password.get_secret_value()),
                role=role,
            )
            for role, name, email in [
                (UserRole.ADMIN, "Amanda Rocha", "admin@aurora.demo"),
                (UserRole.FINANCE, "Felipe Lima", "finance@aurora.demo"),
                (UserRole.MANAGER, "Marina Costa", "manager@aurora.demo"),
            ]
        ]
        suppliers = [
            Supplier(
                id=stable_id(f"supplier/{index + 1}"),
                company_id=company.id,
                name=name,
                document_number=document_number,
                email=f"financeiro{index + 1}@supplier.demo",
                category=category,
                status=SupplierStatus.ACTIVE,
            )
            for index, (name, document_number, category) in enumerate(SUPPLIERS)
        ]
        cost_centers = [
            CostCenter(
                id=stable_id(f"cost-center/{code.lower()}"),
                company_id=company.id,
                name=name,
                code=code,
                description=description,
            )
            for code, name, description in COST_CENTERS
        ]
        invoices = build_invoices(company.id, suppliers, cost_centers, datetime.now(UTC).date())

        session.add_all([*users, *suppliers, *cost_centers, *invoices])
        await session.commit()
        print(
            "Seed completed: 1 company, 3 users, "
            f"{len(suppliers)} suppliers, {len(cost_centers)} cost centers, "
            f"and {len(invoices)} invoices."
        )


if __name__ == "__main__":
    asyncio.run(seed_database())
