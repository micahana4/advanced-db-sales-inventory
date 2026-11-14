import uuid
from django.conf import settings

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
    )
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    average_cost = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        editable=False,
    )
    stock = models.PositiveIntegerField(default=0, editable=False)
    reorder_level = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name="product_price_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Transaction(models.Model):
    class Kind(models.TextChoices):
        SALE = "sale", "Sale"
        PURCHASE = "purchase", "Purchase"
        ADD = "add", "Stock addition"
        REMOVE = "remove", "Stock deduction"

    kind = models.CharField(max_length=12, choices=Kind.choices)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reference = models.CharField(max_length=200, blank=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tendered = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    @property
    def total(self):
        return self.subtotal + self.tax

    @property
    def change(self):
        return self.tendered - self.total if self.kind == self.Kind.SALE else 0


class TransactionLine(models.Model):
    transaction = models.ForeignKey(Transaction, related_name="lines", on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="transaction_lines")
    product_label = models.CharField(max_length=220)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=16, decimal_places=4)
    stock_after = models.PositiveIntegerField()

    @property
    def amount(self):
        return self.quantity * self.unit_price

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="line_quantity_positive"),
            models.UniqueConstraint(fields=["transaction", "product"], name="one_product_per_transaction"),
        ]


class Expense(models.Model):
    incurred_on = models.DateField(db_index=True)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self):
        return self.description