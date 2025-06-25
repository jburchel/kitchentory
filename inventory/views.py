from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from datetime import date, timedelta
import json

from .models import (
    Product, InventoryItem, Category, StorageLocation,
    ProductBarcode
)
from .forms import (
    ProductForm, InventoryItemForm, QuickAddForm,
    StorageLocationForm, BulkActionForm, ManualProductForm
)


@login_required
def inventory_dashboard(request):
    """Main inventory dashboard view."""
    household = request.user.household
    
    if not household:
        messages.info(request, _('Please create or join a household first.'))
        return redirect('accounts:household_create')
    
    # Get inventory statistics
    items = InventoryItem.objects.filter(
        household=household,
        is_consumed=False
    )
    
    stats = {
        'total_items': items.count(),
        'expiring_soon': items.filter(
            expiration_date__lte=date.today() + timedelta(days=7),
            expiration_date__gte=date.today()
        ).count(),
        'expired': items.filter(
            expiration_date__lt=date.today()
        ).count(),
        'categories': items.values('product__category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
    }
    
    # Get items expiring soon
    expiring_items = items.filter(
        expiration_date__lte=date.today() + timedelta(days=7)
    ).select_related(
        'product', 'product__category', 'location'
    ).order_by('expiration_date')[:10]
    
    # Get recent items
    recent_items = items.select_related(
        'product', 'product__category', 'location'
    ).order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'expiring_items': expiring_items,
        'recent_items': recent_items,
    }
    
    return render(request, 'inventory/dashboard.html', context)


