from django.contrib import admin

from .models import Category, Product, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "phone", "email"]
    search_fields = ["name", "contact_person", "phone", "email"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "sku",
        "name",
        "category",
        "supplier",
        "price",
        "stock",
        "reorder_level",
        "is_active",
    ]
    list_filter = ["category", "supplier", "is_active"]
    search_fields = ["sku", "name"]
    readonly_fields = ["stock", "average_cost"]
    list_select_related = ["category", "supplier"]