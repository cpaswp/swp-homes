from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_company_logo")]

    operations = [
        migrations.AlterField(
            model_name="company",
            name="logo",
            field=models.FileField(blank=True, null=True, upload_to="company-logos/"),
        ),
    ]
