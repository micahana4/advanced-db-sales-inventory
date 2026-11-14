from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F
from django.urls import reverse
from django.utils.html import format_html

from .models import Category, Expense, Product, Supplier, Transaction, TransactionLine


class LowStockFilter(SimpleListFilter):
    title = "reorder status"
    parameter_name = "reorder"

    def lookups(self, request, model_admin):
        return [("yes", "Reorder needed")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(is_active=True, stock__lte=F("reorder_level"))
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "supplier", "price", "stock", "reorder_level", "is_active"]
    list_filter = ["category", "supplier", "is_active", LowStockFilter]
    search_fields = ["sku", "name"]
    readonly_fields = ["stock", "average_cost"]
    list_select_related = ["category", "supplier"]

    def get_object(self, request, object_id, from_field=None):
        is_change = request.resolver_match.url_name == "inventory_product_change"
        if request.method == "POST" and is_change and object_id.isascii() and object_id.isdecimal() and len(object_id) < 20:
            # The admin change form already wraps POST in a database transaction.
            Product.objects.select_for_update().filter(pk=object_id).first()
        return super().get_object(request, object_id, from_field)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "phone", "email"]
    search_fields = ["name", "contact_person", "email", "phone"]
    readonly_fields = ["purchase_history"]

    @admin.display(description="Purchase history")
    def purchase_history(self, supplier):
        if not supplier.pk:
            return "Save the supplier first."
        url = reverse("admin:inventory_transaction_changelist")
        return format_html('<a href="{}?supplier__id__exact={}&amp;kind__exact=purchase">View purchases</a>', url, supplier.pk)


class LineInline(admin.TabularInline):
    model = TransactionLine
    fields = readonly_fields = ["product_label", "quantity", "unit_price", "unit_cost", "stock_after"]
    extra = 0
    can_delete = False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "kind", "supplier", "operator", "created_at", "total"]
    list_filter = ["kind", "supplier", "created_at"]
    search_fields = ["reference", "supplier__name", "lines__product_label"]
    inlines = [LineInline]
    readonly_fields = ["kind", "supplier", "operator", "created_at", "reference", "subtotal", "tax", "tendered"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["incurred_on", "description", "amount"]
    list_filter = ["incurred_on"]
    search_fields = ["description"]