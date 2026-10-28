from datetime import date
from decimal import Decimal
import pytest
from core.models import Company
from accounting.models import Account, FiscalPeriod, JournalEntry, JournalLine
from accounting.services import post_journal_entry, PostingError

@pytest.mark.django_db
def test_balanced_journal_posts():
    company = Company.objects.create(name="شركة")
    FiscalPeriod.objects.create(company=company, name="2026", start_date=date(2026,1,1), end_date=date(2026,12,31))
    cash = Account.objects.create(company=company, code="1100", name="الصندوق", account_type="asset")
    revenue = Account.objects.create(company=company, code="4100", name="الإيراد", account_type="revenue")
    entry = JournalEntry.objects.create(company=company, entry_number="JV-1", entry_date=date(2026,10,1), description="اختبار")
    JournalLine.objects.create(entry=entry, account=cash, debit=Decimal("100.00"))
    JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal("100.00"))
    assert post_journal_entry(entry.id).status == "posted"

@pytest.mark.django_db
def test_unbalanced_journal_rejected():
    company = Company.objects.create(name="شركة")
    FiscalPeriod.objects.create(company=company, name="2026", start_date=date(2026,1,1), end_date=date(2026,12,31))
    cash = Account.objects.create(company=company, code="1100", name="الصندوق", account_type="asset")
    revenue = Account.objects.create(company=company, code="4100", name="الإيراد", account_type="revenue")
    entry = JournalEntry.objects.create(company=company, entry_number="JV-2", entry_date=date(2026,10,1), description="اختبار")
    JournalLine.objects.create(entry=entry, account=cash, debit=Decimal("100.00"))
    JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal("99.00"))
    with pytest.raises(PostingError): post_journal_entry(entry.id)
    entry.refresh_from_db()
    assert entry.status == "draft"

@pytest.mark.django_db
def test_posting_rejects_account_from_another_company():
    company = Company.objects.create(name="الشركة الأولى")
    other_company = Company.objects.create(name="الشركة الثانية")
    FiscalPeriod.objects.create(company=company, name="2026", start_date=date(2026,1,1), end_date=date(2026,12,31))
    cash = Account.objects.create(company=company, code="1100", name="الصندوق", account_type="asset")
    foreign_revenue = Account.objects.create(company=other_company, code="4100", name="إيراد أجنبي", account_type="revenue")
    entry = JournalEntry.objects.create(company=company, entry_number="JV-CROSS-CO", entry_date=date(2026,10,1), description="اختبار عزل الشركات")
    JournalLine.objects.create(entry=entry, account=cash, debit=Decimal("100.00"))
    JournalLine.objects.create(entry=entry, account=foreign_revenue, credit=Decimal("100.00"))

    with pytest.raises(PostingError, match="another company"):
        post_journal_entry(entry.id)

    entry.refresh_from_db()
    assert entry.status == "draft"


@pytest.mark.django_db
def test_posting_rejects_manual_posting_to_control_account():
    company = Company.objects.create(name="شركة")
    FiscalPeriod.objects.create(company=company, name="2026", start_date=date(2026,1,1), end_date=date(2026,12,31))
    cash = Account.objects.create(company=company, code="1100", name="الصندوق", account_type="asset", allow_manual_posting=False)
    revenue = Account.objects.create(company=company, code="4100", name="الإيراد", account_type="revenue")
    entry = JournalEntry.objects.create(company=company, entry_number="JV-3", entry_date=date(2026,10,1), description="اختبار")
    JournalLine.objects.create(entry=entry, account=cash, debit=Decimal("100.00"))
    JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal("100.00"))
    with pytest.raises(PostingError, match="disallows manual"):
        post_journal_entry(entry.id)

@pytest.mark.django_db
def test_posting_rejects_foreign_currency_without_fx_support():
    company = Company.objects.create(name="شركة", base_currency="EGP")
    FiscalPeriod.objects.create(company=company, name="2026", start_date=date(2026,1,1), end_date=date(2026,12,31))
    cash = Account.objects.create(company=company, code="1100", name="الصندوق", account_type="asset")
    revenue = Account.objects.create(company=company, code="4100", name="الإيراد", account_type="revenue")
    entry = JournalEntry.objects.create(company=company, entry_number="JV-4", entry_date=date(2026,10,1), description="اختبار")
    JournalLine.objects.create(entry=entry, account=cash, debit=Decimal("100.00"), currency="USD")
    JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal("100.00"), currency="USD")
    with pytest.raises(PostingError, match="base currency"):
        post_journal_entry(entry.id)

@pytest.mark.django_db
def test_posting_rejects_closed_fiscal_period():
    company = Company.objects.create(name="شركة فترة مغلقة")
    FiscalPeriod.objects.create(company=company, name="2026", start_date=date(2026,1,1), end_date=date(2026,12,31), is_closed=True)
    cash = Account.objects.create(company=company, code="1100", name="الصندوق", account_type="asset")
    revenue = Account.objects.create(company=company, code="4100", name="الإيراد", account_type="revenue")
    entry = JournalEntry.objects.create(company=company, entry_number="JV-CLOSED", entry_date=date(2026,10,1), description="اختبار فترة مقفلة")
    JournalLine.objects.create(entry=entry, account=cash, debit=Decimal("100.00"))
    JournalLine.objects.create(entry=entry, account=revenue, credit=Decimal("100.00"))

    with pytest.raises(PostingError, match="closed"):
        post_journal_entry(entry.id)

    entry.refresh_from_db()
    assert entry.status == "draft"


