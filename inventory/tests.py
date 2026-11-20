from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
from threading import Barrier
from uuid import uuid4

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from .models import Category, Expense, Product, Supplier, Transaction
from .services import post_transaction


class StoreWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles")
        cls.admin = User.objects.create_superuser("manager", password="manager-test-123")
        cls.cashier = User.objects.create_user("cashier")
        cls.cashier.groups.add(Group.objects.get(name="Cashier"))
        cls.clerk = User.objects.create_user("clerk", is_staff=True)
        cls.clerk.groups.add(Group.objects.get(name="Inventory Clerk"))
        cls.supplier = Supplier.objects.create(name="Sunrise")
        cls.category = Category.objects.create(name="Office")
        cls.product = Product.objects.create(
            name="Paper", sku="PAPER", category=cls.category, price=120, reorder_level=4,
        )

    def post_movement(self, kind, **changes):
        data = {
            "request_id": uuid4(), "reference": "Demo",
            "form-TOTAL_FORMS": 1, "form-INITIAL_FORMS": 0,
            "form-0-product": self.product.pk, "form-0-quantity": 10,
            "form-0-unit_price": "75.00", "supplier": self.supplier.pk,
            "tax_rate": "0", "tendered": "1000.00",
        }
        data.update(changes)
        return self.client.post(reverse("transaction", args=[kind]), data)

    def receive_stock(self):
        self.client.force_login(self.clerk)
        response = self.post_movement("purchase")
        self.assertEqual(response.status_code, 302)
        return response

    def test_purchase_sale_receipts_reports_and_replay(self):
        purchase = self.receive_stock()
        self.assertContains(self.client.get(purchase.url), "Stock-in record")
        self.client.force_login(self.cashier)
        self.assertEqual(self.client.get(purchase.url).status_code, 404)
        data = {"request_id": uuid4(), "form-0-quantity": 6, "tax_rate": "12"}
        sale = self.post_movement("sale", **data)
        self.assertEqual(sale.status_code, 302)
        self.assertEqual(self.post_movement("sale", **data).url, sale.url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(Transaction.objects.count(), 2)
        record = Transaction.objects.get(kind="sale")
        self.assertEqual(record.total, Decimal("806.40"))
        self.assertEqual(record.change, Decimal("193.60"))
        self.assertContains(self.client.get(sale.url), "Sales receipt")
        self.assertContains(self.client.get(reverse("dashboard")), "Reorder needed")
        self.assertEqual(self.client.get(reverse("reports")).status_code, 403)

        self.client.force_login(self.admin)
        Expense.objects.create(incurred_on=timezone.localdate(), amount=50, description="Delivery")
        filters = {"date": timezone.localdate().isoformat(), "period": "day"}
        self.assertContains(self.client.get(reverse("reports"), dict(filters, kind="profit")), "220.00")
        self.assertContains(self.client.get(reverse("reports"), dict(filters, kind="movement")), "PAPER")
        pdf = self.client.get(reverse("reports"), dict(filters, kind="sales", export="pdf"))
        self.assertTrue(pdf.content.startswith(b"%PDF-"))
        xlsx = self.client.get(reverse("reports"), dict(filters, kind="inventory", export="xlsx"))
        workbook = load_workbook(BytesIO(xlsx.content))
        self.assertEqual(list(workbook.active.values)[3], ("PAPER", "Paper", 4, 4, "Reorder"))

    def test_rejected_sales_roll_back_header_and_stock(self):
        self.receive_stock()
        self.client.force_login(self.cashier)
        oversale = self.post_movement("sale", **{"form-0-quantity": 11})
        self.assertContains(oversale, "has only 10 in stock")
        underpaid = self.post_movement("sale", tendered="1")
        self.assertContains(underpaid, "Payment must cover")
        self.assertEqual(Transaction.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_roles_and_stock_corrections(self):
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        self.receive_stock()
        self.assertEqual(self.post_movement("sale").status_code, 403)
        self.assertEqual(self.post_movement("remove", **{"form-0-quantity": 3}).status_code, 302)
        self.assertEqual(self.post_movement("add", **{"form-0-quantity": 2}).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)
        self.client.force_login(self.cashier)
        self.assertEqual(self.post_movement("purchase").status_code, 403)
        self.assertEqual(self.post_movement("remove").status_code, 403)

    def test_admin_can_change_product_without_changing_stock(self):
        self.receive_stock()
        response = self.client.post(reverse("admin:inventory_product_change", args=[self.product.pk]), {
            "sku": self.product.sku, "name": "A4 Paper", "category": self.category.pk,
            "price": "120.00", "stock": "1000", "reorder_level": 4, "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "A4 Paper")
        self.assertEqual(self.product.stock, 10)


class ConcurrentSalesTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_cashiers_cannot_sell_the_same_last_unit(self):
        category = Category.objects.create(name="Office")
        product = Product.objects.create(
            name="Paper", sku="PAPER", category=category, stock=1, price=120,
        )
        operators = [User.objects.create_user(name) for name in ("cashier1", "cashier2")]
        ready = Barrier(len(operators))

        def sell(operator):
            close_old_connections()
            try:
                ready.wait(timeout=10)
                post_transaction(
                    kind=Transaction.Kind.SALE, operator=operator, supplier=None,
                    reference="", request_id=uuid4(), tendered=Decimal(120),
                    tax_rate=Decimal(0), entries=[{"product": product, "quantity": 1}],
                )
            except ValidationError as error:
                return str(error)
            finally:
                connections.close_all()
            return "posted"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(sell, operators))
        self.assertEqual(results.count("posted"), 1)
        self.assertTrue(any("has only 0 in stock" in result for result in results))
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertEqual(Transaction.objects.count(), 1)