@login_required
def inventory_list(request):
    """List all inventory items with filtering."""
    household = request.user.household
    
    if not household:
        return redirect('accounts:household_create')
    
    items = InventoryItem.objects.filter(
        household=household,
        is_consumed=False
    ).select_related('product', 'product__category', 'location')
    
    # Filtering
    category_id = request.GET.get('category')
    if category_id:
        items = items.filter(product__category_id=category_id)
    
    location_id = request.GET.get('location')
    if location_id:
        items = items.filter(location_id=location_id)
    
    search = request.GET.get('search')
    if search:
        items = items.filter(
            Q(product__name__icontains=search) |
            Q(product__brand__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Sorting
    sort = request.GET.get('sort', '-created_at')
    if sort in ['product__name', '-product__name', 'expiration_date', '-expiration_date', 'created_at', '-created_at']:
        items = items.order_by(sort)
    
    # Get filter options
    categories = Category.objects.filter(
        products__inventory_items__household=household,
        products__inventory_items__is_consumed=False
    ).distinct().annotate(
        item_count=Count('products__inventory_items')
    )
    
    locations = StorageLocation.objects.filter(
        household=household
    ).annotate(
        item_count=Count('items', filter=Q(items__is_consumed=False))
    )
    
    context = {
        'items': items,
        'categories': categories,
        'locations': locations,
        'current_filters': {
            'category': category_id,
            'location': location_id,
            'search': search,
            'sort': sort,
        }
    }
    
    return render(request, 'inventory/list.html', context)


@login_required
def add_item(request):
    """Add a new inventory item."""
    if request.method == 'POST':
        form = QuickAddForm(request.POST, user=request.user)
        if form.is_valid():
            # Create or get product
            product_data = {
                'name': form.cleaned_data['name'],
                'brand': form.cleaned_data['brand'],
                'category': form.cleaned_data['category'],
            }
            
            if form.cleaned_data['barcode']:
                product_data['barcode'] = form.cleaned_data['barcode']
            
            product, created = Product.objects.get_or_create(
                name__iexact=product_data['name'],
                brand__iexact=product_data['brand'] or '',
                defaults=product_data
            )
            
            # Create inventory item
            item = InventoryItem(
                user=request.user,
                household=request.user.household,
                product=product,
                current_quantity=form.cleaned_data['current_quantity'],
                unit=form.cleaned_data['unit'],
                location=form.cleaned_data['location'],
            )
            
            # Set expiration date if provided
            days = form.cleaned_data.get('days_until_expiration')
            if days:
                item.expiration_date = date.today() + timedelta(days=days)
            
            item.save()
            
            messages.success(request, _('Item added successfully!'))
            
            # Check if this is an HTMX request
            if request.headers.get('HX-Request'):
                return render(request, 'inventory/partials/item_card.html', {'item': item})
            
            return redirect('inventory:list')
    else:
        form = QuickAddForm(user=request.user)
    
    context = {
        'form': form,
    }
    
    return render(request, 'inventory/add_item.html', context)


@login_required
def item_detail(request, pk):
    """View and edit inventory item details."""
    item = get_object_or_404(
        InventoryItem,
        pk=pk,
        household=request.user.household
    )
    
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Item updated successfully!'))
            return redirect('inventory:detail', pk=pk)
    else:
        form = InventoryItemForm(instance=item, user=request.user)
    
    context = {
        'item': item,
        'form': form,
    }
    
    return render(request, 'inventory/item_detail.html', context)


@login_required
@require_http_methods(["POST"])
def consume_item(request, pk):
    """Mark an item as consumed."""
    item = get_object_or_404(
        InventoryItem,
        pk=pk,
        household=request.user.household
    )
    
    item.is_consumed = True
    item.consumed_date = timezone.now()
    item.save()
    
    messages.success(request, _(f'{item.product.name} marked as consumed.'))
    
    if request.headers.get('HX-Request'):
        return HttpResponse(status=200)
    
    return redirect('inventory:list')


@login_required
@require_http_methods(["DELETE"])
def delete_item(request, pk):
    """Delete an inventory item."""
    item = get_object_or_404(
        InventoryItem,
        pk=pk,
        household=request.user.household
    )
    
    item.delete()
    
    if request.headers.get('HX-Request'):
        return HttpResponse(status=200)
    
    messages.success(request, _('Item deleted successfully.'))
    return redirect('inventory:list')


@login_required
def product_search(request):
    """Enhanced AJAX endpoint for product search with autocomplete and fuzzy matching."""
    query = request.GET.get('q', '').strip()
    format_type = request.GET.get('format', 'json')  # 'json' or 'html'
    
    if len(query) < 2:
        if format_type == 'html':
            return HttpResponse('')
        return JsonResponse({'results': []})
    
    # Use the search method from our Product model (includes fuzzy matching)
    products = Product.search(query)[:10]
    
    # Check if we found exact matches or fuzzy matches
    exact_matches = Product._exact_search(query)[:10]
    is_fuzzy_search = not exact_matches.exists() and products.exists()
    
    if format_type == 'html':
        # Return HTML for HTMX autocomplete
        context = {
            'products': products,
            'query': query,
            'is_fuzzy_search': is_fuzzy_search,
            'fuzzy_message': f'Did you mean one of these? (searched for "{query}")' if is_fuzzy_search else None
        }
        html = render_to_string('inventory/partials/search_results.html', context, request)
        return HttpResponse(html)
    
    # Return JSON for traditional AJAX
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'brand': product.brand or '',
            'display_name': f"{product.brand} - {product.name}" if product.brand else product.name,
            'category': product.category.name if product.category else '',
            'image_url': product.image_url or '',
            'local_image': product.local_image.url if product.local_image else '',
            'barcode': product.barcode or ''
        })
    
    return JsonResponse({
        'results': results, 
        'query': query,
        'is_fuzzy_search': is_fuzzy_search,
        'fuzzy_message': f'Did you mean one of these? (searched for "{query}")' if is_fuzzy_search else None
    })


