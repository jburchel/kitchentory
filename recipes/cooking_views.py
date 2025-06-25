"""
Views for cooking mode functionality.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import json
from datetime import datetime, timedelta

from .models import Recipe, CookingSession, RecipeStep, UserRecipeInteraction
from .matching import check_recipe_cookability
from inventory.models import InventoryItem


@login_required
def start_cooking(request, slug):
    """
    Start a new cooking session for a recipe.
    """
    recipe = get_object_or_404(Recipe, slug=slug)
    
    # Check if user can view this recipe
    if not recipe.is_public and recipe.created_by != request.user:
        messages.error(request, _('You do not have permission to cook this recipe.'))
        return redirect('recipes:list')
    
    # Check recipe cookability
    match = check_recipe_cookability(request.user, recipe)
    
    # Handle serving size adjustment
    serving_multiplier = 1.0
    if request.method == 'POST':
        requested_servings = int(request.POST.get('servings', recipe.servings))
        serving_multiplier = requested_servings / recipe.servings if recipe.servings > 0 else 1.0
    else:
        requested_servings = recipe.servings
    
    # Create or get existing cooking session
    cooking_session, created = CookingSession.objects.get_or_create(
        user=request.user,
        recipe=recipe,
        status__in=['planning', 'cooking', 'paused'],
        defaults={
            'servings_planned': requested_servings,
            'status': 'planning'
        }
    )
    
    # If not created, update servings if different
    if not created and cooking_session.servings_planned != requested_servings:
        cooking_session.servings_planned = requested_servings
        cooking_session.save()
    
    context = {
        'recipe': recipe,
        'cooking_session': cooking_session,
        'match': match,
        'serving_multiplier': serving_multiplier,
        'requested_servings': requested_servings,
        'ingredients': recipe.ingredients.all().order_by('order'),
        'steps': recipe.steps.all().order_by('step_number'),
    }
    
    return render(request, 'recipes/cooking/start.html', context)


@login_required
def cooking_mode(request, slug):
    """
    Active cooking mode interface with step-by-step navigation.
    """
    recipe = get_object_or_404(Recipe, slug=slug)
    
    # Get or create cooking session
    try:
        cooking_session = CookingSession.objects.get(
            user=request.user,
            recipe=recipe,
            status__in=['planning', 'cooking', 'paused']
        )
    except CookingSession.DoesNotExist:
        # Redirect to start cooking if no session
        return redirect('recipes:cooking:start', slug=slug)
    
    # Start the session if it's in planning
    if cooking_session.status == 'planning':
        cooking_session.start_cooking()
    
    # Get current step
    current_step_number = int(request.GET.get('step', 1))
    steps = recipe.steps.all().order_by('step_number')
    
    if not steps.exists():
        messages.warning(request, _('This recipe has no cooking steps defined.'))
        return redirect('recipes:detail', slug=slug)
    
    # Ensure step number is valid
    total_steps = steps.count()
    current_step_number = max(1, min(current_step_number, total_steps))
    
    try:
        current_step = steps.get(step_number=current_step_number)
        cooking_session.current_step = current_step
        cooking_session.save()
    except RecipeStep.DoesNotExist:
        current_step = steps.first()
    
    # Get previous and next steps
    previous_step = steps.filter(step_number__lt=current_step_number).last()
    next_step = steps.filter(step_number__gt=current_step_number).first()
    
    # Calculate progress
    progress_percentage = (current_step_number / total_steps) * 100
    
    # Adjust ingredients for serving size
    serving_multiplier = cooking_session.servings_planned / recipe.servings if recipe.servings > 0 else 1.0
    ingredients = recipe.ingredients.all().order_by('order')
    
    context = {
        'recipe': recipe,
        'cooking_session': cooking_session,
        'current_step': current_step,
        'current_step_number': current_step_number,
        'total_steps': total_steps,
        'previous_step': previous_step,
        'next_step': next_step,
        'progress_percentage': progress_percentage,
        'serving_multiplier': serving_multiplier,
        'ingredients': ingredients,
        'all_steps': steps,
    }
    
    return render(request, 'recipes/cooking/mode.html', context)


@login_required
@require_http_methods(["POST"])
def update_cooking_session(request, session_id):
    """
    Update cooking session status and progress.
    """
    cooking_session = get_object_or_404(
        CookingSession, 
        id=session_id, 
        user=request.user
    )
    
    data = json.loads(request.body)
    action = data.get('action')
    
    if action == 'pause':
        cooking_session.status = 'paused'
        cooking_session.save()
        
    elif action == 'resume':
        cooking_session.status = 'cooking'
        cooking_session.save()
        
    elif action == 'complete':
        cooking_session.complete_cooking()
        
        # Create interaction record
        UserRecipeInteraction.objects.get_or_create(
            user=request.user,
            recipe=cooking_session.recipe,
            interaction_type='cook'
        )
        
    elif action == 'abandon':
        cooking_session.status = 'abandoned'
        cooking_session.save()
        
    elif action == 'update_step':
        step_number = data.get('step_number')
        if step_number:
            try:
                step = cooking_session.recipe.steps.get(step_number=step_number)
                cooking_session.current_step = step
                cooking_session.save()
            except RecipeStep.DoesNotExist:
                return JsonResponse({'error': 'Invalid step number'}, status=400)
    
    return JsonResponse({
        'status': cooking_session.status,
        'current_step': cooking_session.current_step.step_number if cooking_session.current_step else None,
        'progress': cooking_session.progress_percentage
    })


@login_required
@require_http_methods(["POST"])
def toggle_ingredient_check(request):
    """
    Toggle ingredient check-off status.
    """
    data = json.loads(request.body)
    ingredient_id = data.get('ingredient_id')
    checked = data.get('checked', False)
    
    # For now, just return success (could store in session or database)
    return JsonResponse({
        'success': True,
        'ingredient_id': ingredient_id,
        'checked': checked
    })


@login_required
@require_http_methods(["POST"])
def deplete_inventory(request):
    """
    Deplete inventory items after cooking a recipe.
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    
    cooking_session = get_object_or_404(
        CookingSession, 
        id=session_id, 
        user=request.user
    )
    
    # Get the recipe and calculate quantities needed
    recipe = cooking_session.recipe
    serving_multiplier = cooking_session.servings_planned / recipe.servings if recipe.servings > 0 else 1.0
    
    depleted_items = []
    warnings = []
    
    for recipe_ingredient in recipe.ingredients.all():
        if recipe_ingredient.product and recipe_ingredient.quantity:
            try:
                inventory_item = InventoryItem.objects.get(
                    user=request.user,
                    product=recipe_ingredient.product
                )
                
                # Calculate amount to deplete
                amount_needed = float(recipe_ingredient.quantity) * serving_multiplier
                
                if inventory_item.quantity >= amount_needed:
                    # Sufficient quantity - deplete it
                    inventory_item.quantity -= amount_needed
                    inventory_item.save()
                    
                    depleted_items.append({
                        'name': recipe_ingredient.name,
                        'amount_used': amount_needed,
                        'remaining': float(inventory_item.quantity)
                    })
                    
                    # Check if item is running low
                    if inventory_item.quantity <= 1.0:  # Configurable threshold
                        warnings.append({
                            'name': recipe_ingredient.name,
                            'remaining': float(inventory_item.quantity),
                            'message': 'Running low - consider adding to shopping list'
                        })
                else:
                    # Insufficient quantity - use what's available
                    amount_used = float(inventory_item.quantity)
                    inventory_item.quantity = 0
                    inventory_item.save()
                    
                    depleted_items.append({
                        'name': recipe_ingredient.name,
                        'amount_used': amount_used,
                        'remaining': 0
                    })
                    
                    warnings.append({
                        'name': recipe_ingredient.name,
                        'remaining': 0,
                        'message': 'Used all available - item now empty'
                    })
                    
            except InventoryItem.DoesNotExist:
                # Ingredient not in inventory
                warnings.append({
                    'name': recipe_ingredient.name,
                    'remaining': 0,
                    'message': 'Not found in inventory'
                })
    
    return JsonResponse({
        'success': True,
        'depleted_items': depleted_items,
        'warnings': warnings,
        'total_depleted': len(depleted_items)
    })


