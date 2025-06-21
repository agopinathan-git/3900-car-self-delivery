# Create your models here.
import shortuuid
from django.db import models
from django.contrib.humanize.templatetags.humanize import intcomma
from django.conf import settings

import uuid

NOTIFICATION_TYPE_CHOICES = (
    ('o', 'Order Confirmation'),
    ('d', 'Delivery Update'),
    ('t', 'In Transit'),
)

class Car(models.Model):
    """Model representing a car listing."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, help_text="Unique ID for the car"
    )

    CAR_MODEL_CHOICES = (
        ("s", "Sedan"),
        ("u", "SUV"),
        ("p", "Pickup"),
    )

    CONDITION_CHOICES = (
        ("n", "New"),
        ("u", "Used"),
    )

    brand = models.CharField(max_length=100, help_text="Brand name")
    model = models.CharField(
        max_length=1, choices=CAR_MODEL_CHOICES, help_text="Car model type"
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Sale price")
    color = models.CharField(max_length=50, help_text="Car color")
    condition = models.CharField(
        max_length=1, choices=CONDITION_CHOICES, help_text="New or used"
    )
    available = models.BooleanField(default=True, help_text="Availability status")
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Listing creation time"
    )

    class Meta:
        ordering = ["brand", "model"]

    def __str__(self):
        return (
            f"{self.brand} {self.get_model_display()} ({self.get_condition_display()})"
        )

    @property
    def formatted_price(self):
        return f"${intcomma(self.price.quantize(0))}.{str(self.price)[-2:]}"


class Order(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, help_text="Unique order ID")

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="User placing the order"
    )
    car = models.ForeignKey('Car', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    delivery_address = models.TextField()
    phone_number = models.CharField(max_length=20, blank=True, null=True,
                                    help_text="Contact phone number for delivery")
    delivery_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # <<< NEW FIELD >>>
    # This field will store your new readable ID
    display_id = models.CharField(
        max_length=15,          # Example max length (e.g., 'O' + 8 chars = 9-10, leave room)
        unique=True,            # Ensures each display_id is unique
        blank=True,             # Allows the field to be blank in forms
        null=True,              # Allows the field to be NULL in the database
        db_index=True           # Creates a database index for faster lookups
    )

    def save(self, *args, **kwargs):
        # Generate display_id only when the object is first created
        # and display_id is not already set.
        if not self.display_id:
            prefix = 'O' # Prefix for Order IDs
            while True:
                # Generate a short UUID, convert to uppercase, and take the first 8 characters
                generated_suffix = shortuuid.uuid().upper()[:8]
                new_display_id = f"{prefix}{generated_suffix}"
                # Check if this generated ID already exists to ensure uniqueness (highly unlikely with shortuuid but good practice)
                if not Order.objects.filter(display_id=new_display_id).exists():
                    self.display_id = new_display_id
                    break # Exit loop if a unique ID is found
        super().save(*args, **kwargs) # Call the original save method

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.display_id} - {self.customer.username}"

    @property
    def is_assigned(self):
        # Checks if there's an associated DeliveryAssignment and an agent is set
        # Using hasattr and then accessing avoids DoesNotExist for OneToOneField
        try:
            return hasattr(self, 'deliveryassignment') and self.deliveryassignment.agent is not None
        except DeliveryAssignment.DoesNotExist:
            return False


class DeliveryAssignment(models.Model):
    """Model representing an assignment of a delivery agent to an order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Unique delivery assignment ID")

    STATUS_CHOICES = (
        ('a', 'Assigned'),
        ('t', 'In Transit'),
        ('d', 'Delivered'),
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='deliveryassignment', # <<< ADDED: For reverse lookup from Order
        help_text="Order being delivered"
    )
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="Assigned delivery agent",
        limit_choices_to={'groups__name': 'CarhubDeliveryAgent'},
        related_name='assigned_deliveries'
    )
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='a', help_text="Delivery status")
    assigned_at = models.DateTimeField(auto_now_add=True, help_text="Time of assignment")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last updated time")

    class Meta:
        ordering = ["-assigned_at"] # <<< CHANGED: Order by assignment time
        verbose_name = "Delivery Assignment"
        verbose_name_plural = "Delivery Assignments"

    def __str__(self):
        order_short_id = str(self.order.id)[:8]
        agent_name = self.agent.username if self.agent else "No Agent"
        return f"Assignment for Order {order_short_id} - Agent: {agent_name} ({self.get_status_display()})"

class EmailNotification(models.Model):
    """Model representing an email notification sent to a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Unique notification ID")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, help_text="User receiving the email")
    subject = models.CharField(max_length=255, help_text="Email subject")
    content = models.TextField(help_text="The full text content of the notification.") # <--- ADD THIS LINE!
    sent_at = models.DateTimeField(auto_now_add=True, help_text="Time sent")
    notification_type = models.CharField(
        max_length=1,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text="Type of notification",
    )

    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Email Notification" # Optional: improve admin display
        verbose_name_plural = "Email Notifications"

    def __str__(self):
        return f"Email to {self.user.username} - {self.get_notification_type_display()} - {self.subject}" # Optional: include subject


class SalesReport(models.Model):
    """Model representing a record of a car sale."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, help_text="Unique sales report ID"
    )
    car = models.ForeignKey('Car', on_delete=models.CASCADE, help_text="Sold car")
    order = models.ForeignKey(
        'Order', on_delete=models.CASCADE, help_text="Related order"
    )
    sale_price = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Final sale price"
    )
    sold_on = models.DateTimeField(help_text="Timestamp of sale")

    display_id = models.CharField(
        max_length=15,          # Example max length (e.g., 'S' + 8 chars = 9-10, leave room)
        unique=True,            # Ensures each display_id is unique
        blank=True,             # Allows the field to be blank in forms
        null=True,              # Allows the field to be NULL in the database
        db_index=True           # Creates a database index for faster lookups
    )

    class Meta:
        ordering = ["-sold_on"]

    # <<< OVERRIDE SAVE METHOD >>>
    def save(self, *args, **kwargs):
        # Generate display_id only when the object is first created
        # and display_id is not already set.
        if not self.display_id:
            prefix = 'S' # Prefix for SalesReport IDs, as you requested (e.g., SFEG...)
            while True:
                # Generate a short UUID, convert to uppercase, and take the first 8 characters
                generated_suffix = shortuuid.uuid().upper()[:8]
                new_display_id = f"{prefix}{generated_suffix}"
                # Check if this generated ID already exists in the database to ensure uniqueness
                if not SalesReport.objects.filter(display_id=new_display_id).exists():
                    self.display_id = new_display_id
                    break # Exit loop if a unique ID is found
        super().save(*args, **kwargs) # Call the original save method to save the instance

    def __str__(self):
        # Including display_id in __str__ is good for admin and debugging
        if self.car and self.sale_price:
            return f"Sale: {self.display_id or self.id} - {self.car.brand} - ${self.sale_price}"
        return f"Sale Report ID: {self.display_id or self.id}" # Fallback if car/price not available
