import hashlib
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import get_language

from accounting.models import JournalEntry
from core.forms import PropertyForm, UnitForm
from core.models import AuditEvent, CompanyMembership, Property, Unit
from leasing.models import Lease, LeaseCharge


def health(request):
    """Minimal liveness endpoint; deliberately reveals no configuration or secrets."""
    return JsonResponse({"status": "ok", "service": "swp-homes"})


def _otp_cleanup(request):
    for key in ("admin_otp_user_id", "admin_otp_hash", "admin_otp_expires", "admin_otp_attempts"):
        request.session.pop(key, None)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    stage = "verify" if request.session.get("admin_otp_hash") else "credentials"
    if request.method == "POST" and request.POST.get("otp"):
        stage = "verify"
        expected = request.session.get("admin_otp_hash")
        expires = request.session.get("admin_otp_expires", 0)
        attempts = request.session.get("admin_otp_attempts", 0)
        supplied = request.POST.get("otp", "").strip()
        valid_format = supplied.isdigit() and len(supplied) == 6
        digest = hashlib.sha256(supplied.encode()).hexdigest() if valid_format else ""
        if not expected or time.time() > expires or attempts >= 5:
            _otp_cleanup(request)
            messages.error(request, "انتهت صلاحية الرمز أو تجاوزت عدد المحاولات. ابدأ تسجيل الدخول مجددًا.")
            stage = "credentials"
        elif secrets.compare_digest(digest, expected):
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.filter(pk=request.session.get("admin_otp_user_id"), is_active=True).first()
            _otp_cleanup(request)
            if user:
                login(request, user)
                request.session.set_expiry(60 * 60 * 10)
                return redirect(request.POST.get("next") or settings.LOGIN_REDIRECT_URL)
            messages.error(request, "الحساب غير متاح.")
            stage = "credentials"
        else:
            request.session["admin_otp_attempts"] = attempts + 1
            messages.error(request, "رمز التحقق غير صحيح.")
    elif request.method == "POST" and request.POST.get("resend_otp"):
        if request.session.get("admin_otp_user_id") and time.time() <= request.session.get("admin_otp_expires", 0):
            code = f"{secrets.randbelow(1000000):06d}"
            request.session["admin_otp_hash"] = hashlib.sha256(code.encode()).hexdigest()
            request.session["admin_otp_expires"] = time.time() + 300
            request.session["admin_otp_attempts"] = 0
            try:
                send_mail("رمز الدخول إلى SWP-HOMES", f"رمز التحقق: {code}\nصالح لمدة 5 دقائق. لا تشاركه مع أي شخص.", settings.DEFAULT_FROM_EMAIL, [settings.SWP_HOMES_ADMIN_EMAIL], fail_silently=False)
                messages.success(request, "تم إرسال رمز تحقق جديد إلى بريد مدير النظام.")
                stage = "verify"
            except Exception:
                _otp_cleanup(request)
                messages.error(request, "تعذر إرسال البريد. راجع إعدادات البريد الإلكتروني.")
                stage = "credentials"
        else:
            _otp_cleanup(request)
            stage = "credentials"
    elif request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None or not user.is_active:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")
        elif user.is_superuser or user.is_staff:
            code = f"{secrets.randbelow(1000000):06d}"
            request.session["admin_otp_user_id"] = user.pk
            request.session["admin_otp_hash"] = hashlib.sha256(code.encode()).hexdigest()
            request.session["admin_otp_expires"] = time.time() + 300
            request.session["admin_otp_attempts"] = 0
            try:
                send_mail("رمز الدخول إلى SWP-HOMES", f"رمز التحقق: {code}\nصالح لمدة 5 دقائق. لا تشاركه مع أي شخص.", settings.DEFAULT_FROM_EMAIL, [settings.SWP_HOMES_ADMIN_EMAIL], fail_silently=False)
                messages.success(request, "تم إرسال رمز التحقق إلى بريد مدير النظام.")
                stage = "verify"
            except Exception:
                _otp_cleanup(request)
                messages.error(request, "تعذر إرسال رمز التحقق. تأكد من إعداد البريد الإلكتروني.")
        else:
            login(request, user)
            request.session.set_expiry(60 * 60 * 10)
            return redirect(request.POST.get("next") or settings.LOGIN_REDIRECT_URL)
    return render(request, "registration/login.html", {"otp_stage": stage, "next": request.POST.get("next", request.GET.get("next", ""))})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")


