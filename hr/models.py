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
