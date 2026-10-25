# Additive migration: rejects non-positive financial amounts at the database layer.
# Before production rollout, inspect legacy rows for zero/negative values.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("leasing", "0001_initial")]
    operations = [
        migrations.AddConstraint(
            model_name="leasecharge",
            constraint=models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_lease_charge_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="receipt",
            constraint=models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_receipt_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="receiptallocation",
            constraint=models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_receipt_allocation_positive"),
        ),
    ]
