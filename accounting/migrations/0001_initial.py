# Initial accounting schema. Additive follow-up migrations only after deployment.
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.CreateModel(name="Account", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("code", models.CharField(max_length=30)), ("name", models.CharField(max_length=180)),
            ("account_type", models.CharField(choices=[("asset", "Asset"), ("liability", "Liability"), ("equity", "Equity"), ("revenue", "Revenue"), ("expense", "Expense")], max_length=20)),
            ("is_control_account", models.BooleanField(default=False)), ("allow_manual_posting", models.BooleanField(default=True)),
            ("is_active", models.BooleanField(default=True)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="core.company")),
            ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="accounting.account")),
        ]),
        migrations.CreateModel(name="FiscalPeriod", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=100)), ("start_date", models.DateField()), ("end_date", models.DateField()),
            ("is_closed", models.BooleanField(default=False)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fiscal_periods", to="core.company")),
        ]),
        migrations.CreateModel(name="JournalEntry", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("entry_number", models.CharField(max_length=40)), ("entry_date", models.DateField()), ("description", models.CharField(max_length=250)),
            ("source_type", models.CharField(blank=True, max_length=60)), ("source_id", models.CharField(blank=True, max_length=80)),
            ("idempotency_key", models.CharField(blank=True, max_length=100)),
            ("status", models.CharField(choices=[("draft", "Draft"), ("posted", "Posted"), ("reversed", "Reversed")], default="draft", max_length=12)),
            ("posted_at", models.DateTimeField(blank=True, null=True)),
            ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_entries", to="core.company")),
        ]),
        migrations.CreateModel(name="JournalLine", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("description", models.CharField(blank=True, max_length=250)),
            ("debit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)),
            ("credit", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)), ("currency", models.CharField(default="EGP", max_length=3)),
            ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="journal_lines", to="accounting.account")),
            ("entry", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="accounting.journalentry")),
        ]),
        migrations.AddConstraint(model_name="account", constraint=models.UniqueConstraint(fields=("company", "code"), name="uq_account_code_company")),
        migrations.AddIndex(model_name="account", index=models.Index(fields=["company", "account_type"], name="acct_account_co_type_idx")),
        migrations.AddConstraint(model_name="fiscalperiod", constraint=models.UniqueConstraint(fields=("company", "name"), name="uq_period_name_company")),
        migrations.AddConstraint(model_name="fiscalperiod", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="ck_period_dates_valid")),
        migrations.AddConstraint(model_name="journalentry", constraint=models.UniqueConstraint(fields=("company", "entry_number"), name="uq_journal_number_company")),
        migrations.AddConstraint(model_name="journalentry", constraint=models.UniqueConstraint(condition=models.Q(("idempotency_key", ""), _negated=True), fields=("company", "idempotency_key"), name="uq_journal_idempotency_company")),
        migrations.AddIndex(model_name="journalentry", index=models.Index(fields=["company", "entry_date", "status"], name="acct_journal_co_date_status")),
        migrations.AddConstraint(model_name="journalline", constraint=models.CheckConstraint(condition=models.Q(models.Q(("debit__gt", 0), ("credit__gt", 0)), _negated=True), name="ck_journal_line_not_both_sides")),
        migrations.AddConstraint(model_name="journalline", constraint=models.CheckConstraint(condition=models.Q(("debit__gte", 0), ("credit__gte", 0)), name="ck_journal_line_nonnegative")),
    ]
