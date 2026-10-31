from datetime import date
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from core.models import Company, Party, Property, Unit
from leasing.models import Lease, LeaseCharge, Receipt
from leasing.services import generate_lease_schedule, allocate_receipt

@pytest.mark.django_db
def test_monthly_schedule_generated():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    p = Property.objects.create(company=c, code="P1", name="عقار", kind="residential", ownership_type="company_owned")
    u = Unit.objects.create(company=c, property=p, code="U1", kind="apartment")
    lease = Lease.objects.create(company=c, lease_number="L1", unit=u, tenant=tenant, start_date=date(2026,1,1),
        end_date=date(2026,3,31), rent_amount=Decimal("8000.00"), due_day=1)
    assert generate_lease_schedule(lease.id) == 3

@pytest.mark.django_db
def test_schedule_does_not_create_charge_before_lease_start():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    p = Property.objects.create(company=c, code="P-START", name="عقار", kind="residential", ownership_type="company_owned")
    u = Unit.objects.create(company=c, property=p, code="U-START", kind="apartment")
    lease = Lease.objects.create(company=c, lease_number="L-START", unit=u, tenant=tenant,
        start_date=date(2026, 1, 20), end_date=date(2026, 3, 31),
        rent_amount=Decimal("8000.00"), due_day=1, frequency="monthly")

    assert generate_lease_schedule(lease.id) == 2
    charges = list(lease.charges.order_by("due_date").values_list("due_date", flat=True))
    assert charges == [date(2026, 2, 1), date(2026, 3, 1)]


@pytest.mark.django_db
def test_partial_receipt_allocation():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    p = Property.objects.create(company=c, code="P1", name="عقار", kind="residential", ownership_type="company_owned")
    u = Unit.objects.create(company=c, property=p, code="U1", kind="apartment")
    lease = Lease.objects.create(company=c, lease_number="L1", unit=u, tenant=tenant, start_date=date(2026,1,1),
        end_date=date(2026,1,31), rent_amount=Decimal("8000.00"))
    charge = LeaseCharge.objects.create(company=c, lease=lease, due_date=date(2026,1,1), amount=Decimal("8000.00"))
    receipt = Receipt.objects.create(company=c, receipt_number="R1", tenant=tenant, receipt_date=date(2026,1,5),
        amount=Decimal("5000.00"), cash_account_code="1100")
    allocate_receipt(receipt.id, [{"charge_id":charge.id,"amount":"5000.00"}])
    charge.refresh_from_db()
    assert charge.status == "partial"

@pytest.mark.django_db
def test_overallocation_rejected():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    p = Property.objects.create(company=c, code="P1", name="عقار", kind="residential", ownership_type="company_owned")
    u = Unit.objects.create(company=c, property=p, code="U1", kind="apartment")
    lease = Lease.objects.create(company=c, lease_number="L1", unit=u, tenant=tenant, start_date=date(2026,1,1),
        end_date=date(2026,1,31), rent_amount=Decimal("8000.00"))
    charge = LeaseCharge.objects.create(company=c, lease=lease, due_date=date(2026,1,1), amount=Decimal("8000.00"))
    receipt = Receipt.objects.create(company=c, receipt_number="R1", tenant=tenant, receipt_date=date(2026,1,5),
        amount=Decimal("9000.00"), cash_account_code="1100")
    with pytest.raises(ValidationError):
        allocate_receipt(receipt.id, [{"charge_id":charge.id,"amount":"9000.00"}])


@pytest.mark.django_db
def test_receipt_allocation_rejects_currency_mismatch():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    p = Property.objects.create(company=c, code="P1", name="عقار", kind="residential", ownership_type="company_owned")
    u = Unit.objects.create(company=c, property=p, code="U1", kind="apartment")
    lease = Lease.objects.create(company=c, lease_number="L-CUR", unit=u, tenant=tenant,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), rent_amount=Decimal("100.00"), currency="USD")
    charge = LeaseCharge.objects.create(company=c, lease=lease, due_date=date(2026, 1, 1),
        amount=Decimal("100.00"), currency="USD")
    receipt = Receipt.objects.create(company=c, receipt_number="R-CUR", tenant=tenant,
        receipt_date=date(2026, 1, 5), amount=Decimal("100.00"), currency="EGP", cash_account_code="1100")
    with pytest.raises(ValidationError, match="currencies must match"):
        allocate_receipt(receipt.id, [{"charge_id": charge.id, "amount": "50.00"}])
    assert not receipt.allocations.exists()

