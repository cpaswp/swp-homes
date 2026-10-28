# Additive migration: workforce skills, career development and succession planning.
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0006_recruitment_interviews"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, unique=True, verbose_name="المهارة")),
                ("category", models.CharField(blank=True, max_length=80, verbose_name="التصنيف")),
                ("description", models.TextField(blank=True, verbose_name="الوصف")),
                ("is_active", models.BooleanField(default=True, verbose_name="نشطة")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["category", "name"], "verbose_name": "مهارة", "verbose_name_plural": "مصفوفة المهارات"},
        ),
        migrations.CreateModel(
            name="EmployeeSkill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("level", models.PositiveSmallIntegerField(choices=[(1, "مبتدئ"), (2, "أساسي"), (3, "متوسط"), (4, "متقدم"), (5, "خبير")], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name="مستوى الإتقان")),
                ("assessed_at", models.DateField(auto_now=True, verbose_name="تاريخ التقييم")),
                ("evidence", models.TextField(blank=True, verbose_name="الأدلة والملاحظات")),
                ("next_review_date", models.DateField(blank=True, null=True, verbose_name="موعد المراجعة التالية")),
                ("assessed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hr_skill_assessments", to=settings.AUTH_USER_MODEL, verbose_name="مقيّم المهارة")),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="skill_assessments", to="hr.employee", verbose_name="الموظف")),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employee_assessments", to="hr.skill", verbose_name="المهارة")),
            ],
            options={"ordering": ["employee__employee_code", "skill__name"], "verbose_name": "تقييم مهارة موظف", "verbose_name_plural": "تقييمات مهارات الموظفين"},
        ),
        migrations.CreateModel(
            name="CareerDevelopmentPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180, verbose_name="عنوان الخطة")),
                ("objective", models.TextField(verbose_name="الهدف التطويري")),
                ("actions", models.TextField(blank=True, verbose_name="أنشطة وخطوات التطوير")),
                ("status", models.CharField(choices=[("draft", "مسودة"), ("active", "قيد التنفيذ"), ("completed", "مكتملة"), ("cancelled", "ملغاة")], default="draft", max_length=20, verbose_name="الحالة")),
                ("start_date", models.DateField(blank=True, null=True, verbose_name="تاريخ البداية")),
                ("target_date", models.DateField(blank=True, null=True, verbose_name="التاريخ المستهدف")),
                ("progress_percent", models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name="نسبة الإنجاز")),
                ("review_notes", models.TextField(blank=True, verbose_name="ملاحظات المراجعة")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="development_plans", to="hr.employee", verbose_name="الموظف")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_development_plans", to=settings.AUTH_USER_MODEL, verbose_name="المسؤول عن المتابعة")),
            ],
            options={"ordering": ["target_date", "employee__employee_code"], "verbose_name": "خطة تطوير وظيفي", "verbose_name_plural": "خطط التطوير الوظيفي"},
        ),
        migrations.CreateModel(
            name="SuccessionPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("readiness", models.CharField(choices=[("ready", "جاهز"), ("one_year", "جاهزية خلال سنة"), ("two_years", "جاهزية خلال سنتين"), ("development", "يحتاج إلى تطوير")], default="development", max_length=20, verbose_name="درجة الجاهزية")),
                ("development_needs", models.TextField(blank=True, verbose_name="احتياجات التطوير")),
                ("risk_notes", models.TextField(blank=True, verbose_name="ملاحظات المخاطر")),
                ("reviewed_at", models.DateField(blank=True, null=True, verbose_name="تاريخ المراجعة")),
                ("is_active", models.BooleanField(default=True, verbose_name="خطة نشطة")),
                ("nominee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="succession_nominations", to="hr.employee", verbose_name="المرشح البديل")),
                ("position", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="succession_candidates", to="hr.jobposition", verbose_name="الوظيفة الحرجة")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_succession_plans", to=settings.AUTH_USER_MODEL, verbose_name="المراجع")),
            ],
            options={"ordering": ["position__title", "readiness", "nominee__full_name"], "verbose_name": "خطة تعاقب وظيفي", "verbose_name_plural": "خطط التعاقب الوظيفي"},
        ),
        migrations.AddConstraint(
            model_name="employeeskill",
            constraint=models.UniqueConstraint(fields=("employee", "skill"), name="hr_unique_employee_skill"),
        ),
        migrations.AddConstraint(
            model_name="successionplan",
            constraint=models.UniqueConstraint(fields=("position", "nominee"), name="hr_unique_position_successor"),
        ),
    ]
