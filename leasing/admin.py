from django.contrib import admin
from .models import Lease, LeaseCharge, Receipt, ReceiptAllocation
admin.site.register([Lease, LeaseCharge, Receipt, ReceiptAllocation])
