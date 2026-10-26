from calendar import monthrange
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from .models import Lease, LeaseCharge, Receipt, ReceiptAllocation

STEPS = {"monthly":1,"quarterly":3,"semiannual":6,"annual":12}
def add_months(d, months, day):
    idx = d.month - 1 + months
    year, month = d.year + idx // 12, idx % 12 + 1
    return date(year, month, min(day, monthrange(year, month)[1]))

@transaction.atomic
def generate_lease_schedule(lease_id):
    lease = Lease.objects.select_for_update().select_related("company","unit","tenant").get(pk=lease_id)
    if lease.status not in ("draft","active"):
        raise ValidationError("Only draft or active leases can generate schedules.")
    if lease.unit.company_id != lease.company_id or lease.tenant.company_id != lease.company_id:
        raise ValidationError("Lease, unit, tenant and company must match.")
    if lease.end_date < lease.start_date:
        raise ValidationError("Lease end date cannot precede start date.")
    if lease.charges.filter(schedule_version=lease.schedule_version).exists():
        raise ValidationError("Schedule already exists for this version.")
    cursor = date(lease.start_date.year, lease.start_date.month, min(lease.due_day, monthrange(lease.start_date.year, lease.start_date.month)[1]))
    count = 0
    while cursor <= lease.end_date:
        LeaseCharge.objects.create(company=lease.company, lease=lease, due_date=cursor, amount=lease.rent_amount,
            currency=lease.currency, schedule_version=lease.schedule_version, period_label=cursor.strftime("%Y-%m"))
        count += 1
        cursor = add_months(cursor, STEPS[lease.frequency], lease.due_day)
    return count

@transaction.atomic
def allocate_receipt(receipt_id, allocations):
    receipt = Receipt.objects.select_for_update().select_related("company","tenant").get(pk=receipt_id)
    if receipt.is_posted:
        raise ValidationError("Posted receipts cannot be changed.")
    if receipt.tenant.company_id != receipt.company_id:
        raise ValidationError("Receipt tenant belongs to another company.")
    if receipt.allocations.exists():
        raise ValidationError("Receipt already has allocations.")
    total, prepared, seen = Decimal("0.00"), [], set()
    for item in allocations:
        charge_id = int(item["charge_id"])
        amount = Decimal(str(item["amount"])).quantize(Decimal("0.01"))
        if amount <= 0: raise ValidationError("Allocation must be positive.")
        if charge_id in seen: raise ValidationError("Duplicate charge in allocation list.")
        seen.add(charge_id)
        charge = LeaseCharge.objects.select_for_update().select_related("lease").get(pk=charge_id)
        if charge.company_id != receipt.company_id or charge.lease.tenant_id != receipt.tenant_id:
            raise ValidationError("Charge does not belong to this receipt tenant/company.")
        if charge.status == "void": raise ValidationError("Cannot allocate to a void charge.")
        allocated = charge.allocations.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        if allocated + amount > charge.amount: raise ValidationError("Allocation exceeds outstanding charge balance.")
        total += amount
        prepared.append((charge, amount))
    if total > receipt.amount: raise ValidationError("Allocations cannot exceed receipt amount.")
    for charge, amount in prepared:
        ReceiptAllocation.objects.create(receipt=receipt, charge=charge, amount=amount)
        allocated = charge.allocations.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        charge.status = "paid" if allocated >= charge.amount else "partial"
        charge.save(update_fields=["status","updated_at"])
    return receipt


@transaction.atomic
def post_receipt(receipt_id):
    from accounting.models import Account, JournalEntry, JournalLine
    from accounting.services import post_journal_entry
    from django.core.exceptions import ValidationError
    receipt=Receipt.objects.select_for_update().select_related("company","tenant").get(pk=receipt_id)
    if receipt.is_posted:
        existing=JournalEntry.objects.filter(company=receipt.company,source_type="receipt",source_id=str(receipt.pk),status="posted").first()
        if existing: return existing
        raise ValidationError("Receipt is marked posted but its journal is missing; administrator review is required.")
    if receipt.tenant.company_id!=receipt.company_id: raise ValidationError("Receipt tenant belongs to another company.")
    if receipt.amount<=0: raise ValidationError("Receipt amount must be positive.")
    if receipt.currency.upper()!=receipt.company.base_currency.upper(): raise ValidationError("Foreign-currency receipt posting is not enabled.")
    cash=Account.objects.filter(company=receipt.company,code=receipt.cash_account_code,is_active=True).first()
    ar=Account.objects.filter(company=receipt.company,code="1200",is_active=True).first()
    if not cash or not ar: raise ValidationError("Cash/bank or receivables account missing; seed chart of accounts first.")
    key=f"receipt:{receipt.pk}"
    entry,created=JournalEntry.objects.get_or_create(company=receipt.company,idempotency_key=key,defaults={"entry_number":f"RCPT-{receipt.receipt_number}","entry_date":receipt.receipt_date,"description":f"Receipt {receipt.receipt_number} / {receipt.tenant.display_name}","source_type":"receipt","source_id":str(receipt.pk),"status":"draft"})
    if created:
        JournalLine.objects.create(entry=entry,account=cash,description="Cash/bank received",debit=receipt.amount,credit=Decimal("0.00"),currency=receipt.currency)
        JournalLine.objects.create(entry=entry,account=ar,description="Tenant receivable cleared",debit=Decimal("0.00"),credit=receipt.amount,currency=receipt.currency)
    elif entry.status!="posted": raise ValidationError("A draft journal already exists for this receipt; administrator review is required.")
    entry = post_journal_entry(entry.pk)
    receipt.is_posted=True; receipt.save(update_fields=["is_posted","updated_at"])
    return entry
