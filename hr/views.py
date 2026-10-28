import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET
from .models import Employee, Department, AttendanceRecord, LeaveRequest, ApprovalRequest, PayrollPeriod, PayrollItem


@login_required
def dashboard(request):
    active = Employee.objects.filter(status=Employee.Status.ACTIVE)
    context = {
        "employee_count": active.count(),
        "department_count": Department.objects.filter(is_active=True).count(),
        "today_attendance": AttendanceRecord.objects.filter(recorded_at__date=__import__("django").utils.timezone.localdate()).count(),
        "pending_leaves": LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count(),
        "pending_approvals": ApprovalRequest.objects.filter(status=ApprovalRequest.Status.PENDING).count(),
        "latest_employees": active.select_related("department", "position").order_by("-created_at")[:8],
        "payroll_totals": PayrollItem.objects.filter(period__status__in=["review","approved","paid"]).aggregate(total=Sum("net_salary"))["total"] or Decimal("0.00"),
    }
    return render(request, "hr/dashboard.html", context)


@login_required
def employee_list(request):
    employees = Employee.objects.select_related("department", "position", "manager").all()
    query = request.GET.get("q", "").strip()
    if query:
        employees = employees.filter(full_name__icontains=query) | employees.filter(employee_code__icontains=query)
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
    return render(request, "hr/org_chart.html", {"nodes_json": json.dumps(nodes, ensure_ascii=False)})


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
