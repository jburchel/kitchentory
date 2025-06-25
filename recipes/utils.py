"""
Recipe import utilities for parsing recipes from URLs.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse
from django.utils.text import slugify
from decimal import Decimal
from .models import Recipe, RecipeCategory, RecipeTag, RecipeIngredient, RecipeStep


class RecipeParser:
    """
    Parse recipes from various websites using structured data and HTML parsing.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def parse_recipe_url(self, url):
        """
        Parse a recipe from a URL.
        Returns a dictionary with recipe data or None if parsing fails.
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to parse JSON-LD structured data first
            recipe_data = self._parse_json_ld(soup)
            
            # If no JSON-LD found, try microdata
            if not recipe_data:
                recipe_data = self._parse_microdata(soup)
            
            # If still no data, try site-specific parsing
            if not recipe_data:
                recipe_data = self._parse_site_specific(soup, url)
            
            # If still no data, try generic HTML parsing
            if not recipe_data:
                recipe_data = self._parse_generic_html(soup)
            
            if recipe_data:
                recipe_data['source_url'] = url
                recipe_data['source_name'] = self._get_site_name(url)
                return self._clean_recipe_data(recipe_data)
            
            return None
            
        except Exception as e:
            print(f"Error parsing recipe from {url}: {str(e)}")
            return None
    
    def _parse_json_ld(self, soup):
        """
        Parse JSON-LD structured data (Schema.org Recipe).
        """
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Handle array of objects
                if isinstance(data, list):
                    for item in data:
                        if self._is_recipe_object(item):
                            return self._extract_recipe_from_json_ld(item)
                else:
                    # Handle single object or nested objects
                    recipe = self._find_recipe_in_json_ld(data)
                    if recipe:
                        return self._extract_recipe_from_json_ld(recipe)
                        
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return None
    
    def _is_recipe_object(self, obj):
        """Check if an object is a recipe."""
        if not isinstance(obj, dict):
            return False
        
        obj_type = obj.get('@type', '').lower()
        return 'recipe' in obj_type or obj.get('recipeIngredient') or obj.get('recipeInstructions')
    
    def _find_recipe_in_json_ld(self, data):
        """Recursively find recipe object in nested JSON-LD."""
        if isinstance(data, dict):
            if self._is_recipe_object(data):
                return data
            
            # Check nested objects
            for value in data.values():
                if isinstance(value, (dict, list)):
                    result = self._find_recipe_in_json_ld(value)
                    if result:
                        return result
        
        elif isinstance(data, list):
            for item in data:
                result = self._find_recipe_in_json_ld(item)
                if result:
                    return result
        
        return None
    
    def _extract_recipe_from_json_ld(self, recipe_obj):
        """Extract recipe data from JSON-LD object."""
        data = {
            'title': self._get_text_value(recipe_obj.get('name')),
            'description': self._get_text_value(recipe_obj.get('description')),
            'image_url': self._get_image_url(recipe_obj.get('image')),
            'author': self._get_author(recipe_obj.get('author')),
            'servings': self._get_servings(recipe_obj.get('recipeYield')),
            'prep_time': self._parse_duration(recipe_obj.get('prepTime')),
            'cook_time': self._parse_duration(recipe_obj.get('cookTime')),
            'total_time': self._parse_duration(recipe_obj.get('totalTime')),
            'ingredients': self._get_ingredients(recipe_obj.get('recipeIngredient', [])),
            'instructions': self._get_instructions(recipe_obj.get('recipeInstructions', [])),
            'nutrition': self._get_nutrition(recipe_obj.get('nutrition')),
            'category': self._get_category(recipe_obj.get('recipeCategory')),
            'cuisine': self._get_text_value(recipe_obj.get('recipeCuisine')),
            'keywords': self._get_keywords(recipe_obj.get('keywords')),
        }
        
        return data
    
    def _parse_microdata(self, soup):
        """Parse microdata structured data."""
        # Look for recipe microdata
        recipe_elem = soup.find(attrs={'itemtype': re.compile(r'.*Recipe', re.I)})
        
        if not recipe_elem:
            return None
        
        data = {
            'title': self._get_microdata_property(recipe_elem, 'name'),
            'description': self._get_microdata_property(recipe_elem, 'description'),
            'image_url': self._get_microdata_property(recipe_elem, 'image', 'src'),
            'author': self._get_microdata_property(recipe_elem, 'author'),
            'prep_time': self._parse_duration(self._get_microdata_property(recipe_elem, 'prepTime')),
            'cook_time': self._parse_duration(self._get_microdata_property(recipe_elem, 'cookTime')),
            'total_time': self._parse_duration(self._get_microdata_property(recipe_elem, 'totalTime')),
            'servings': self._get_microdata_property(recipe_elem, 'recipeYield'),
            'ingredients': self._get_microdata_list(recipe_elem, 'recipeIngredient'),
            'instructions': self._get_microdata_instructions(recipe_elem),
        }
        
        return data
    
    def _parse_site_specific(self, soup, url):
        """Site-specific parsing for popular recipe websites."""
        domain = urlparse(url).netloc.lower().replace('www.', '')
        
        if 'allrecipes.com' in domain:
            return self._parse_allrecipes(soup)
        elif 'food.com' in domain:
            return self._parse_food_com(soup)
        elif 'foodnetwork.com' in domain:
            return self._parse_foodnetwork(soup)
        # Add more site-specific parsers as needed
        
        return None
    
    def _parse_generic_html(self, soup):
        """Generic HTML parsing fallback."""
        data = {}
        
        # Try to find title
        title_selectors = [
            'h1.recipe-title', 'h1.entry-title', 'h1[class*="title"]',
            '.recipe-header h1', '.entry-header h1', 'h1'
        ]
        data['title'] = self._find_text_by_selectors(soup, title_selectors)
        
        # Try to find description
        desc_selectors = [
            '.recipe-description', '.entry-content p:first-of-type',
            '.recipe-summary', '.description'
        ]
        data['description'] = self._find_text_by_selectors(soup, desc_selectors)
        
        # Try to find ingredients
        ingredient_selectors = [
            '.recipe-ingredients li', '.ingredients li',
            '.recipe-ingredient', '[class*="ingredient"]'
        ]
        data['ingredients'] = self._find_list_by_selectors(soup, ingredient_selectors)
        
        # Try to find instructions
        instruction_selectors = [
            '.recipe-instructions li', '.instructions li',
            '.recipe-instruction', '.directions li', '[class*="instruction"]'
        ]
        data['instructions'] = self._find_list_by_selectors(soup, instruction_selectors)
        
        return data if data.get('title') else None
    
    def _get_text_value(self, value):
        """Extract text from various value types."""
        if isinstance(value, str):
            return value.strip()
        elif isinstance(value, dict):
            return value.get('name', '') or value.get('text', '') or str(value)
        elif isinstance(value, list) and value:
            return self._get_text_value(value[0])
        return ''
    
    def _get_image_url(self, image_data):
        """Extract image URL from various formats."""
        if isinstance(image_data, str):
            return image_data
        elif isinstance(image_data, dict):
            return image_data.get('url', '')
        elif isinstance(image_data, list) and image_data:
            return self._get_image_url(image_data[0])
        return ''
    
    def _get_author(self, author_data):
        """Extract author name."""
        if isinstance(author_data, str):
            return author_data
        elif isinstance(author_data, dict):
            return author_data.get('name', '')
        elif isinstance(author_data, list) and author_data:
            return self._get_author(author_data[0])
        return ''
    
    def _get_servings(self, yield_data):
        """Extract serving count."""
        if isinstance(yield_data, (int, float)):
            return int(yield_data)
        elif isinstance(yield_data, str):
            # Extract number from string like "4-6 servings"
            match = re.search(r'(\d+)', yield_data)
            return int(match.group(1)) if match else 4
        elif isinstance(yield_data, list) and yield_data:
            return self._get_servings(yield_data[0])
        return 4
    
    def _parse_duration(self, duration_str):
        """Parse ISO 8601 duration or time strings to minutes."""
        if not duration_str:
            return None
        
        duration_str = str(duration_str).upper()
        
        # Handle ISO 8601 duration (PT15M, PT1H30M)
        if duration_str.startswith('PT'):
            minutes = 0
            
            # Extract hours
            hour_match = re.search(r'(\d+)H', duration_str)
            if hour_match:
                minutes += int(hour_match.group(1)) * 60
            
            # Extract minutes
            min_match = re.search(r'(\d+)M', duration_str)
            if min_match:
                minutes += int(min_match.group(1))
            
            return minutes if minutes > 0 else None
        
        # Handle simple time formats (15 minutes, 1 hour 30 minutes)
        total_minutes = 0
        
        # Extract hours
        hour_match = re.search(r'(\d+)\s*h', duration_str, re.I)
        if hour_match:
            total_minutes += int(hour_match.group(1)) * 60
        
        # Extract minutes
        min_match = re.search(r'(\d+)\s*m', duration_str, re.I)
        if min_match:
            total_minutes += int(min_match.group(1))
        
        # If no units found, assume it's minutes
        if total_minutes == 0:
            number_match = re.search(r'(\d+)', duration_str)
            if number_match:
                total_minutes = int(number_match.group(1))
        
        return total_minutes if total_minutes > 0 else None
    
    def _get_ingredients(self, ingredients_data):
        """Extract ingredients list."""
        ingredients = []
        
        if isinstance(ingredients_data, list):
            for item in ingredients_data:
                text = self._get_text_value(item)
                if text:
                    ingredients.append(text)
        elif isinstance(ingredients_data, str):
            ingredients = [ingredients_data]
        
        return ingredients
    
    def _get_instructions(self, instructions_data):
        """Extract instructions list."""
        instructions = []
        
        if isinstance(instructions_data, list):
            for item in instructions_data:
                if isinstance(item, dict):
                    text = item.get('text', '') or item.get('name', '')
                else:
                    text = self._get_text_value(item)
                
                if text:
                    instructions.append(text)
        elif isinstance(instructions_data, str):
            instructions = [instructions_data]
        
        return instructions
    
    def _get_nutrition(self, nutrition_data):
        """Extract nutrition information."""
        if not isinstance(nutrition_data, dict):
            return {}
        
        return {
            'calories': self._parse_number(nutrition_data.get('calories')),
            'protein': self._parse_number(nutrition_data.get('proteinContent')),
            'carbs': self._parse_number(nutrition_data.get('carbohydrateContent')),
            'fat': self._parse_number(nutrition_data.get('fatContent')),
        }
    
    def _parse_number(self, value):
        """Parse numeric value from string."""
        if isinstance(value, (int, float)):
            return value
        elif isinstance(value, str):
            # Extract first number from string
            match = re.search(r'(\d+(?:\.\d+)?)', value)
            return float(match.group(1)) if match else None
        return None
    
    def _get_category(self, category_data):
        """Extract category."""
        return self._get_text_value(category_data)
    
    def _get_keywords(self, keywords_data):
        """Extract keywords/tags."""
        if isinstance(keywords_data, str):
            return [k.strip() for k in keywords_data.split(',')]
        elif isinstance(keywords_data, list):
            return [self._get_text_value(k) for k in keywords_data]
        return []
    
    def _get_site_name(self, url):
        """Extract site name from URL."""
        domain = urlparse(url).netloc.lower()
        domain = domain.replace('www.', '')
        
        site_names = {
            'allrecipes.com': 'Allrecipes',
            'food.com': 'Food.com',
            'foodnetwork.com': 'Food Network',
            'epicurious.com': 'Epicurious',
            'cooking.nytimes.com': 'NYT Cooking',
            'tasty.co': 'Tasty',
            'delish.com': 'Delish',
            'eatingwell.com': 'EatingWell',
            'simplyrecipes.com': 'Simply Recipes',
            'budgetbytes.com': 'Budget Bytes',
        }
        
        return site_names.get(domain, domain.title())
    
    def _clean_recipe_data(self, data):
        """Clean and validate recipe data."""
        # Clean text fields
        for field in ['title', 'description', 'author', 'category', 'cuisine']:
            if data.get(field):
                data[field] = re.sub(r'\s+', ' ', data[field]).strip()
        
        # Ensure we have required fields
        if not data.get('title'):
            return None
        
        # Clean ingredients and instructions
        if data.get('ingredients'):
            data['ingredients'] = [
                re.sub(r'\s+', ' ', ing).strip() 
                for ing in data['ingredients'] 
                if ing and ing.strip()
            ]
        
        if data.get('instructions'):
            data['instructions'] = [
                re.sub(r'\s+', ' ', inst).strip() 
                for inst in data['instructions'] 
                if inst and inst.strip()
            ]
        
        return data
    
    # Helper methods for microdata parsing
    def _get_microdata_property(self, elem, prop, attr='text'):
        """Get microdata property value."""
        prop_elem = elem.find(attrs={'itemprop': prop})
        if not prop_elem:
            return ''
        
        if attr == 'text':
            return prop_elem.get_text(strip=True)
        else:
            return prop_elem.get(attr, '')
    
    def _get_microdata_list(self, elem, prop):
        """Get list of microdata properties."""
        prop_elems = elem.find_all(attrs={'itemprop': prop})
        return [elem.get_text(strip=True) for elem in prop_elems]
    
    def _get_microdata_instructions(self, elem):
        """Get microdata instructions."""
        # Try different instruction patterns
        instructions = []
        
        # Look for HowToStep items
        steps = elem.find_all(attrs={'itemtype': re.compile(r'.*HowToStep', re.I)})
        for step in steps:
            text = self._get_microdata_property(step, 'text')
            if text:
                instructions.append(text)
        
        # Fallback to simple recipeInstructions
        if not instructions:
            instructions = self._get_microdata_list(elem, 'recipeInstructions')
        
        return instructions
    
    # Helper methods for generic parsing
    def _find_text_by_selectors(self, soup, selectors):
        """Find text using CSS selectors."""
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    return text
        return ''
    
    def _find_list_by_selectors(self, soup, selectors):
        """Find list of text using CSS selectors."""
        for selector in selectors:
            elems = soup.select(selector)
            if elems:
                texts = [elem.get_text(strip=True) for elem in elems]
                texts = [t for t in texts if t]  # Filter empty
                if texts:
                    return texts
        return []


def import_recipe_from_url(url):
    """
    Import recipe from URL using RecipeParser.
    """
    parser = RecipeParser()
    return parser.parse_recipe_url(url)


def create_recipe_from_data(recipe_data, user, make_public=False):
    """
    Create a Recipe object from parsed recipe data.
    """
    if not recipe_data or not recipe_data.get('title'):
        return None
    
    # Create base recipe
    recipe = Recipe(
        title=recipe_data['title'][:200],  # Truncate to field limit
        description=recipe_data.get('description', '')[:1000],
        created_by=user,
        is_public=make_public,
        source_url=recipe_data.get('source_url', ''),
        source_name=recipe_data.get('source_name', ''),
        author=recipe_data.get('author', '')[:200],
        image_url=recipe_data.get('image_url', ''),
        prep_time=recipe_data.get('prep_time') or 0,
        cook_time=recipe_data.get('cook_time') or 0,
        servings=recipe_data.get('servings', 4)
    )
    
    # Calculate total time
    recipe.total_time = (recipe.prep_time or 0) + (recipe.cook_time or 0)
    
    # Set nutrition if available
    nutrition = recipe_data.get('nutrition', {})
    if nutrition.get('calories'):
        recipe.calories_per_serving = int(nutrition['calories'])
    if nutrition.get('protein'):
        recipe.protein_grams = Decimal(str(nutrition['protein']))
    if nutrition.get('carbs'):
        recipe.carb_grams = Decimal(str(nutrition['carbs']))
    if nutrition.get('fat'):
        recipe.fat_grams = Decimal(str(nutrition['fat']))
    
    # Try to find matching category
    category_name = recipe_data.get('category') or recipe_data.get('cuisine')
    if category_name:
        try:
            recipe.category = RecipeCategory.objects.filter(
                name__icontains=category_name
            ).first()
        except:
            pass
    
    # Generate unique slug
    base_slug = slugify(recipe.title)
    recipe.slug = base_slug
    counter = 1
    while Recipe.objects.filter(slug=recipe.slug).exists():
        recipe.slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Save recipe
    recipe.save()
    
    # Add ingredients
    ingredients = recipe_data.get('ingredients', [])
    for i, ingredient_text in enumerate(ingredients):
        if ingredient_text:
            # Parse ingredient (reuse the parsing logic from views)
            from .views import parse_ingredient_line
            parsed = parse_ingredient_line(ingredient_text)
            
            RecipeIngredient.objects.create(
                recipe=recipe,
                order=i + 1,
                name=parsed['name'][:200],
                quantity=parsed['quantity'],
                unit=parsed['unit'],
                preparation=parsed['preparation'][:200]
            )
    
    # Add instructions
    instructions = recipe_data.get('instructions', [])
    for i, instruction_text in enumerate(instructions):
        if instruction_text:
            RecipeStep.objects.create(
                recipe=recipe,
                step_number=i + 1,
                instruction=instruction_text[:1000]
            )
    
    # Add tags from keywords
    keywords = recipe_data.get('keywords', [])
    for keyword in keywords[:5]:  # Limit to 5 tags
        tag, created = RecipeTag.objects.get_or_create(
            name=keyword[:50],
            defaults={'slug': slugify(keyword)}
        )
        recipe.tags.add(tag)
    
    return recipe