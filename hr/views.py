import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import (Employee, Department, AttendanceRecord, LeaveRequest, ApprovalRequest, PayrollPeriod, PayrollItem,
                     DepartmentWorkforcePlan, EmployeeRequirement, EmployeeDocument, EmployeeAdvance,\n                     CustodyAsset, CustodyAssignment, PositionAssignment)


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
        "overdue_requirements": overdue_requirements, "missing_documents": missing_documents,
        "expired_documents": expired_documents, "expiring_assets": expiring_assets,
        "uninsured_assigned_assets": uninsured_assigned_assets,
        "active_advance_count": advance_totals["count"] or 0,
        "advance_outstanding": advance_totals["outstanding"] or Decimal("0"),
        "planned_vacancies": planned_vacancies,
        "current_assignments_count": current_assignments.count(),
    }
    return render(request, "hr/management_reports.html", context)
