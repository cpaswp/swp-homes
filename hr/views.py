import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import (Employee, Department, AttendanceRecord, LeaveRequest, ApprovalRequest, PayrollPeriod, PayrollItem,
                     DepartmentWorkforcePlan, EmployeeRequirement, EmployeeDocument, EmployeeAdvance, CustodyAsset, CustodyAssignment, PositionAssignment, EmployeeContract, EmployeeWarning, EmployeeCompensationItem, DepartmentTarget, TargetAchievement,
                     Skill, EmployeeSkill, CareerDevelopmentPlan, SuccessionPlan, JobPosition)


@login_required
def dashboard(request):
    active = Employee.objects.filter(status=Employee.Status.ACTIVE)
    context = {
        "employee_count": active.count(),
        "department_count": Department.objects.filter(is_active=True).count(),
        "today_attendance": AttendanceRecord.objects.filter(recorded_at__date=timezone.localdate()).count(),
        "pending_leaves": LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count(),
        "pending_approvals": ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING).count(),
        "latest_employees": active.select_related("department", "position").order_by("-created_at")[:8],
        "payroll_totals": PayrollItem.objects.filter(period__status__in=["review", "approved", "paid"]).aggregate(total=Sum("net_salary"))["total"] or Decimal("0.00"),
    }
    return render(request, "hr/dashboard.html", context)


@login_required
def employee_list(request):
    query = request.GET.get("q", "").strip()
    employees = Employee.objects.select_related("department", "position", "manager").all()
    if query:
        from django.db.models import Q
        employees = employees.filter(Q(full_name__icontains=query) | Q(employee_code__icontains=query))
    return render(request, "hr/employee_list.html", {"employees": employees[:500], "query": query})


@login_required
def employee_detail_api(request, employee_id):
    employee = get_object_or_404(Employee.objects.select_related("department", "position", "manager"), pk=employee_id)
    data = {
        "id": employee.pk, "employee_code": employee.employee_code, "full_name": employee.full_name,
        "email": employee.email, "phone": employee.phone, "address": employee.address,
        "date_of_birth": employee.date_of_birth.isoformat() if employee.date_of_birth else "",
        "hire_date": employee.hire_date.isoformat() if employee.hire_date else "",
        "department": employee.department.name if employee.department_id else "",
        "position": employee.position.title if employee.position_id else "",
        "job_description": employee.position.job_description if employee.position_id else "",
        "responsibilities": employee.position.responsibilities if employee.position_id else "",
        "manager": employee.manager.full_name if employee.manager_id else "",
        "documents": [{"title": d.title, "type": d.document_type, "expiry_date": d.expiry_date.isoformat() if d.expiry_date else ""} for d in employee.documents.all()],
    }
    return JsonResponse(data)


@login_required
def org_chart(request):
    employees = list(Employee.objects.filter(status=Employee.Status.ACTIVE).select_related("department", "position", "manager").order_by("full_name"))
    nodes = [{"id": e.pk, "name": e.full_name, "code": e.employee_code, "title": e.position.title if e.position_id else "غير محدد", "department": e.department.name if e.department_id else "غير محدد", "manager_id": e.manager_id} for e in employees]
    return render(request, "hr/org_chart.html", {"nodes": nodes})


@login_required
def payroll_preview(request):
    period = PayrollPeriod.objects.order_by("-start_date").first()
    items = PayrollItem.objects.filter(period=period).select_related("employee") if period else PayrollItem.objects.none()
    totals = items.aggregate(basic=Sum("basic_salary"), allowances=Sum("allowances"), overtime=Sum("overtime"), deductions=Sum("deductions"), tax=Sum("tax_and_insurance"), net=Sum("net_salary"))
    return render(request, "hr/payroll.html", {"period": period, "items": items, "totals": totals})


@login_required
def approval_inbox(request):
    pending = ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING).select_related("requester").prefetch_related("steps")
    return render(request, "hr/approvals.html", {"requests": pending[:200]})



