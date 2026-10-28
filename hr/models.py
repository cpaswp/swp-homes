from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Department(models.Model):
    code = models.CharField("كود الإدارة", max_length=20, unique=True)
    name = models.CharField("اسم الإدارة", max_length=160)
    parent = models.ForeignKey("self", verbose_name="الإدارة الأعلى", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    manager = models.ForeignKey("Employee", verbose_name="مدير الإدارة", null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_departments")
    is_active = models.BooleanField("نشطة", default=True)
    class Meta:
        ordering = ["name"]
        verbose_name = "إدارة"
        verbose_name_plural = "الإدارات"
    def __str__(self):
        return f"{self.code} — {self.name}"


class JobPosition(models.Model):
    code = models.CharField("كود الوظيفة", max_length=20, unique=True)
    title = models.CharField("المسمى الوظيفي", max_length=160)
    department = models.ForeignKey(Department, verbose_name="الإدارة", on_delete=models.PROTECT, related_name="positions")
    job_description = models.TextField("الوصف الوظيفي", blank=True)
    responsibilities = models.TextField("المهام والمسؤوليات", blank=True)
    is_active = models.BooleanField("نشطة", default=True)
    class Meta:
        ordering = ["title"]
        verbose_name = "وظيفة"
        verbose_name_plural = "الوظائف"
    def __str__(self):
        return f"{self.code} — {self.title}"


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "على رأس العمل"
        LEAVE = "leave", "إجازة"
        SUSPENDED = "suspended", "موقوف"
        TERMINATED = "terminated", "منتهي الخدمة"
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="حساب الدخول", null=True, blank=True, on_delete=models.SET_NULL, related_name="hr_profile")
    employee_code = models.CharField("كود الموظف", max_length=30, unique=True)
    full_name = models.CharField("اسم الموظف", max_length=180)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    phone = models.CharField("الهاتف", max_length=40, blank=True)
    address = models.TextField("العنوان", blank=True)
    date_of_birth = models.DateField("تاريخ الميلاد", null=True, blank=True)
    hire_date = models.DateField("تاريخ التعيين", null=True, blank=True)
    department = models.ForeignKey(Department, verbose_name="الإدارة", null=True, blank=True, on_delete=models.PROTECT, related_name="employees")
    position = models.ForeignKey(JobPosition, verbose_name="الوظيفة", null=True, blank=True, on_delete=models.PROTECT, related_name="employees")
    manager = models.ForeignKey("self", verbose_name="المدير المباشر", null=True, blank=True, on_delete=models.SET_NULL, related_name="direct_reports")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    base_salary = models.DecimalField("الراتب الأساسي", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(0)])
    emergency_contact = models.CharField("جهة اتصال للطوارئ", max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["employee_code"]
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"
    def __str__(self):
        return f"{self.employee_code} — {self.full_name}"
    @property
    def job_title(self):
        return self.position.title if self.position_id else ""


class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, verbose_name="الموظف", on_delete=models.CASCADE, related_name="documents")
    title = models.CharField("اسم المستند", max_length=160)
    document_type = models.CharField("نوع المستند", max_length=60)
    file = models.FileField("الملف", upload_to="hr/employee-documents/%Y/%m/")
    issue_date = models.DateField("تاريخ الإصدار", null=True, blank=True)
    expiry_date = models.DateField("تاريخ الانتهاء", null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "مستند موظف"
        verbose_name_plural = "مستندات الموظفين"


class AttendanceSite(models.Model):
    name = models.CharField("اسم الموقع", max_length=120)
    latitude = models.DecimalField("خط العرض", max_digits=10, decimal_places=7)
    longitude = models.DecimalField("خط الطول", max_digits=10, decimal_places=7)
    radius_meters = models.PositiveSmallIntegerField("نطاق الحضور بالمتر", default=50, validators=[MinValueValidator(1), MaxValueValidator(500)])
    is_active = models.BooleanField("نشط", default=True)
    class Meta:
        verbose_name = "موقع حضور"
        verbose_name_plural = "مواقع الحضور"
    def __str__(self):
        return self.name


class AttendanceRecord(models.Model):
    class Kind(models.TextChoices):
        IN = "in", "حضور"
        OUT = "out", "انصراف"
    employee = models.ForeignKey(Employee, verbose_name="الموظف", on_delete=models.PROTECT, related_name="attendance_records")
    site = models.ForeignKey(AttendanceSite, verbose_name="الموقع", null=True, blank=True, on_delete=models.PROTECT)
    kind = models.CharField("النوع", max_length=3, choices=Kind.choices)
    recorded_at = models.DateTimeField("وقت التسجيل", auto_now_add=True)
    latitude = models.DecimalField("خط العرض المسجل", max_digits=10, decimal_places=7)
    longitude = models.DecimalField("خط الطول المسجل", max_digits=10, decimal_places=7)
    distance_meters = models.DecimalField("المسافة من الموقع", max_digits=8, decimal_places=2, null=True, blank=True)
    face_verified = models.BooleanField("تم التحقق من الوجه", default=False)
    face_provider_ref = models.CharField("مرجع مزود التحقق", max_length=160, blank=True)
    device_fingerprint = models.CharField("معرف الجهاز", max_length=160, blank=True)
    class Meta:
        ordering = ["-recorded_at"]
        verbose_name = "سجل حضور وانصراف"
        verbose_name_plural = "سجلات الحضور والانصراف"


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        PENDING = "pending", "بانتظار الاعتماد"
        APPROVED = "approved", "معتمدة"
        REJECTED = "rejected", "مرفوضة"
        CANCELLED = "cancelled", "ملغاة"
    employee = models.ForeignKey(Employee, verbose_name="الموظف", on_delete=models.PROTECT, related_name="leave_requests")
    leave_type = models.CharField("نوع الإجازة", max_length=50)
    start_date = models.DateField("من")
    end_date = models.DateField("إلى")
    reason = models.TextField("السبب")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب إجازة"
        verbose_name_plural = "طلبات الإجازات"


class ApprovalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "بانتظار الاعتماد"
        APPROVED = "approved", "معتمد"
        REJECTED = "rejected", "مرفوض"
    request_number = models.CharField("رقم الطلب", max_length=30, unique=True)
    requester = models.ForeignKey(Employee, verbose_name="مقدم الطلب", on_delete=models.PROTECT, related_name="submitted_approvals")
    subject = models.CharField("موضوع الطلب", max_length=180)
    details = models.TextField("التفاصيل")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.PENDING)
    current_step = models.PositiveSmallIntegerField("مرحلة الاعتماد الحالية", default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب اعتماد"
        verbose_name_plural = "طلبات الاعتماد"


class ApprovalStep(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "المدير المباشر"
        HR = "hr", "الموارد البشرية"
        GENERAL_MANAGER = "gm", "المدير العام"
    request = models.ForeignKey(ApprovalRequest, verbose_name="الطلب", on_delete=models.CASCADE, related_name="steps")
    sequence = models.PositiveSmallIntegerField("الترتيب")
    role = models.CharField("جهة الاعتماد", max_length=20, choices=Role.choices)
    approver = models.ForeignKey(Employee, verbose_name="المعتمد", null=True, blank=True, on_delete=models.PROTECT, related_name="approval_tasks")
    decision = models.CharField("القرار", max_length=20, choices=[("pending","بانتظار القرار"),("approved","موافقة"),("rejected","رفض")], default="pending")
    comment = models.TextField("ملاحظات", blank=True)
    decided_at = models.DateTimeField("تاريخ القرار", null=True, blank=True)
    class Meta:
        ordering = ["sequence"]
        unique_together = [("request", "sequence")]
        verbose_name = "مرحلة اعتماد"
        verbose_name_plural = "مراحل الاعتماد"


class PayrollPeriod(models.Model):
    name = models.CharField("اسم فترة المرتب", max_length=80)
    start_date = models.DateField("بداية الفترة")
    end_date = models.DateField("نهاية الفترة")
    status = models.CharField("الحالة", max_length=20, choices=[("draft","مسودة"),("review","مراجعة"),("approved","معتمدة"),("paid","تم الصرف")], default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-start_date"]
        verbose_name = "فترة مرتبات"
        verbose_name_plural = "فترات المرتبات"


class PayrollItem(models.Model):
    period = models.ForeignKey(PayrollPeriod, verbose_name="فترة المرتب", on_delete=models.CASCADE, related_name="items")
    employee = models.ForeignKey(Employee, verbose_name="الموظف", on_delete=models.PROTECT, related_name="payroll_items")
    basic_salary = models.DecimalField("الأساسي", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    allowances = models.DecimalField("البدلات", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    overtime = models.DecimalField("الإضافي", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deductions = models.DecimalField("الاستقطاعات", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_and_insurance = models.DecimalField("الضرائب والتأمينات", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_salary = models.DecimalField("صافي المرتب", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    class Meta:
        unique_together = [("period", "employee")]
        verbose_name = "بند مرتب"
        verbose_name_plural = "بنود المرتبات"


# Operational HR modules. All records are linked to the canonical Employee record.
class LeavePolicy(models.Model):
    code = models.CharField("كود نوع الإجازة", max_length=24, unique=True)
    name = models.CharField("نوع الإجازة", max_length=100)
    annual_entitlement_days = models.DecimalField("الرصيد السنوي", max_digits=6, decimal_places=2, default=Decimal("0"))
    carry_forward_limit_days = models.DecimalField("حد الترحيل", max_digits=6, decimal_places=2, default=Decimal("0"))
    paid = models.BooleanField("مدفوعة", default=True)
    requires_document = models.BooleanField("تتطلب مستنداً", default=False)
    active = models.BooleanField("نشطة", default=True)
    class Meta:
        verbose_name = "لائحة نوع إجازة"
        verbose_name_plural = "لوائح أنواع الإجازات"
    def __str__(self):
        return self.name


class EmployeeLeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="leave_balances", verbose_name="الموظف")
    policy = models.ForeignKey(LeavePolicy, on_delete=models.PROTECT, related_name="balances", verbose_name="نوع الإجازة")
    year = models.PositiveSmallIntegerField("السنة")
    opening_days = models.DecimalField("رصيد أول المدة", max_digits=7, decimal_places=2, default=Decimal("0"))
    accrued_days = models.DecimalField("المستحق خلال السنة", max_digits=7, decimal_places=2, default=Decimal("0"))
    used_days = models.DecimalField("المستخدم", max_digits=7, decimal_places=2, default=Decimal("0"))
    adjusted_days = models.DecimalField("تسويات", max_digits=7, decimal_places=2, default=Decimal("0"))
    class Meta:
        unique_together = [("employee", "policy", "year")]
        verbose_name = "رصيد إجازة موظف"
        verbose_name_plural = "أرصدة إجازات الموظفين"
    @property
    def remaining_days(self):
        return self.opening_days + self.accrued_days + self.adjusted_days - self.used_days


class RecruitmentCandidate(models.Model):
    class Stage(models.TextChoices):
        NEW = "new", "جديد"
        SCREENING = "screening", "فرز"
        INTERVIEW = "interview", "مقابلة"
        OFFER = "offer", "عرض وظيفي"
        HIRED = "hired", "تم التعيين"
        REJECTED = "rejected", "مرفوض"
        WITHDRAWN = "withdrawn", "انسحب"
    full_name = models.CharField("اسم المرشح", max_length=180)
    email = models.EmailField("البريد", blank=True)
    phone = models.CharField("الهاتف", max_length=40, blank=True)
    position = models.ForeignKey(JobPosition, on_delete=models.PROTECT, related_name="candidates", null=True, blank=True, verbose_name="الوظيفة المطلوبة")
    source = models.CharField("مصدر الاستقطاب", max_length=100, blank=True)
    applied_at = models.DateField("تاريخ التقديم", null=True, blank=True)
    stage = models.CharField("المرحلة", max_length=20, choices=Stage.choices, default=Stage.NEW)
    expected_salary = models.DecimalField("الراتب المتوقع", max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    hired_employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="recruitment_source", null=True, blank=True, verbose_name="ملف الموظف الناتج")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "مرشح توظيف"
        verbose_name_plural = "سجل استقطاب الموظفين"


class MissionRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        PENDING = "pending", "بانتظار الاعتماد"
        APPROVED = "approved", "معتمدة"
        REJECTED = "rejected", "مرفوضة"
        COMPLETED = "completed", "منتهية"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="missions", verbose_name="الموظف")
    destination = models.CharField("جهة المأمورية", max_length=180)
    purpose = models.TextField("الغرض")
    start_at = models.DateTimeField("بداية المأمورية")
    end_at = models.DateTimeField("نهاية المأمورية")
    transport_allowance = models.DecimalField("بدل انتقال", max_digits=12, decimal_places=2, default=Decimal("0"))
    per_diem = models.DecimalField("بدل يومي", max_digits=12, decimal_places=2, default=Decimal("0"))
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="missions", verbose_name="طلب الاعتماد")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-start_at"]
        verbose_name = "مأمورية"
        verbose_name_plural = "المأموريات"


class AttendanceException(models.Model):
    class Kind(models.TextChoices):
        LATE = "late", "تأخير"
        EARLY = "early", "انصراف مبكر"
        ABSENCE = "absence", "غياب"
        OVERTIME = "overtime", "إضافي"
        MANUAL = "manual", "تعديل يدوي"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="attendance_exceptions", verbose_name="الموظف")
    work_date = models.DateField("تاريخ العمل")
    kind = models.CharField("النوع", max_length=20, choices=Kind.choices)
    minutes = models.PositiveIntegerField("الدقائق", default=0)
    reason = models.TextField("السبب", blank=True)
    excused = models.BooleanField("مبرر", default=False)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_exceptions", verbose_name="طلب الاعتماد")
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_exceptions", verbose_name="بند المرتب المرتبط")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "استثناء حضور"
        verbose_name_plural = "التأخيرات والانصراف المبكر والغياب"


class EmployeeInsuranceRecord(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.PROTECT, related_name="insurance_record", verbose_name="الموظف")
    insurance_number = models.CharField("الرقم التأميني", max_length=40, blank=True, db_index=True)
    establishment_number = models.CharField("رقم المنشأة التأمينية", max_length=40, blank=True)
    insured_salary = models.DecimalField("أجر الاشتراك التأميني", max_digits=12, decimal_places=2, default=Decimal("0"))
    start_date = models.DateField("تاريخ بدء التأمين", null=True, blank=True)
    end_date = models.DateField("تاريخ انتهاء التأمين", null=True, blank=True)
    office = models.CharField("مكتب التأمينات", max_length=160, blank=True)
    status = models.CharField("حالة التأمين", max_length=40, default="pending")
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        verbose_name = "ملف التأمينات الاجتماعية"
        verbose_name_plural = "ملفات التأمينات الاجتماعية"


class InsuranceFormRecord(models.Model):
    class FormType(models.TextChoices):
        S1 = "s1", "نموذج 1 — اشتراك مؤمن عليه"
        S2 = "s2", "نموذج 2 — تحديث بيانات/أجور (تحقق من النموذج الرسمي الساري)"
        S6 = "s6", "نموذج 6 — إنهاء اشتراك"
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        PREPARED = "prepared", "مجهز"
        SUBMITTED = "submitted", "تم التقديم"
        ACCEPTED = "accepted", "مقبول"
        REJECTED = "rejected", "مرفوض"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="insurance_forms", verbose_name="الموظف")
    form_type = models.CharField("نوع النموذج", max_length=8, choices=FormType.choices)
    reference_number = models.CharField("رقم المرجع", max_length=80, blank=True)
    effective_date = models.DateField("تاريخ السريان")
    submitted_at = models.DateField("تاريخ التقديم", null=True, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    attachment = models.FileField("نسخة النموذج/الإيصال", upload_to="hr/insurance-forms/%Y/%m/", blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-effective_date"]
        verbose_name = "معاملة نموذج تأمينات"
        verbose_name_plural = "نماذج التأمينات"


class SalaryChange(models.Model):
    class ChangeType(models.TextChoices):
        ANNUAL = "annual", "زيادة سنوية"
        EXCEPTIONAL = "exceptional", "زيادة استثنائية"
        PROMOTION = "promotion", "ترقية"
        ALLOWANCE = "allowance", "تعديل بدل"
        CORRECTION = "correction", "تصحيح"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="salary_changes", verbose_name="الموظف")
    change_type = models.CharField("نوع الحركة", max_length=20, choices=ChangeType.choices)
    effective_date = models.DateField("تاريخ السريان")
    old_salary = models.DecimalField("الراتب السابق", max_digits=12, decimal_places=2)
    new_salary = models.DecimalField("الراتب الجديد", max_digits=12, decimal_places=2)
    percentage = models.DecimalField("نسبة الزيادة %", max_digits=7, decimal_places=3, default=Decimal("0"))
    reason = models.TextField("المبرر")
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, related_name="salary_changes", verbose_name="طلب الاعتماد")
    applied = models.BooleanField("تم تطبيق الحركة", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-effective_date"]
        verbose_name = "حركة راتب/ترقية"
        verbose_name_plural = "العلاوات والزيادات والترقيات"


class PayrollComponent(models.Model):
    class Kind(models.TextChoices):
        EARNING = "earning", "استحقاق"
        DEDUCTION = "deduction", "استقطاع"
        TAX = "tax", "ضريبة"
        INSURANCE = "insurance", "تأمينات"
        PENALTY = "penalty", "جزاء"
    code = models.CharField("الكود", max_length=30, unique=True)
    name = models.CharField("اسم البند", max_length=120)
    kind = models.CharField("نوع البند", max_length=20, choices=Kind.choices)
    taxable = models.BooleanField("خاضع للضريبة", default=True)
    insurable = models.BooleanField("خاضع للتأمينات", default=True)
    recurring = models.BooleanField("متكرر", default=False)
    active = models.BooleanField("نشط", default=True)
    class Meta:
        verbose_name = "بند مرتب"
        verbose_name_plural = "تعريف بنود المرتبات"
    def __str__(self):
        return f"{self.code} — {self.name}"


class EmployeeDeduction(models.Model):
    class Kind(models.TextChoices):
        PENALTY = "penalty", "جزاء"
        TAX = "tax", "كسب عمل"
        INSURANCE = "insurance", "تأمينات"
        ABSENCE = "absence", "غياب"
        LATE = "late", "تأخير/انصراف مبكر"
        ADVANCE = "advance", "سلفة"
        OTHER = "other", "أخرى"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="deductions", verbose_name="الموظف")
    component = models.ForeignKey(PayrollComponent, on_delete=models.PROTECT, related_name="deductions", null=True, blank=True, verbose_name="بند المرتب")
    kind = models.CharField("نوع الاستقطاع", max_length=20, choices=Kind.choices)
    amount = models.DecimalField("القيمة", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    effective_date = models.DateField("تاريخ السريان")
    installments = models.PositiveSmallIntegerField("عدد الأقساط", default=1)
    remaining_installments = models.PositiveSmallIntegerField("الأقساط المتبقية", default=1)
    reason = models.TextField("السبب")
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, related_name="deductions", null=True, blank=True, verbose_name="طلب الاعتماد")
    active = models.BooleanField("نشط", default=True)
    class Meta:
        verbose_name = "استقطاع موظف"
        verbose_name_plural = "استقطاعات الموظفين"


class InternalRegulation(models.Model):
    code = models.CharField("كود اللائحة/البند", max_length=40, unique=True)
    title = models.CharField("اسم البند", max_length=180)
    category = models.CharField("التصنيف", max_length=80)
    description = models.TextField("التفاصيل")
    effective_from = models.DateField("ساري من")
    effective_to = models.DateField("ساري حتى", null=True, blank=True)
    active = models.BooleanField("ساري", default=True)
    document = models.FileField("نسخة اللائحة", upload_to="hr/regulations/%Y/%m/", blank=True)
    class Meta:
        ordering = ["category", "code"]
        verbose_name = "بند لائحة داخلية"
        verbose_name_plural = "اللائحة الداخلية وبنودها"


class DisciplinaryAction(models.Model):
    class Status(models.TextChoices):
        INVESTIGATION = "investigation", "قيد التحقيق"
        PROPOSED = "proposed", "جزاء مقترح"
        APPROVED = "approved", "معتمد"
        APPLIED = "applied", "تم التطبيق"
        CANCELLED = "cancelled", "ملغى"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="disciplinary_actions", verbose_name="الموظف")
    regulation = models.ForeignKey(InternalRegulation, on_delete=models.PROTECT, related_name="disciplinary_actions", verbose_name="بند اللائحة")
    incident_date = models.DateField("تاريخ الواقعة")
    description = models.TextField("وصف الواقعة")
    investigation_notes = models.TextField("محضر التحقيق/رد الموظف", blank=True)
    proposed_action = models.CharField("الجزاء المقترح", max_length=180)
    deduction_amount = models.DecimalField("قيمة الخصم", max_digits=12, decimal_places=2, default=Decimal("0"))
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.INVESTIGATION)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, related_name="disciplinary_actions", null=True, blank=True, verbose_name="طلب الاعتماد")
    payroll_deduction = models.ForeignKey(EmployeeDeduction, on_delete=models.SET_NULL, related_name="disciplinary_actions", null=True, blank=True, verbose_name="الاستقطاع الناتج")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-incident_date"]
        verbose_name = "إجراء تأديبي"
        verbose_name_plural = "الجزاءات والتحقيقات"


class KPI(models.Model):
    code = models.CharField("كود المؤشر", max_length=30, unique=True)
    name = models.CharField("اسم المؤشر", max_length=160)
    description = models.TextField("الوصف", blank=True)
    weight_percent = models.DecimalField("الوزن النسبي %", max_digits=5, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    active = models.BooleanField("نشط", default=True)
    class Meta:
        verbose_name = "مؤشر أداء"
        verbose_name_plural = "مؤشرات الأداء KPI"
    def __str__(self):
        return self.name


class PerformanceReview(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="performance_reviews", verbose_name="الموظف")
    reviewer = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="reviews_given", verbose_name="المقيّم")
    period_start = models.DateField("بداية فترة التقييم")
    period_end = models.DateField("نهاية فترة التقييم")
    performance_score = models.DecimalField("الأداء", max_digits=5, decimal_places=2, default=Decimal("0"))
    behavior_score = models.DecimalField("السلوك", max_digits=5, decimal_places=2, default=Decimal("0"))
    appearance_score = models.DecimalField("المظهر المهني", max_digits=5, decimal_places=2, default=Decimal("0"))
    commitment_score = models.DecimalField("الالتزام", max_digits=5, decimal_places=2, default=Decimal("0"))
    overall_score = models.DecimalField("التقييم الإجمالي", max_digits=5, decimal_places=2, default=Decimal("0"))
    strengths = models.TextField("نقاط القوة", blank=True)
    improvement_plan = models.TextField("خطة التحسين", blank=True)
    status = models.CharField("الحالة", max_length=20, default="draft")
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="performance_reviews", verbose_name="طلب الاعتماد")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-period_end"]
        verbose_name = "تقييم موظف"
        verbose_name_plural = "تقييمات الأداء والسلوك"


