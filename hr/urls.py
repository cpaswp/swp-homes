from django.urls import path
from . import views

app_name = "hr"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("employees/", views.employee_list, name="employees"),
    path("api/employees/<int:employee_id>/", views.employee_detail_api, name="employee_detail_api"),
    path("organization/", views.org_chart, name="org_chart"),
    path("payroll/", views.payroll_preview, name="payroll"),
    path("approvals/", views.approval_inbox, name="approvals"),
]
