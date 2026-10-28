from django.contrib import admin
from .models import (
    Department, JobPosition, Employee, EmployeeDocument, AttendanceSite,
    AttendanceRecord, LeaveRequest, ApprovalRequest, ApprovalStep, PayrollPeriod, PayrollItem,
    LeavePolicy, EmployeeLeaveBalance, RecruitmentCandidate, MissionRequest, AttendanceException,
    EmployeeInsuranceRecord, InsuranceFormRecord, SalaryChange, PayrollComponent, EmployeeDeduction,
    InternalRegulation, DisciplinaryAction, KPI, PerformanceReview, TrainingCourse, EmployeeTraining,
    EmployeeAuditEvent, EmployeeRequirement, PositionAssignment, DepartmentWorkforcePlan,
    AdvancePolicy, EmployeeAdvance, CustodyAsset, CustodyAssignment, EmployeeContract, EmployeeWarning,
    EmployeeCompensationItem, DepartmentTarget, TargetAchievement, RecordAttachment,
    AttendanceDeviceConfiguration, RegulationRule, HiringDocumentTemplate, OfferLetter, EmployeeDependent,
    EmployeeMedicalBenefit, EmployeeHousingAssignment, EmployeeChildcareBenefit, EmployeeBenefitEnrollment,
    RecruitmentInterview, InterviewCriterion, InterviewEvaluation,
    Skill, EmployeeSkill, CareerDevelopmentPlan, SuccessionPlan, EmployeeOfTheMonthSettings, EmployeeFundPolicy, EmployeeFundMembership, EmployeeFundContribution, EmployeeAssociationTurn, EmployeeEmergencyClaim,
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "full_name", "department", "position", "manager", "status")
    list_filter = ("status", "department")
    search_fields = ("employee_code", "full_name", "email", "phone")
    autocomplete_fields = ("department", "position", "manager", "user")


@admin.register(DepartmentWorkforcePlan)
class DepartmentWorkforcePlanAdmin(admin.ModelAdmin):
    list_display = ("department", "fiscal_year", "approved_headcount", "maximum_headcount",
                    "approved_monthly_payroll_budget", "approved_annual_payroll_budget")
    list_filter = ("fiscal_year", "department")
    search_fields = ("department__name", "department__code")


@admin.register(EmployeeRequirement)
class EmployeeRequirementAdmin(admin.ModelAdmin):
    list_display = ("employee", "title", "status", "required_by", "submitted_at")
    list_filter = ("status", "category")
    search_fields = ("employee__employee_code", "employee__full_name", "title")
    autocomplete_fields = ("employee", "document", "verified_by")


@admin.register(CustodyAsset)
class CustodyAssetAdmin(admin.ModelAdmin):
    list_display = ("asset_code", "name", "category", "status", "insured", "insurance_end")
    list_filter = ("status", "category", "insured")
    search_fields = ("asset_code", "name", "serial_number", "insurance_policy_number")


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ("employee", "skill", "level", "assessed_at", "next_review_date")
    list_filter = ("skill__category", "level")
    search_fields = ("employee__employee_code", "employee__full_name", "skill__name")
    autocomplete_fields = ("employee", "skill", "assessed_by")


@admin.register(CareerDevelopmentPlan)
class CareerDevelopmentPlanAdmin(admin.ModelAdmin):
    list_display = ("employee", "title", "status", "progress_percent", "target_date", "owner")
    list_filter = ("status",)
    search_fields = ("employee__employee_code", "employee__full_name", "title")
    autocomplete_fields = ("employee", "owner")


@admin.register(SuccessionPlan)
class SuccessionPlanAdmin(admin.ModelAdmin):
    list_display = ("position", "nominee", "readiness", "is_active", "reviewed_at")
    list_filter = ("readiness", "is_active", "position__department")
    search_fields = ("position__title", "nominee__employee_code", "nominee__full_name")
    autocomplete_fields = ("position", "nominee", "reviewed_by")


admin.site.register([
    Department, JobPosition, EmployeeDocument, AttendanceSite, AttendanceRecord,
    LeaveRequest, ApprovalRequest, ApprovalStep, PayrollPeriod, PayrollItem,
    LeavePolicy, EmployeeLeaveBalance, RecruitmentCandidate, MissionRequest, AttendanceException,
    EmployeeInsuranceRecord, InsuranceFormRecord, SalaryChange, PayrollComponent, EmployeeDeduction,
    InternalRegulation, DisciplinaryAction, KPI, PerformanceReview, TrainingCourse, EmployeeTraining,
    EmployeeAuditEvent, PositionAssignment, AdvancePolicy, EmployeeAdvance, CustodyAssignment,
    EmployeeContract, EmployeeWarning, EmployeeCompensationItem, DepartmentTarget, TargetAchievement,
    OfferLetter, EmployeeDependent, EmployeeMedicalBenefit, EmployeeHousingAssignment,
    EmployeeChildcareBenefit, EmployeeBenefitEnrollment, AttendanceDeviceConfiguration, RegulationRule,
    HiringDocumentTemplate, RecordAttachment, RecruitmentInterview, InterviewCriterion, InterviewEvaluation,
    Skill,
])

admin.site.register([
    EmployeeOfTheMonthSettings, EmployeeFundPolicy, EmployeeFundMembership,
    EmployeeFundContribution, EmployeeAssociationTurn, EmployeeEmergencyClaim,
])
