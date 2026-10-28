from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import Department, JobPosition, Employee, PayrollPeriod, PayrollItem, DepartmentWorkforcePlan


class HRScreenTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-test", password="a-strong-test-password")
        self.department = Department.objects.create(code="OPS", name="العمليات")
        self.position = JobPosition.objects.create(code="OPS-01", title="أخصائي عمليات", department=self.department, job_description="وصف تجريبي", responsibilities="مهام تجريبية")
        self.employee = Employee.objects.create(user=self.user, employee_code="EMP-001", full_name="موظف تجريبي", department=self.department, position=self.position, date_of_birth=date(1990, 1, 1))

    def test_hr_dashboard_requires_login(self):
        response = self.client.get(reverse("hr:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_employee_directory_and_auto_fill_api(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("hr:employees"))
        self.assertEqual(page.status_code, 200)
        response = self.client.get(reverse("hr:employee_detail_api", args=[self.employee.pk]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["employee_code"], "EMP-001")
        self.assertEqual(payload["department"], "العمليات")
        self.assertEqual(payload["position"], "أخصائي عمليات")
        self.assertEqual(payload["job_description"], "وصف تجريبي")

    def test_organization_chart_renders(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("hr:org_chart"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "الخريطة التنظيمية")


    def test_integrated_management_report_renders(self):
        self.client.force_login(self.user)
        period = PayrollPeriod.objects.create(
            name="أكتوبر 2026", start_date=date(2026, 10, 1), end_date=date(2026, 10, 31)
        )
        PayrollItem.objects.create(
            period=period, employee=self.employee, basic_salary="10000.00",
            allowances="1000.00", overtime="0.00", deductions="250.00",
            tax_and_insurance="1200.00", net_salary="9550.00"
        )
        DepartmentWorkforcePlan.objects.create(
            department=self.department, fiscal_year=2026, approved_headcount=2,
            minimum_headcount=1, maximum_headcount=3,
            approved_monthly_payroll_budget="25000.00",
            approved_annual_payroll_budget="300000.00"
        )
        response = self.client.get(reverse("hr:management_reports"), {"period": period.pk, "year": 2026})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تكلفة المرتبات حسب الإدارة")
        self.assertContains(response, "العمليات")
        self.assertContains(response, "25000.00")
