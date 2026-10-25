import uuid
from decimal import Decimal
from django.db import models
from core.models import TimeStampedModel, Company, Party, Unit

class Lease(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="leases")
    lease_number = models.CharField(max_length=50)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="leases")
    tenant = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="leases_as_tenant")
    start_date = models.DateField()
    end_date = models.DateField()
    rent_amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default="EGP")
    frequency = models.CharField(max_length=20, choices=[("monthly","Monthly"),("quarterly","Quarterly"),("semiannual","Semiannual"),("annual","Annual")], default="monthly")
    due_day = models.PositiveSmallIntegerField(default=1)
    management_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    security_deposit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=12, choices=[("draft","Draft"),("active","Active"),("expired","Expired"),("terminated","Terminated")], default="draft")
    schedule_version = models.PositiveIntegerField(default=1)
    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.unit_id and self.company_id and self.unit.company_id != self.company_id:
            errors["unit"] = "الوحدة يجب أن تتبع نفس الشركة."
        if self.tenant_id and self.company_id and self.tenant.company_id != self.company_id:
            errors["tenant"] = "المستأجر يجب أن يتبع نفس الشركة."
        if self.rent_amount is not None and self.rent_amount <= 0:
            errors["rent_amount"] = "قيمة الإيجار يجب أن تكون أكبر من صفر."
        if self.security_deposit is not None and self.security_deposit < 0:
            errors["security_deposit"] = "التأمين لا يمكن أن يكون سالبًا."
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company","lease_number"], name="uq_lease_number_company"),
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="ck_lease_dates_valid"),
            models.CheckConstraint(condition=models.Q(due_day__gte=1) & models.Q(due_day__lte=28), name="ck_lease_due_day_1_28"),
            models.CheckConstraint(condition=models.Q(management_fee_percent__gte=0) & models.Q(management_fee_percent__lte=100), name="ck_lease_fee_percent_range")]

class LeaseCharge(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="lease_charges")
    lease = models.ForeignKey(Lease, on_delete=models.PROTECT, related_name="charges")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default="EGP")
    status = models.CharField(max_length=12, choices=[("scheduled","Scheduled"),("partial","Partially paid"),("paid","Paid"),("void","Void")], default="scheduled")
    schedule_version = models.PositiveIntegerField(default=1)
    period_label = models.CharField(max_length=80, blank=True)
    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.lease_id and self.company_id and self.lease.company_id != self.company_id:
            errors["lease"] = "الاستحقاق والعقد يجب أن يتبعا نفس الشركة."
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "قيمة الاستحقاق يجب أن تكون أكبر من صفر."
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["lease","due_date","schedule_version"], name="uq_charge_lease_due_version"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_lease_charge_amount_positive")
        ]
        indexes = [models.Index(fields=["company","due_date","status"], name="lease_charge_co_due_status")]

class Receipt(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="receipts")
    receipt_number = models.CharField(max_length=50)
    tenant = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="receipts")
    receipt_date = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default="EGP")
    payment_method = models.CharField(max_length=20, choices=[("cash","Cash"),("bank","Bank transfer"),("cheque","Cheque"),("card","Card")], default="cash")
    cash_account_code = models.CharField(max_length=30)
    idempotency_key = models.UUIDField(default=uuid.uuid4, editable=False)
    is_posted = models.BooleanField(default=False)
    external_reference = models.CharField(max_length=100, blank=True)
    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.tenant_id and self.company_id and self.tenant.company_id != self.company_id:
            errors["tenant"] = "المستأجر يجب أن يتبع نفس الشركة."
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "قيمة سند القبض يجب أن تكون أكبر من صفر."
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company","receipt_number"], name="uq_receipt_number_company"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_receipt_amount_positive"),
            models.UniqueConstraint(fields=["company","idempotency_key"], name="uq_receipt_idempotency_company")]

class ReceiptAllocation(TimeStampedModel):
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name="allocations")
    charge = models.ForeignKey(LeaseCharge, on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.receipt_id and self.charge_id:
            if self.receipt.company_id != self.charge.company_id:
                errors["charge"] = "سند القبض والاستحقاق يجب أن يتبعا نفس الشركة."
            elif self.receipt.tenant_id != self.charge.lease.tenant_id:
                errors["charge"] = "الاستحقاق لا يخص مستأجر سند القبض."
            if self.receipt.currency.upper() != self.charge.currency.upper():
                errors["amount"] = "عملة سند القبض يجب أن تطابق عملة الاستحقاق."
        if self.amount is not None and self.amount <= 0:
            errors["amount"] = "قيمة التخصيص يجب أن تكون أكبر من صفر."
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["receipt","charge"], name="uq_receipt_charge_allocation"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_receipt_allocation_positive")
        ]
