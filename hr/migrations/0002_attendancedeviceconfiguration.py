# Additive migration for attendance device connection settings.
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("hr", "0001_initial")]
    operations = [migrations.CreateModel(
        name="AttendanceDeviceConfiguration",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(default="ماكينة الحضور الرئيسية", max_length=120, verbose_name="اسم تعريفي للماكينة")),
            ("manufacturer", models.CharField(max_length=160, verbose_name="الشركة المصنعة")),
            ("model_name", models.CharField(max_length=160, verbose_name="موديل الجهاز")),
            ("connection_type", models.CharField(choices=[("lan","شبكة LAN / عنوان IP"),("usb","USB عبر برنامج وسيط"),("software","برنامج وسيط / SDK"),("file","استيراد ملف"),("cloud","خدمة سحابية / API")], default="lan", max_length=20, verbose_name="طريقة الاتصال")),
            ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="عنوان IP")),
            ("port", models.PositiveIntegerField(blank=True, null=True, verbose_name="المنفذ")),
            ("site_name", models.CharField(blank=True, max_length=160, verbose_name="موقع الجهاز / الفرع")),
            ("protocol_or_software", models.CharField(blank=True, max_length=160, verbose_name="البروتوكول أو البرنامج الوسيط")),
            ("external_device_id", models.CharField(blank=True, max_length=120, verbose_name="معرف الجهاز الخارجي")),
            ("enabled", models.BooleanField(default=False, verbose_name="تفعيل التكامل")),
            ("notes", models.TextField(blank=True, verbose_name="ملاحظات")),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ],
        options={"ordering":["manufacturer","model_name"],"verbose_name":"إعداد ماكينة حضور","verbose_name_plural":"إعدادات ماكينات الحضور"},
    )]
