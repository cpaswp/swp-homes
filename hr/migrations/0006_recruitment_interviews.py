# Additive migration: recruitment interview stages and scoring.
import decimal
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0005_recordattachment"),
    ]
    operations = [
        migrations.CreateModel(
            name="RecruitmentInterview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stage", models.CharField(choices=[("hr", "الموارد البشرية"), ("department", "مدير الإدارة"), ("executive", "المدير العام / صاحب الشركة")], max_length=20, verbose_name="مرحلة المقابلة")),
                ("scheduled_at", models.DateTimeField(verbose_name="موعد المقابلة")),
                ("location_or_link", models.CharField(blank=True, max_length=300, verbose_name="المكان أو رابط الاجتماع")),
                ("status", models.CharField(choices=[("scheduled", "مجدولة"), ("completed", "مكتملة"), ("cancelled", "ملغاة")], default="scheduled", max_length=20, verbose_name="الحالة")),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات المقابلة")),
                ("earned_score", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=8, verbose_name="الدرجة المحققة")),
                ("maximum_score", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=8, verbose_name="إجمالي الدرجات")),
                ("score_percent", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=5, verbose_name="النسبة المئوية")),
                ("recommendation", models.CharField(choices=[("pending", "بانتظار التقييم"), ("advance", "ينتقل للمرحلة التالية"), ("hold", "مراجعة إضافية"), ("reject", "غير مناسب")], default="pending", max_length=20, verbose_name="التوصية")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="وقت إكمال التقييم")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interviews", to="hr.recruitmentcandidate", verbose_name="المرشح")),
                ("interviewer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="recruitment_interviews", to="hr.employee", verbose_name="المقابل")),
            ],
            options={"ordering": ["candidate__full_name", "stage", "scheduled_at"], "verbose_name": "مقابلة توظيف", "verbose_name_plural": "جدول مقابلات التوظيف"},
        ),
        migrations.AddConstraint(model_name="recruitmentinterview", constraint=models.UniqueConstraint(fields=("candidate", "stage"), name="hr_unique_candidate_interview_stage")),
        migrations.CreateModel(
            name="InterviewCriterion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=500, verbose_name="السؤال / معيار التقييم")),
                ("maximum_score", models.DecimalField(decimal_places=2, max_digits=6, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))], verbose_name="الدرجة القصوى")),
                ("sort_order", models.PositiveSmallIntegerField(default=1, verbose_name="الترتيب")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="criteria", to="hr.recruitmentinterview", verbose_name="المقابلة")),
            ],
            options={"ordering": ["sort_order", "id"], "verbose_name": "سؤال ومعيار تقييم", "verbose_name_plural": "أسئلة ومعايير المقابلات"},
        ),
        migrations.CreateModel(
            name="InterviewEvaluation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.DecimalField(decimal_places=2, default=decimal.Decimal("0"), max_digits=6, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))], verbose_name="الدرجة الممنوحة")),
                ("answer_notes", models.TextField(blank=True, verbose_name="ملاحظات الإجابة")),
                ("evaluated_at", models.DateTimeField(auto_now=True)),
                ("criterion", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="evaluation", to="hr.interviewcriterion", verbose_name="السؤال")),
            ],
            options={"verbose_name": "تقييم إجابة مقابلة", "verbose_name_plural": "تقييمات إجابات المقابلات"},
        ),
    ]
