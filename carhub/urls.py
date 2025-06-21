# carhub/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Inventory/Car Management
    path('inventory/', views.CarListView.as_view(), name='inventory'),
    path('car/add/', views.CarCreateView.as_view(), name='car-create'),
    path('car/<uuid:pk>/edit/', views.CarUpdateView.as_view(), name='car-update'),

    path('mark-unavailable/', views.mark_unavailable, name='mark_unavailable'), # Functional view

    # Order Management
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('order/initiate/', views.order_initiate, name='order-initiate'),
    path('order/submit/', views.order_submit, name='order-submit'),
    path('orders/<uuid:pk>/edit/', views.OrderUpdateView.as_view(), name='order-update'),
    path('order/<uuid:pk>/assign-agent/', views.assign_delivery_agent, name='assign-delivery-agent'),

    # Delivery Assignments
    path('deliveries/', views.DeliveryAssignmentListView.as_view(), name='deliveryassignment-list'),
    path('deliveries/<int:pk>/', views.DeliveryAssignmentDetailView.as_view(), name='deliveryassignment-detail'),

    # Notifications
    path('notifications/', views.EmailNotificationListView.as_view(), name='emailnotification-list'),
    path('notifications/<int:pk>/', views.EmailNotificationDetailView.as_view(), name='emailnotification-detail'),

    # Sales Reports
    path('sales/', views.SalesReportListView.as_view(), name='salesreport-list'),
    path('sales/export/csv/', views.export_sales_report_csv, name='export-sales-report-csv'), # Functional view
]