class TrainingCourse(models.Model):
    code = models.CharField("كود الدورة", max_length=30, unique=True)
    title = models.CharField("اسم البرنامج التدريبي", max_length=180)
    provider = models.CharField("جهة التدريب", max_length=180, blank=True)
    skills = models.TextField("المهارات المستهدفة", blank=True)
    start_date = models.DateField("بداية التدريب", null=True, blank=True)
    end_date = models.DateField("نهاية التدريب", null=True, blank=True)
    cost = models.DecimalField("التكلفة", max_digits=12, decimal_places=2, default=Decimal("0"))
    active = models.BooleanField("نشط", default=True)
    class Meta:
        verbose_name = "برنامج تدريبي"
        verbose_name_plural = "برامج تطوير الموظفين"


class EmployeeTraining(models.Model):
    class Status(models.TextChoices):
        NOMINATED = "nominated", "مرشح"
        APPROVED = "approved", "معتمد"
        IN_PROGRESS = "in_progress", "قيد التنفيذ"
        COMPLETED = "completed", "مكتمل"
        FAILED = "failed", "لم يجتز"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="trainings", verbose_name="الموظف")
    course = models.ForeignKey(TrainingCourse, on_delete=models.PROTECT, related_name="participants", verbose_name="البرنامج")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.NOMINATED)
    score = models.DecimalField("النتيجة", max_digits=5, decimal_places=2, null=True, blank=True)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="training_enrollments", verbose_name="طلب الاعتماد")
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        unique_together = [("employee", "course")]
        verbose_name = "التحاق بتدريب"
        verbose_name_plural = "سجل تدريب الموظفين"


class EmployeeAuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المستخدم المنفذ")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="audit_events", verbose_name="الموظف")
    event_type = models.CharField("نوع الحركة", max_length=80)
    object_type = models.CharField("نوع السجل", max_length=80, blank=True)
    object_id = models.CharField("رقم السجل", max_length=80, blank=True)
    before_data = models.JSONField("قبل التعديل", default=dict, blank=True)
    after_data = models.JSONField("بعد التعديل", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "سجل تدقيق موظف"
        verbose_name_plural = "سجل تدقيق الموارد البشرية"


class EmployeeRequirement(models.Model):
    class Status(models.TextChoices):
        REQUIRED = "required", "مطلوب"
        SUBMITTED = "submitted", "تم التسليم"
        VERIFIED = "verified", "تمت المراجعة"
        REJECTED = "rejected", "مرفوض"
        WAIVED = "waived", "معفى"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="requirements", verbose_name="الموظف")
    title = models.CharField("المطلوب من الموظف", max_length=180)
    category = models.CharField("التصنيف", max_length=80, blank=True)
    required_by = models.DateField("الموعد النهائي", null=True, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.REQUIRED)
    submitted_at = models.DateField("تاريخ التسليم", null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_employee_requirements", verbose_name="راجع المستند")
    verified_at = models.DateTimeField("تاريخ المراجعة", null=True, blank=True)
    document = models.ForeignKey(EmployeeDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="requirement_evidence", verbose_name="المستند المرفق")
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        ordering = ["status", "required_by"]
        verbose_name = "مطلوب من موظف"
        verbose_name_plural = "متطلبات ومستندات الموظفين"


class PositionAssignment(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "مخطط"
        ACTIVE = "active", "ساري"
        ENDED = "ended", "منتهي"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="position_assignments", verbose_name="الموظف")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="assignments", verbose_name="الإدارة")
    position = models.ForeignKey(JobPosition, on_delete=models.PROTECT, related_name="assignments", verbose_name="الوظيفة")
    start_date = models.DateField("من تاريخ")
    end_date = models.DateField("حتى تاريخ", null=True, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.PLANNED)
    acting_for = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="acting_substitutes", verbose_name="بديل عن الموظف")
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="position_assignments", verbose_name="طلب الاعتماد")
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        ordering = ["-start_date"]
        verbose_name = "تسكين/تكليف وظيفي"
        verbose_name_plural = "التسكين والتكليف والبدائل"


