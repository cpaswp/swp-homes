from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import get_language
from core.models import AuditEvent, CompanyMembership
from leasing.forms import LeaseForm, ReceiptForm
from leasing.models import Lease, LeaseCharge, Receipt
from leasing.services import generate_lease_schedule, post_receipt

def _membership(request):
    qs=CompanyMembership.objects.filter(user=request.user,is_active=True,company__is_active=True).select_related('company')
    requested=request.GET.get('company') or request.POST.get('company')
    return get_object_or_404(qs,company_id=requested) if requested else qs.order_by('company__name').first()

@login_required
def lease_list(request):
    m=_membership(request); lang=(get_language() or 'ar')[:2]
    if not m: return render(request,'core/no_company.html',{'language':lang})
    leases=Lease.objects.filter(company=m.company).select_related('unit__property','tenant').order_by('-start_date','lease_number')
    q=request.GET.get('q','').strip()
    if q: leases=leases.filter(Q(lease_number__icontains=q)|Q(tenant__display_name__icontains=q))
    return render(request,'leasing/lease_list.html',{'language':lang,'active_company':m.company,'leases':leases,'query':q})

@login_required
def lease_create(request):
    m=_membership(request); lang=(get_language() or 'ar')[:2]
    if not m: return render(request,'core/no_company.html',{'language':lang})
    if m.role not in ('owner','admin','property_manager'):
        messages.error(request,'ليس لديك صلاحية إنشاء العقود.'); return redirect('lease_list')
    form=LeaseForm(request.POST or None,company=m.company,language=lang)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                lease=form.save(commit=False); lease.company=m.company; lease.save(); count=generate_lease_schedule(lease.pk)
                AuditEvent.objects.create(company=m.company,actor=request.user,action='lease.create_and_schedule',model_label='leasing.Lease',object_id=str(lease.pk),details={'lease_number':lease.lease_number,'charges_generated':count})
            messages.success(request,f'تم حفظ العقد وإنشاء {count} استحقاق.'); return redirect('lease_charges')
        except (ValidationError,ValueError) as exc: form.add_error(None,str(exc))
    return render(request,'leasing/lease_form.html',{'language':lang,'active_company':m.company,'form':form})

@login_required
def lease_charges(request):
    m=_membership(request); lang=(get_language() or 'ar')[:2]
    if not m: return render(request,'core/no_company.html',{'language':lang})
    charges=LeaseCharge.objects.filter(company=m.company).exclude(status='void').select_related('lease','lease__tenant','lease__unit','lease__unit__property').annotate(allocated_amount=Sum('allocations__amount')).order_by('due_date','lease__lease_number')
    q=request.GET.get('q','').strip()
    if q: charges=charges.filter(Q(lease__lease_number__icontains=q)|Q(lease__tenant__display_name__icontains=q))
    rows=[]
    for c in charges:
        allocated=c.allocated_amount or Decimal('0.00'); rows.append({'charge':c,'allocated':allocated,'outstanding':max(Decimal('0.00'),c.amount-allocated)})
    return render(request,'leasing/charge_list.html',{'language':lang,'active_company':m.company,'rows':rows,'query':q})

@login_required
def receipt_list(request):
    m=_membership(request); lang=(get_language() or 'ar')[:2]
    if not m: return render(request,'core/no_company.html',{'language':lang})
    receipts=Receipt.objects.filter(company=m.company).select_related('tenant').order_by('-receipt_date','-id')
    return render(request,'leasing/receipt_list.html',{'language':lang,'active_company':m.company,'receipts':receipts})

@login_required
def receipt_create(request):
    m=_membership(request); lang=(get_language() or 'ar')[:2]
    if not m: return render(request,'core/no_company.html',{'language':lang})
    if m.role not in ('owner','admin','accountant'):
        messages.error(request,'ليس لديك صلاحية إنشاء سندات القبض.'); return redirect('receipt_list')
    form=ReceiptForm(request.POST or None,company=m.company,language=lang)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            receipt=form.save(commit=False); receipt.company=m.company; receipt.save()
            AuditEvent.objects.create(company=m.company,actor=request.user,action='receipt.create',model_label='leasing.Receipt',object_id=str(receipt.pk),details={'receipt_number':receipt.receipt_number,'amount':str(receipt.amount)})
        messages.success(request,'تم إنشاء سند القبض كمسودة. راجعه ثم رحّله محاسبيًا.'); return redirect('receipt_list')
    return render(request,'leasing/receipt_form.html',{'language':lang,'active_company':m.company,'form':form})

@login_required
def receipt_post(request,receipt_id):
    m=_membership(request)
    if not m: return render(request,'core/no_company.html',{'language':(get_language() or 'ar')[:2]})
    if request.method!='POST': return redirect('receipt_list')
    if m.role not in ('owner','admin','accountant'):
        messages.error(request,'ليس لديك صلاحية ترحيل سندات القبض.'); return redirect('receipt_list')
    receipt=get_object_or_404(Receipt,pk=receipt_id,company=m.company)
    try:
        entry=post_receipt(receipt.pk)
        AuditEvent.objects.create(company=m.company,actor=request.user,action='receipt.post',model_label='leasing.Receipt',object_id=str(receipt.pk),details={'journal_entry':entry.entry_number})
        messages.success(request,f'تم ترحيل السند إلى القيد {entry.entry_number}.')
    except (ValidationError,ValueError) as exc: messages.error(request,str(exc))
    return redirect('receipt_list')
