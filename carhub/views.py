# carhub/views.py

import csv
from decimal import Decimal
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group  # Import Group for permission checks
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Sum  # Ensure Q is imported if you use it in get_queryset
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic
from django.views.generic import ListView

from .forms import OrderDetailsForm, CarForm, DeliveryAssignmentForm
from .forms import OrderSubmissionForm
from .forms import OrderUpdateForm
from .models import Car
from .models import Order, DeliveryAssignment, EmailNotification, SalesReport


# Roshni
def addItems(request):
    viewName = "addItems"
    print("calling viewName")
    if request.method == "POST":
        print("inside POST")
        selected_ids = request.POST.getlist("selected_cars")
        print(selected_ids)
        selected_items = Car.objects.filter(id__in=selected_ids)
        print(selected_items)

        for item in selected_items:
            print(item)
            new_item = Order(
                # id=3,
                status="Pending112",
                delivery_address="Pending12",
                # delivery_date,
                # created_at,
                car_id=item.id,
                customer_id="23f78cadf2bb4f31b794119364a350c8",
            )
            new_item.save()

    else:
        print("inside GET")
        selected_ids = request.GET.getlist("selected_cars")
        print(selected_ids)
        selected_items = Car.objects.filter(id__in=selected_ids)
        print(selected_items)

    return render(
        request,
        "carhub/order_form.html",  # ----------added from kodjo
    )


# End Roshni


# Added from Kodjo

def generic_order_submission_view(request):
    if request.method == "POST":
        form = OrderSubmissionForm(request.POST)
        if form.is_valid():
            # Get selected cars from session
            selected_car_ids = request.session.get("selected_cars", [])

            if not selected_car_ids:
                messages.error(request, "No cars selected for order.")
                return redirect("inventory")

            # Format delivery address
            delivery_address = (
                f"{form.cleaned_data['name']}\n"
                f"{form.cleaned_data['address1']}\n"
                f"{form.cleaned_data['address2']}\n"
                f"{form.cleaned_data['city']}, {form.cleaned_data['state']} {form.cleaned_data['zip_code']}\n"
                f"Phone: {form.cleaned_data['phone']}"
            )

            # Get customer (you might want to modify this based on your authentication)
            customer = User.objects.filter(role="c").first()

            # Create orders for each selected car
            for car_id in selected_car_ids:
                try:
                    car = Car.objects.get(id=car_id)
                    Order.objects.create(
                        customer=customer,
                        car=car,
                        status="p",  # Pending status
                        delivery_address=delivery_address,
                        created_at=timezone.now(),
                    )
                except Car.DoesNotExist:
                    messages.error(request, f"Could not find car with ID {car_id}")
                    continue

            # Clear session after creating orders
            if "selected_cars" in request.session:
                del request.session["selected_cars"]

            messages.success(request, "Orders created successfully!")
            return redirect("order-list")
        else:
            messages.error(request, "Please correct the form errors.")
    else:
        form = OrderSubmissionForm()
        selected_car_ids = request.GET.getlist("selected_cars")
        if selected_car_ids:
            request.session["selected_cars"] = selected_car_ids
            selected_cars = Car.objects.filter(id__in=selected_car_ids)
            return render(
                request,
                "carhub/order_form.html",
                {"form": form, "selected_cars": selected_cars},
            )

    return render(request, "carhub/order_form.html", {"form": form})


# Ended from Kodjo


def generic_order_summary(request):
    return render(request, "carhub/order_list.html")


# Get the active User model
User = get_user_model()


# --- Home/Index View ---

def home(request):
    """
    Handles the landing page or redirects to inventory if authenticated.
    """
    if request.user.is_authenticated:
        # Redirect authenticated users to the inventory page (CarListView)
        return redirect('inventory')
    return render(request, 'carhub/landing.html')


