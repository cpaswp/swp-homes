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
