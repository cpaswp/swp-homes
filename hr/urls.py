from django.urls import path
from . import views

app_name = "hr"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("employees/", views.employee_list, name="employees"),
    path("settings/attendance-devices/", views.attendance_device_settings, name="attendance_device_settings"),
    path("employees/<int:employee_id>/id-card/", views.employee_id_card, name="employee_id_card"),
    path("api/employees/<int:employee_id>/", views.employee_detail_api, name="employee_detail_api"),
    path("organization/", views.org_chart, name="org_chart"),
    path("payroll/", views.payroll_preview, name="payroll"),
    path("approvals/", views.approval_inbox, name="approvals"),
    path("reports/management/", views.management_reports, name="management_reports"),
]