@login_required
def management_reports(request):
    """Cross-module management report sourced from canonical HR records."""
    from django.db.models import Count, Q
    from datetime import date, timedelta

    today = timezone.localdate()
    year = int(request.GET.get("year", today.year)) if request.GET.get("year", "").isdigit() else today.year
    period_id = request.GET.get("period")
    periods = PayrollPeriod.objects.order_by("-start_date")
    selected_period = periods.filter(pk=period_id).first() if period_id and period_id.isdigit() else periods.first()

    active_employees = Employee.objects.filter(status=Employee.Status.ACTIVE)
    headcount_by_department = list(
        Department.objects.filter(is_active=True).annotate(
            active_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE), distinct=True)
        ).order_by("name")
    )
    plans = {p.department_id: p for p in DepartmentWorkforcePlan.objects.filter(fiscal_year=year).select_related("department")}
    for department in headcount_by_department:
        department.workforce_plan = plans.get(department.pk)
        department.headcount_variance = (
            department.active_count - department.workforce_plan.approved_headcount
            if department.workforce_plan else None
        )

    payroll_rows = []
    payroll_totals = {"basic": Decimal("0"), "allowances": Decimal("0"), "overtime": Decimal("0"),
                      "deductions": Decimal("0"), "tax_and_insurance": Decimal("0"), "net": Decimal("0")}
    if selected_period:
        payroll_rows = list(
            PayrollItem.objects.filter(period=selected_period)
            .values("employee__department__name")
            .annotate(employee_count=Count("employee_id", distinct=True),
                      basic=Sum("basic_salary"), allowances=Sum("allowances"), overtime=Sum("overtime"),
                      deductions=Sum("deductions"), tax_and_insurance=Sum("tax_and_insurance"),
                      net=Sum("net_salary"))
            .order_by("employee__department__name")
        )
        for row in payroll_rows:
            for key in ("basic", "allowances", "overtime", "deductions", "tax_and_insurance", "net"):
                row[key] = row[key] or Decimal("0")
                payroll_totals[key] += row[key]

    compensation_pending_rows = []
    compensation_pending_total = Decimal("0")
    if selected_period:
        compensation_pending_rows = list(
            EmployeeCompensationItem.objects.filter(
                approved=True, payroll_item__isnull=True,
                effective_from__lte=selected_period.end_date
            ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=selected_period.start_date))
            .values("employee__department__name", "kind")
            .annotate(amount_total=Sum("amount"), item_count=Count("id"))
            .order_by("employee__department__name", "kind")
        )
        compensation_pending_total = sum((row["amount_total"] or Decimal("0") for row in compensation_pending_rows), Decimal("0"))
    overdue_requirements = EmployeeRequirement.objects.filter(
        status=EmployeeRequirement.Status.REQUIRED, required_by__lt=today
    ).count()
    missing_documents = EmployeeRequirement.objects.filter(
        status__in=[EmployeeRequirement.Status.REQUIRED, EmployeeRequirement.Status.REJECTED]
    ).count()
    expired_documents = EmployeeDocument.objects.filter(expiry_date__lt=today).count()
    expiring_assets = CustodyAsset.objects.filter(
        insured=True, insurance_end__gte=today, insurance_end__lte=today + timedelta(days=30)
    ).count()
    uninsured_assigned_assets = CustodyAsset.objects.filter(status=CustodyAsset.Status.ASSIGNED, insured=False).count()
    active_advances = EmployeeAdvance.objects.filter(
        status__in=[EmployeeAdvance.Status.DISBURSED, EmployeeAdvance.Status.REPAYING]
    )
    advance_totals = active_advances.aggregate(
        outstanding=Sum("remaining_balance"), count=Count("id")
    )
    target_rows = list(DepartmentTarget.objects.filter(fiscal_year=year).select_related("department", "owner").prefetch_related("achievements").order_by("department__name", "name"))
    target_totals = {"target_quantity": Decimal("0"), "actual_quantity": Decimal("0"), "target_value": Decimal("0"), "actual_value": Decimal("0"), "budget_amount": Decimal("0"), "actual_cost": Decimal("0")}
    for target in target_rows:
        achievements = [a for a in target.achievements.all() if a.verified]
        target.actual_quantity = sum((a.actual_quantity for a in achievements), Decimal("0"))
        target.actual_value = sum((a.actual_value for a in achievements), Decimal("0"))
        target.actual_cost = sum((a.actual_cost for a in achievements), Decimal("0"))
        target.quantity_pct = min(target.actual_quantity / target.target_quantity * 100, Decimal("999.99")) if target.target_quantity else Decimal("0")
        target.value_pct = min(target.actual_value / target.target_value * 100, Decimal("999.99")) if target.target_value else Decimal("0")
        target.budget_used_pct = min(target.actual_cost / target.budget_amount * 100, Decimal("999.99")) if target.budget_amount else Decimal("0")
        for key in target_totals:
            target_totals[key] += getattr(target, key)
    target_totals["quantity_pct"] = sum((target.quantity_pct for target in target_rows), Decimal("0")) / len(target_rows) if target_rows else Decimal("0")
    target_totals["value_pct"] = target_totals["actual_value"] / target_totals["target_value"] * 100 if target_totals["target_value"] else Decimal("0")
    target_totals["budget_used_pct"] = target_totals["actual_cost"] / target_totals["budget_amount"] * 100 if target_totals["budget_amount"] else Decimal("0")
    active_contracts = EmployeeContract.objects.filter(status=EmployeeContract.Status.ACTIVE)
    contracts_expiring = active_contracts.filter(end_date__gte=today, end_date__lte=today + timedelta(days=60)).count()
    contracts_expired = EmployeeContract.objects.filter(end_date__lt=today, status=EmployeeContract.Status.ACTIVE).count()
    open_warnings = EmployeeWarning.objects.filter(status__in=[EmployeeWarning.Status.ISSUED, EmployeeWarning.Status.UNDER_REVIEW]).count()
    current_assignments = PositionAssignment.objects.filter(
        status=PositionAssignment.Status.ACTIVE, start_date__lte=today
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
    planned_vacancies = sum(max(plan.approved_headcount - active_employees.filter(department_id=plan.department_id).count(), 0)
                            for plan in plans.values())
    context = {
        "year": year, "periods": periods, "selected_period": selected_period,
        "active_employee_count": active_employees.count(),
        "department_count": Department.objects.filter(is_active=True).count(),
        "headcount_by_department": headcount_by_department,
        "payroll_rows": payroll_rows, "payroll_totals": payroll_totals,
        "compensation_pending_rows": compensation_pending_rows, "compensation_pending_total": compensation_pending_total,
        "overdue_requirements": overdue_requirements, "missing_documents": missing_documents,
        "expired_documents": expired_documents, "expiring_assets": expiring_assets,
        "uninsured_assigned_assets": uninsured_assigned_assets,
        "active_advance_count": advance_totals["count"] or 0,
        "advance_outstanding": advance_totals["outstanding"] or Decimal("0"),
        "planned_vacancies": planned_vacancies,
        "current_assignments_count": current_assignments.count(),
        "target_rows": target_rows, "target_totals": target_totals,
        "contracts_expiring": contracts_expiring, "contracts_expired": contracts_expired,
        "open_warnings": open_warnings,
    }
    return render(request, "hr/management_reports.html", context)


@login_required
def employee_id_card(request, employee_id):
    """Print-ready front/back employee ID card; company data comes from the user's active membership."""
    employee = get_object_or_404(
        Employee.objects.select_related("department", "position"),
        pk=employee_id,
    )
    membership = request.user.company_memberships.select_related("company").first()
    company = membership.company if membership else None
    today = timezone.localdate()
    contract = EmployeeContract.objects.filter(
        employee=employee, status=EmployeeContract.Status.ACTIVE
    ).order_by("-end_date").first()
    valid_until = contract.end_date if contract and contract.end_date else None
    return render(request, "hr/employee_id_card.html", {
        "employee": employee,
        "company": company,
        "valid_until": valid_until,
        "today": today,
    })

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .models import AttendanceDeviceConfiguration

ATTENDANCE_DEVICE_CATALOG = [
    {"manufacturer":"ZKTeco","models":["K40","K50","K60","K70","F18","F19","F22","F28","iClock 680","iClock 880","MB10","MB20","MB2000","SpeedFace-V5L","ProFace X","uFace 800"]},
    {"manufacturer":"Hikvision","models":["DS-K1T804","DS-K1T805","DS-K1T341","DS-K1T671","DS-K1T673","MinMoe series","DS-K1A802"]},
    {"manufacturer":"Suprema","models":["BioStation 2","BioStation 3","BioEntry W2","FaceStation F2","BioLite N2","BioEntry P2"]},
    {"manufacturer":"Anviz","models":["C2 Pro","C2 Slim","W1 Pro","FaceDeep 3","FaceDeep 5","VF30 Pro","EP300 Pro"]},
    {"manufacturer":"HID","models":["Signo 20","Signo 40","iCLASS SE","VertX EVO"]},
    {"manufacturer":"Nitgen","models":["HFDU06","eNBioAccess-T9","NAC-5000"]},
    {"manufacturer":"Matrix COSEC","models":["PATH","ARC DC200P","DOOR FOP","VEGA FAXQ"]},
    {"manufacturer":"Realtime","models":["T52","T53","T55","T60","T62"]},
    {"manufacturer":"Dahua","models":["ASI6213J-MW","ASI7213X-T1","ASI8213Y-V3","ASA1222E"]},
    {"manufacturer":"HFSecurity","models":["HF-A5","HF-FR1500","HF-FR1200"]},
    {"manufacturer":"ESSL","models":["X990","K90 Pro","MB20","FaceX"]},
    {"manufacturer":"Ronald Jack","models":["X628C","U160","F18","iClock 680","K40"]},
    {"manufacturer":"Other / غير ذلك","models":["موديل آخر — إدخال يدوي"]},
]

@login_required
@staff_member_required
def attendance_device_settings(request):
    if request.method == "POST":
        device_id = request.POST.get("device_id", "").strip()
        device = get_object_or_404(AttendanceDeviceConfiguration, pk=device_id) if device_id else AttendanceDeviceConfiguration()
        device.name = request.POST.get("name", "").strip() or "ماكينة الحضور"
        device.manufacturer = request.POST.get("manufacturer", "").strip()
        device.model_name = request.POST.get("model_name", "").strip()
        device.connection_type = request.POST.get("connection_type", "lan")
        device.ip_address = request.POST.get("ip_address", "").strip() or None
        port = request.POST.get("port", "").strip()
        device.port = int(port) if port.isdigit() and 1 <= int(port) <= 65535 else None
        device.site_name = request.POST.get("site_name", "").strip()
        device.protocol_or_software = request.POST.get("protocol_or_software", "").strip()
        device.external_device_id = request.POST.get("external_device_id", "").strip()
        device.enabled = request.POST.get("enabled") == "on"
        device.notes = request.POST.get("notes", "").strip()
        if not device.manufacturer or not device.model_name:
            messages.error(request, "يرجى تحديد الشركة المصنعة وموديل الجهاز.")
        else:
            device.save()
            messages.success(request, "تم حفظ الإعدادات. يلزم تنفيذ واختبار موصل متوافق قبل المزامنة الفعلية.")
            return redirect("hr:attendance_device_settings")
    return render(request, "hr/attendance_device_settings.html", {
        "devices": AttendanceDeviceConfiguration.objects.all(),
        "connection_choices": AttendanceDeviceConfiguration.ConnectionType.choices,
        "catalog": ATTENDANCE_DEVICE_CATALOG,
    })


from .models import RegulationRule, HiringDocumentTemplate

@login_required
@staff_member_required
def compliance_settings(request):
    rules = RegulationRule.objects.filter(active=True)
    documents = HiringDocumentTemplate.objects.filter(active=True)
    return render(request, "hr/compliance_settings.html", {
        "rules": rules, "document_templates": documents,
        "rule_types": RegulationRule.RuleType.choices,
        "document_categories": HiringDocumentTemplate.Category.choices,
    })


from io import BytesIO
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import HttpResponse
from django.utils.dateparse import parse_date, parse_datetime
from openpyxl import Workbook, load_workbook
from .models import RecordAttachment

EXCEL_EXCLUDED_MODELS = {"RecordAttachment"}
def _excel_models():
    return [m for m in apps.get_app_config("hr").get_models()
            if m.__name__ not in EXCEL_EXCLUDED_MODELS and not m._meta.proxy]

def _excel_fields(model):
    fields = []
    for field in model._meta.concrete_fields:
        if field.primary_key or field.auto_created or field.name in ("created_at", "updated_at"):
            continue
        if field.many_to_one or field.one_to_one:
            fields.append((field, field.attname))
        elif field.get_internal_type() in ("FileField", "ImageField"):
            continue
        elif field.editable:
            fields.append((field, field.name))
    return fields

@login_required
@staff_member_required
def excel_center(request):
    model_list = _excel_models()
    selected = request.GET.get("model") or request.POST.get("model") or ""
    model = next((m for m in model_list if m.__name__ == selected), None)
    if request.method == "POST" and request.FILES.get("workbook"):
        if not model:
            messages.error(request, "اختر الجدول المستهدف قبل الاستيراد.")
            return redirect("hr:excel_center")
        uploaded = request.FILES["workbook"]
        if not uploaded.name.lower().endswith(".xlsx"):
            messages.error(request, "يرجى رفع ملف Excel بصيغة .xlsx فقط.")
            return redirect("hr:excel_center")
        try:
            workbook = load_workbook(uploaded, read_only=True, data_only=True)
            sheet = workbook.active
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, None)
            allowed = {attr: field for field, attr in _excel_fields(model)}
            if not headers:
                raise ValueError("الملف فارغ.")
            header_names = [str(x).strip() if x is not None else "" for x in headers]
            unknown = [x for x in header_names if x and x != "id" and x not in allowed]
            if unknown:
                raise ValueError("أعمدة غير معروفة: " + ", ".join(unknown[:8]) + ". صدّر قالب الجدول أولًا.")
            imported = 0
            errors = []
            with transaction.atomic():
                for row_num, values in enumerate(rows, start=2):
                    data = {header_names[i]: values[i] for i in range(min(len(header_names), len(values)))
                            if i < len(header_names) and header_names[i] and values[i] is not None}
                    if not data:
                        continue
                    try:
                        obj_id = data.pop("id", None)
                        if obj_id is not None and model._meta.pk.name not in data:
                            obj = model.objects.select_for_update().get(pk=int(obj_id))
                            for name, value in data.items():
                                field = allowed[name]
                                setattr(obj, field.attname if (field.many_to_one or field.one_to_one) else field.name, _coerce_excel_value(field, value))
                            obj.save()
                        else:
                            kwargs = {}
                            for name, value in data.items():
                                field = allowed[name]
                                kwargs[name] = _coerce_excel_value(field, value)
                            model.objects.create(**kwargs)
                        imported += 1
                    except Exception as exc:
                        errors.append(f"صف {row_num}: {str(exc)[:220]}")
                        if len(errors) >= 20:
                            break
                if errors:
                    transaction.set_rollback(True)
            workbook.close()
            if errors:
                messages.error(request, f"أُلغي الاستيراد بالكامل ولم تُحفظ أي تغييرات. عدد الأخطاء: {len(errors)}. " + " | ".join(errors[:5]))
            else:
                messages.success(request, f"تم استيراد / تحديث {imported} سجلًا بنجاح.")
        except Exception as exc:
            messages.error(request, f"تعذر قراءة الملف: {str(exc)[:300]}")
        return redirect(f"{request.path}?model={selected}")
    return render(request, "hr/excel_center.html", {
        "models": [{"name": m.__name__, "label": m._meta.verbose_name_plural} for m in model_list],
        "selected": selected,
        "selected_label": model._meta.verbose_name_plural if model else "",
        "fields": [{"name": attr, "label": str(f.verbose_name)} for f, attr in _excel_fields(model)] if model else [],
    })

