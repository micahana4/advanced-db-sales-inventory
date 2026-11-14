from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .models import Category, Expense, Product, Transaction, TransactionLine

REPORTS = {
    "sales": "Sales summary", "inventory": "Current inventory",
    "movement": "Product movement", "profit": "Profit and loss",
}


class ReportForm(forms.Form):
    period = forms.ChoiceField(choices=[("day", "Daily"), ("week", "Weekly"), ("month", "Monthly")])
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    category = forms.ModelChoiceField(Category.objects.order_by("name"), required=False)

    def clean_date(self):
        selected = self.cleaned_data["date"]
        if not date(1900, 1, 1) <= selected <= date(9998, 12, 31):
            raise forms.ValidationError("Enter a date between 1900 and 9998.")
        return selected


def period_dates(anchor, period):
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=7)
    if period == "month":
        start = anchor.replace(day=1)
        return start, (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return anchor, anchor + timedelta(days=1)


def report_data(kind, start, end, category):
    products = Product.objects.all()
    if category:
        products = products.filter(category=category)
    if kind == "inventory":
        columns = ["SKU", "Product", "Stock", "Reorder at", "Status"]
        rows = [
            (p.sku, p.name, p.stock, p.reorder_level,
             "Inactive" if not p.is_active else "Reorder" if p.stock <= p.reorder_level else "Available")
            for p in products.select_related("category")
        ]
        return columns, rows

    sales = Transaction.objects.filter(
        kind=Transaction.Kind.SALE,
        created_at__gte=timezone.make_aware(datetime.combine(start, time.min)),
        created_at__lt=timezone.make_aware(datetime.combine(end, time.min)),
    ).order_by("created_at", "pk")
    lines = TransactionLine.objects.filter(transaction__in=sales)
    if category:
        lines = lines.filter(product__category=category)

    if kind == "movement":
        counts = products.annotate(units=Sum(
            "transaction_lines__quantity", filter=Q(transaction_lines__transaction__in=sales), default=0,
        )).order_by("-units", "name", "sku")
        return ["SKU", "Product", "Units sold"], [(p.sku, p.name, p.units) for p in counts]

    if kind == "sales":
        if category:
            rows = lines.values("transaction_id").annotate(
                revenue=Sum(F("unit_price") * F("quantity")),
            ).order_by("transaction_id")
            results = [(row["transaction_id"], row["revenue"]) for row in rows]
            results.append(("Period total", sum(value for _, value in results)))
            return ["Receipt", "Category sales (PHP)"], results
        results = [
            (sale.pk, timezone.localtime(sale.created_at).strftime("%Y-%m-%d %H:%M"),
             sale.subtotal, sale.tax, sale.total) for sale in sales
        ]
        results.append(("Period total", "", *(sum(row[i] for row in results) for i in (2, 3, 4))))
        return ["Receipt", "Date (Manila)", "Subtotal (PHP)", "Tax (PHP)", "Total (PHP)"], results

    totals = lines.aggregate(revenue=Sum(F("unit_price") * F("quantity"), default=0),
                             cost=Sum(F("unit_cost") * F("quantity"), default=0))
    revenue, cost = totals["revenue"], totals["cost"].quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
    expenses = Expense.objects.filter(incurred_on__gte=start, incurred_on__lt=end).aggregate(
        amount=Sum("amount", default=0),
    )["amount"]
    return ["Measure", "Amount (PHP)"], [
        ("Net sales before tax", revenue), ("Cost of goods sold", cost),
        ("Gross profit", revenue - cost), ("Operating expenses", expenses),
        ("Net profit or loss", revenue - cost - expenses),
    ]


def export_report(kind, export, title, scope, columns, rows):
    buffer = BytesIO()
    if export == "xlsx":
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = REPORTS[kind]
        sheet.append([title])
        sheet.append([scope])
        sheet.append(columns)
        sheet.freeze_panes = "A4"
        for row in rows:
            sheet.append(row)
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value, str):
                    cell.data_type = "s"  # Keep catalog labels as text, including leading "=".
                if isinstance(cell.value, Decimal):
                    cell.number_format = "#,##0.00"
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 25
        workbook.save(buffer)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

        styles = getSampleStyleSheet()
        data = [[Paragraph(escape(str(cell)), styles["BodyText"]) for cell in row]
                for row in [columns, *rows]]
        table = LongTable(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce9ee")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f7")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        SimpleDocTemplate(buffer, title=title).build([
            Paragraph(escape(title), styles["Title"]),
            Paragraph(escape(scope), styles["BodyText"]), Spacer(1, 12), table,
        ])
        content_type = "application/pdf"
    return HttpResponse(buffer.getvalue(), content_type=content_type, headers={
        "Content-Disposition": f'attachment; filename="{kind}.{export}"',
    })


@login_required
def reports(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    kind = request.GET.get("kind", "sales")
    export = request.GET.get("export", "")
    if kind not in REPORTS or export not in ("", "pdf", "xlsx"):
        raise Http404
    form = ReportForm(request.GET if "date" in request.GET else {
        "date": timezone.localdate(), "period": "day",
    })
    if kind == "profit":
        del form.fields["category"]

    columns, rows, scope = [], [], ""
    query = ""
    if form.is_valid():
        filters = form.cleaned_data
        start, end = period_dates(filters["date"], filters["period"])
        category = filters.get("category")
        columns, rows = report_data(kind, start, end, category)
        scope = ("Current stock snapshot" if kind == "inventory"
                 else f"{start} through {end - timedelta(days=1)}")
        if category:
            scope += f" | {category.name}"
        if export:
            return export_report(kind, export, REPORTS[kind], scope, columns, rows)
        query = urlencode({"kind": kind, "date": filters["date"], "period": filters["period"],
                           "category": category.pk if category else ""})
    return render(request, "reports.html", {
        "form": form, "reports": REPORTS, "kind": kind, "title": REPORTS[kind],
        "columns": columns, "rows": rows, "scope": scope, "query": query,
    })
