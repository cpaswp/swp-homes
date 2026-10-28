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
