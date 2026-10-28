# Additive migration: company/legal compliance rules and hiring-document catalog.
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("hr", "0002_attendancedeviceconfiguration")]
    operations = [
        migrations.CreateModel(
            name="RegulationRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="كود القاعدة")),
                ("title", models.CharField(max_length=180, verbose_name="عنوان القاعدة")),
                ("rule_type", models.CharField(choices=[("allowance","مسموح / استحقاق"),("prohibition","ممنوع"),("limit","حد أقصى / قيد"),("approval","يتطلب موافقة"),("legal","التزام قانوني")], max_length=20, verbose_name="نوع القاعدة")),
                ("scope", models.CharField(help_text="مثال: إجازات، خصومات، عهد، مصوغات تعيين", max_length=100, verbose_name="النطاق / العملية")),
                ("description", models.TextField(verbose_name="تفاصيل القاعدة")),
                ("source_type", models.CharField(choices=[("company","لائحة الشركة"),("law","قانون / قرار رسمي"),("contract","عقد العمل"),("policy","سياسة داخلية")], default="company", max_length=30, verbose_name="مصدر القاعدة")),
                ("source_reference", models.CharField(blank=True, max_length=180, verbose_name="مرجع المادة أو القرار")),
                ("effective_from", models.DateField(verbose_name="ساري من")),
                ("effective_to", models.DateField(blank=True, null=True, verbose_name="ساري حتى")),
                ("limit_value", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="قيمة الحد إن وجدت")),
                ("limit_unit", models.CharField(blank=True, max_length=40, verbose_name="وحدة الحد")),
                ("requires_approval", models.BooleanField(default=False, verbose_name="يتطلب اعتمادًا")),
                ("active", models.BooleanField(default=True, verbose_name="نشطة")),
                ("document", models.FileField(blank=True, upload_to="hr/regulations/rules/%Y/%m/", verbose_name="مستند مرجعي")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering":["scope","code"],"verbose_name":"قاعدة لائحة / امتثال","verbose_name_plural":"قواعد اللوائح والقانون والامتثال"},
        ),
        migrations.CreateModel(
            name="HiringDocumentTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True, verbose_name="كود المصوغ")),
                ("title", models.CharField(max_length=180, verbose_name="اسم مصوغ التعيين")),
                ("category", models.CharField(choices=[("identity","إثبات شخصية"),("education","مؤهل دراسي"),("experience","خبرة"),("medical","طبي"),("insurance","تأمينات"),("tax","ضرائب"),("bank","بيانات بنكية"),("contract","عقد / عرض عمل"),("other","أخرى")], default="other", max_length=20, verbose_name="التصنيف")),
                ("description", models.TextField(blank=True, verbose_name="الوصف أو متطلبات القبول")),
                ("mandatory", models.BooleanField(default=True, verbose_name="إلزامي")),
                ("applies_to", models.CharField(default="all", help_text="all أو نوع وظيفة/فئة موظفين", max_length=120, verbose_name="ينطبق على")),
                ("due_days_after_hire", models.PositiveSmallIntegerField(default=0, verbose_name="مهلة التسليم بعد التعيين بالأيام")),
                ("has_expiry", models.BooleanField(default=False, verbose_name="له تاريخ صلاحية")),
                ("default_validity_months", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="الصلاحية الافتراضية بالشهور")),
                ("alert_days_before_expiry", models.PositiveSmallIntegerField(default=30, verbose_name="التنبيه قبل الانتهاء بالأيام")),
                ("requires_original", models.BooleanField(default=False, verbose_name="يتطلب أصل المستند")),
                ("active", models.BooleanField(default=True, verbose_name="نشط")),
                ("sort_order", models.PositiveSmallIntegerField(default=100, verbose_name="ترتيب العرض")),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات")),
            ],
            options={"ordering":["sort_order","title"],"verbose_name":"تعريف مصوغ تعيين","verbose_name_plural":"مصوغات التعيين المطلوبة"},
        ),
    ]
