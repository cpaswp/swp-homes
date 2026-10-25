from decimal import Decimal
from django.db import models
from core.models import TimeStampedModel, Company

class FiscalPeriod(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="fiscal_periods")
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company","name"], name="uq_period_name_company"),
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="ck_period_dates_valid")]

class Account(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="accounts")
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=180)
    account_type = models.CharField(max_length=20, choices=[("asset","Asset"),("liability","Liability"),("equity","Equity"),("revenue","Revenue"),("expense","Expense")])
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_control_account = models.BooleanField(default=False)
    allow_manual_posting = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["company","code"], name="uq_account_code_company")]
        indexes = [models.Index(fields=["company","account_type"], name="acct_account_co_type_idx")]

class JournalEntry(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="journal_entries")
    entry_number = models.CharField(max_length=40)
    entry_date = models.DateField()
    description = models.CharField(max_length=250)
    source_type = models.CharField(max_length=60, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    idempotency_key = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=[("draft","Draft"),("posted","Posted"),("reversed","Reversed")], default="draft")
    posted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company","entry_number"], name="uq_journal_number_company"),
            models.UniqueConstraint(fields=["company","idempotency_key"], condition=~models.Q(idempotency_key=""), name="uq_journal_idempotency_company")]
        indexes = [models.Index(fields=["company","entry_date","status"], name="acct_journal_co_date_status")]

class JournalLine(TimeStampedModel):
    entry = models.ForeignKey(JournalEntry, on_delete=models.PROTECT, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    description = models.CharField(max_length=250, blank=True)
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="EGP")
    class Meta:
        constraints = [
            models.CheckConstraint(condition=~(models.Q(debit__gt=0) & models.Q(credit__gt=0)), name="ck_journal_line_not_both_sides"),
            models.CheckConstraint(condition=models.Q(debit__gte=0) & models.Q(credit__gte=0), name="ck_journal_line_nonnegative")]
