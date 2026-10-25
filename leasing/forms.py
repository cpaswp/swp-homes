from django import forms
from .models import Lease, Receipt
from core.models import Party, Unit
from accounting.models import Account

class LeaseForm(forms.ModelForm):
    class Meta:
        model=Lease
        fields=["lease_number","unit","tenant","start_date","end_date","rent_amount","currency","frequency","due_day","management_fee_percent","security_deposit","status"]
        widgets={"start_date":forms.DateInput(attrs={"type":"date"}),"end_date":forms.DateInput(attrs={"type":"date"}),"rent_amount":forms.NumberInput(attrs={"step":"0.01","min":"0.01"}),"management_fee_percent":forms.NumberInput(attrs={"step":"0.01","min":"0","max":"100"}),"security_deposit":forms.NumberInput(attrs={"step":"0.01","min":"0"}),"due_day":forms.NumberInput(attrs={"min":"1","max":"28"})}
    def __init__(self,*args,company=None,language="ar",**kwargs):
        super().__init__(*args,**kwargs); self.company=company
        self.fields['unit'].queryset=Unit.objects.filter(company=company,property__is_active=True).select_related('property').order_by('property__name','code') if company else Unit.objects.none()
        self.fields['tenant'].queryset=Party.objects.filter(company=company,is_active=True).order_by('display_name') if company else Party.objects.none()
        labels={"lease_number":("رقم العقد","Lease number"),"unit":("الوحدة العقارية","Property unit"),"tenant":("المستأجر","Tenant"),"start_date":("بداية العقد","Start date"),"end_date":("نهاية العقد","End date"),"rent_amount":("قيمة الدفعة الدورية","Periodic rent"),"currency":("العملة","Currency"),"frequency":("دورية السداد","Frequency"),"due_day":("يوم الاستحقاق","Due day"),"management_fee_percent":("عمولة الإدارة %","Management fee %"),"security_deposit":("التأمين","Security deposit"),"status":("حالة العقد","Lease status")}
        for n,pair in labels.items(): self.fields[n].label=pair[0] if language=='ar' else pair[1]
    def clean(self):
        d=super().clean(); u,t=d.get('unit'),d.get('tenant')
        if self.company and u and u.company_id!=self.company.id: self.add_error('unit','الوحدة لا تتبع الشركة الحالية.')
        if self.company and t and t.company_id!=self.company.id: self.add_error('tenant','المستأجر لا يتبع الشركة الحالية.')
        if d.get('start_date') and d.get('end_date') and d['end_date']<d['start_date']: self.add_error('end_date','نهاية العقد تسبق بدايته.')
        if d.get('rent_amount') is not None and d['rent_amount']<=0: self.add_error('rent_amount','الإيجار يجب أن يكون أكبر من صفر.')
        return d

class ReceiptForm(forms.ModelForm):
    class Meta:
        model=Receipt
        fields=["receipt_number","tenant","receipt_date","amount","currency","payment_method","cash_account_code","external_reference"]
        widgets={"receipt_date":forms.DateInput(attrs={"type":"date"}),"amount":forms.NumberInput(attrs={"step":"0.01","min":"0.01"})}
    def __init__(self,*args,company=None,language='ar',**kwargs):
        super().__init__(*args,**kwargs); self.company=company
        self.fields['tenant'].queryset=Party.objects.filter(company=company,is_active=True).order_by('display_name') if company else Party.objects.none()
        self.fields['cash_account_code'].widget=forms.Select(choices=[(a.code,f'{a.code} — {a.name}') for a in Account.objects.filter(company=company,code__in=['1100','1110'],is_active=True).order_by('code')] if company else [])
        labels={"receipt_number":("رقم سند القبض","Receipt number"),"tenant":("المستأجر","Tenant"),"receipt_date":("تاريخ القبض","Receipt date"),"amount":("المبلغ","Amount"),"currency":("العملة","Currency"),"payment_method":("طريقة الدفع","Payment method"),"cash_account_code":("الصندوق / البنك","Cash / bank account"),"external_reference":("المرجع الخارجي","External reference")}
        for n,pair in labels.items(): self.fields[n].label=pair[0] if language=='ar' else pair[1]
    def clean(self):
        d=super().clean(); t=d.get('tenant'); amount=d.get('amount')
        if self.company and t and t.company_id!=self.company.id: self.add_error('tenant','المستأجر لا يتبع الشركة الحالية.')
        if amount is not None and amount<=0: self.add_error('amount','المبلغ يجب أن يكون أكبر من صفر.')
        if self.company and d.get('currency') and d['currency'].upper()!=self.company.base_currency.upper(): self.add_error('currency','العملة الأجنبية غير مفعلة في هذه المرحلة.')
        if self.company and d.get('cash_account_code') and not Account.objects.filter(company=self.company,code=d['cash_account_code'],is_active=True).exists(): self.add_error('cash_account_code','حساب الصندوق/البنك غير موجود؛ جهز دليل الحسابات أولًا.')
        return d
