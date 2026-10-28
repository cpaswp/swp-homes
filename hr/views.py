import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import (Employee, Department, AttendanceRecord, LeaveRequest, ApprovalRequest, PayrollPeriod, PayrollItem,
                     DepartmentWorkforcePlan, EmployeeRequirement, EmployeeDocument, EmployeeAdvance, CustodyAsset, CustodyAssignment, PositionAssignment, EmployeeContract, EmployeeWarning, EmployeeCompensationItem, DepartmentTarget, TargetAchievement)


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
