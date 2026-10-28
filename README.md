# SWP-HOMES — Property Management ERP Foundation

Arabic/English Django/PostgreSQL foundation branded as SWP-HOMES for managing company-owned and client-managed property across multiple independent companies.

## Included
- Company, company membership, parties, properties, units
- Leases and scheduled lease charges
- Receipts and allocations (partial payments supported)
- Chart of accounts, fiscal periods, journal entries and lines
- Atomic journal posting with balance and closed-period checks
- Seed chart of accounts
- Initial automated tests

## Setup
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations core accounting leasing
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
pytest
```
PostgreSQL is recommended. SQLite is used only when DATABASE_URL is unset for local smoke tests.

## Safe migration rules
- Never edit a migration already applied to any environment.
- Use additive/expand-contract migrations for schema changes.
- Back up production and test against a restored staging database before deployment.
- For new required fields, add nullable/default-safe, backfill, then enforce constraints in a later migration.
- CI should run `python manage.py makemigrations --check --dry-run` and the full test suite.
- Never use `--fake` to conceal a failed migration.

## Not production-ready yet
This is the first backend foundation, not a finished ERP. Before real production use, implement API endpoints, frontend, company-scoped authorization on every request, robust audit logging, receipt-to-journal orchestration, reversals, bank reconciliation, deployment hardening, and PostgreSQL integration tests. A company_id field alone is not a security boundary.


## SWP-HOMES branding update
- The supplied SWP logo is displayed in the shared application header and login screen.
- The active company's name and optional company logo appear on the left side of the shared header.
- `Company.logo` is a nullable image field introduced through additive migration `core.0002_company_logo`; existing company records remain valid.
- Configure durable media storage before production because uploaded company logos must survive redeploys.

## Tenant database architecture status
This build still uses a single configured Django database with company-scoped records. It does **not** yet implement a separate physical PostgreSQL database per client, central tenant registry, database provisioning, or privileged administrator OTP. Do not represent it as meeting those requirements yet. These need a separate control-plane design, tenant connection lifecycle, email delivery configuration, and security tests before production.


## Phase 2 — Property and unit screens
See `PHASE2_STATUS_AR.md` for the exact implemented scope and verification limits. Property/unit list and create pages are company-scoped, and create actions are role-gated and audit-logged. Django tests still need to be executed in an environment with requirements installed.

## Phase 5 — Accounting reports
See `PHASE5_REPORTS_STATUS_AR.md`. Reports are derived from posted journals and should not be used for statutory reporting until the full accounting workflow, opening balances, cash-flow classifications and Django tests are completed.

## دليل النشر الآمن

### متغيرات البيئة في منصة الاستضافة
- `DJANGO_ENV=production` و`DJANGO_DEBUG=False`.
- `DJANGO_SECRET_KEY`: مفتاح عشوائي قوي وفريد، يُحفظ كسر في المنصة فقط.
- `DJANGO_ALLOWED_HOSTS`: أسماء المضيفين فقط مفصولة بفواصل، دون `https://` أو مسارات.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: الأصول الكاملة عبر HTTPS مفصولة بفواصل، مثل `https://app.example.com`.
- `DATABASE_URL`: رابط PostgreSQL/Neon الحالي، محفوظ كسر في المنصة ولا يوضع في Git.
- `PORT`: تستخدمه صورة Docker تلقائيًا، والافتراضي المحلي 8000.

### إصدار آمن
1. انتظر نجاح GitHub Actions وراجع التغييرات قبل دمجها إلى `main`.
2. ابنِ صورة Docker؛ يتم تجهيز ملفات الإنتاج الثابتة وmanifest أثناء البناء.
3. خذ نسخة احتياطية من قاعدة Neon قبل الترحيلات، وراجع `python manage.py showmigrations`.
4. نفّذ `python manage.py migrate --noinput` كخطوة إصدار واحدة متحكم بها، لا تلقائيًا مع كل عامل Gunicorn.
5. بعد النشر اختبر `/health/` وتسجيل الدخول والملفات الثابتة وراجع السجلات.
6. عند الفشل ارجع لصورة التطبيق السابقة. لا تستخدم `migrate --fake` ولا تحذف قاعدة البيانات.

### حدود التشغيل
- الملفات المرفوعة محليًا داخل الحاوية ليست دائمة؛ يلزم تخزين دائم لشعارات الشركات قبل الإنتاج.
- نجاح CI لا يغني عن اختبار الخدمة بعد النشر ولا يعني اكتمال جاهزية النظام المحاسبية.
- لا تضع الأسرار أو رابط قاعدة البيانات في المستودع أو السجلات.