@login_required
def cooking_timer(request):
    """
    Standalone cooking timer page.
    """
    return render(request, 'recipes/cooking/timer.html')


@login_required
def cooking_history(request):
    """
    User's cooking session history.
    """
    sessions = CookingSession.objects.filter(
        user=request.user
    ).select_related('recipe').order_by('-created_at')[:50]
    
    # Group by status
    completed_sessions = sessions.filter(status='completed')
    abandoned_sessions = sessions.filter(status='abandoned')
    active_sessions = sessions.filter(status__in=['planning', 'cooking', 'paused'])
    
    context = {
        'completed_sessions': completed_sessions,
        'abandoned_sessions': abandoned_sessions,
        'active_sessions': active_sessions,
        'total_cooked': completed_sessions.count(),
    }
    
    return render(request, 'recipes/cooking/history.html', context)


@login_required
@require_http_methods(["POST"])
def adjust_serving_size(request):
    """
    Adjust serving size for active cooking session.
    """
    data = json.loads(request.body)
    session_id = data.get('session_id')
    new_servings = int(data.get('servings', 1))
    
    cooking_session = get_object_or_404(
        CookingSession, 
        id=session_id, 
        user=request.user
    )
    
    # Update serving size
    cooking_session.servings_planned = max(1, new_servings)
    cooking_session.save()
    
    # Calculate new multiplier
    serving_multiplier = cooking_session.servings_planned / cooking_session.recipe.servings if cooking_session.recipe.servings > 0 else 1.0
    
    # Return updated ingredient quantities
    updated_ingredients = []
    for ingredient in cooking_session.recipe.ingredients.all():
        if ingredient.quantity:
            adjusted_quantity = float(ingredient.quantity) * serving_multiplier
            updated_ingredients.append({
                'id': ingredient.id,
                'original_quantity': float(ingredient.quantity),
                'adjusted_quantity': adjusted_quantity,
                'display_quantity': f"{adjusted_quantity:.2f}".rstrip('0').rstrip('.')
            })
    
    return JsonResponse({
        'success': True,
        'new_servings': cooking_session.servings_planned,
        'serving_multiplier': serving_multiplier,
        'updated_ingredients': updated_ingredients
    })