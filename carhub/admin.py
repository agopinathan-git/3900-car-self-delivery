# carhub/admin.py
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.forms import ModelForm

from .models import Car, Order, DeliveryAssignment, EmailNotification, SalesReport

User = get_user_model()

class OrderAdminForm(ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        customer_group = Group.objects.get(name='CarhubCustomer')
        admin_group = Group.objects.get(name='CarhubAdmin')
        self.fields['customer'].queryset = User.objects.filter(
            groups__in=[customer_group, admin_group]
        ).distinct().order_by('email') # Or by 'username' if you use it


class DeliveryAssignmentAdminForm(ModelForm):
    class Meta:
        model = DeliveryAssignment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        delivery_agent_group = Group.objects.get(name='CarhubDeliveryAgent')
        self.fields['agent'].queryset = User.objects.filter(
            groups=delivery_agent_group
        ).distinct().order_by('email')


# Register your models with these custom forms
@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'price', 'available', 'created_at')
    list_filter = ('available', 'condition', 'model')
    search_fields = ('brand', 'color')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm # <--- Apply the custom form here
    list_display = ('id', 'customer', 'car', 'status', 'delivery_date', 'created_at')
    list_filter = ('status', 'created_at')
    raw_id_fields = ('car',)
    search_fields = ('customer__email', 'car__brand', 'car__model')

@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    form = DeliveryAssignmentAdminForm # <--- Apply the custom form here
    list_display = ('order', 'agent', 'status', 'updated_at')
    list_filter = ('status', 'updated_at')
    raw_id_fields = ('order',)
    search_fields = ('order__id', 'agent__email')

@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'notification_type', 'sent_at')
    list_filter = ('notification_type', 'sent_at')
    search_fields = ('user__email', 'subject')

@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ('car', 'order', 'sale_price', 'sold_on')
    list_filter = ('sold_on',)
    search_fields = ('car__brand', 'order__customer__email')
    raw_id_fields = ('car', 'order')