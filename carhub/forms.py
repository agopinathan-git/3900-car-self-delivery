# carhub/forms.py
import re
from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Order, Car, DeliveryAssignment


class OrderSubmissionForm(forms.Form):
    # Delivery Details
    name = forms.CharField(max_length=100, label="Full Name")
    address1 = forms.CharField(max_length=255, label="Address Line 1")
    address2 = forms.CharField(max_length=255, required=False, label="Address Line 2")
    city = forms.CharField(max_length=100)
    state = forms.CharField(max_length=100)
    zip_code = forms.CharField(max_length=20, label="ZIP Code")
    phone = forms.CharField(max_length=20)


class OrderDetailsForm(forms.Form):
    address1 = forms.CharField(label="Address 1", max_length=100)
    address2 = forms.CharField(label="Address 2", max_length=100, required=False)
    city = forms.CharField(label="City", max_length=50)
    state = forms.CharField(label="State", max_length=50)
    zip = forms.CharField(label="ZIP Code", max_length=10)
    phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))

    delivery_date = forms.DateField(
        label="Preferred Delivery Date",
        widget=forms.DateInput(attrs={'type': 'date'}),  # HTML5 date picker
        required=True  # Set to True if it should be mandatory
    )

    # Payment details (not stored)
    name_on_card = forms.CharField(label="Name on Card", max_length=100)
    card_number = forms.CharField(label="Card Number", max_length=19)
    security_code = forms.CharField(label="Security Code", max_length=4)
    expiration = forms.CharField(label="Expiration Date (MM/YY)", max_length=5)

    # --- Start of Expiration and Card Number Validation Methods ---
    def clean_expiration(self):
        expiration_date_str = self.cleaned_data['expiration']

        # 1. Validate Basic MM/YY Format using Regex
        # Ensures input is like "01/23" or "12/99"
        if not re.match(r'^(0[1-9]|1[0-2])\/\d{2}$', expiration_date_str):
            raise forms.ValidationError('Please enter expiration in MM/YY format (e.g., 03/25).')

        month_str, year_str = expiration_date_str.split('/')
        month = int(month_str)
        year = int(year_str)

        # Convert 2-digit year to 4-digit year.
        # This heuristic attempts to put the 2-digit year into the correct century.
        # Example: Current date is June 20, 2025
        # If input year is '24', it means 2024. If '25', it means 2025. If '26', it means 2026.
        # If input year is '99', it means 1999 (assuming typical card validity).
        current_year_full = date.today().year  # e.g., 2025
        current_century_prefix = (current_year_full // 100) * 100  # e.g., 2000

        # Dynamic pivot for 2-digit year to 4-digit year conversion:
        # Years up to (current 2-digit year + 20) are assumed to be in the current century.
        # Years beyond that are assumed to be in the previous century.
        # E.g., if current_year_full is 2025, (25 + 20) = 45.
        # So, 2-digit years '00' through '44' map to 20xx.
        # 2-digit years '45' through '99' map to 19xx.
        pivot_year_2_digit = (current_year_full % 100) + 20

        if year >= pivot_year_2_digit:
            full_year = 1900 + year
        else:
            full_year = 2000 + year

        # Validate against current date
        today = date.today()  # e.g., 2025-06-20

        # Check if the expiration year is in the past
        if full_year < today.year:
            raise forms.ValidationError('Expiration year cannot be in the past.')

        # If the expiration year is the current year, check the month
        if full_year == today.year:
            if month < today.month:
                raise forms.ValidationError('Expiration month cannot be in the past for the current year.')

        # Optional: Check for excessively future dates (e.g., more than 15-20 years out)
        if full_year > today.year + 15:  # Most cards are valid for max 5-10 years. 15 is a generous buffer.
            raise forms.ValidationError('Expiration date is too far in the future. Please check.')

        return expiration_date_str

    def clean_card_number(self):
        card_number = self.cleaned_data['card_number']
        # Remove any spaces or hyphens from the input
        cleaned_card_number = re.sub(r'[\s\-]', '', card_number)

        if not cleaned_card_number.isdigit():
            raise forms.ValidationError('Card number must contain only digits.')

        # Common range for credit card numbers (13 to 19 digits)
        if not (13 <= len(cleaned_card_number) <= 19):
            raise forms.ValidationError('Card number has an invalid length.')

        # For more robust validation, consider implementing or using a library for the Luhn algorithm.
        # Example (uncomment if you add the _luhn_checksum_valid helper method):
        # if not self._luhn_checksum_valid(cleaned_card_number):
        #     raise forms.ValidationError('Invalid card number.')

        return cleaned_card_number  # Return the cleaned (digits-only) card number

    # Optional: Example Luhn algorithm check (add this method if you uncommented its call above)
    # def _luhn_checksum_valid(self, card_number):
    #     digits = [int(d) for d in card_number]
    #     odd_digits = digits[-1::-2]
    #     even_digits = digits[-2::-2]
    #     total = sum(odd_digits)
    #     for digit in even_digits:
    #         total += sum(divmod(digit * 2, 10))
    #     return total % 10 == 0
    # --- End of Expiration and Card Number Validation Methods ---


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        exclude = ['id']  # this ensures 'id' is not rendered

    def __init__(self, *args, **kwargs):
        super(CarForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'


class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'delivery_date', 'delivery_address', 'phone_number']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # Custom __init__ to parse the phone number from old delivery_address values
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we are editing an existing order instance
        if self.instance and self.instance.delivery_address:
            # If phone_number is already populated (for newly created orders or converted ones)
            if self.instance.phone_number:
                self.initial['phone_number'] = self.instance.phone_number
                # The delivery_address from the instance should already be clean if phone_number is set
            else:
                # This is for old orders where phone number is embedded in delivery_address
                # Attempt to parse phone number from delivery_address
                address_lines = self.instance.delivery_address.split('\n')
                # Regex to find a line starting with 'Phone:' and capture the digits
                phone_pattern = r'^\s*Phone:\s*(\d{10,})\s*$'

                parsed_phone = None
                clean_address_lines = []

                for line in address_lines:
                    match = re.search(phone_pattern, line, re.IGNORECASE)
                    if match:
                        parsed_phone = match.group(1)
                    else:
                        clean_address_lines.append(line)

                if parsed_phone:
                    self.initial['phone_number'] = parsed_phone
                    # Update initial delivery_address to remove the phone line
                    self.initial['delivery_address'] = '\n'.join(clean_address_lines).strip()
                # If no phone found, leave initial delivery_address as is and phone_number empty.

    # Custom save method to ensure delivery_address does NOT contain the phone number upon saving
    def save(self, commit=True):
        # Get the Order instance from the form, but don't save to the database yet
        order = super().save(commit=False)

        # Ensure that the delivery_address stored does NOT contain the phone number.
        # This is for consistency, especially when editing older data or if someone manually typed phone in address.
        if order.delivery_address:
            address_lines = order.delivery_address.split('\n')
            phone_pattern = r'^\s*Phone:\s*\d{10,}\s*$'  # Again, pattern to remove phone line
            clean_address_lines = []
            for line in address_lines:
                if not re.search(phone_pattern, line, re.IGNORECASE):
                    clean_address_lines.append(line)
            order.delivery_address = '\n'.join(clean_address_lines).strip()

        if commit:
            order.save()
        return order


class DeliveryAssignmentForm(forms.ModelForm):
    agent = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),  # Initialize with empty queryset
        label="Select Delivery Agent",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = DeliveryAssignment
        fields = ['agent']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This explicit filtering is good for providing a specific error message
        # if the 'CarhubDeliveryAgent' group does not exist.
        try:
            delivery_agent_group = Group.objects.get(name='CarhubDeliveryAgent')
            self.fields['agent'].queryset = delivery_agent_group.user_set.all().order_by('username')
        except Group.DoesNotExist:
            self.fields['agent'].queryset = get_user_model().objects.none()
            self.fields[
                'agent'].help_text = "The 'CarhubDeliveryAgent' group does not exist. Please create it and assign users."