def _active_membership(request):
    memberships = CompanyMembership.objects.filter(user=request.user, is_active=True, company__is_active=True).select_related("company")
    requested_company = request.GET.get("company") or request.POST.get("company")
    if requested_company:
        return get_object_or_404(memberships, company_id=requested_company)
    return memberships.order_by("company__name").first()


@login_required
def dashboard(request):
    memberships = CompanyMembership.objects.filter(user=request.user, is_active=True, company__is_active=True).select_related("company").order_by("company__name")
    requested_company = request.GET.get("company")
    membership = get_object_or_404(memberships, company_id=requested_company) if requested_company else memberships.first()
    language = (get_language() or "ar")[:2]
    if membership is None:
        return render(request, "core/no_company.html", {"language": language})
    company = membership.company
    charges = LeaseCharge.objects.filter(company=company).exclude(status="void")
    charge_total = charges.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    allocation_total = charges.aggregate(total=Sum("allocations__amount"))["total"] or Decimal("0.00")
    outstanding = max(Decimal("0.00"), charge_total - allocation_total)
    context = {"language": language, "memberships": memberships, "active_company": company,
        "property_count": Property.objects.filter(company=company, is_active=True).count(),
        "unit_count": Unit.objects.filter(company=company).count(),
        "active_lease_count": Lease.objects.filter(company=company, status="active").count(),
        "outstanding": outstanding,
        "posted_journal_count": JournalEntry.objects.filter(company=company, status="posted").count(),
        "recent_journals": JournalEntry.objects.filter(company=company).order_by("-entry_date", "-id")[:8]}
    return render(request, "core/dashboard.html", context)


@login_required
def property_list(request):
    membership = _active_membership(request)
    language = (get_language() or "ar")[:2]
    if membership is None: return render(request, "core/no_company.html", {"language": language})
    company = membership.company
    query = request.GET.get("q", "").strip()
    properties = Property.objects.filter(company=company).select_related("client_owner").order_by("code")
    if query: properties = properties.filter(Q(code__icontains=query) | Q(name__icontains=query) | Q(city__icontains=query) | Q(address__icontains=query))
    return render(request, "core/property_list.html", {"language": language, "active_company": company, "properties": properties, "query": query})


@login_required
def property_create(request):
    membership = _active_membership(request)
    language = (get_language() or "ar")[:2]
    if membership is None: return render(request, "core/no_company.html", {"language": language})
    if membership.role not in ("owner", "admin", "property_manager"):
        messages.error(request, "ليس لديك صلاحية إنشاء العقارات."); return redirect("property_list")
    if request.method == "POST":
        form = PropertyForm(request.POST, company=membership.company, language=language)
        if form.is_valid():
            obj = form.save(commit=False); obj.company = membership.company; obj.save()
            AuditEvent.objects.create(company=membership.company, actor=request.user, action="property.create", model_label="core.Property", object_id=str(obj.pk), details={"code": obj.code, "name": obj.name})
            messages.success(request, "تم حفظ العقار بنجاح."); return redirect("property_list")
    else: form = PropertyForm(company=membership.company, language=language)
    return render(request, "core/property_form.html", {"language": language, "active_company": membership.company, "form": form})


@login_required
def unit_list(request):
    membership = _active_membership(request); language = (get_language() or "ar")[:2]
    if membership is None: return render(request, "core/no_company.html", {"language": language})
    units = Unit.objects.filter(company=membership.company).select_related("property").order_by("property__code", "code")
    query = request.GET.get("q", "").strip()
    if query: units = units.filter(Q(code__icontains=query) | Q(property__name__icontains=query))
    return render(request, "core/unit_list.html", {"language": language, "active_company": membership.company, "units": units, "query": query})


@login_required
def unit_create(request):
    membership = _active_membership(request); language = (get_language() or "ar")[:2]
    if membership is None: return render(request, "core/no_company.html", {"language": language})
    if membership.role not in ("owner", "admin", "property_manager"):
        messages.error(request, "ليس لديك صلاحية إنشاء الوحدات."); return redirect("unit_list")
    if request.method == "POST":
        form = UnitForm(request.POST, company=membership.company, language=language)
        if form.is_valid():
            obj = form.save(commit=False); obj.company = membership.company; obj.save()
            AuditEvent.objects.create(company=membership.company, actor=request.user, action="unit.create", model_label="core.Unit", object_id=str(obj.pk), details={"code": obj.code, "property_id": obj.property_id})
            messages.success(request, "تم حفظ الوحدة بنجاح."); return redirect("unit_list")
    else: form = UnitForm(company=membership.company, language=language)
    return render(request, "core/unit_form.html", {"language": language, "active_company": membership.company, "form": form})
