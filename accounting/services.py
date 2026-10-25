from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import JournalEntry, FiscalPeriod

class PostingError(ValueError):
    pass

@transaction.atomic
def post_journal_entry(entry_id):
    entry = JournalEntry.objects.select_for_update().select_related("company").get(pk=entry_id)
    if entry.status == "posted":
        return entry
    if entry.status != "draft":
        raise PostingError("Only draft entries can be posted.")
    periods = list(FiscalPeriod.objects.select_for_update().filter(
        company=entry.company, start_date__lte=entry.entry_date, end_date__gte=entry.entry_date
    )[:2])
    if not periods:
        raise PostingError("No fiscal period covers this journal date.")
    if len(periods) > 1:
        raise PostingError("Multiple fiscal periods cover this journal date; resolve the overlap first.")
    period = periods[0]
    if period.is_closed:
        raise PostingError("The fiscal period is closed.")
    lines = list(entry.lines.select_related("account"))
    if len(lines) < 2:
        raise PostingError("A journal entry needs at least two lines.")
    debit = sum((x.debit for x in lines), Decimal("0.00"))
    credit = sum((x.credit for x in lines), Decimal("0.00"))
    if debit <= 0 or debit != credit:
        raise PostingError(f"Journal entry is not balanced: debit={debit}, credit={credit}.")
    currencies = {line.currency.upper() for line in lines}
    if len(currencies) != 1 or next(iter(currencies)) != entry.company.base_currency.upper():
        raise PostingError("All journal lines must use the company base currency; foreign currency posting is not enabled yet.")
    for line in lines:
        if line.debit == 0 and line.credit == 0:
            raise PostingError("Journal lines cannot have both debit and credit equal to zero.")
        if line.account.company_id != entry.company_id:
            raise PostingError("Journal account belongs to another company.")
        if not line.account.is_active:
            raise PostingError("Cannot post to an inactive account.")
        if not line.account.allow_manual_posting and entry.source_type not in {"receipt", "lease_charge", "vendor_bill", "payment_voucher", "owner_payout", "opening_balance", "system_reversal"}:
            raise PostingError("Cannot post manually to a control account; use an approved source workflow.")
    entry.status = "posted"
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status","posted_at","updated_at"])
    return entry
