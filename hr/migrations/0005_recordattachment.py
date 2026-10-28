from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0004_seed_hiring_document_templates"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="RecordAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.PositiveBigIntegerField(verbose_name="رقم السجل")),
                ("title", models.CharField(max_length=180, verbose_name="عنوان المرفق")),
                ("file", models.FileField(upload_to="hr/record-attachments/%Y/%m/", verbose_name="الملف المرفق")),
                ("category", models.CharField(blank=True, max_length=80, verbose_name="تصنيف المرفق")),
                ("issue_date", models.DateField(blank=True, null=True, verbose_name="تاريخ المستند")),
                ("expiry_date", models.DateField(blank=True, null=True, verbose_name="تاريخ الانتهاء")),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype", verbose_name="نوع السجل")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name="رفع بواسطة")),
            ],
            options={"ordering":["-uploaded_at"],"verbose_name":"مرفق مستند لسجل","verbose_name_plural":"مرفقات المستندات والسجلات"},
        ),
    ]
