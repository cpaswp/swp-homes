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

## HRMS foundation — SWP People
- Added a separate Django `hr` app and additive initial migration, registered alongside the existing ERP apps.
- HR records: departments, job positions/descriptions, employee profiles, employee documents, attendance sites/records, leave requests, approval requests/steps, payroll periods and payroll lines.
- Initial Arabic responsive UI: `/hr/`, employee directory with employee-data lookup, organization chart, payroll register preview, and approval inbox.
- Smoke tests added in `hr/tests.py`.
- Implementation boundaries and phased delivery requirements: `HRMS_ROADMAP_AR.md`.
- This foundation does not yet implement face verification, server-enforced 50m geofencing, live approval decisions, payroll calculations, central tenant database selection, or admin email OTP. Do not enable it for production payroll/attendance until those workflows and security tests are completed.

## GitHub + Neon deployment setup
- See `NEON_GITHUB_SETUP_AR.md` for the guarded manual Neon migration workflow, required GitHub secrets, and deployment limitations.
