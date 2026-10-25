from django.contrib import admin
from .models import Company, CompanyMembership, Party, Property, Unit, AuditEvent
admin.site.register([Company, CompanyMembership, Party, Property, Unit, AuditEvent])