def _coerce_excel_value(field, value):
    if value is None:
        return None
    if field.many_to_one or field.one_to_one:
        return int(value)
    internal = field.get_internal_type()
    if internal in ("DateField",):
        if hasattr(value, "date"):
            return value.date()
        return parse_date(str(value)[:10])
    if internal in ("DateTimeField",):
        if hasattr(value, "isoformat"):
            return value
        return parse_datetime(str(value))
    if internal in ("BooleanField", "NullBooleanField"):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "نعم", "نعم ")
    return value

@login_required
@staff_member_required
def excel_export(request, model_name):
    model = next((m for m in _excel_models() if m.__name__ == model_name), None)
    if not model:
        return HttpResponse("Unknown model", status=404)
    fields = _excel_fields(model)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    headers = ["id"] + [attr for _, attr in fields]
    sheet.append(headers)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for obj in model.objects.all().iterator():
        values = [obj.pk]
        for field, attr in fields:
            value = getattr(obj, attr)
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            elif value is not None and not isinstance(value, (str, int, float, bool)):
                value = str(value)
            values.append(value)
        sheet.append(values)
    for col in sheet.columns:
        letter = col[0].column_letter
        sheet.column_dimensions[letter].width = min(max(max(len(str(cell.value or "")) for cell in col[:100]) + 2, 12), 36)
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{model.__name__.lower()}_export.xlsx"'
    return response