@login_required
def category_browse(request, category_id):
    """Browse products by category with pagination."""
    category = get_object_or_404(Category, id=category_id)
    
    # Get products in this category and its children
    child_categories = category.children.all() if hasattr(category, 'children') else []
    category_ids = [category.id] + [child.id for child in child_categories]
    
    products = Product.objects.filter(category_id__in=category_ids).order_by('name')
    
    # Add pagination
    from django.core.paginator import Paginator
    paginator = Paginator(products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    format_type = request.GET.get('format', 'html')
    
    if format_type == 'json':
        # Return JSON for AJAX requests
        results = []
        for product in page_obj:
            results.append({
                'id': product.id,
                'name': product.name,
                'brand': product.brand or '',
                'display_name': f"{product.brand} - {product.name}" if product.brand else product.name,
                'category': product.category.name if product.category else '',
                'image_url': product.image_url or '',
                'local_image': product.local_image.url if product.local_image else '',
                'barcode': product.barcode or ''
            })
        
        return JsonResponse({
            'results': results,
            'category': category.name,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages
        })
    
    # Return HTML template
    context = {
        'category': category,
        'products': page_obj,
        'child_categories': child_categories,
    }
    
    if request.headers.get('HX-Request'):
        # Return partial template for HTMX
        return render(request, 'inventory/partials/category_products.html', context)
    
    return render(request, 'inventory/category_browse.html', context)


@login_required
def barcode_lookup(request):
    """AJAX endpoint for barcode lookup."""
    barcode = request.GET.get('barcode', '')
    
    if not barcode:
        return JsonResponse({'error': 'No barcode provided'}, status=400)
    
    # First check our database
    product = Product.objects.filter(barcode=barcode).first()
    if not product:
        # Check additional barcodes
        barcode_entry = ProductBarcode.objects.filter(barcode=barcode).first()
        if barcode_entry:
            product = barcode_entry.product
    
    if product:
        return JsonResponse({
            'found': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'brand': product.brand,
                'category_id': product.category_id,
            }
        })
    
    # TODO: Implement external barcode API lookup
    return JsonResponse({'found': False})


@login_required
def storage_locations(request):
    """Manage storage locations."""
    if not request.user.household:
        return redirect('accounts:household_create')
    
    locations = StorageLocation.objects.filter(
        household=request.user.household
    ).annotate(
        item_count=Count('items', filter=Q(items__is_consumed=False))
    )
    
    if request.method == 'POST':
        form = StorageLocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.household = request.user.household
            location.save()
            messages.success(request, _('Storage location added successfully!'))
            return redirect('inventory:storage_locations')
    else:
        form = StorageLocationForm()
    
    context = {
        'locations': locations,
        'form': form,
    }
    
    return render(request, 'inventory/storage_locations.html', context)


@login_required
def add_product_manual(request):
    """Manually add a product that wasn't found in external databases."""
    
    # Check if user provided a barcode from scanning
    initial_barcode = request.GET.get('barcode', '')
    
    if request.method == 'POST':
        form = ManualProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, _('Product "{}" added successfully!').format(product.name))
            
            # Redirect to add inventory item for this product
            return redirect('inventory:add_item_for_product', product_id=product.id)
    else:
        # Pre-fill barcode if provided
        initial_data = {}
        if initial_barcode:
            initial_data['barcode'] = initial_barcode
        
        form = ManualProductForm(initial=initial_data)
    
    context = {
        'form': form,
        'initial_barcode': initial_barcode,
    }
    
    return render(request, 'inventory/add_product_manual.html', context)


@login_required
def add_item_for_product(request, product_id):
    """Add inventory item for a specific product."""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.household = request.user.household
            item.product = product
            item.save()
            
            messages.success(request, _('Item added to your inventory!'))
            return redirect('inventory:list')
    else:
        # Pre-fill form with product and sensible defaults
        initial_data = {
            'product': product,
            'unit': product.default_unit or 'count',
            'quantity': 1,
            'purchase_date': date.today()
        }
        form = InventoryItemForm(initial=initial_data, user=request.user)
        form.fields['product'].widget.attrs['readonly'] = True
    
    context = {
        'form': form,
        'product': product,
    }
    
    return render(request, 'inventory/add_item_for_product.html', context)