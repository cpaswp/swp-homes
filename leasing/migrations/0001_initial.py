# Initial leasing schema. Additive follow-up migrations only after deployment.
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.CreateModel(name="Lease", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("lease_number", models.CharField(max_length=50)), ("start_date", models.DateField()), ("end_date", models.DateField()),
            ("rent_amount", models.DecimalField(decimal_places=2, max_digits=16)), ("currency", models.CharField(default="EGP", max_length=3)),
            ("frequency", models.CharField(choices=[("monthly", "Monthly"), ("quarterly", "Quarterly"), ("semiannual", "Semiannual"), ("annual", "Annual")], default="monthly", max_length=20)),
            ("due_day", models.PositiveSmallIntegerField(default=1)), ("management_fee_percent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5)),
            ("security_deposit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)),
            ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("expired", "Expired"), ("terminated", "Terminated")], default="draft", max_length=12)),
            ("schedule_version", models.PositiveIntegerField(default=1)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="leases", to="core.company")),
            ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="leases_as_tenant", to="core.party")),
            ("unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="leases", to="core.unit")),
        ]),
        migrations.CreateModel(name="LeaseCharge", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("due_date", models.DateField()), ("amount", models.DecimalField(decimal_places=2, max_digits=16)), ("currency", models.CharField(default="EGP", max_length=3)),
            ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("partial", "Partially paid"), ("paid", "Paid"), ("void", "Void")], default="scheduled", max_length=12)),
            ("schedule_version", models.PositiveIntegerField(default=1)), ("period_label", models.CharField(blank=True, max_length=80)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lease_charges", to="core.company")),
            ("lease", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="charges", to="leasing.lease")),
        ]),
        migrations.CreateModel(name="Receipt", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("receipt_number", models.CharField(max_length=50)), ("receipt_date", models.DateField()), ("amount", models.DecimalField(decimal_places=2, max_digits=16)),
            ("currency", models.CharField(default="EGP", max_length=3)),
            ("payment_method", models.CharField(choices=[("cash", "Cash"), ("bank", "Bank transfer"), ("cheque", "Cheque"), ("card", "Card")], default="cash", max_length=20)),
            ("cash_account_code", models.CharField(max_length=30)), ("idempotency_key", models.UUIDField(default=uuid.uuid4, editable=False)),
            ("is_posted", models.BooleanField(default=False)), ("external_reference", models.CharField(blank=True, max_length=100)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receipts", to="core.company")),
            ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receipts", to="core.party")),
        ]),
        migrations.CreateModel(name="ReceiptAllocation", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("amount", models.DecimalField(decimal_places=2, max_digits=16)),
            ("charge", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="leasing.leasecharge")),
            ("receipt", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="allocations", to="leasing.receipt")),
        ]),
        migrations.AddConstraint(model_name="lease", constraint=models.UniqueConstraint(fields=("company", "lease_number"), name="uq_lease_number_company")),
        migrations.AddConstraint(model_name="lease", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="ck_lease_dates_valid")),
        migrations.AddConstraint(model_name="lease", constraint=models.CheckConstraint(condition=models.Q(("due_day__gte", 1), ("due_day__lte", 28)), name="ck_lease_due_day_1_28")),
        migrations.AddConstraint(model_name="lease", constraint=models.CheckConstraint(condition=models.Q(("management_fee_percent__gte", 0), ("management_fee_percent__lte", 100)), name="ck_lease_fee_percent_range")),
        migrations.AddConstraint(model_name="leasecharge", constraint=models.UniqueConstraint(fields=("lease", "due_date", "schedule_version"), name="uq_charge_lease_due_version")),
        migrations.AddIndex(model_name="leasecharge", index=models.Index(fields=["company", "due_date", "status"], name="lease_charge_co_due_status")),
        migrations.AddConstraint(model_name="receipt", constraint=models.UniqueConstraint(fields=("company", "receipt_number"), name="uq_receipt_number_company")),
        migrations.AddConstraint(model_name="receipt", constraint=models.UniqueConstraint(fields=("company", "idempotency_key"), name="uq_receipt_idempotency_company")),
        migrations.AddConstraint(model_name="receiptallocation", constraint=models.UniqueConstraint(fields=("receipt", "charge"), name="uq_receipt_charge_allocation")),
    ]