@pytest.mark.django_db
def test_receipt_allocation_rejects_charge_currency_different_from_lease():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    p = Property.objects.create(company=c, code="P-CUR2", name="عقار", kind="residential", ownership_type="company_owned")
    u = Unit.objects.create(company=c, property=p, code="U-CUR2", kind="apartment")
    lease = Lease.objects.create(company=c, lease_number="L-CUR2", unit=u, tenant=tenant,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31), rent_amount=Decimal("100.00"), currency="EGP")
    charge = LeaseCharge.objects.create(company=c, lease=lease, due_date=date(2026, 1, 1),
        amount=Decimal("100.00"), currency="USD")
    receipt = Receipt.objects.create(company=c, receipt_number="R-CUR2", tenant=tenant,
        receipt_date=date(2026, 1, 5), amount=Decimal("100.00"), currency="USD", cash_account_code="1100")
    with pytest.raises(ValidationError, match="Charge currency must match its lease currency"):
        allocate_receipt(receipt.id, [{"charge_id": charge.id, "amount": "50.00"}])
    assert not receipt.allocations.exists()

@pytest.mark.django_db
def test_empty_receipt_allocation_is_rejected():
    c = Company.objects.create(name="شركة")
    tenant = Party.objects.create(company=c, display_name="مستأجر")
    receipt = Receipt.objects.create(company=c, receipt_number="R-EMPTY", tenant=tenant,
        receipt_date=date(2026, 1, 5), amount=Decimal("100.00"), cash_account_code="1100")
    with pytest.raises(ValidationError, match="At least one allocation is required"):
        allocate_receipt(receipt.id, [])
    assert not receipt.allocations.exists()

@pytest.mark.django_db
def test_receipt_allocation_is_atomic_when_a_later_charge_is_invalid():
    company = Company.objects.create(name="شركة التخصيص")
    other_company = Company.objects.create(name="شركة أخرى")
    tenant = Party.objects.create(company=company, display_name="المستأجر")
    other_tenant = Party.objects.create(company=other_company, display_name="مستأجر آخر")
    prop = Property.objects.create(company=company, code="P-ATOMIC", name="عقار", kind="residential", ownership_type="company_owned")
    unit = Unit.objects.create(company=company, property=prop, code="U-ATOMIC", kind="apartment")
    lease = Lease.objects.create(company=company, lease_number="L-ATOMIC", unit=unit, tenant=tenant,
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), rent_amount=Decimal("100.00"))
    valid_charge = LeaseCharge.objects.create(company=company, lease=lease, due_date=date(2026, 1, 1), amount=Decimal("100.00"))
    other_property = Property.objects.create(company=other_company, code="P-OTHER", name="عقار آخر", kind="residential", ownership_type="company_owned")
    other_unit = Unit.objects.create(company=other_company, property=other_property, code="U-OTHER", kind="apartment")
    other_lease = Lease.objects.create(company=other_company, lease_number="L-OTHER", unit=other_unit, tenant=other_tenant,
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), rent_amount=Decimal("100.00"))
    foreign_charge = LeaseCharge.objects.create(company=other_company, lease=other_lease, due_date=date(2026, 1, 1), amount=Decimal("100.00"))
    receipt = Receipt.objects.create(company=company, receipt_number="R-ATOMIC", tenant=tenant,
        receipt_date=date(2026, 1, 5), amount=Decimal("100.00"), cash_account_code="1100")

    with pytest.raises(ValidationError, match="does not belong"):
        allocate_receipt(receipt.pk, [
            {"charge_id": valid_charge.pk, "amount": "50.00"},
            {"charge_id": foreign_charge.pk, "amount": "50.00"},
        ])

    assert not receipt.allocations.exists()
    valid_charge.refresh_from_db()
    assert valid_charge.status == "scheduled"


@pytest.mark.django_db
def test_posted_receipt_cannot_be_allocated_again():
    company = Company.objects.create(name="شركة سند مرحل")
    tenant = Party.objects.create(company=company, display_name="مستأجر")
    prop = Property.objects.create(company=company, code="P-POSTED", name="عقار", kind="residential", ownership_type="company_owned")
    unit = Unit.objects.create(company=company, property=prop, code="U-POSTED", kind="apartment")
    lease = Lease.objects.create(company=company, lease_number="L-POSTED", unit=unit, tenant=tenant,
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), rent_amount=Decimal("100.00"))
    charge = LeaseCharge.objects.create(company=company, lease=lease, due_date=date(2026, 1, 1), amount=Decimal("100.00"))
    receipt = Receipt.objects.create(company=company, receipt_number="R-POSTED", tenant=tenant,
        receipt_date=date(2026, 1, 5), amount=Decimal("100.00"), cash_account_code="1100", is_posted=True)

    with pytest.raises(ValidationError, match="Posted receipts cannot be changed"):
        allocate_receipt(receipt.pk, [{"charge_id": charge.pk, "amount": "100.00"}])

    assert not receipt.allocations.exists()
