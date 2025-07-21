from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import ShoppingList, Store, ShoppingListItem
from subscriptions.decorators import usage_limit_required


@login_required
def shopping_dashboard(request):
    """Shopping dashboard view."""
    household = request.user.household

    if not household:
        messages.info(request, _("Please create or join a household first."))
        return redirect("accounts:household_create")

    # Get shopping lists for the household
    shopping_lists = (
        ShoppingList.objects.filter(household=household)
        .select_related("created_by")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    context = {
        "shopping_lists": shopping_lists,
        "household": household,
    }

    return render(request, "shopping/dashboard_simple.html", context)


@login_required
@usage_limit_required('shopping_list', redirect_to_upgrade=True)
def create_shopping_list(request):
    """Create a new shopping list."""
    household = request.user.household

    if not household:
        messages.info(request, _("Please create or join a household first."))
        return redirect("accounts:household_create")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        store_id = request.POST.get("store")

        if not name:
            messages.error(request, _("Please provide a name for your shopping list."))
        else:
            # Create the shopping list
            shopping_list = ShoppingList.objects.create(
                name=name,
                description=description,
                created_by=request.user,
                household=household,
                status="active",
                generation_source="manual",
            )

            # Update shopping list usage tracking
            from subscriptions.models import ShoppingListUsage
            usage, _ = ShoppingListUsage.objects.get_or_create(user=request.user)
            usage.increment_list_count()

            # Add store if selected
            if store_id:
                try:
                    store = Store.objects.get(id=store_id)
                    shopping_list.store = store
                    shopping_list.save()
                except Store.DoesNotExist:
                    pass

            messages.success(
                request, _('Shopping list "{}" created successfully!').format(name)
            )
            return redirect("shopping:dashboard")

    # Get available stores
    stores = Store.objects.all().order_by("name")

    context = {
        "stores": stores,
    }

    return render(request, "shopping/create_list.html", context)


@login_required
def shopping_list_detail(request, list_id):
    """View shopping list details and manage items."""
    household = request.user.household

    if not household:
        messages.info(request, _("Please create or join a household first."))
        return redirect("accounts:household_create")

    # Get the shopping list
    try:
        shopping_list = ShoppingList.objects.get(id=list_id, household=household)
    except ShoppingList.DoesNotExist:
        messages.error(request, _("Shopping list not found."))
        return redirect("shopping:dashboard")

    # Get items in the list
    items = shopping_list.items.all().order_by("section_order", "custom_order", "name")

    context = {
        "shopping_list": shopping_list,
        "items": items,
        "household": household,
    }

    return render(request, "shopping/list_detail.html", context)
