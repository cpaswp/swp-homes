from django.contrib import admin
from .models import (Department, JobPosition, Employee, EmployeeDocument, AttendanceSite,
                     AttendanceRecord, LeaveRequest, ApprovalRequest, ApprovalStep, PayrollPeriod, PayrollItem)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "full_name", "department", "position", "manager", "status")
    list_filter = ("status", "department")
    search_fields = ("employee_code", "full_name", "email", "phone")
    autocomplete_fields = ("department", "position", "manager", "user")


admin.site.register([Department, JobPosition, EmployeeDocument, AttendanceSite, AttendanceRecord,
                     LeaveRequest, ApprovalRequest, ApprovalStep, PayrollPeriod, PayrollItem])
