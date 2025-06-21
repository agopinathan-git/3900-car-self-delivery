# carhub/management/commands/populate_display_ids.py

import shortuuid
from django.core.management.base import BaseCommand
from django.db import transaction

# Import your models (adjust import paths if your models are in a different file)
from carhub.models import Order, SalesReport

class Command(BaseCommand):
    help = 'Populates the display_id for existing Order and SalesReport objects that are missing it.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting to populate display_ids for existing records..."))

        # --- Populate Order display_ids ---
        orders_updated = 0
        # Use transaction.atomic() to ensure either all updates succeed or all fail
        with transaction.atomic():
            # Filter for orders where display_id is currently NULL or empty string
            for order in Order.objects.filter(display_id__isnull=True):
                prefix = 'O'
                while True: # Loop to ensure uniqueness, though highly unlikely with shortuuid
                    generated_suffix = shortuuid.uuid().upper()[:8] # Generates 8 random alphanumeric chars
                    new_display_id = f"{prefix}{generated_suffix}"
                    # Check if this generated ID already exists
                    if not Order.objects.filter(display_id=new_display_id).exists():
                        order.display_id = new_display_id
                        # Save only the display_id field to avoid triggering other save side-effects
                        order.save(update_fields=['display_id'])
                        orders_updated += 1
                        break # Found a unique ID, break from while loop
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {orders_updated} Order display_ids."))

        # --- Populate SalesReport display_ids ---
        sales_reports_updated = 0
        with transaction.atomic():
            # Filter for sales reports where display_id is currently NULL or empty string
            for sales_report in SalesReport.objects.filter(display_id__isnull=True):
                prefix = 'S'
                while True: # Loop to ensure uniqueness
                    generated_suffix = shortuuid.uuid().upper()[:8]
                    new_display_id = f"{prefix}{generated_suffix}"
                    # Check if this generated ID already exists
                    if not SalesReport.objects.filter(display_id=new_display_id).exists():
                        sales_report.display_id = new_display_id
                        # Save only the display_id field
                        sales_report.save(update_fields=['display_id'])
                        sales_reports_updated += 1
                        break # Found a unique ID, break from while loop
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {sales_reports_updated} SalesReport display_ids."))

        self.stdout.write(self.style.SUCCESS("Display ID population complete for existing records."))