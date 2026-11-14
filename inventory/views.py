from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import HeaderForm, LineFormSet
from .models import Category, Product, Transaction
from .services import post_transaction

KIND = Transaction.Kind


def can_post(user, kind):
    group = "Cashier" if kind == KIND.SALE else "Inventory Clerk"
    return user.is_superuser or user.groups.filter(name=group).exists()


@login_required
def dashboard(request):
    products = Product.objects.select_related("category").filter(is_active=True)
    low_stock = products.filter(stock__lte=F("reorder_level"))
    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if search:
        products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))
    if category.isdecimal() and len(category) <= 18:
        products = products.filter(category_id=int(category))

    history = Transaction.objects.select_related("supplier", "operator").order_by("-created_at", "-pk")
    if not request.user.has_perm("inventory.view_transaction"):
        history = history.filter(operator=request.user)
    return render(request, "dashboard.html", {
        "products": products, "low_stock": low_stock,
        "history": history[:20], "categories": Category.objects.order_by("name"),
        "category": category, "q": search,
        "actions": [(kind.value, kind.label) for kind in KIND if can_post(request.user, kind)],
    })


@login_required
def create_transaction(request, kind):
    if kind not in KIND.values or not can_post(request.user, kind):
        raise PermissionDenied
    data = request.POST if request.method == "POST" else None
    form = HeaderForm(data, kind=kind, initial={"request_id": uuid4()})
    lines = LineFormSet(data, form_kwargs={"kind": kind})
    if request.method == "POST" and form.is_valid() and lines.is_valid():
        values = form.cleaned_data
        try:
            record = post_transaction(
                kind=kind, operator=request.user, supplier=values.get("supplier"),
                reference=values["reference"], request_id=values["request_id"],
                tendered=values.get("tendered", Decimal(0)), tax_rate=values.get("tax_rate", Decimal(0)),
                entries=[row for row in lines.cleaned_data if row],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("receipt", pk=record.pk)
    return render(request, "transaction.html", {"form": form, "lines": lines, "title": KIND(kind).label})


@login_required
def receipt(request, pk):
    records = Transaction.objects.select_related("operator", "supplier").prefetch_related("lines")
    if not request.user.has_perm("inventory.view_transaction"):
        records = records.filter(operator=request.user)
    return render(request, "receipt.html", {"record": get_object_or_404(records, pk=pk)})