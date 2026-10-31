from datetime import date
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Company, CompanyMembership, Party, Property, Unit
from leasing.models import Lease, LeaseCharge, Receipt, ReceiptAllocation


@pytest.mark.django_db
def test_health_endpoint_does_not_require_login(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_dashboard_scopes_metrics_to_user_company(client):
    user = get_user_model().objects.create_user(username="operator", password="strong-test-password")
    visible = Company.objects.create(name="Visible")
    hidden = Company.objects.create(name="Hidden")
    CompanyMembership.objects.create(company=visible, user=user, role="viewer")
    Property.objects.create(company=visible, code="P-1", name="Visible property", kind="residential", ownership_type="company_owned")
    Property.objects.create(company=hidden, code="P-2", name="Hidden property", kind="residential", ownership_type="company_owned")
    client.force_login(user)
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert response.context["property_count"] == 1
    assert response.context["active_company"] == visible


@pytest.mark.django_db
def test_property_list_scopes_to_active_company(client):
    user = get_user_model().objects.create_user(username="manager", password="strong-test-password")
    own = Company.objects.create(name="Own")
    other = Company.objects.create(name="Other")
    CompanyMembership.objects.create(company=own, user=user, role="viewer")
    Property.objects.create(company=own, code="OWN-1", name="Visible home", kind="residential", ownership_type="company_owned")
    Property.objects.create(company=other, code="OTH-1", name="Hidden home", kind="residential", ownership_type="company_owned")
    client.force_login(user)
    response = client.get(reverse("property_list"))
    assert response.status_code == 200
    assert len(response.context["properties"]) == 1
    assert response.context["properties"][0].code == "OWN-1"


@pytest.mark.django_db
def test_viewer_cannot_create_property(client):
    user = get_user_model().objects.create_user(username="viewer", password="strong-test-password")
    company = Company.objects.create(name="Company")
    CompanyMembership.objects.create(company=company, user=user, role="viewer")
    client.force_login(user)
    response = client.post(reverse("property_create"), {
        "code": "P-1", "name": "Test", "kind": "residential",
        "ownership_type": "company_owned", "currency": "EGP", "is_active": "on",
    })
    assert response.status_code == 302
    assert not Property.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_property_form_requires_owner_for_client_managed(client):
    user = get_user_model().objects.create_user(username="owner", password="strong-test-password")
    company = Company.objects.create(name="Company")
    CompanyMembership.objects.create(company=company, user=user, role="owner")
    client.force_login(user)
    response = client.post(reverse("property_create"), {
        "code": "P-1", "name": "Managed", "kind": "residential",
        "ownership_type": "client_managed", "currency": "EGP", "is_active": "on",
    })
    assert response.status_code == 200
    assert not Property.objects.filter(company=company).exists()
    assert "client_owner" in response.context["form"].errors


@pytest.mark.django_db
def test_unit_form_rejects_property_from_other_company(client):
    user = get_user_model().objects.create_user(username="manager2", password="strong-test-password")
    own = Company.objects.create(name="Own")
    other = Company.objects.create(name="Other")
    CompanyMembership.objects.create(company=own, user=user, role="owner")
    foreign_property = Property.objects.create(company=other, code="OTH-1", name="Foreign", kind="residential", ownership_type="company_owned")
    client.force_login(user)
    response = client.post(reverse("unit_create"), {
        "property": foreign_property.pk, "code": "U-1", "kind": "apartment", "status": "available",
    })
    assert response.status_code == 200
    assert not Unit.objects.filter(company=own).exists()


@pytest.mark.django_db
def test_dashboard_outstanding_does_not_duplicate_charges_with_multiple_allocations(client):
    user = get_user_model().objects.create_user(username="dashboard-balance", password="strong-test-password")
    company = Company.objects.create(name="Balance company")
    CompanyMembership.objects.create(company=company, user=user, role="viewer")
    tenant = Party.objects.create(company=company, display_name="Balance tenant")
    prop = Property.objects.create(company=company, code="BAL-1", name="Balance property",
        kind="residential", ownership_type="company_owned")
    unit = Unit.objects.create(company=company, property=prop, code="BAL-U1", kind="apartment")
    lease = Lease.objects.create(company=company, lease_number="BAL-L1", unit=unit, tenant=tenant,
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), rent_amount=Decimal("1000.00"))
    charge = LeaseCharge.objects.create(company=company, lease=lease, due_date=date(2026, 1, 1),
        amount=Decimal("1000.00"))
    first = Receipt.objects.create(company=company, receipt_number="BAL-R1", tenant=tenant,
        receipt_date=date(2026, 1, 5), amount=Decimal("200.00"), cash_account_code="1100")
    second = Receipt.objects.create(company=company, receipt_number="BAL-R2", tenant=tenant,
        receipt_date=date(2026, 1, 6), amount=Decimal("300.00"), cash_account_code="1100")
    ReceiptAllocation.objects.create(receipt=first, charge=charge, amount=Decimal("200.00"))
    ReceiptAllocation.objects.create(receipt=second, charge=charge, amount=Decimal("300.00"))

    client.force_login(user)
    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["outstanding"] == Decimal("500.00")


