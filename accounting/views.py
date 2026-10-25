from datetime import date
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import get_language
from core.models import CompanyMembership
from accounting.models import Account
from accounting.reports import trial_balance,income_statement,balance_sheet,general_ledger

def _report_context(request):
    memberships=CompanyMembership.objects.filter(user=request.user,is_active=True,company__is_active=True).select_related('company').order_by('company__name')
    wanted=request.GET.get('company') or request.POST.get('company')
    membership=memberships.filter(company_id=wanted).first() if wanted else memberships.first()
    return membership,memberships,(get_language() or 'ar')[:2]
def _date(value):
    try: return date.fromisoformat(value) if value else None
    except (TypeError,ValueError): return None
@login_required
def trial_balance_view(request):
    m,memberships,lang=_report_context(request)
    if not m: return render(request,'core/no_company.html',{'language':lang})
    start=_date(request.GET.get('start')); end=_date(request.GET.get('end'))
    rows=trial_balance(m.company,start,end)
    return render(request,'accounting/report_table.html',{'language':lang,'active_company':m.company,'memberships':memberships,'report_title_ar':'ميزان المراجعة','report_title_en':'Trial balance','rows':rows,'start':start,'end':end,'totals':{'debit':sum((r['debit'] for r in rows), Decimal('0.00')),'credit':sum((r['credit'] for r in rows), Decimal('0.00'))},'report_kind':'trial'})
@login_required
def income_statement_view(request):
    m,memberships,lang=_report_context(request)
    if not m: return render(request,'core/no_company.html',{'language':lang})
    start=_date(request.GET.get('start')); end=_date(request.GET.get('end'))
    rows,revenue,expenses,profit=income_statement(m.company,start,end)
    return render(request,'accounting/report_table.html',{'language':lang,'active_company':m.company,'memberships':memberships,'report_title_ar':'قائمة الدخل','report_title_en':'Income statement','rows':rows,'start':start,'end':end,'revenue':revenue,'expenses':expenses,'profit':profit,'report_kind':'income'})
@login_required
def balance_sheet_view(request):
    m,memberships,lang=_report_context(request)
    if not m: return render(request,'core/no_company.html',{'language':lang})
    as_of=_date(request.GET.get('end'))
    rows,assets,liabilities,equity,profit,difference=balance_sheet(m.company,as_of)
    return render(request,'accounting/report_table.html',{'language':lang,'active_company':m.company,'memberships':memberships,'report_title_ar':'الميزانية العمومية','report_title_en':'Balance sheet','rows':rows,'end':as_of,'assets':assets,'liabilities':liabilities,'equity':equity,'profit':profit,'difference':difference,'report_kind':'balance'})
@login_required
def general_ledger_view(request):
    m,memberships,lang=_report_context(request)
    if not m: return render(request,'core/no_company.html',{'language':lang})
    start=_date(request.GET.get('start')); end=_date(request.GET.get('end'))
    account_id=request.GET.get('account') or None
    accounts=Account.objects.filter(company=m.company,is_active=True).order_by('code')
    lines=general_ledger(m.company,start,end,account_id)
    return render(request,'accounting/general_ledger.html',{'language':lang,'active_company':m.company,'memberships':memberships,'accounts':accounts,'lines':lines,'start':start,'end':end,'selected_account':account_id})
