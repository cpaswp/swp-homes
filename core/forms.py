from django import forms
from .models import Party, Property, Unit


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "code", "name", "kind", "ownership_type", "client_owner",
            "address", "city", "area_sqm", "acquisition_cost", "currency", "is_active",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "area_sqm": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "acquisition_cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, company=None, language="ar", **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        labels = {
            "code": ("كود العقار", "Property code"),
            "name": ("اسم العقار", "Property name"),
            "kind": ("نوع العقار", "Property type"),
            "ownership_type": ("نمط الملكية والإدارة", "Ownership / management"),
            "client_owner": ("المالك العميل", "Client owner"),
            "address": ("العنوان", "Address"),
            "city": ("المدينة", "City"),
            "area_sqm": ("المساحة بالمتر المربع", "Area (m²)"),
            "acquisition_cost": ("تكلفة الاقتناء", "Acquisition cost"),
            "currency": ("العملة", "Currency"),
            "is_active": ("عقار نشط", "Active property"),
        }
        for field_name, pair in labels.items():
            self.fields[field_name].label = pair[0] if language == "ar" else pair[1]
        self.fields["client_owner"].queryset = Party.objects.filter(
            company=company, is_active=True
        ).order_by("display_name") if company else Party.objects.none()
        self.fields["client_owner"].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("ownership_type") == "client_managed" and not cleaned.get("client_owner"):
            self.add_error("client_owner", "اختر المالك للعقار المُدار للغير.")
        if cleaned.get("ownership_type") == "company_owned":
            cleaned["client_owner"] = None
        return cleaned


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["property", "code", "kind", "floor_label", "area_sqm", "status"]
        widgets = {"area_sqm": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}

    def __init__(self, *args, company=None, language="ar", **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        labels = {
            "property": ("العقار", "Property"),
            "code": ("كود الوحدة", "Unit code"),
            "kind": ("نوع الوحدة", "Unit type"),
            "floor_label": ("الدور", "Floor"),
            "area_sqm": ("المساحة بالمتر المربع", "Area (m²)"),
            "status": ("الحالة", "Status"),
        }
        for field_name, pair in labels.items():
            self.fields[field_name].label = pair[0] if language == "ar" else pair[1]
        self.fields["property"].queryset = Property.objects.filter(
            company=company, is_active=True
        ).order_by("name") if company else Property.objects.none()

    def clean(self):
        cleaned = super().clean()
        prop = cleaned.get("property")
        if prop and self.company and prop.company_id != self.company.id:
            self.add_error("property", "العقار لا يتبع الشركة الحالية.")
        return cleaned