@login_required
@staff_member_required
def record_attachments(request):
    model_list = _excel_models()
    model_name = request.GET.get("model", "")
    object_id = request.GET.get("object_id", "")
    selected_model = next((m for m in model_list if m.__name__ == model_name), None)
    target = None
    if selected_model and object_id:
        target = get_object_or_404(selected_model, pk=object_id)
    if request.method == "POST":
        model_name = request.POST.get("model", "")
        object_id = request.POST.get("object_id", "")
        selected_model = next((m for m in model_list if m.__name__ == model_name), None)
        if not selected_model or not object_id:
            messages.error(request, "حدد نوع السجل ورقمه.")
        elif not request.FILES.get("file"):
            messages.error(request, "اختر ملفًا لإرفاقه.")
        else:
            target = get_object_or_404(selected_model, pk=object_id)
            RecordAttachment.objects.create(
                content_object=target,
                title=request.POST.get("title", "").strip() or request.FILES["file"].name,
                file=request.FILES["file"],
                category=request.POST.get("category", "").strip(),
                issue_date=parse_date(request.POST.get("issue_date", "")) if request.POST.get("issue_date") else None,
                expiry_date=parse_date(request.POST.get("expiry_date", "")) if request.POST.get("expiry_date") else None,
                notes=request.POST.get("notes", "").strip(),
                uploaded_by=request.user,
            )
            messages.success(request, "تم إرفاق المستند بالسجل.")
            return redirect(f"{request.path}?model={model_name}&object_id={object_id}")
    attachments = RecordAttachment.objects.filter(content_type__app_label="hr", content_type__model=selected_model._meta.model_name, object_id=object_id) if target else RecordAttachment.objects.none()
    return render(request, "hr/record_attachments.html", {
        "models": [{"name": m.__name__, "label": m._meta.verbose_name_plural} for m in model_list],
        "selected_model": model_name, "object_id": object_id, "target": target, "attachments": attachments,
    })


