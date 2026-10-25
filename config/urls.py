from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.i18n import set_language
from accounting.views import trial_balance_view, income_statement_view, balance_sheet_view, general_ledger_view

from core.views import dashboard, health, property_list, property_create, unit_list, unit_create
from leasing.views import lease_list, lease_create, lease_charges, receipt_list, receipt_create, receipt_post

urlpatterns = [
    path("health/", health, name="health"),
    path("reports/trial-balance/", trial_balance_view, name="trial_balance"),
    path("reports/income-statement/", income_statement_view, name="income_statement"),
    path("reports/balance-sheet/", balance_sheet_view, name="balance_sheet"),
    path("reports/general-ledger/", general_ledger_view, name="general_ledger"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("i18n/setlang/", set_language, name="set_language"),
    path("admin/", admin.site.urls),
    path("properties/", property_list, name="property_list"),
    path("properties/new/", property_create, name="property_create"),
    path("units/", unit_list, name="unit_list"),
    path("units/new/", unit_create, name="unit_create"),
    path("leases/", lease_list, name="lease_list"),
    path("leases/new/", lease_create, name="lease_create"),
    path("leases/charges/", lease_charges, name="lease_charges"),
    path("receipts/", receipt_list, name="receipt_list"),
    path("receipts/new/", receipt_create, name="receipt_create"),
    path("receipts/<int:receipt_id>/post/", receipt_post, name="receipt_post"),
    path("", dashboard, name="dashboard"),
]
