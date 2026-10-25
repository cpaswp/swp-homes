from decimal import Decimal
from django.db.models import Sum
from .models import Account, JournalLine

ZERO=Decimal('0.00')
def account_balances(company, start_date=None, end_date=None, account_types=None):
    qs=JournalLine.objects.filter(entry__company=company,entry__status='posted')
    if start_date: qs=qs.filter(entry__entry_date__gte=start_date)
    if end_date: qs=qs.filter(entry__entry_date__lte=end_date)
    if account_types: qs=qs.filter(account__account_type__in=account_types)
    grouped=qs.values('account_id').annotate(debit_total=Sum('debit'),credit_total=Sum('credit'))
    totals={r['account_id']:(r['debit_total'] or ZERO,r['credit_total'] or ZERO) for r in grouped}
    accounts=Account.objects.filter(company=company,is_active=True)
    if account_types: accounts=accounts.filter(account_type__in=account_types)
    rows=[]
    for a in accounts.order_by('code'):
        debit,credit=totals.get(a.pk,(ZERO,ZERO))
        # Natural balance sign: debit for assets/expenses, credit for liabilities/equity/revenue.
        balance=debit-credit if a.account_type in ('asset','expense') else credit-debit
        if debit or credit or balance:
            rows.append({'account':a,'debit':debit,'credit':credit,'balance':balance})
    return rows

def trial_balance(company,start_date=None,end_date=None):
    return account_balances(company,start_date,end_date)

def income_statement(company,start_date=None,end_date=None):
    rows=account_balances(company,start_date,end_date,('revenue','expense'))
    revenue=sum((r['balance'] for r in rows if r['account'].account_type=='revenue'),ZERO)
    expenses=sum((r['balance'] for r in rows if r['account'].account_type=='expense'),ZERO)
    return rows,revenue,expenses,revenue-expenses

def balance_sheet(company,as_of_date=None):
    rows=account_balances(company,None,as_of_date,('asset','liability','equity'))
    assets=sum((r['balance'] for r in rows if r['account'].account_type=='asset'),ZERO)
    liabilities=sum((r['balance'] for r in rows if r['account'].account_type=='liability'),ZERO)
    equity=sum((r['balance'] for r in rows if r['account'].account_type=='equity'),ZERO)
    # Profit/loss to date is presented separately as current-period retained result.
    _,rev,exp,profit=income_statement(company,None,as_of_date)
    return rows,assets,liabilities,equity,profit,assets-(liabilities+equity+profit)

def general_ledger(company,start_date=None,end_date=None,account_id=None):
    qs=JournalLine.objects.filter(entry__company=company,entry__status='posted').select_related('entry','account').order_by('entry__entry_date','entry__entry_number','pk')
    if start_date: qs=qs.filter(entry__entry_date__gte=start_date)
    if end_date: qs=qs.filter(entry__entry_date__lte=end_date)
    if account_id: qs=qs.filter(account_id=account_id)
    return qs
