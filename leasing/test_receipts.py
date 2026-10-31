from datetime import date
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from core.models import Company, Party
from accounting.models import Account, FiscalPeriod, JournalEntry
from leasing.models import Receipt
from leasing.services import post_receipt

@pytest.mark.django_db
def test_receipt_posting_creates_balanced_journal():
    c=Company.objects.create(name='Receipts Co',base_currency='EGP'); t=Party.objects.create(company=c,display_name='Tenant')
    Account.objects.create(company=c,code='1100',name='Cash',account_type='asset',allow_manual_posting=True)
    Account.objects.create(company=c,code='1200',name='Receivables',account_type='asset',is_control_account=True,allow_manual_posting=False)
    FiscalPeriod.objects.create(company=c,name='FY',start_date=date(2026,1,1),end_date=date(2026,12,31))
    r=Receipt.objects.create(company=c,receipt_number='R-001',tenant=t,receipt_date=date(2026,5,1),amount=Decimal('100.00'),currency='EGP',payment_method='cash',cash_account_code='1100')
    e=post_receipt(r.pk); lines=list(e.lines.all())
    assert e.status=='posted' and len(lines)==2
    assert sum(x.debit for x in lines)==sum(x.credit for x in lines)==Decimal('100.00')
    r.refresh_from_db(); assert r.is_posted

@pytest.mark.django_db
def test_receipt_posting_fails_without_fiscal_period():
    c=Company.objects.create(name='No Period',base_currency='EGP'); t=Party.objects.create(company=c,display_name='Tenant')
    Account.objects.create(company=c,code='1100',name='Cash',account_type='asset',allow_manual_posting=True)
    Account.objects.create(company=c,code='1200',name='Receivables',account_type='asset',is_control_account=True,allow_manual_posting=False)
    r=Receipt.objects.create(company=c,receipt_number='R-002',tenant=t,receipt_date=date(2026,5,1),amount=Decimal('50.00'),currency='EGP',payment_method='cash',cash_account_code='1100')
    with pytest.raises(ValueError): post_receipt(r.pk)
    r.refresh_from_db(); assert not r.is_posted

@pytest.mark.django_db
def test_receipt_posting_is_idempotent():
    c=Company.objects.create(name='Idempotent Receipts',base_currency='EGP')
    t=Party.objects.create(company=c,display_name='Tenant')
    Account.objects.create(company=c,code='1100',name='Cash',account_type='asset',allow_manual_posting=True)
    Account.objects.create(company=c,code='1200',name='Receivables',account_type='asset',is_control_account=True,allow_manual_posting=False)
    FiscalPeriod.objects.create(company=c,name='FY',start_date=date(2026,1,1),end_date=date(2026,12,31))
    receipt=Receipt.objects.create(company=c,receipt_number='R-IDEMP',tenant=t,receipt_date=date(2026,6,1),
        amount=Decimal('75.00'),currency='EGP',payment_method='cash',cash_account_code='1100')

    first=post_receipt(receipt.pk)
    second=post_receipt(receipt.pk)

    assert first.pk == second.pk
    assert JournalEntry.objects.filter(company=c,source_type='receipt',source_id=str(receipt.pk),status='posted').count() == 1
    assert first.lines.count() == 2


@pytest.mark.django_db
def test_receipt_posting_failure_rolls_back_draft_journal():
    c=Company.objects.create(name='Rollback Receipts',base_currency='EGP')
    t=Party.objects.create(company=c,display_name='Tenant')
    Account.objects.create(company=c,code='1100',name='Cash',account_type='asset',allow_manual_posting=True)
    Account.objects.create(company=c,code='1200',name='Receivables',account_type='asset',is_control_account=True,allow_manual_posting=False)
    receipt=Receipt.objects.create(company=c,receipt_number='R-ROLLBACK',tenant=t,receipt_date=date(2026,6,1),
        amount=Decimal('75.00'),currency='EGP',payment_method='cash',cash_account_code='1100')

    with pytest.raises(ValueError):
        post_receipt(receipt.pk)

    receipt.refresh_from_db()
    assert not receipt.is_posted
    assert not JournalEntry.objects.filter(company=c,source_type='receipt',source_id=str(receipt.pk)).exists()


@pytest.mark.django_db
def test_receipt_post_view_rolls_back_posting_when_audit_event_fails(client, monkeypatch):
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from core.models import AuditEvent, CompanyMembership

    company = Company.objects.create(name='Audit Rollback Co', base_currency='EGP')
    tenant = Party.objects.create(company=company, display_name='Tenant')
    user = get_user_model().objects.create_user(username='audit-user', password='test-pass')
    CompanyMembership.objects.create(company=company, user=user, role='accountant')
    Account.objects.create(company=company, code='1100', name='Cash', account_type='asset', allow_manual_posting=True)
    Account.objects.create(company=company, code='1200', name='Receivables', account_type='asset', is_control_account=True, allow_manual_posting=False)
    FiscalPeriod.objects.create(company=company, name='FY', start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    receipt = Receipt.objects.create(
        company=company, receipt_number='R-AUDIT-ROLLBACK', tenant=tenant,
        receipt_date=date(2026, 6, 1), amount=Decimal('90.00'), currency='EGP',
        payment_method='cash', cash_account_code='1100',
    )
    client.force_login(user)

    def fail_audit_create(*args, **kwargs):
        raise RuntimeError('simulated audit storage failure')

    monkeypatch.setattr(AuditEvent.objects, 'create', fail_audit_create)

    with pytest.raises(RuntimeError, match='simulated audit storage failure'):
        client.post(reverse('receipt_post', args=[receipt.pk]))

    receipt.refresh_from_db()
    assert not receipt.is_posted
    assert not JournalEntry.objects.filter(
        company=company, source_type='receipt', source_id=str(receipt.pk)
    ).exists()