class DepartmentWorkforcePlan(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="workforce_plans", verbose_name="الإدارة")
    fiscal_year = models.PositiveSmallIntegerField("السنة المالية")
    approved_headcount = models.PositiveIntegerField("العدد المعتمد")
    minimum_headcount = models.PositiveIntegerField("الحد الأدنى", default=0)
    maximum_headcount = models.PositiveIntegerField("الحد الأقصى")
    approved_annual_payroll_budget = models.DecimalField("موازنة المرتبات السنوية", max_digits=15, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    approved_monthly_payroll_budget = models.DecimalField("موازنة المرتبات الشهرية", max_digits=15, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_workforce_plans", verbose_name="اعتمدت بواسطة")
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="workforce_plans", verbose_name="طلب الاعتماد")
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [("department", "fiscal_year")]
        ordering = ["-fiscal_year", "department__name"]
        verbose_name = "خطة قوى عاملة وموازنة"
        verbose_name_plural = "حدود وموازنة الإدارات"


class AdvancePolicy(models.Model):
    name = models.CharField("اسم سياسة السلف", max_length=120)
    maximum_amount = models.DecimalField("الحد الأقصى للسلفة", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    maximum_salary_multiple = models.DecimalField("مضاعف الراتب الأقصى", max_digits=6, decimal_places=2, default=Decimal("1"), validators=[MinValueValidator(0)])
    maximum_active_advances = models.PositiveSmallIntegerField("أقصى عدد سلف قائمة", default=1)
    maximum_deduction_percent = models.DecimalField("أقصى نسبة استقطاع شهري %", max_digits=5, decimal_places=2, default=Decimal("25"), validators=[MinValueValidator(0), MaxValueValidator(100)])
    minimum_service_months = models.PositiveSmallIntegerField("مدة الخدمة المطلوبة بالشهور", default=0)
    active = models.BooleanField("نشطة", default=True)
    effective_from = models.DateField("سارية من")
    effective_to = models.DateField("سارية حتى", null=True, blank=True)
    class Meta:
        verbose_name = "سياسة سلف"
        verbose_name_plural = "سياسات وحدود السلف"


class EmployeeAdvance(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        PENDING = "pending", "بانتظار الاعتماد"
        APPROVED = "approved", "معتمدة"
        DISBURSED = "disbursed", "تم الصرف"
        REPAYING = "repaying", "قيد السداد"
        SETTLED = "settled", "مسددة"
        REJECTED = "rejected", "مرفوضة"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="advances", verbose_name="الموظف")
    policy = models.ForeignKey(AdvancePolicy, on_delete=models.PROTECT, related_name="requests", verbose_name="سياسة السلف")
    request_date = models.DateField("تاريخ الطلب")
    requested_amount = models.DecimalField("المبلغ المطلوب", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    approved_amount = models.DecimalField("المبلغ المعتمد", max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    installment_amount = models.DecimalField("قيمة القسط", max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    installments_count = models.PositiveSmallIntegerField("عدد الأقساط", default=1)
    remaining_balance = models.DecimalField("الرصيد المتبقي", max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_advances", verbose_name="طلب الاعتماد")
    payroll_deduction = models.ForeignKey(EmployeeDeduction, on_delete=models.SET_NULL, null=True, blank=True, related_name="advance_requests", verbose_name="استقطاع السداد")
    disbursed_at = models.DateField("تاريخ الصرف", null=True, blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-request_date"]
        verbose_name = "سلفة موظف"
        verbose_name_plural = "طلبات السلف وسدادها"


class CustodyAsset(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "متاح"
        ASSIGNED = "assigned", "بعهدة موظف"
        MAINTENANCE = "maintenance", "صيانة"
        LOST = "lost", "مفقود"
        RETIRED = "retired", "مستبعد"
    asset_code = models.CharField("كود العهدة", max_length=40, unique=True)
    name = models.CharField("اسم العهدة", max_length=180)
    category = models.CharField("التصنيف", max_length=80)
    serial_number = models.CharField("الرقم المسلسل", max_length=120, blank=True)
    acquisition_date = models.DateField("تاريخ الشراء", null=True, blank=True)
    acquisition_cost = models.DecimalField("تكلفة الشراء", max_digits=14, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    current_value = models.DecimalField("القيمة الدفترية الحالية", max_digits=14, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    insured = models.BooleanField("مؤمن عليها", default=False)
    insurance_policy_number = models.CharField("رقم وثيقة التأمين", max_length=100, blank=True)
    insurer = models.CharField("شركة التأمين", max_length=160, blank=True)
    insurance_start = models.DateField("بداية التأمين", null=True, blank=True)
    insurance_end = models.DateField("نهاية التأمين", null=True, blank=True)
    insured_value = models.DecimalField("القيمة المؤمن عليها", max_digits=14, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        ordering = ["asset_code"]
        verbose_name = "عهدة/أصل"
        verbose_name_plural = "سجل العهد والأصول"


class CustodyAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "بعهدة الموظف"
        RETURNED = "returned", "تم الرد"
        LOST = "lost", "مفقود"
        DAMAGED = "damaged", "تالف"
    asset = models.ForeignKey(CustodyAsset, on_delete=models.PROTECT, related_name="assignments", verbose_name="العهدة")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="custody_assignments", verbose_name="الموظف")
    issued_at = models.DateField("تاريخ التسليم")
    expected_return = models.DateField("تاريخ الرد المتوقع", null=True, blank=True)
    returned_at = models.DateField("تاريخ الرد الفعلي", null=True, blank=True)
    condition_out = models.CharField("حالة التسليم", max_length=120, blank=True)
    condition_in = models.CharField("حالة الاستلام", max_length=120, blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    custody_document = models.FileField("محضر تسليم/استلام", upload_to="hr/custody/%Y/%m/", blank=True)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="custody_assignments", verbose_name="طلب الاعتماد")
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "تسليم عهدة"
        verbose_name_plural = "حركة عهد الموظفين"


class EmployeeContract(models.Model):
    class ContractType(models.TextChoices):
        PERMANENT = "permanent", "دائم"
        FIXED_TERM = "fixed_term", "محدد المدة"
        PROBATION = "probation", "تحت الاختبار"
        PART_TIME = "part_time", "دوام جزئي"
        TEMPORARY = "temporary", "مؤقت"
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        ACTIVE = "active", "ساري"
        EXPIRED = "expired", "منتهي"
        TERMINATED = "terminated", "منهى"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="contracts", verbose_name="الموظف")
    contract_number = models.CharField("رقم العقد", max_length=60, unique=True)
    contract_type = models.CharField("نوع العقد", max_length=20, choices=ContractType.choices)
    start_date = models.DateField("تاريخ البداية")
    end_date = models.DateField("تاريخ النهاية", null=True, blank=True)
    probation_end_date = models.DateField("نهاية الاختبار", null=True, blank=True)
    notice_days = models.PositiveSmallIntegerField("مدة الإخطار بالأيام", default=30)
    agreed_basic_salary = models.DecimalField("الأساسي المتفق عليه", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    currency = models.CharField("العملة", max_length=3, default="EGP")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    signed_document = models.FileField("نسخة العقد الموقعة", upload_to="hr/contracts/%Y/%m/", blank=True)
    renewed_from = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="renewals", verbose_name="العقد السابق")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_hr_contracts", verbose_name="اعتمد بواسطة")
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-start_date"]
        verbose_name = "عقد موظف"
        verbose_name_plural = "عقود الموظفين"


class EmployeeWarning(models.Model):
    class Severity(models.TextChoices):
        NOTICE = "notice", "تنبيه"
        FIRST = "first", "إنذار أول"
        FINAL = "final", "إنذار نهائي"
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        UNDER_REVIEW = "under_review", "قيد المراجعة"
        ISSUED = "issued", "صادر"
        ACKNOWLEDGED = "acknowledged", "تم الإقرار بالاستلام"
        APPEALED = "appealed", "تم التظلم"
        CANCELLED = "cancelled", "ملغى"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="warnings", verbose_name="الموظف")
    warning_number = models.CharField("رقم الإنذار", max_length=60, unique=True)
    incident_date = models.DateField("تاريخ الواقعة")
    issued_date = models.DateField("تاريخ الإصدار", null=True, blank=True)
    severity = models.CharField("درجة الإنذار", max_length=20, choices=Severity.choices)
    reason = models.TextField("سبب الإنذار")
    policy_reference = models.CharField("مرجع اللائحة", max_length=160, blank=True)
    corrective_action = models.TextField("الإجراء التصحيحي المطلوب", blank=True)
    response_deadline = models.DateField("موعد الرد", null=True, blank=True)
    employee_response = models.TextField("رد الموظف", blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_employee_warnings", verbose_name="صدر بواسطة")
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_warnings", verbose_name="طلب الاعتماد")
    attachment = models.FileField("مرفق/محضر", upload_to="hr/warnings/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-incident_date"]
        verbose_name = "إنذار موظف"
        verbose_name_plural = "إنذارات الموظفين"


class EmployeeCompensationItem(models.Model):
    class Kind(models.TextChoices):
        ALLOWANCE = "allowance", "بدل"
        BONUS = "bonus", "مكافأة"
        COMMISSION = "commission", "عمولة"
        OVERTIME = "overtime", "إضافي"
        DEDUCTION = "deduction", "استقطاع"
        PENALTY = "penalty", "جزاء مالي"
        EMPLOYEE_INSURANCE = "employee_insurance", "حصة الموظف بالتأمينات"
        TAX = "tax", "ضريبة"
        ADVANCE_REPAYMENT = "advance_repayment", "قسط سلفة"
        OTHER = "other", "أخرى"
    class Frequency(models.TextChoices):
        ONE_TIME = "one_time", "مرة واحدة"
        MONTHLY = "monthly", "شهري"
        QUARTERLY = "quarterly", "ربع سنوي"
        ANNUAL = "annual", "سنوي"
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="compensation_items", verbose_name="الموظف")
    kind = models.CharField("نوع البند", max_length=30, choices=Kind.choices)
    name = models.CharField("اسم البند", max_length=160)
    amount = models.DecimalField("المبلغ", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    frequency = models.CharField("التكرار", max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    effective_from = models.DateField("ساري من")
    effective_to = models.DateField("ساري حتى", null=True, blank=True)
    taxable = models.BooleanField("خاضع للضريبة", default=True)
    insured = models.BooleanField("خاضع للتأمينات", default=True)
    approved = models.BooleanField("معتمد", default=False)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="compensation_items", verbose_name="طلب الاعتماد")
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="compensation_sources", verbose_name="بند المرتب الناتج")
    notes = models.TextField("ملاحظات", blank=True)
    class Meta:
        ordering = ["employee", "kind", "effective_from"]
        verbose_name = "استحقاق/استقطاع موظف"
        verbose_name_plural = "بدلات ومكافآت واستحقاقات واستبعادات الموظفين"


class DepartmentTarget(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        APPROVED = "approved", "معتمد"
        ACTIVE = "active", "قيد التنفيذ"
        CLOSED = "closed", "مغلق"
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="targets", verbose_name="الإدارة")
    code = models.CharField("كود المستهدف", max_length=40)
    name = models.CharField("المستهدف", max_length=180)
    description = models.TextField("الوصف/معيار القياس", blank=True)
    owner = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="owned_targets", verbose_name="المسؤول")
    fiscal_year = models.PositiveSmallIntegerField("السنة المالية")
    unit = models.CharField("وحدة القياس", max_length=50, default="وحدة")
    target_quantity = models.DecimalField("الكمية المستهدفة", max_digits=15, decimal_places=3, default=Decimal("0"), validators=[MinValueValidator(0)])
    target_value = models.DecimalField("القيمة المستهدفة", max_digits=15, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    budget_amount = models.DecimalField("الموازنة المعتمدة", max_digits=15, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    start_date = models.DateField("بداية المستهدف")
    end_date = models.DateField("نهاية المستهدف")
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.DRAFT)
    approval_request = models.ForeignKey(ApprovalRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="department_targets", verbose_name="طلب الاعتماد")
    class Meta:
        unique_together = [("department", "code", "fiscal_year")]
        ordering = ["department__name", "fiscal_year", "name"]
        verbose_name = "مستهدف إدارة"
        verbose_name_plural = "مستهدفات الإدارات وموازناتها"


class TargetAchievement(models.Model):
    target = models.ForeignKey(DepartmentTarget, on_delete=models.PROTECT, related_name="achievements", verbose_name="المستهدف")
    period_start = models.DateField("بداية الفترة")
    period_end = models.DateField("نهاية الفترة")
    actual_quantity = models.DecimalField("الكمية المنجزة", max_digits=15, decimal_places=3, default=Decimal("0"), validators=[MinValueValidator(0)])
    actual_value = models.DecimalField("القيمة المنجزة", max_digits=15, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    actual_cost = models.DecimalField("التكلفة الفعلية", max_digits=15, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)])
    source_reference = models.CharField("مرجع المصدر", max_length=160, blank=True)
    verified = models.BooleanField("تم التحقق", default=False)
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [("target", "period_start", "period_end")]
        ordering = ["period_start"]
        verbose_name = "إنجاز مستهدف"
        verbose_name_plural = "الإنجاز الفعلي للمستهدفات"
