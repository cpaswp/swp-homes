from datetime import date
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Company, CompanyMembership, Party, Property, Unit
from leasing.models import Lease, LeaseCharge

@pytest.mark.django_db
def test_lease_list_is_company_scoped(client):
    user=get_user_model().objects.create_user(username='leaseviewer',password='test-password-strong')
    company=Company.objects.create(name='My company'); other=Company.objects.create(name='Other company')
    CompanyMembership.objects.create(company=company,user=user,role='viewer')
    prop=Property.objects.create(company=company,code='P1',name='Own property',kind='residential',ownership_type='company_owned')
    unit=Unit.objects.create(company=company,property=prop,code='U1',kind='apartment')
    tenant=Party.objects.create(company=company,display_name='Own tenant')
    Lease.objects.create(company=company,lease_number='L-1',unit=unit,tenant=tenant,start_date=date(2026,1,1),end_date=date(2026,12,31),rent_amount=Decimal('1000'),status='active')
    other_prop=Property.objects.create(company=other,code='P2',name='Hidden property',kind='residential',ownership_type='company_owned')
    other_unit=Unit.objects.create(company=other,property=other_prop,code='U2',kind='apartment')
    other_tenant=Party.objects.create(company=other,display_name='Hidden tenant')
    Lease.objects.create(company=other,lease_number='SECRET',unit=other_unit,tenant=other_tenant,start_date=date(2026,1,1),end_date=date(2026,12,31),rent_amount=Decimal('9999'))
    client.force_login(user)
    response=client.get(reverse('lease_list'))
    assert response.status_code==200
    assert len(response.context['leases'])==1
    assert response.context['leases'][0].lease_number=='L-1'


@pytest.mark.django_db
def test_receipt_form_uses_company_postable_asset_accounts_only():
    from leasing.forms import ReceiptForm
    from accounting.models import Account

    company = Company.objects.create(name="Dynamic receipt accounts")
    eligible = Account.objects.create(
        company=company, code="1015", name="Main cash",
        account_type="asset", allow_manual_posting=True,
    )
    Account.objects.create(
        company=company, code="1200", name="Receivables control",
        account_type="asset", allow_manual_posting=False, is_control_account=True,
    )
    Account.objects.create(
        company=company, code="2100", name="Payables",
        account_type="liability", allow_manual_posting=True,
    )
    other = Company.objects.create(name="Other company")
    Account.objects.create(
        company=other, code="1020", name="Other cash",
        account_type="asset", allow_manual_posting=True,
    )

    form = ReceiptForm(company=company)
    choices = dict(form.fields["cash_account_code"].widget.choices)
    assert eligible.code in choices
    assert "1200" not in choices
    assert "2100" not in choices
    assert "1020" not in choices