@login_required
def recruitment_interviews(request):
    """Interview calendar, weighted scoring, stage progression and candidate ranking."""
    from decimal import Decimal, InvalidOperation
    from django.contrib import messages
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.db.models import Avg, Count
    from django.utils.dateparse import parse_datetime
    from .models import RecruitmentCandidate, RecruitmentInterview, InterviewCriterion, InterviewEvaluation

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "schedule":
            candidate = get_object_or_404(RecruitmentCandidate, pk=request.POST.get("candidate"))
            stage = request.POST.get("stage", "")
            if stage not in RecruitmentInterview.Stage.values:
                messages.error(request, "مرحلة المقابلة غير صحيحة.")
                return redirect("hr:recruitment_interviews")
            # Enforce the interview chain: HR -> department manager -> executive.
            prerequisites = {
                RecruitmentInterview.Stage.DEPARTMENT: RecruitmentInterview.Stage.HR,
                RecruitmentInterview.Stage.EXECUTIVE: RecruitmentInterview.Stage.DEPARTMENT,
            }
            previous_stage = prerequisites.get(stage)
            if previous_stage:
                previous = RecruitmentInterview.objects.filter(
                    candidate=candidate, stage=previous_stage,
                    status=RecruitmentInterview.Status.COMPLETED,
                    recommendation="advance",
                ).first()
                if not previous:
                    messages.error(request, "لا يمكن جدولة هذه المرحلة قبل اجتياز المرحلة السابقة بتوصية انتقال.")
                    return redirect("hr:recruitment_interviews")
            scheduled_at = parse_datetime(request.POST.get("scheduled_at", ""))
            if not scheduled_at:
                messages.error(request, "أدخل موعد مقابلة صحيحًا.")
                return redirect("hr:recruitment_interviews")
            if timezone.is_naive(scheduled_at):
                scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
            interviewer = Employee.objects.filter(pk=request.POST.get("interviewer")).first() if request.POST.get("interviewer") else None
            if RecruitmentInterview.objects.filter(candidate=candidate, stage=stage).exists():
                messages.error(request, "توجد مقابلة مسجلة بالفعل لهذا المرشح في هذه المرحلة.")
                return redirect("hr:recruitment_interviews")
            interview = RecruitmentInterview.objects.create(
                candidate=candidate, stage=stage, interviewer=interviewer,
                scheduled_at=scheduled_at, location_or_link=request.POST.get("location_or_link", "").strip(),
                notes=request.POST.get("notes", "").strip()
            )
            added = 0
            for n in range(1, 11):
                question = request.POST.get(f"question_{n}", "").strip()
                maximum = request.POST.get(f"maximum_{n}", "").strip()
                if not question and not maximum:
                    continue
                try:
                    max_score = Decimal(maximum)
                    if not question or max_score <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    interview.delete()
                    messages.error(request, "لكل سؤال مضاف يجب إدخال نص السؤال ودرجة قصوى أكبر من صفر. لم يتم حفظ المقابلة.")
                    return redirect("hr:recruitment_interviews")
                InterviewCriterion.objects.create(interview=interview, question=question, maximum_score=max_score, sort_order=n)
                added += 1
            if not added:
                interview.delete()
                messages.error(request, "أضف سؤالًا واحدًا على الأقل وحدد درجته قبل حفظ المقابلة.")
                return redirect("hr:recruitment_interviews")
            candidate.stage = RecruitmentCandidate.Stage.INTERVIEW
            candidate.save(update_fields=["stage"])
            messages.success(request, "تمت جدولة المقابلة وحفظ أسئلتها ودرجاتها.")
            return redirect("hr:recruitment_interviews")

        if action == "evaluate":
            interview = get_object_or_404(RecruitmentInterview.objects.select_related("candidate"), pk=request.POST.get("interview"))
            if interview.status != RecruitmentInterview.Status.SCHEDULED:
                messages.error(request, "لا يمكن تعديل تقييم مقابلة غير مجدولة.")
                return redirect("hr:recruitment_interviews")
            criteria = list(interview.criteria.all())
            if not criteria:
                messages.error(request, "لا توجد أسئلة تقييم في هذه المقابلة.")
                return redirect("hr:recruitment_interviews")
            earned = Decimal("0")
            maximum_total = Decimal("0")
            try:
                with transaction.atomic():
                    for criterion in criteria:
                        score = Decimal(request.POST.get(f"score_{criterion.pk}", "0") or "0")
                        if score < 0 or score > criterion.maximum_score:
                            raise ValueError(f"درجة السؤال «{criterion.question}» يجب أن تكون بين صفر و{criterion.maximum_score}.")
                        evaluation, _ = InterviewEvaluation.objects.get_or_create(criterion=criterion)
                        evaluation.score = score
                        evaluation.answer_notes = request.POST.get(f"answer_notes_{criterion.pk}", "").strip()
                        evaluation.full_clean()
                        evaluation.save()
                        earned += score
                        maximum_total += criterion.maximum_score
                    if maximum_total <= 0:
                        raise ValueError("إجمالي الدرجات القصوى يجب أن يكون أكبر من صفر.")
                    interview.earned_score = earned
                    interview.maximum_score = maximum_total
                    interview.score_percent = (earned * Decimal("100") / maximum_total).quantize(Decimal("0.01"))
                    recommendation = request.POST.get("recommendation", "hold")
                    if recommendation not in {"advance", "hold", "reject"}:
                        recommendation = "hold"
                    interview.recommendation = recommendation
                    interview.notes = request.POST.get("notes", interview.notes).strip()
                    interview.status = RecruitmentInterview.Status.COMPLETED
                    interview.completed_at = timezone.now()
                    interview.save()
                    if recommendation == "reject":
                        interview.candidate.stage = RecruitmentCandidate.Stage.REJECTED
                        interview.candidate.save(update_fields=["stage"])
                    elif recommendation == "advance" and interview.stage == RecruitmentInterview.Stage.EXECUTIVE:
                        interview.candidate.stage = RecruitmentCandidate.Stage.OFFER
                        interview.candidate.save(update_fields=["stage"])
            except (ValueError, InvalidOperation, ValidationError) as exc:
                messages.error(request, str(exc))
                return redirect("hr:recruitment_interviews")
            messages.success(request, f"تم حفظ النتيجة: {earned}/{maximum_total} — {interview.score_percent}%.")
            return redirect("hr:recruitment_interviews")

    interviews = RecruitmentInterview.objects.select_related("candidate", "candidate__position", "interviewer").prefetch_related("criteria__evaluation").all()
    candidates = RecruitmentCandidate.objects.exclude(stage__in=[RecruitmentCandidate.Stage.HIRED, RecruitmentCandidate.Stage.REJECTED, RecruitmentCandidate.Stage.WITHDRAWN]).order_by("full_name")
    completed = RecruitmentInterview.objects.filter(status=RecruitmentInterview.Status.COMPLETED)
    ranking = []
    for candidate in RecruitmentCandidate.objects.all():
        rounds = list(completed.filter(candidate=candidate).order_by("stage"))
        if rounds:
            average = sum((r.score_percent for r in rounds), Decimal("0")) / Decimal(len(rounds))
            ranking.append({"candidate": candidate, "rounds": rounds, "average": average.quantize(Decimal("0.01")), "completed_count": len(rounds)})
    ranking.sort(key=lambda row: (row["average"], row["completed_count"]), reverse=True)
    return render(request, "hr/recruitment_interviews.html", {
        "interviews": interviews, "candidates": candidates,
        "employees": Employee.objects.filter(status=Employee.Status.ACTIVE).order_by("full_name"),
        "ranking": ranking,
        "stages": RecruitmentInterview.Stage.choices,
    })



