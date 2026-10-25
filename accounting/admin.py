from django.contrib import admin
from .models import Account, FiscalPeriod, JournalEntry, JournalLine
admin.site.register([Account, FiscalPeriod, JournalEntry, JournalLine])
