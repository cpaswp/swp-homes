from datetime import date
from decimal import Decimal
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

class TalentCenterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="talent-admin", password="a-strong-test-password", is_staff=True, is_superuser=True
        )
        self.department = Department.objects.create(code="TAL", name="المواهب")
        self.position = JobPosition.objects.create(code="TAL-01", title="أخصائي مواهب", department=self.department)
        self.employee = Employee.objects.create(
            employee_code="TAL-EMP-01", full_name="موظف اختبار المواهب",
            department=self.department, position=self.position, date_of_birth=date(1990, 1, 1)
        )

    def test_talent_center_is_staff_only(self):
        from django.contrib.auth import get_user_model
        from django.urls import reverse
        regular = get_user_model().objects.create_user(username="regular-talent", password="password-12345")
        self.client.force_login(regular)
        response = self.client.get(reverse("hr:talent_center"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_skill_and_assessment(self):
        from django.urls import reverse
        self.client.force_login(self.user)
        url = reverse("hr:talent_center")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "المهارات النشطة")
        response = self.client.post(url, {
            "action": "skill", "name": "تحليل البيانات", "category": "تقنية",
            "description": "مهارة تحليلية"
        })
        self.assertEqual(response.status_code, 302)
        from .models import Skill, EmployeeSkill
        skill = Skill.objects.get(name="تحليل البيانات")
        response = self.client.post(url, {
            "action": "assessment", "employee": self.employee.pk, "skill": skill.pk,
            "level": "4", "evidence": "تقييم عملي", "next_review_date": "2027-01-15"
        })
        self.assertEqual(response.status_code, 302)
        assessment = EmployeeSkill.objects.get(employee=self.employee, skill=skill)
        self.assertEqual(assessment.level, 4)
        self.assertEqual(assessment.assessed_by, self.user)

    def test_development_plan_rejects_target_before_start(self):
        from django.urls import reverse
        from .models import CareerDevelopmentPlan
        self.client.force_login(self.user)
        response = self.client.post(reverse("hr:talent_center"), {
            "action": "development", "employee": self.employee.pk,
            "title": "تطوير القيادة", "objective": "إدارة فريق",
            "start_date": "2027-03-01", "target_date": "2027-02-01",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CareerDevelopmentPlan.objects.count(), 0)

class EmployeeExcellenceAndFundTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="fund-admin", email="fund-admin@example.test", password="a-strong-test-password"
        )
        self.department = Department.objects.create(code="FND", name="إدارة الصندوق")
        self.position = JobPosition.objects.create(code="FND-01", title="موظف", department=self.department)
        self.employee = Employee.objects.create(
            employee_code="FND-EMP-01", full_name="موظف الصندوق",
            department=self.department, position=self.position, date_of_birth=date(1990, 1, 1),
            base_salary="1000.00",
        )

    def test_employee_excellence_dashboard_uses_approved_weighted_reviews(self):
        from .models import PerformanceReview
        PerformanceReview.objects.create(
            employee=self.employee, reviewer=self.employee,
            period_start=date(2026, 1, 1), period_end=date(2026, 9, 30),
            performance_score="80", appearance_score="60", behavior_score="90",
            commitment_score="100", overall_score="0", status="approved",
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("hr:employee_excellence_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["company_ranking"]), 1)
        self.assertEqual(response.context["company_ranking"][0]["overall"], Decimal("84.00"))

    def test_fund_policy_requires_percentages_total_100(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("hr:employee_fund_center"), {
            "action": "policy", "name": "صندوق اختبار", "monthly_deduction_amount": "100",
            "emergency_share_percent": "15", "association_share_percent": "90",
            "effective_from": "2026-11-01",
        })
        self.assertEqual(response.status_code, 302)
        from .models import EmployeeFundPolicy
        self.assertEqual(EmployeeFundPolicy.objects.count(), 0)

    def test_fund_deduction_splits_10_90_and_is_idempotent(self):
        from .models import EmployeeFundPolicy, EmployeeFundMembership, EmployeeFundContribution
        policy = EmployeeFundPolicy.objects.create(
            name="صندوق الاختبار", monthly_deduction_amount="100.00",
            emergency_share_percent="10.00", association_share_percent="90.00",
            effective_from=date(2026, 1, 1), active=True,
        )
        membership = EmployeeFundMembership.objects.create(
            employee=self.employee, policy=policy, monthly_amount="100.00",
            joined_on=date(2026, 1, 1), consent_reference="CONSENT-TEST-1",
        )
        period = PayrollPeriod.objects.create(
            name="نوفمبر 2026", start_date=date(2026, 11, 1), end_date=date(2026, 11, 30), status="draft"
        )
        item = PayrollItem.objects.create(
            period=period, employee=self.employee, basic_salary="1000.00",
            allowances="0.00", overtime="0.00", deductions="0.00",
            tax_and_insurance="100.00", net_salary="900.00",
        )
        self.client.force_login(self.admin)
        payload = {"action": "generate", "period": period.pk, "policy": policy.pk}
        self.client.post(reverse("hr:employee_fund_center"), payload)
        self.client.post(reverse("hr:employee_fund_center"), payload)
        contribution = EmployeeFundContribution.objects.get(membership=membership, period=period)
        item.refresh_from_db()
        self.assertEqual(contribution.emergency_amount, Decimal("10.00"))
        self.assertEqual(contribution.association_amount, Decimal("90.00"))
        self.assertEqual(item.deductions, Decimal("100.00"))
        self.assertEqual(item.net_salary, Decimal("800.00"))
        self.assertEqual(EmployeeFundContribution.objects.filter(membership=membership, period=period).count(), 1)

