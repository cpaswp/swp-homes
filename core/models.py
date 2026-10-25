from django.conf import settings
from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Company(TimeStampedModel):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=250, blank=True)
    tax_number = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(upload_to="company-logos/", blank=True, null=True)
    base_currency = models.CharField(max_length=3, default="EGP")
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class CompanyMembership(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_memberships")
    role = models.CharField(max_length=30, choices=[("owner","Owner"),("admin","Admin"),("accountant","Accountant"),("property_manager","Property Manager"),("viewer","Viewer")], default="viewer")
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["company","user"], name="uq_company_membership_user")]

class Party(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="parties")
    kind = models.CharField(max_length=10, choices=[("person","Person"),("company","Company")], default="person")
    display_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    national_or_tax_id = models.CharField(max_length=60, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        indexes = [models.Index(fields=["company","display_name"], name="core_party_co_name_idx")]

class Property(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="properties")
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=[("residential","Residential"),("commercial","Commercial"),("land","Land"),("mixed","Mixed use")])
    ownership_type = models.CharField(max_length=20, choices=[("company_owned","Company owned"),("client_managed","Client managed")])
    client_owner = models.ForeignKey(Party, null=True, blank=True, on_delete=models.PROTECT, related_name="owned_properties")
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    area_sqm = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    acquisition_cost = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EGP")
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["company","code"], name="uq_property_code_per_company")]
        indexes = [models.Index(fields=["company","kind","ownership_type"], name="core_property_co_kind_owner")]

class Unit(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="units")
    property = models.ForeignKey(Property, on_delete=models.PROTECT, related_name="units")
    code = models.CharField(max_length=40)
    kind = models.CharField(max_length=20, choices=[("apartment","Apartment"),("shop","Shop"),("office","Office"),("warehouse","Warehouse"),("land_parcel","Land parcel"),("other","Other")])
    floor_label = models.CharField(max_length=30, blank=True)
    area_sqm = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("available","Available"),("occupied","Occupied"),("maintenance","Maintenance"),("inactive","Inactive")], default="available")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["property","code"], name="uq_unit_code_per_property")]

class AuditEvent(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    model_label = models.CharField(max_length=150)
    object_id = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)
