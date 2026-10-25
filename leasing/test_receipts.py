from datetime import date
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from core.models import Company, Party
from accounting.models import Account, FiscalPeriod
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
