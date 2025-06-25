from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import UpdateView
from django.urls import reverse_lazy

from .models import User, Household
from .forms import UserProfileForm, HouseholdForm, JoinHouseholdForm


@login_required
def profile_view(request):
    """Display user profile page."""
    context = {
        'user': request.user,
        'household': request.user.household,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """Edit user profile information."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully.'))
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def household_view(request):
    """Display household information and members."""
    household = request.user.household
    
    if not household:
        return redirect('accounts:household_create')
    
    members = household.members.all()
    
    context = {
        'household': household,
        'members': members,
        'is_admin': request.user.is_household_admin,
    }
    return render(request, 'accounts/household.html', context)


@login_required
def household_create_view(request):
    """Create a new household."""
    if request.user.household:
        messages.info(request, _('You are already part of a household.'))
        return redirect('accounts:household')
    
    if request.method == 'POST':
        form = HouseholdForm(request.POST)
        if form.is_valid():
            household = form.save(commit=False)
            household.created_by = request.user
            household.save()
            
            # Add the user to the household as admin
            request.user.household = household
            request.user.is_household_admin = True
            request.user.save()
            
            messages.success(request, _('Household created successfully.'))
            return redirect('accounts:household')
    else:
        form = HouseholdForm()
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/household_create.html', context)


@login_required
def household_join_view(request):
    """Join an existing household using an invite code."""
    if request.user.household:
        messages.info(request, _('You are already part of a household.'))
        return redirect('accounts:household')
    
    if request.method == 'POST':
        form = JoinHouseholdForm(request.POST)
        if form.is_valid():
            household = form.household
            
            # Add the user to the household
            request.user.household = household
            request.user.is_household_admin = False
            request.user.save()
            
            messages.success(request, _(f'You have joined {household.name}.'))
            return redirect('accounts:household')
    else:
        form = JoinHouseholdForm()
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/household_join.html', context)


@login_required
def household_leave_view(request):
    """Leave the current household."""
    if not request.user.household:
        messages.error(request, _('You are not part of any household.'))
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        household = request.user.household
        
        # Check if user is the only admin
        admin_count = household.members.filter(is_household_admin=True).count()
        if request.user.is_household_admin and admin_count == 1:
            messages.error(request, _('You cannot leave as you are the only admin. Please assign another admin first.'))
            return redirect('accounts:household')
        
        # Remove user from household
        request.user.household = None
        request.user.is_household_admin = False
        request.user.save()
        
        messages.success(request, _('You have left the household.'))
        return redirect('accounts:profile')
    
    return render(request, 'accounts/household_leave_confirm.html')


@login_required
def household_settings_view(request):
    """Edit household settings (admin only)."""
    if not request.user.household:
        return redirect('accounts:household_create')
    
    if not request.user.is_household_admin:
        messages.error(request, _('You do not have permission to edit household settings.'))
        return redirect('accounts:household')
    
    household = request.user.household
    
    if request.method == 'POST':
        form = HouseholdForm(request.POST, instance=household)
        if form.is_valid():
            form.save()
            messages.success(request, _('Household settings updated successfully.'))
            return redirect('accounts:household')
    else:
        form = HouseholdForm(instance=household)
    
    context = {
        'form': form,
        'household': household,
    }
    return render(request, 'accounts/household_settings.html', context)
