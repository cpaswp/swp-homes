from datetime import date
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Company, CompanyMembership, Party, Property, Unit
from leasing.models import Lease, LeaseCharge


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