@login_required
def talent_center(request):
    """HR-staff-only talent, skills and succession workspace."""
    from datetime import date
    from django.contrib import messages
    from django.core.exceptions import ValidationError
    from django.db import IntegrityError, transaction

    if not request.user.is_staff:
        return HttpResponseForbidden("Access denied")

    english = request.LANGUAGE_CODE == "en"
    labels = {
        "created": "Saved successfully." if english else "تم الحفظ بنجاح.",
        "invalid": "Please review the submitted values." if english else "يرجى مراجعة البيانات المدخلة.",
        "invalid_dates": "The target date must be on or after the start date." if english else "يجب أن يكون التاريخ المستهدف في تاريخ البداية أو بعده.",
        "duplicate": "This employee/skill or position/nominee pair already exists." if english else "هذا الربط موجود بالفعل.",
    }

    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            with transaction.atomic():
                if action == "skill":
                    name = request.POST.get("name", "").strip()
                    if not name:
                        raise ValueError
                    Skill.objects.create(
                        name=name,
                        category=request.POST.get("category", "").strip(),
                        description=request.POST.get("description", "").strip(),
                    )
                elif action == "assessment":
                    employee = get_object_or_404(Employee, pk=request.POST.get("employee"))
                    skill = get_object_or_404(Skill, pk=request.POST.get("skill"), is_active=True)
                    level = int(request.POST.get("level", "0"))
                    if level not in range(1, 6):
                        raise ValueError
                    EmployeeSkill.objects.update_or_create(
                        employee=employee, skill=skill,
                        defaults={
                            "level": level,
                            "assessed_by": request.user,
                            "evidence": request.POST.get("evidence", "").strip(),
                            "next_review_date": date.fromisoformat(request.POST["next_review_date"]) if request.POST.get("next_review_date") else None,
                        },
                    )
                elif action == "development":
                    employee = get_object_or_404(Employee, pk=request.POST.get("employee"))
                    start = date.fromisoformat(request.POST["start_date"]) if request.POST.get("start_date") else None
                    target = date.fromisoformat(request.POST["target_date"]) if request.POST.get("target_date") else None
                    if start and target and target < start:
                        messages.error(request, labels["invalid_dates"])
                        return redirect("hr:talent_center")
                    title = request.POST.get("title", "").strip()
                    objective = request.POST.get("objective", "").strip()
                    if not title or not objective:
                        raise ValueError
                    CareerDevelopmentPlan.objects.create(
                        employee=employee, title=title, objective=objective,
                        actions=request.POST.get("actions", "").strip(),
                        start_date=start, target_date=target, owner=request.user,
                        status=CareerDevelopmentPlan.Status.ACTIVE,
                    )
                elif action == "succession":
                    position = get_object_or_404(JobPosition, pk=request.POST.get("position"), is_active=True)
                    nominee = get_object_or_404(Employee, pk=request.POST.get("nominee"), status=Employee.Status.ACTIVE)
                    if not request.POST.get("readiness") in dict(SuccessionPlan.Readiness.choices):
                        raise ValueError
                    SuccessionPlan.objects.create(
                        position=position, nominee=nominee,
                        readiness=request.POST["readiness"],
                        development_needs=request.POST.get("development_needs", "").strip(),
                        risk_notes=request.POST.get("risk_notes", "").strip(),
                        reviewed_by=request.user, reviewed_at=date.today(),
                    )
                else:
                    raise ValueError
            messages.success(request, labels["created"])
        except IntegrityError:
            messages.error(request, labels["duplicate"])
        except (ValueError, TypeError, ValidationError, KeyError):
            messages.error(request, labels["invalid"])
        return redirect("hr:talent_center")

    employees = Employee.objects.filter(status=Employee.Status.ACTIVE).select_related("department", "position").order_by("full_name")
    development_plans = list(CareerDevelopmentPlan.objects.select_related("employee", "owner").all()[:100])
    development_status_labels = {
        "draft": "Draft", "active": "In progress", "completed": "Completed", "cancelled": "Cancelled"
    } if english else {
        "draft": "مسودة", "active": "قيد التنفيذ", "completed": "مكتملة", "cancelled": "ملغاة"
    }
    for plan in development_plans:
        plan.status_label = development_status_labels.get(plan.status, plan.status)
    succession_plans = list(SuccessionPlan.objects.filter(is_active=True).select_related("position", "nominee", "reviewed_by").all()[:100])
    readiness_labels = {
        "ready": "Ready now", "one_year": "Ready within one year",
        "two_years": "Ready within two years", "development": "Needs development"
    } if english else dict(SuccessionPlan.Readiness.choices)
    for plan in succession_plans:
        plan.readiness_label = readiness_labels.get(plan.readiness, plan.readiness)
    readiness_choices = [(value, readiness_labels[value]) for value, _label in SuccessionPlan.Readiness.choices]
    return render(request, "hr/talent_center.html", {
        "skills": Skill.objects.filter(is_active=True),
        "assessments": EmployeeSkill.objects.select_related("employee", "skill", "assessed_by").all()[:100],
        "development_plans": development_plans,
        "succession_plans": succession_plans,
        "employees": employees,
        "positions": JobPosition.objects.filter(is_active=True).select_related("department").order_by("title"),
        "readiness_choices": readiness_choices,
        "skill_count": Skill.objects.filter(is_active=True).count(),
        "assessment_count": EmployeeSkill.objects.count(),
        "active_development_count": CareerDevelopmentPlan.objects.filter(status=CareerDevelopmentPlan.Status.ACTIVE).count(),
        "critical_positions_covered": SuccessionPlan.objects.filter(is_active=True).values("position_id").distinct().count(),
        "english": english,
    })
