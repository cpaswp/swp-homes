from django.db import transaction
from .models import Account

DEFAULT_ACCOUNTS = [
("1000","الأصول","asset",True,False),("1100","النقدية بالصندوق","asset",False,True),
("1110","البنوك","asset",False,True),("1200","العملاء والمستأجرون","asset",True,False),
("1300","إيرادات مستحقة غير محصلة","asset",False,True),("1500","العقارات الاستثمارية","asset",False,True),
("2000","الالتزامات","liability",True,False),("2100","تأمينات المستأجرين","liability",False,True),
("2200","مبالغ مستحقة للملاك","liability",False,True),("2300","الموردون","liability",True,False),
("3000","حقوق الملكية","equity",True,False),("4000","الإيرادات","revenue",True,False),
("4100","إيرادات إيجارات عقارات مملوكة","revenue",False,True),("4200","عمولات إدارة الأملاك","revenue",False,True),
("5000","المصروفات","expense",True,False),("5100","مصروفات الصيانة","expense",False,True),
("5200","مصروفات تشغيل العقارات","expense",False,True),("5300","مصروفات إدارية وعمومية","expense",False,True)]
@transaction.atomic
def seed_chart(company):
    count = 0
    for code, name, kind, control, manual in DEFAULT_ACCOUNTS:
        _, created = Account.objects.get_or_create(company=company, code=code, defaults={
            "name":name,"account_type":kind,"is_control_account":control,"allow_manual_posting":manual})
        count += int(created)
    return count
