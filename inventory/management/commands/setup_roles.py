from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the Cashier and Inventory Clerk permission groups."

    def handle(self, *args, **options):
        roles = {
            "Cashier": {"view_product", "view_category"},
            "Inventory Clerk": {
                "view_transaction", "view_transactionline",
                *{f"{action}_{model}" for action in ("add", "change", "delete", "view")
                  for model in ("category", "product", "supplier")},
            },
        }
        for name, codes in roles.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(Permission.objects.filter(
                content_type__app_label="inventory", codename__in=codes,
            ))
        self.stdout.write(self.style.SUCCESS("Cashier and Inventory Clerk groups are ready."))