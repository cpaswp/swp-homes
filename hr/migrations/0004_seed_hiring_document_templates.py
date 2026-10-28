from django.db import migrations

DEFAULTS = [
    ("NID", "صورة بطاقة الرقم القومي سارية", "identity", True, True, 0, 30, "يُراجع الأصل عند الحاجة؛ تأكد من صلاحية البطاقة."),
    ("BIRTH", "شهادة الميلاد", "identity", True, False, 0, 30, "تحدد الشركة هل المطلوب أصل أم صورة طبق الأصل."),
    ("EDU", "المؤهل الدراسي", "education", True, False, 0, 30, "تحدد الوظيفة متطلبات المؤهل والتصديقات."),
    ("MIL", "موقف التجنيد للذكور عند انطباقه", "other", False, False, 0, 30, "يطبق وفق الحالة الشخصية والقواعد السارية."),
    ("CRIM", "صحيفة الحالة الجنائية عند اشتراطها للوظيفة", "other", False, True, 0, 30, "لا تجعلها إلزامية لكل الوظائف دون مراجعة قانونية."),
    ("EXPERIENCE", "شهادات الخبرة السابقة إن وجدت", "experience", False, False, 15, 30, "حسب متطلبات الوظيفة."),
    ("BANK", "بيانات الحساب البنكي لصرف المستحقات", "bank", False, False, 15, 30, "تجمع بالحد الأدنى اللازم وبصلاحيات وصول مناسبة."),
]

def seed_templates(apps, schema_editor):
    Template = apps.get_model("hr", "HiringDocumentTemplate")
    for code, title, category, mandatory, requires_original, due_days, alert_days, notes in DEFAULTS:
        Template.objects.get_or_create(
            code=code,
            defaults={
                "title": title, "category": category, "mandatory": mandatory,
                "applies_to": "all", "due_days_after_hire": due_days,
                "has_expiry": code == "NID", "default_validity_months": None,
                "alert_days_before_expiry": alert_days, "requires_original": requires_original,
                "active": True, "sort_order": 100, "notes": notes,
                "description": "تعريف افتراضي قابل للتعديل حسب لائحة الشركة والقانون الساري.",
            },
        )

def unseed_templates(apps, schema_editor):
    Template = apps.get_model("hr", "HiringDocumentTemplate")
    Template.objects.filter(code__in=[x[0] for x in DEFAULTS]).delete()

class Migration(migrations.Migration):
    dependencies = [("hr", "0003_regulationrule_hiringdocumenttemplate")]
    operations = [migrations.RunPython(seed_templates, unseed_templates)]
