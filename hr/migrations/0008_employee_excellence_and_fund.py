# Generated additive migration for employee excellence and staff mutual-aid fund.
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0007_workforce_talent_planning"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeOfTheMonthSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("performance_weight", models.DecimalField(decimal_places=2, default="40.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="وزن الأداء %")),
                ("appearance_weight", models.DecimalField(decimal_places=2, default="15.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="وزن الهيئة المهنية %")),
                ("behavior_weight", models.DecimalField(decimal_places=2, default="20.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="وزن السلوك %")),
                ("commitment_weight", models.DecimalField(decimal_places=2, default="25.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="وزن الالتزام %")),
                ("minimum_reviews", models.PositiveSmallIntegerField(default=1, verbose_name="الحد الأدنى للتقييمات")),
                ("minimum_score", models.DecimalField(decimal_places=2, default="0.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="الحد الأدنى للترشيح")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "إعدادات الموظف المثالي", "verbose_name_plural": "إعدادات الموظف المثالي"},
        ),
        migrations.CreateModel(
            name="EmployeeFundPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="صندوق الزمالة والجمعية", max_length=160, verbose_name="اسم الصندوق")),
                ("monthly_deduction_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="الاستقطاع الشهري لكل موظف")),
                ("emergency_share_percent", models.DecimalField(decimal_places=2, default="10.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="نسبة صندوق الطوارئ %")),
                ("association_share_percent", models.DecimalField(decimal_places=2, default="90.00", max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="نسبة قسط الجمعية %")),
                ("effective_from", models.DateField(verbose_name="ساري من")),
                ("effective_to", models.DateField(blank=True, null=True, verbose_name="ساري حتى")),
                ("active", models.BooleanField(default=True, verbose_name="نشط")),
                ("requires_approval", models.BooleanField(default=True, verbose_name="يتطلب اعتماد الإدارة")),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات ومرجع قرار الإدارة")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-effective_from"], "verbose_name": "سياسة صندوق العاملين", "verbose_name_plural": "سياسات صندوق العاملين"},
        ),
        migrations.CreateModel(
            name="EmployeeFundMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monthly_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="الاستقطاع الشهري المتفق عليه")),
                ("joined_on", models.DateField(verbose_name="تاريخ الاشتراك")),
                ("status", models.CharField(choices=[("active", "مشترك"), ("paused", "موقوف مؤقتًا"), ("withdrawn", "منسحب")], default="active", max_length=20, verbose_name="الحالة")),
                ("consent_reference", models.CharField(blank=True, max_length=160, verbose_name="مرجع موافقة الموظف")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fund_memberships", to="hr.employee", verbose_name="الموظف")),
                ("policy", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="hr.employeefundpolicy", verbose_name="سياسة الصندوق")),
            ],
            options={"ordering": ["employee__employee_code"], "verbose_name": "اشتراك موظف في الصندوق", "verbose_name_plural": "اشتراكات صندوق العاملين"},
        ),
        migrations.CreateModel(
            name="EmployeeFundContribution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gross_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="إجمالي الاستقطاع")),
                ("emergency_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="حصة الطوارئ")),
                ("association_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="قسط الجمعية")),
                ("status", models.CharField(choices=[("planned", "مجدول"), ("deducted", "مستقطع من الراتب"), ("reconciled", "تمت المطابقة"), ("reversed", "ملغى/معكوس")], default="planned", max_length=20, verbose_name="الحالة")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="contributions", to="hr.employeefundmembership", verbose_name="الاشتراك")),
                ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fund_contributions", to="hr.payrollperiod", verbose_name="فترة المرتب")),
                ("payroll_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="fund_contributions", to="hr.payrollitem", verbose_name="بند المرتب")),
            ],
            options={"ordering": ["period__start_date", "membership__employee__employee_code"], "verbose_name": "استقطاع صندوق العاملين", "verbose_name_plural": "استقطاعات صندوق العاملين"},
        ),
        migrations.CreateModel(
            name="EmployeeAssociationTurn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cycle_name", models.CharField(max_length=120, verbose_name="اسم دورة الجمعية")),
                ("turn_number", models.PositiveIntegerField(verbose_name="ترتيب الدور")),
                ("scheduled_date", models.DateField(blank=True, null=True, verbose_name="تاريخ الدور المتوقع")),
                ("expected_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="قيمة الجمعية المتوقعة")),
                ("actual_paid_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name="المبلغ المصروف فعليًا")),
                ("status", models.CharField(choices=[("queued", "في انتظار الدور"), ("approved", "معتمد للصرف"), ("paid", "تم الصرف"), ("cancelled", "ملغى")], default="queued", max_length=20, verbose_name="الحالة")),
                ("approval_reference", models.CharField(blank=True, max_length=160, verbose_name="مرجع الاعتماد")),
                ("paid_at", models.DateField(blank=True, null=True, verbose_name="تاريخ الصرف")),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات")),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="association_turns", to="hr.employeefundmembership", verbose_name="المشترك")),
            ],
            options={"ordering": ["cycle_name", "turn_number"], "verbose_name": "دور جمعية العاملين", "verbose_name_plural": "أدوار جمعية العاملين"},
        ),
        migrations.CreateModel(
            name="EmployeeEmergencyClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("accident", "حادث"), ("medical", "طارئ صحي"), ("death", "وفاة"), ("fire", "حريق/حادث ممتلكات"), ("other", "ظرف طارئ آخر")], max_length=20, verbose_name="نوع الظرف")),
                ("event_date", models.DateField(verbose_name="تاريخ الحدث")),
                ("description", models.TextField(verbose_name="تفاصيل الحدث")),
                ("requested_amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name="المبلغ المطلوب")),
                ("approved_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name="المبلغ المعتمد")),
                ("status", models.CharField(choices=[("submitted", "مقدم"), ("under_review", "قيد المراجعة"), ("approved", "معتمد"), ("paid", "تم الصرف"), ("rejected", "مرفوض")], default="submitted", max_length=20, verbose_name="الحالة")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateField(blank=True, null=True, verbose_name="تاريخ الصرف")),
                ("decision_notes", models.TextField(blank=True, verbose_name="قرار وملاحظات الاعتماد")),
                ("attachment", models.FileField(blank=True, upload_to="hr/employee_fund/claims/%Y/%m/", verbose_name="مستندات مؤيدة")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="emergency_fund_claims", to="hr.employee", verbose_name="الموظف")),
                ("reviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_emergency_claims", to=settings.AUTH_USER_MODEL, verbose_name="المراجع")),
            ],
            options={"ordering": ["-event_date", "-created_at"], "verbose_name": "طلب مساعدة من صندوق الطوارئ", "verbose_name_plural": "طلبات صندوق الطوارئ"},
        ),
        migrations.AddConstraint(
            model_name="employeefundmembership",
            constraint=models.UniqueConstraint(fields=("employee", "policy"), name="hr_unique_employee_fund_membership"),
        ),
        migrations.AddConstraint(
            model_name="employeefundcontribution",
            constraint=models.UniqueConstraint(fields=("membership", "period"), name="hr_unique_fund_contribution_period"),
        ),
        migrations.AddConstraint(
            model_name="employeeassociationturn",
            constraint=models.UniqueConstraint(fields=("cycle_name", "turn_number"), name="hr_unique_association_cycle_turn"),
        ),
        migrations.AddConstraint(
            model_name="employeeassociationturn",
            constraint=models.UniqueConstraint(fields=("cycle_name", "membership"), name="hr_unique_membership_per_association_cycle"),
        ),
    ]
