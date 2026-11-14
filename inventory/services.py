from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Product, Transaction, TransactionLine

CENT = Decimal("0.01")
KIND = Transaction.Kind


@transaction.atomic
def post_transaction(*, kind, operator, supplier, reference, request_id, tendered, tax_rate, entries):
    existing = Transaction.objects.filter(request_id=request_id, operator=operator, kind=kind).first()
    if existing:
        return existing

    products = {p.pk: p for p in Product.objects.select_for_update().filter(
        pk__in=[entry["product"].pk for entry in entries]
    ).order_by("pk")}
    record, created = Transaction.objects.get_or_create(
        request_id=request_id, defaults={
            "kind": kind, "operator": operator, "supplier": supplier,
            "reference": reference, "tendered": tendered,
        },
    )
    if not created:
        if record.operator_id != operator.pk or record.kind != kind:
            raise ValidationError("Reload the form and try again.")
        return record

    lines = []
    for entry in entries:
        product = products.get(entry["product"].pk)
        if product is None or not product.is_active:
            raise ValidationError("A selected product is no longer active.")
        quantity = entry["quantity"]
        incoming = kind in (KIND.PURCHASE, KIND.ADD)
        new_stock = product.stock + (quantity if incoming else -quantity)
        if new_stock < 0:
            raise ValidationError(f"{product} has only {product.stock} in stock.")
        if new_stock > 2147483647:
            raise ValidationError("The resulting stock exceeds the supported limit.")

        cost = product.average_cost
        price = product.price if kind == KIND.SALE else Decimal(0)
        if incoming:
            price = cost = entry["unit_price"]
            product.average_cost = (
                (product.stock * product.average_cost + quantity * cost) / new_stock
            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        product.stock = new_stock
        product.save(update_fields=["stock", "average_cost"])
        lines.append(TransactionLine(
            transaction=record, product=product, product_label=str(product),
            quantity=quantity, unit_price=price, unit_cost=cost, stock_after=new_stock,
        ))

    record.subtotal = sum(line.amount for line in lines)
    record.tax = (record.subtotal * tax_rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    if record.total >= Decimal("10000000000000000"):
        raise ValidationError("The transaction total exceeds the supported limit.")
    if kind == KIND.SALE and tendered < record.total:
        raise ValidationError(f"Payment must cover the total of {record.total:.2f}.")
    record.save(update_fields=["subtotal", "tax"])
    TransactionLine.objects.bulk_create(lines)
    return record