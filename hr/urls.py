from django.urls import path
from . import views

app_name = "hr"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("employees/", views.employee_list, name="employees"),
    path("recruitment/interviews/", views.recruitment_interviews, name="recruitment_interviews"),
    path("talent/", views.talent_center, name="talent_center"),\n    path("employee-excellence/", views.employee_excellence_dashboard, name="employee_excellence_dashboard"),\n    path("employee-fund/", views.employee_fund_center, name="employee_fund_center"),
    path("settings/attendance-devices/", views.attendance_device_settings, name="attendance_device_settings"),
    path("settings/compliance/", views.compliance_settings, name="compliance_settings"),
    path("data/excel/", views.excel_center, name="excel_center"),
    path("data/excel/export/<str:model_name>/", views.excel_export, name="excel_export"),
    path("data/attachments/", views.record_attachments, name="record_attachments"),
    path("employees/<int:employee_id>/id-card/", views.employee_id_card, name="employee_id_card"),
    path("api/employees/<int:employee_id>/", views.employee_detail_api, name="employee_detail_api"),
    path("organization/", views.org_chart, name="org_chart"),
    path("payroll/", views.payroll_preview, name="payroll"),
    path("approvals/", views.approval_inbox, name="approvals"),
    path("reports/management/", views.management_reports, name="management_reports"),
]