# --- Car Views (Inventory) ---
class CarListView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """
    Displays a list of cars (inventory). Handles GET for filtering and POST for actions.
    """
    model = Car
    template_name = 'carhub/index.html'
    context_object_name = 'cars'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        filter_option = self.request.GET.get('filter', 'available')

        if user.groups.filter(name='CarhubCustomer').exists():
            # Customers only see available cars
            queryset = queryset.filter(available=True)
        elif user.groups.filter(name__in=['CarhubAdmin', 'CarhubDeliveryAgent']).exists():
            # Admins and Agents can filter by availability or see all
            if filter_option == 'unavailable':
                queryset = queryset.filter(available=False)
            elif filter_option == 'all':
                queryset = queryset.all()
            else:  # Default to available for admins/agents if no filter or 'available' is chosen
                queryset = queryset.filter(available=True)
        else:
            # Fallback for unhandled roles (shouldn't happen with LoginRequiredMixin)
            queryset = Car.objects.none()

        return queryset.order_by('-created_at')

    def test_func(self):
        """
        Permissions for CarListView: Admins, Customers, and Delivery Agents can view inventory.
        """
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=[
            'CarhubAdmin',
            'CarhubCustomer',
            'CarhubDeliveryAgent'
        ]).exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view the inventory.")
        return redirect('index')  # Redirect to home/landing if not authorized

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests for actions on selected cars (e.g., mark unavailable, order).
        """
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_cars')

        # --- Debugging Prints (remove after testing) ---
        print(f"\n--- DEBUG: In CarListView POST handler ---")
        print(f"Action button clicked: {action}")
        print(f"Raw POST data: {request.POST}")
        print(f"'selected_cars' from getlist(): {selected_ids}")
        print(f"Length of selected_ids: {len(selected_ids)}")
        # --- End Debugging Prints ---

        if not selected_ids:
            messages.warning(request, "Please select at least one car.")
            # Redirect back to the current page (inventory) to preserve GET parameters
            return HttpResponseRedirect(self.request.path_info)

        if action == 'mark_unavailable':
            # Store selected_ids in session and redirect to mark_unavailable view
            self.request.session['selected_car_ids_for_action'] = selected_ids
            return redirect('mark_unavailable')

        elif action == 'order_initiate':
            # Store selected_ids in session and redirect to order_initiate view
            self.request.session['selected_car_ids'] = selected_ids
            messages.info(request, "Initiating order for selected cars...")
            return redirect('order-initiate')  # Use the correct URL name with hyphen

        messages.error(request, "Invalid action requested.")
        return HttpResponseRedirect(self.request.path_info)


class CarCreateView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    """
    Allows CarhubAdmin or CarhubDeliveryAgent to add new cars to the inventory.
    """
    model = Car
    form_class = CarForm
    template_name = 'carhub/car_form.html'
    success_url = reverse_lazy('inventory')

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=['CarhubAdmin', 'CarhubDeliveryAgent']).exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to add/edit cars.")
        return redirect(reverse_lazy('inventory'))

    # This post method handles both single form submission and CSV upload
    def post(self, request, *args, **kwargs):
        if 'bulk_upload_submit' in request.POST and 'csv_file' in request.FILES:
            return self.handle_csv_upload(request)
        else:
            # If it's not a bulk upload, it's a single car form submission
            return super().post(request, *args, **kwargs)

    def handle_csv_upload(self, request):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'The uploaded file is not a CSV file.')
            return redirect('car-create')

        if csv_file.size > 5 * 1024 * 1024:  # 5MB limit
            messages.error(request, 'The CSV file is too large (max 5MB).')
            return redirect('car-create')

        decoded_file = csv_file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)

        cars_to_create = []
        errors = []
        line_num = 1  # Start from 1 for header, increment for each row

        # Define expected headers based on your model's current fields
        expected_headers = ['brand', 'model_type', 'price', 'color', 'condition', 'available']

        # Check if all expected headers are present
        if not all(header in reader.fieldnames for header in expected_headers):
            missing_headers = [h for h in expected_headers if h not in reader.fieldnames]
            messages.error(request,
                           f"CSV headers are incorrect or missing. Expected: {', '.join(expected_headers)}. Missing: {', '.join(missing_headers)}")
            return redirect('car-create')

        # Get display values for choices to validate against
        # (value_in_model, display_value_for_csv)
        model_type_map = {display.upper(): value for value, display in Car.CAR_MODEL_CHOICES}
        condition_map = {display.upper(): value for value, display in Car.CONDITION_CHOICES}

        for row in reader:
            line_num += 1
            try:
                brand = row.get('brand', '').strip()
                # Convert CSV 'model_type' display value to model's internal value
                model_type = model_type_map.get(row.get('model_type', '').strip().upper())
                price_str = row.get('price', '0.00').strip()
                color = row.get('color', '').strip()
                # Convert CSV 'condition' display value to model's internal value
                condition = condition_map.get(row.get('condition', '').strip().upper())
                available_str = row.get('available', '').strip().lower()

                # Basic validation for mandatory fields
                if not all([brand, model_type, price_str, color, condition, available_str is not None]):
                    raise ValueError("Missing or invalid mandatory field(s).")

                # Validate model_type against choices
                if model_type not in [val for val, _ in Car.CAR_MODEL_CHOICES]:
                    raise ValueError(
                        f"Invalid model_type: '{row.get('model_type')}'. Expected one of: {', '.join([d for v, d in Car.CAR_MODEL_CHOICES])}.")

                # Validate condition against choices
                if condition not in [val for val, _ in Car.CONDITION_CHOICES]:
                    raise ValueError(
                        f"Invalid condition: '{row.get('condition')}'. Expected one of: {', '.join([d for v, d in Car.CONDITION_CHOICES])}.")

                try:
                    price = Decimal(price_str)
                    if price < 0:
                        raise ValueError("Price cannot be negative.")
                except Exception:
                    raise ValueError(f"Invalid price format: '{price_str}'. Must be a number.")

                available = None
                if available_str == 'true':
                    available = True
                elif available_str == 'false':
                    available = False
                else:
                    raise ValueError(f"Invalid available value: '{available_str}'. Must be 'True' or 'False'.")

                cars_to_create.append(
                    Car(
                        brand=brand,
                        model=model_type,  # Use the internal value
                        price=price,
                        color=color,
                        condition=condition,  # Use the internal value
                        available=available,
                    )
                )

            except ValueError as ve:
                errors.append(f"Row {line_num}: {ve}")
            except Exception as e:
                errors.append(f"Row {line_num}: An unexpected error occurred - {e}")

        if errors:
            for error_msg in errors:
                messages.error(request, error_msg)
            messages.warning(request, f"Some cars could not be uploaded. Please correct errors and try again.")
            return redirect('car-create')

        if not cars_to_create:
            messages.warning(request, "No valid cars found in the CSV file to upload.")
            return redirect('car-create')

        try:
            with transaction.atomic():
                Car.objects.bulk_create(cars_to_create)
            messages.success(request, f"Successfully uploaded {len(cars_to_create)} car(s) from CSV.")
        except Exception as e:
            messages.error(request, f"Database error during bulk upload: {e}")
            messages.error(request, "No cars were added due to a database error.")

        return redirect('inventory')  # <-- Redirect after successful CSV upload

    def form_valid(self, form):
        messages.success(self.request, f"Car {form.instance.brand} {form.instance.model} added successfully!")
        return super().form_valid(form)


class CarUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """
    Allows CarhubAdmin to edit existing car details.
    """
    model = Car
    form_class = CarForm
    template_name = 'carhub/car_form.html'
    context_object_name = 'car'  # The object will be available as 'car' in the template

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.groups.filter(name='CarhubAdmin').exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to edit cars.")
        return redirect(reverse_lazy('inventory'))

    def get_context_data(self, **kwargs):
        """Adds a 'title' variable to the template context."""
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Car'  # Title for the update page
        return context

    def get_success_url(self):
        messages.success(self.request, f"Car {self.object.brand} {self.object.model} updated successfully!")
        return reverse_lazy('inventory')  # Redirect after successful update


# --- Order Views ---
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'carhub/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25  # Adjust your pagination size if needed

    def get_queryset(self):
        # Start with the base queryset, ordered by creation date (newest first)
        queryset = super().get_queryset().order_by('-created_at')

        # Get filter parameters from the request
        status = self.request.GET.get('status')
        user_query = self.request.GET.get('user')  # This is the filter causing the issue

        # Apply status filter if present
        if status:
            queryset = queryset.filter(status=status)

        # Apply customer username/email filter if present
        if user_query:
            # Use Q objects to search in both username and email fields (case-insensitive)
            queryset = queryset.filter(
                Q(customer__username__icontains=user_query) |
                Q(customer__email__icontains=user_query)
            )

        # --- Permission-based Filtering (Who can see which orders) ---
        # This logic determines which orders are visible to the logged-in user.
        # It's important to apply this *after* initial filters to refine the list.
        user = self.request.user
        if user.is_superuser:
            # Superusers see all orders, no further restrictions
            pass
        elif user.groups.filter(name='CarhubAdmin').exists():
            # Carhub Admins see all orders
            pass
        elif user.groups.filter(name='CarhubCustomer').exists():
            # Customers only see their own orders
            queryset = queryset.filter(customer=user)
        elif user.groups.filter(name='CarhubDeliveryAgent').exists():
            # Delivery Agents only see orders assigned to them
            # Use .distinct() to avoid duplicate orders if an order has multiple related delivery assignments
            queryset = queryset.filter(deliveryassignment__agent=user).distinct()
        else:
            # Users not in any specific role (or guest users) should see no orders by default
            queryset = Order.objects.none()  # Return an empty queryset

        return queryset

    # Note: For ListView, it's generally better to handle role-based data restrictions
    # within get_queryset rather than using UserPassesTestMixin on the class level,
    # as it allows different data to be shown to different users on the same page.
    # If you had a test_func previously, you might not need it here unless it's for
    # a broader access check (e.g., only authenticated users can view the list).

    def test_func(self):
        """
        Permissions for OrderListView: All three user groups can view.
        """
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=[
            'CarhubAdmin',
            'CarhubCustomer',
            'CarhubDeliveryAgent'
        ]).exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view orders.")
        return redirect('index')


class OrderDetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = Order
    template_name = "carhub/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # Determine if the current user can edit this order
        user = self.request.user
        can_edit_order = False
        if user.is_superuser:
            can_edit_order = True
        else:
            try:
                # Check if user is in 'CarhubAdmin' or 'CarhubDeliveryAgent' group
                # Using .filter().exists() is efficient for checking membership
                if user.groups.filter(name__in=['CarhubAdmin', 'CarhubDeliveryAgent']).exists():
                    can_edit_order = True
            except Group.DoesNotExist:
                # This handles cases where the groups might not exist yet (unlikely in production, but good for robustness)
                can_edit_order = False

        # Add the boolean variable to the context
        context['can_edit_order'] = can_edit_order

        # <<< ADD THIS NEW LOGIC FOR 'can_assign_agent' >>>
        can_assign_agent = False
        if user.is_superuser:
            can_assign_agent = True
        else:
            try:
                # Only 'CarhubAdmin' can assign agents
                if user.groups.filter(name='CarhubAdmin').exists():
                    can_assign_agent = True
            except Group.DoesNotExist:
                can_assign_agent = False
        context['can_assign_agent'] = can_assign_agent
        # <<< END NEW LOGIC >>>

        return context

    def test_func(self):
        # Your existing test_func for viewing order details (should allow all three groups)
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=[
            'CarhubAdmin',
            'CarhubCustomer',
            'CarhubDeliveryAgent'
        ]).exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view this order.")
        return redirect('order-list')  # Redirect to the general order list or another appropriate page


@login_required
def order_initiate(request):
    """
    Initiates the order submission process after car selection.
    This view is reached via redirect from CarListView's POST.
    """
    user = request.user
    if not (user.is_superuser or user.groups.filter(name__in=['CarhubAdmin', 'CarhubCustomer']).exists()):
        messages.error(request, "You are not authorized to initiate orders.")
        return redirect('inventory')

    # Get selected_ids from session (DO NOT pop here)
    selected_ids = request.session.get('selected_car_ids', [])

    if not selected_ids:
        messages.warning(request, "No cars selected. Please select at least one car.")
        return redirect('inventory')

    form = OrderDetailsForm()
    return render(request, 'carhub/order_submission.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name__in=['CarhubAdmin', 'CarhubCustomer']).exists())
def order_submit(request):
    """
    Processes the final order submission with delivery details.
    """
    user = request.user
    if not (user.is_superuser or user.groups.filter(name__in=['CarhubAdmin', 'CarhubCustomer']).exists()):
        messages.error(request, "You are not authorized to submit orders.")
        return redirect('inventory')

    selected_car_ids = request.session.get('selected_car_ids', [])

    if not selected_car_ids:
        messages.error(request, "No cars selected for order submission. Please re-select.")
        return redirect('inventory')

    if request.method == 'POST':
        form = OrderDetailsForm(request.POST)
        if form.is_valid():
            address1 = form.cleaned_data['address1']
            address2 = form.cleaned_data.get('address2', '')
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            zip_code = form.cleaned_data['zip']
            phone = form.cleaned_data['phone']
            delivery_date = form.cleaned_data.get('delivery_date')

            delivery_address_parts = [address1]
            if address2:
                delivery_address_parts.append(address2)
            delivery_address_parts.append(f"{city}, {state} {zip_code}")

            delivery_address = '\n'.join(delivery_address_parts).strip()

            orders_created = []

            with transaction.atomic():
                for car_id in selected_car_ids:
                    car = get_object_or_404(Car, id=car_id)

                    order = Order.objects.create(
                        customer=user,
                        car=car,
                        status=Order.Status.PENDING,
                        delivery_address=delivery_address,
                        phone_number=phone,
                        delivery_date=delivery_date,
                    )
                    orders_created.append(order)

                    # Mark car as unavailable immediately after order
                    car.available = False
                    car.save()

                    # --- NEW LOGIC: Create SalesReport record ---
                    try:
                        SalesReport.objects.create(
                            car=car,  # The car associated with this order
                            order=order,  # The newly created order
                            sale_price=car.price,  # Assuming your Car model has a 'price' field
                            sold_on=order.created_at  # Use the order's creation timestamp as the sale date
                        )
                    except Exception as e:
                        # Log this error (in a real app, use Django's logging module)
                        print(f"WARNING: Could not create SalesReport for Order {order.id}: {e}")
                        messages.warning(request,
                                         f"Order {str(order.id)[:8]} placed, but sale report creation failed. Admin might need to review.")
                    # --- END NEW LOGIC ---

                    # Customer EmailNotification
                    EmailNotification.objects.create(
                        user=user,
                        subject="Order Placed",
                        notification_type='o',
                        content=f"Your order for {car.brand} {car.get_model_display()} has been placed.",
                    )

                # Send confirmation email to customer
                try:
                    send_mail(
                        subject="Your CarHub Order Confirmation",
                        message=f"Hi {user.email}, your order for {len(orders_created)} car(s) has been placed successfully!",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except SMTPException as e:
                    # Log the error but don't crash the user's request
                    print(f"Error sending email for Order Confirmation: {e}")
                    # You might want to log this to a file or Sentry/monitoring service
                    # If DEBUG is True, this will print to your PythonAnywhere console log
                    # If DEBUG is False, it will go to the error log.
                    # Consider using Django's logging module for better logging practices.

                    # Optionally, inform the user that the email *might* not have been sent
                    # or have a fallback mechanism (e.g., store notification in DB).
                    # You could also let the request proceed successfully
                    # if email sending is not critical for the core functionality.
                    pass  # Or a more robust fallback like sending a message to the user/admin

                # Notify Admins
                try:
                    admins_group = Group.objects.get(name='CarhubAdmin')
                    admins = admins_group.user_set.all()
                    for admin in admins:
                        try:
                            send_mail(
                                subject="New Order Received - CarHub",
                                message=f"Customer {user.email} placed an order for {len(orders_created)} car(s).",
                                from_email=settings.EMAIL_HOST_USER,
                                recipient_list=[admin.email],
                                fail_silently=True,
                            )
                        except SMTPException as e:
                            print(f"Error sending email for New Order Received: {e}")
                            pass  # Handle gracefully
                    # For admin notification:
                    EmailNotification.objects.create(
                        user=admin,
                        subject="New Customer Order",
                        notification_type='o',
                        content=f"Order placed by {user.email}.",
                    )
                except Group.DoesNotExist:
                    messages.warning(request, "Admin group not found for notifications.")

                # Notify Delivery Agents
                try:
                    agents_group = Group.objects.get(name='CarhubDeliveryAgent')
                    agents = agents_group.user_set.all()
                    for agent in agents:
                        try:
                            send_mail(
                                subject="Delivery Request: New Car Order",
                                message=f"A new car order is pending delivery assignment for customer {user.email}.",
                                from_email=settings.EMAIL_HOST_USER,
                                recipient_list=[agent.email],
                                fail_silently=True,
                            )
                        except SMTPException as e:
                            print(f"Error sending email for New Car Order: {e}")
                            pass  # Handle gracefully
                        # For delivery agent notification:
                    EmailNotification.objects.create(
                        user=agent,
                        subject="New Delivery Needed",
                        notification_type='d',
                        content=f"Delivery needed for order(s) by {user.email}.",  # Changed to 'content'
                    )
                except Group.DoesNotExist:
                    messages.warning(request, "Delivery Agent group not found for notifications.")

            # Clear selected_car_ids from session after successful order
            if 'selected_car_ids' in request.session:
                del request.session['selected_car_ids']
            messages.success(request, "Order placed successfully. Confirmation email sent.")
            return redirect('order-list')
        else:
            messages.error(request, "Invalid form submission. Please check your details.")
            return render(request, 'carhub/order_submission.html', {'form': form})
    else:
        # If it's a GET request, but selected_car_ids is in session, show form
        if selected_car_ids:
            form = OrderDetailsForm()
            return render(request, 'carhub/order_submission.html', {'form': form})
        else:
            messages.warning(request, "No cars selected for order submission.")
        return redirect('inventory')


class OrderUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """
    Allows CarhubAdmin and CarhubDeliveryAgent to update Order status and delivery date.
    """
    model = Order
    form_class = OrderUpdateForm
    template_name = 'carhub/order_form.html'
    context_object_name = 'order'

    def get_success_url(self):
        short_id = str(self.object.id)[:8]
        messages.success(self.request, f"Order #{short_id} updated successfully!")
        return reverse_lazy('order-detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=['CarhubAdmin', 'CarhubDeliveryAgent']).exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to edit orders.")
        if 'pk' in self.kwargs:
            return redirect(reverse_lazy('order-detail', kwargs={'pk': self.kwargs['pk']}))
        return redirect(reverse_lazy('order-list'))


# --- Delivery Assignment Views ---
class DeliveryAssignmentListView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """
    Lists delivery assignments, filtered by agent for Delivery Agents.
    """
    model = DeliveryAssignment
    template_name = 'carhub/deliveryassignment_list.html'
    context_object_name = 'deliveries'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='CarhubAdmin').exists():
            return DeliveryAssignment.objects.all().order_by('-assigned_at')
        elif user.groups.filter(name='CarhubDeliveryAgent').exists():
            return DeliveryAssignment.objects.filter(agent=user).order_by('-assigned_at')
        return DeliveryAssignment.objects.none()

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=['CarhubAdmin', 'CarhubDeliveryAgent']).exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view delivery assignments.")
        return redirect('index')


class DeliveryAssignmentDetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    """
    Displays details of a specific delivery assignment.
    """
    model = DeliveryAssignment
    template_name = "carhub/deliveryassignment_detail.html"
    context_object_name = "delivery"

    def test_func(self):
        user = self.request.user
        delivery = self.get_object()

        if user.is_superuser:
            return True
        if user.groups.filter(name='CarhubAdmin').exists():
            return True
        elif user.groups.filter(name='CarhubDeliveryAgent').exists():
            return user == delivery.agent
        return False

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view this delivery assignment.")
        return redirect('deliveryassignment-list')


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='CarhubAdmin').exists())
def assign_delivery_agent(request, pk):
    order = get_object_or_404(Order, pk=pk)

    # Only allow assignment for PENDING orders
    if order.status != Order.Status.PENDING:
        messages.error(request, f"Order #{str(order.id)[:8]} cannot be assigned. It is not in PENDING status.")
        return redirect('order-detail', pk=order.pk)

    # Check if an active assignment already exists for this order
    # order.is_assigned property correctly handles this
    if order.is_assigned:
        messages.info(request,
                      f"Order #{str(order.id)[:8]} is already assigned to {order.deliveryassignment.agent.username}.")
        return redirect('order-detail', pk=order.pk)

    if request.method == 'POST':
        form = DeliveryAssignmentForm(request.POST)
        if form.is_valid():
            agent = form.cleaned_data['agent']

            with transaction.atomic():
                # Create the DeliveryAssignment
                assignment = DeliveryAssignment.objects.create(
                    order=order,
                    agent=agent,
                    status='a'  # <<< IMPORTANT: Use 'a' to match your STATUS_CHOICES
                )

                # Update the Order status to PROCESSING
                order.status = Order.Status.PROCESSING
                order.save()

                # --- Notifications ---

                # Notify the assigned Delivery Agent
                EmailNotification.objects.create(
                    user=agent,
                    subject="New Delivery Assignment",
                    notification_type='d',
                    content=f"You have been assigned to deliver Order #{str(order.id)[:8]} for {order.customer.email}.",
                )
                try:
                    send_mail(
                        subject="New Delivery Assignment",
                        message=f"Hi {agent.username},\n\nYou have been assigned to deliver Order #{str(order.id)[:8]} for customer {order.customer.username}. "
                                f"Order details: {order.delivery_address}, Phone: {order.phone_number}",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[agent.email],
                        fail_silently=False,
                    )
                except SMTPException as e:
                    print(f"Error sending email for New Delivery Assignment: {e}")
                    pass  # Handle gracefully

                # Notify the Customer about the assignment
                EmailNotification.objects.create(
                    user=order.customer,
                    subject="Your Order is Being Processed",
                    notification_type='o',
                    content=f"Your order #{str(order.id)[:8]} is now being processed and assigned to a delivery agent.",
                )
                try:
                    send_mail(
                        subject=f"Update: Your CarHub Order #{str(order.id)[:8]} is Assigned",
                        message=f"Hi {order.customer.username},\n\nYour order for {order.car.brand} is now being processed. "
                                f"A delivery agent has been assigned to your order. We will notify you when it's out for delivery.",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[order.customer.email],
                        fail_silently=False,
                    )
                except SMTPException as e:
                    print(f"Error sending email for CarHub Order Assigned: {e}")
                    pass  # Handle gracefully

                messages.success(request,
                                 f"Delivery Agent {agent.username} assigned to Order #{str(order.id)[:8]} successfully!")
                return redirect('order-detail', pk=order.pk)
        else:
            messages.error(request, "Invalid form submission. Please select a valid agent.")
    else:
        form = DeliveryAssignmentForm()

    context = {
        'order': order,
        'form': form,
    }
    return render(request, 'carhub/assign_delivery_agent.html', context)


# --- Notification Views ---
class EmailNotificationListView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    """
    Lists email notifications for the logged-in user.
    """
    model = EmailNotification
    template_name = 'carhub/emailnotification_list.html'
    context_object_name = 'notifications'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='CarhubAdmin').exists():
            # Admins can see all notifications (or filter as needed)
            return EmailNotification.objects.all().order_by('-created_at')
        return EmailNotification.objects.filter(user=user).order_by('-created_at')

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.is_authenticated  # LoginRequiredMixin already handles, but explicit is good


class EmailNotificationDetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    """
    Displays details of a specific email notification.
    """
    model = EmailNotification
    template_name = "carhub/emailnotification_detail.html"
    context_object_name = "notification"

    def test_func(self):
        user = self.request.user
        notification = self.get_object()

        if user.is_superuser:
            return True
        if user.groups.filter(name='CarhubAdmin').exists():
            return True
        return user == notification.user

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view this notification.")
        return redirect('emailnotification-list')


# --- Sales Report Views ---
class SalesReportListView(LoginRequiredMixin, UserPassesTestMixin, generic.ListView):
    model = SalesReport
    template_name = 'carhub/salesreport_list.html'
    context_object_name = 'sales_reports'
    paginate_by = 25

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name='CarhubAdmin').exists()

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to view sales reports.")
        return redirect('index')

    def get_queryset(self):
        # This queryset will be used for the main sales_reports table
        # Order by sold_on in descending order for most recent first
        return SalesReport.objects.select_related('order__customer', 'car').order_by('-sold_on')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- Dashboard/Summary Data ---
        total_orders_count = Order.objects.count()
        total_assigned_orders = Order.objects.filter(deliveryassignment__isnull=False).distinct().count()
        total_unassigned_orders = total_orders_count - total_assigned_orders
        total_sales_value = SalesReport.objects.aggregate(Sum('sale_price'))['sale_price__sum'] or 0.00
        pending_assignment_orders_data = Order.objects.filter(
            deliveryassignment__isnull=True
        ).select_related('customer', 'car').order_by('created_at')  # Order by creation date, oldest first

        context['total_orders'] = total_orders_count
        context['total_unassigned'] = total_unassigned_orders
        context['total_assigned'] = total_assigned_orders
        context['total_sales'] = f"{total_sales_value:,.2f}"  # Format as currency
        context['pending_assignment_orders'] = pending_assignment_orders_data

        return context


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='CarhubAdmin').exists())
def export_sales_report_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Sale ID', 'Customer Email', 'Car Brand/Model', 'Sale Price', 'Order ID', 'Sale Date'])

    for report in SalesReport.objects.select_related('order__customer', 'car'):
        writer.writerow([
            report.display_id,
            report.order.customer.email,
            f"{report.car.brand} / {report.car.get_model_display()}",
            report.sale_price,
            report.order.display_id,
            report.sold_on.strftime('%Y-%m-%d %H:%M')
        ])

    return response


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name__in=['CarhubAdmin', 'CarhubDeliveryAgent']).exists())
def mark_unavailable(request):
    """
    Marks selected cars as unavailable.
    This view is reached via redirect from CarListView's POST.
    """
    # Retrieve selected_ids from session
    selected_ids = request.session.pop('selected_car_ids_for_action', [])  # Use .pop() to retrieve and remove

    # --- Debugging Prints (remove after testing) ---
    print(f"\n--- DEBUG: In mark_unavailable view ---")
    print(f"'selected_ids' from session: {selected_ids}")
    print(f"Length of selected_ids: {len(selected_ids)}")
    # --- End Debugging Prints ---

    if not selected_ids:
        messages.warning(request, "No cars selected for removal.")
        print("DEBUG: Redirecting from mark_unavailable because session selected_ids is empty.")  # Debug print
        return redirect('inventory')

        # Since this view is hit by a redirect from a POST request,
        # it implicitly functions as handling the "action" part.
        # The actual marking logic goes here.
    with transaction.atomic():
        Car.objects.filter(id__in=selected_ids).update(available=False)
        messages.success(request, "Selected cars marked as unavailable.")

    return redirect('inventory')


from django.shortcuts import render
from .models import Order, SalesReport


def dashboard_view(request):
    total_orders = Order.objects.count()
    unassigned_orders = Order.objects.filter(deliveryassignment__isnull=True)
    total_unassigned = unassigned_orders.count()
    total_assigned = total_orders - total_unassigned

    total_sales = SalesReport.objects.count()
    recent_sales = SalesReport.objects.order_by('-sold_on')[:5]  # Last 5 sales, newest first

    context = {
        'total_orders': total_orders,
        'total_unassigned': total_unassigned,
        'total_assigned': total_assigned,
        'unassigned_orders': unassigned_orders,
        'total_sales': total_sales,
        'recent_sales': recent_sales,
    }
    return render(request, 'carhub/dashboard.html', context)
