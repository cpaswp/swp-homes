# Initial schema for new installations. Never edit after deployment; add follow-up migrations.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Company", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=200)), ("legal_name", models.CharField(blank=True, max_length=250)),
            ("tax_number", models.CharField(blank=True, max_length=50)), ("base_currency", models.CharField(default="EGP", max_length=3)),
            ("is_active", models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name="Party", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("kind", models.CharField(choices=[("person", "Person"), ("company", "Company")], default="person", max_length=10)),
            ("display_name", models.CharField(max_length=200)), ("phone", models.CharField(blank=True, max_length=40)),
            ("email", models.EmailField(blank=True, max_length=254)), ("national_or_tax_id", models.CharField(blank=True, max_length=60)),
            ("address", models.TextField(blank=True)), ("is_active", models.BooleanField(default=True)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="parties", to="core.company")),
        ]),
        migrations.CreateModel(name="Property", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("code", models.CharField(max_length=40)), ("name", models.CharField(max_length=200)),
            ("kind", models.CharField(choices=[("residential", "Residential"), ("commercial", "Commercial"), ("land", "Land"), ("mixed", "Mixed use")], max_length=20)),
            ("ownership_type", models.CharField(choices=[("company_owned", "Company owned"), ("client_managed", "Client managed")], max_length=20)),
            ("address", models.TextField(blank=True)), ("city", models.CharField(blank=True, max_length=100)),
            ("area_sqm", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
            ("acquisition_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
            ("currency", models.CharField(default="EGP", max_length=3)), ("is_active", models.BooleanField(default=True)),
            ("client_owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="owned_properties", to="core.party")),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="properties", to="core.company")),
        ]),
        migrations.CreateModel(name="CompanyMembership", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Admin"), ("accountant", "Accountant"), ("property_manager", "Property Manager"), ("viewer", "Viewer")], default="viewer", max_length=30)),
            ("is_active", models.BooleanField(default=True)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="core.company")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="company_memberships", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="Unit", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("code", models.CharField(max_length=40)),
            ("kind", models.CharField(choices=[("apartment", "Apartment"), ("shop", "Shop"), ("office", "Office"), ("warehouse", "Warehouse"), ("land_parcel", "Land parcel"), ("other", "Other")], max_length=20)),
            ("floor_label", models.CharField(blank=True, max_length=30)), ("area_sqm", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
            ("status", models.CharField(choices=[("available", "Available"), ("occupied", "Occupied"), ("maintenance", "Maintenance"), ("inactive", "Inactive")], default="available", max_length=20)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="units", to="core.company")),
            ("property", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="units", to="core.property")),
        ]),
        migrations.CreateModel(name="AuditEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("action", models.CharField(max_length=100)), ("model_label", models.CharField(max_length=150)),
            ("object_id", models.CharField(max_length=80)), ("details", models.JSONField(blank=True, default=dict)),
            ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_events", to="core.company")),
        ]),
        migrations.AddConstraint(model_name="companymembership", constraint=models.UniqueConstraint(fields=("company", "user"), name="uq_company_membership_user")),
        migrations.AddIndex(model_name="party", index=models.Index(fields=["company", "display_name"], name="core_party_co_name_idx")),
        migrations.AddConstraint(model_name="property", constraint=models.UniqueConstraint(fields=("company", "code"), name="uq_property_code_per_company")),
        migrations.AddIndex(model_name="property", index=models.Index(fields=["company", "kind", "ownership_type"], name="core_property_co_kind_owner")),
        migrations.AddConstraint(model_name="unit", constraint=models.UniqueConstraint(fields=("property", "code"), name="uq_unit_code_per_property")),
    ]