@pytest.mark.django_db
def test_property_and_audit_event_are_saved_atomically(client, monkeypatch):
    from core.models import AuditEvent

    user = get_user_model().objects.create_user(username="atomic-property", password="strong-test-password")
    company = Company.objects.create(name="Atomic property company")
    CompanyMembership.objects.create(company=company, user=user, role="owner")
    client.force_login(user)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(AuditEvent.objects, "create", fail_audit)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        client.post(reverse("property_create"), {
            "code": "AT-1", "name": "Atomic test property", "kind": "residential",
            "ownership_type": "company_owned", "currency": "EGP", "is_active": "on",
        })

    assert not Property.objects.filter(company=company, code="AT-1").exists()


@pytest.mark.django_db
def test_property_update_is_company_scoped_and_audited(client):
    from core.models import AuditEvent
    user = get_user_model().objects.create_user(username="edit-property", password="strong-test-password")
    company = Company.objects.create(name="Edit company")
    other = Company.objects.create(name="Other edit company")
    CompanyMembership.objects.create(company=company, user=user, role="owner")
    own = Property.objects.create(company=company, code="EP-1", name="Old", kind="residential", ownership_type="company_owned")
    foreign = Property.objects.create(company=other, code="EP-2", name="Foreign", kind="residential", ownership_type="company_owned")
    client.force_login(user)
    response = client.post(reverse("property_update", args=[own.pk]), {
        "code": "EP-1", "name": "Updated", "kind": "residential",
        "ownership_type": "company_owned", "currency": "EGP", "is_active": "on",
    })
    assert response.status_code == 302
    own.refresh_from_db()
    assert own.name == "Updated"
    assert AuditEvent.objects.filter(company=company, action="property.update", object_id=str(own.pk)).exists()
    assert client.get(reverse("property_update", args=[foreign.pk])).status_code == 404


@pytest.mark.django_db
def test_viewer_cannot_update_property(client):
    user = get_user_model().objects.create_user(username="viewer-edit", password="strong-test-password")
    company = Company.objects.create(name="Viewer edit company")
    CompanyMembership.objects.create(company=company, user=user, role="viewer")
    prop = Property.objects.create(company=company, code="VE-1", name="Original", kind="residential", ownership_type="company_owned")
    client.force_login(user)
    response = client.post(reverse("property_update", args=[prop.pk]), {
        "code": "VE-1", "name": "Changed", "kind": "residential",
        "ownership_type": "company_owned", "currency": "EGP", "is_active": "on",
    })
    prop.refresh_from_db()
    assert response.status_code == 302
    assert prop.name == "Original"


@pytest.mark.django_db
def test_unit_update_is_company_scoped_and_audited(client):
    from core.models import AuditEvent
    user = get_user_model().objects.create_user(username="edit-unit", password="strong-test-password")
    company = Company.objects.create(name="Unit edit company")
    other = Company.objects.create(name="Other unit company")
    CompanyMembership.objects.create(company=company, user=user, role="owner")
    prop = Property.objects.create(company=company, code="UP-1", name="Own", kind="residential", ownership_type="company_owned")
    foreign_prop = Property.objects.create(company=other, code="UP-2", name="Foreign", kind="residential", ownership_type="company_owned")
    unit = Unit.objects.create(company=company, property=prop, code="UU-1", kind="apartment")
    client.force_login(user)
    response = client.post(reverse("unit_update", args=[unit.pk]), {
        "property": foreign_prop.pk, "code": "UU-1", "kind": "apartment", "status": "available",
    })
    assert response.status_code == 200
    unit.refresh_from_db()
    assert unit.property_id == prop.pk
    response = client.post(reverse("unit_update", args=[unit.pk]), {
        "property": prop.pk, "code": "UU-1", "kind": "apartment", "status": "available",
    })
    assert response.status_code == 302
    assert AuditEvent.objects.filter(company=company, action="unit.update", object_id=str(unit.pk)).exists()
