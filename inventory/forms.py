from django import forms
from django.forms import BaseFormSet, formset_factory

from .models import Product, Supplier, Transaction


class HeaderForm(forms.Form):
    request_id = forms.UUIDField(widget=forms.HiddenInput)
    reference = forms.CharField(max_length=200, required=False, label="Customer, invoice number or reason")
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.order_by("name"))
    tax_rate = forms.DecimalField(min_value=0, max_value=100, decimal_places=2, initial=0, label="Tax (%)")
    tendered = forms.DecimalField(min_value=0, max_digits=18, decimal_places=2, label="Cash received")

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        if kind != Transaction.Kind.PURCHASE:
            del self.fields["supplier"]
        if kind != Transaction.Kind.SALE:
            del self.fields["tax_rate"]
            del self.fields["tendered"]
        if kind in (Transaction.Kind.ADD, Transaction.Kind.REMOVE):
            self.fields["reference"].required = True


class LineForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True))
    quantity = forms.IntegerField(min_value=1, max_value=2147483647)
    unit_price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, label="Unit cost")

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        if kind in (Transaction.Kind.SALE, Transaction.Kind.REMOVE):
            del self.fields["unit_price"]


class UniqueProducts(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        products = [row["product"].pk for row in self.cleaned_data if row]
        if len(products) != len(set(products)):
            raise forms.ValidationError("Enter each product once per transaction.")


LineFormSet = formset_factory(
    LineForm, formset=UniqueProducts, min_num=1, validate_min=True,
    max_num=50, validate_max=True, absolute_max=50, extra=0,
)