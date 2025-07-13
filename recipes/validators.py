"""
Recipe validation utilities.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def validate_recipe_title(title):
    """
    Validate recipe title.
    """
    if not title or not title.strip():
        raise ValidationError(_("Recipe title is required."))

    title = title.strip()

    if len(title) < 3:
        raise ValidationError(_("Recipe title must be at least 3 characters long."))

    if len(title) > 200:
        raise ValidationError(_("Recipe title must be 200 characters or less."))

    # Check for inappropriate content (basic check)
    inappropriate_words = ["spam", "advertisement", "buy now"]
    for word in inappropriate_words:
        if word.lower() in title.lower():
            raise ValidationError(_("Recipe title contains inappropriate content."))

    return title


def validate_recipe_ingredients(ingredients_data):
    """
    Validate recipe ingredients list.
    """
    errors = []

    if not ingredients_data:
        errors.append(_("At least one ingredient is required."))
        return errors

    # If it's a list of ingredient objects/dicts
    if isinstance(ingredients_data, list):
        valid_ingredients = 0

        for i, ingredient in enumerate(ingredients_data):
            if isinstance(ingredient, dict):
                name = ingredient.get("name", "").strip()
            else:
                name = str(ingredient).strip()

            if name:
                valid_ingredients += 1

                # Check ingredient name length
                if len(name) > 200:
                    errors.append(
                        _("Ingredient {}: Name must be 200 characters or less.").format(
                            i + 1
                        )
                    )

                # Check for valid ingredient format
                if not re.search(r"[a-zA-Z]", name):
                    errors.append(
                        _("Ingredient {}: Must contain at least one letter.").format(
                            i + 1
                        )
                    )

        if valid_ingredients == 0:
            errors.append(_("At least one valid ingredient is required."))

        if valid_ingredients > 50:
            errors.append(_("Maximum 50 ingredients allowed."))

    # If it's a text string (for quick create)
    elif isinstance(ingredients_data, str):
        lines = [line.strip() for line in ingredients_data.strip().split("\n")]
        valid_lines = [line for line in lines if line]

        if not valid_lines:
            errors.append(_("At least one ingredient is required."))

        if len(valid_lines) > 50:
            errors.append(_("Maximum 50 ingredients allowed."))

        for i, line in enumerate(valid_lines):
            if len(line) > 200:
                errors.append(
                    _("Ingredient {}: Must be 200 characters or less.").format(i + 1)
                )

    return errors


def validate_recipe_instructions(instructions_data):
    """
    Validate recipe instructions/steps.
    """
    errors = []

    if not instructions_data:
        errors.append(_("At least one cooking instruction is required."))
        return errors

    # If it's a list of step objects/dicts
    if isinstance(instructions_data, list):
        valid_steps = 0

        for i, step in enumerate(instructions_data):
            if isinstance(step, dict):
                instruction = step.get("instruction", "").strip()
            else:
                instruction = str(step).strip()

            if instruction:
                valid_steps += 1

                # Check instruction length
                if len(instruction) < 10:
                    errors.append(
                        _(
                            "Step {}: Instruction must be at least 10 characters long."
                        ).format(i + 1)
                    )

                if len(instruction) > 1000:
                    errors.append(
                        _(
                            "Step {}: Instruction must be 1000 characters or less."
                        ).format(i + 1)
                    )

        if valid_steps == 0:
            errors.append(_("At least one valid cooking step is required."))

        if valid_steps > 30:
            errors.append(_("Maximum 30 cooking steps allowed."))

    # If it's a text string (for quick create)
    elif isinstance(instructions_data, str):
        lines = [line.strip() for line in instructions_data.strip().split("\n")]
        valid_lines = [line for line in lines if line]

        if not valid_lines:
            errors.append(_("At least one cooking instruction is required."))

        if len(valid_lines) > 30:
            errors.append(_("Maximum 30 cooking steps allowed."))

        for i, line in enumerate(valid_lines):
            if len(line) < 10:
                errors.append(
                    _("Step {}: Must be at least 10 characters long.").format(i + 1)
                )

            if len(line) > 1000:
                errors.append(
                    _("Step {}: Must be 1000 characters or less.").format(i + 1)
                )

    return errors


def validate_recipe_timing(prep_time, cook_time, total_time=None):
    """
    Validate recipe timing.
    """
    errors = []

    # Check that at least one time is provided
    if not prep_time and not cook_time:
        errors.append(
            _("Please provide either preparation time, cooking time, or both.")
        )
        return errors

    # Validate individual times
    if prep_time is not None:
        if prep_time < 0:
            errors.append(_("Preparation time cannot be negative."))
        elif prep_time > 1440:  # 24 hours
            errors.append(_("Preparation time cannot exceed 24 hours."))

    if cook_time is not None:
        if cook_time < 0:
            errors.append(_("Cooking time cannot be negative."))
        elif cook_time > 1440:  # 24 hours
            errors.append(_("Cooking time cannot exceed 24 hours."))

    # Validate total time if provided
    calculated_total = (prep_time or 0) + (cook_time or 0)
    if total_time is not None and total_time != calculated_total:
        if abs(total_time - calculated_total) > 5:  # Allow 5 minute variance
            errors.append(
                _("Total time should equal preparation time plus cooking time.")
            )

    return errors


def validate_recipe_servings(servings):
    """
    Validate recipe servings.
    """
    errors = []

    if servings is None:
        errors.append(_("Number of servings is required."))
        return errors

    try:
        servings = int(servings)
        if servings < 1:
            errors.append(_("Number of servings must be at least 1."))
        elif servings > 100:
            errors.append(_("Number of servings cannot exceed 100."))
    except (ValueError, TypeError):
        errors.append(_("Number of servings must be a valid number."))

    return errors


def validate_recipe_nutrition(calories, protein, carbs, fat):
    """
    Validate nutritional information.
    """
    errors = []

    nutrition_fields = {
        "calories": (calories, 0, 5000, _("Calories")),
        "protein": (protein, 0, 200, _("Protein")),
        "carbs": (carbs, 0, 500, _("Carbohydrates")),
        "fat": (fat, 0, 200, _("Fat")),
    }

    for field_name, (value, min_val, max_val, display_name) in nutrition_fields.items():
        if value is not None:
            try:
                value = float(value)
                if value < min_val:
                    errors.append(_("{} cannot be negative.").format(display_name))
                elif value > max_val:
                    errors.append(
                        _("{} value seems too high (maximum {}).").format(
                            display_name, max_val
                        )
                    )
            except (ValueError, TypeError):
                errors.append(_("{} must be a valid number.").format(display_name))

    return errors


def validate_complete_recipe(recipe_data):
    """
    Validate a complete recipe with all components.
    """
    all_errors = []

    # Validate title
    try:
        validate_recipe_title(recipe_data.get("title", ""))
    except ValidationError as e:
        all_errors.extend(e.messages)

    # Validate ingredients
    ingredients_errors = validate_recipe_ingredients(recipe_data.get("ingredients", []))
    all_errors.extend(ingredients_errors)

    # Validate instructions
    instructions_errors = validate_recipe_instructions(
        recipe_data.get("instructions", [])
    )
    all_errors.extend(instructions_errors)

    # Validate timing
    timing_errors = validate_recipe_timing(
        recipe_data.get("prep_time"),
        recipe_data.get("cook_time"),
        recipe_data.get("total_time"),
    )
    all_errors.extend(timing_errors)

    # Validate servings
    servings_errors = validate_recipe_servings(recipe_data.get("servings"))
    all_errors.extend(servings_errors)

    # Validate nutrition if provided
    nutrition_errors = validate_recipe_nutrition(
        recipe_data.get("calories"),
        recipe_data.get("protein"),
        recipe_data.get("carbs"),
        recipe_data.get("fat"),
    )
    all_errors.extend(nutrition_errors)

    return all_errors


def clean_recipe_text(text):
    """
    Clean and sanitize recipe text content.
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # Remove potential HTML tags (basic cleaning)
    text = re.sub(r"<[^>]+>", "", text)

    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s\-.,;:!?()\'"\/°%&+]', "", text)

    return text


def validate_import_url(url):
    """
    Validate URL for recipe import.
    """
    if not url:
        raise ValidationError(_("URL is required."))

    # Basic URL format check
    if not re.match(r"^https?://", url):
        raise ValidationError(_("URL must start with http:// or https://"))

    # Check URL length
    if len(url) > 2000:
        raise ValidationError(_("URL is too long."))

    # Check for suspicious patterns
    suspicious_patterns = [
        r"javascript:",
        r"data:",
        r"file:",
        r"ftp:",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            raise ValidationError(_("URL contains invalid protocol."))

    return url
