# register/views.py

from django.shortcuts import render, redirect
from .forms import RegisterForm
from django.contrib.auth.models import User,Group

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            uname = form.cleaned_data['username']
            user = form.save()

            try:
                carhub_customer_group = Group.objects.get(name='CarhubCustomer')
                user.groups.add(carhub_customer_group)
                user.save()
                print(f"User '{uname}' registered and added to 'CarhubCustomer' group.") # For debugging
            except Group.DoesNotExist:
                print("Error: 'CarhubCustomer' group does not exist. Please create it in Django Admin.")

            return redirect('login')

        else:
            print("Form is NOT valid. Errors:", form.errors)
            return render(request, "register.html", {"form": form})
    else:
        form = RegisterForm()

    return render(request, "register.html", {"form": form})