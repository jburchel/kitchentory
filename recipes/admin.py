from django.contrib import admin
from django.utils.html import format_html
from .models import (
    RecipeCategory,
    RecipeTag,
    Recipe,
    RecipeIngredient,
    RecipeStep,
    UserRecipeInteraction,
    RecipeReview,
    CookingSession,
)


@admin.register(RecipeCategory)
class RecipeCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "color_display", "order"]
    list_filter = ["parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "name"]

    def color_display(self, obj):
        if obj.color:
            return format_html(
                '<span style="color: {}; font-weight: bold;">● {}</span>',
                obj.color,
                obj.color,
            )
        return "-"

    color_display.short_description = "Color"


@admin.register(RecipeTag)
class RecipeTagAdmin(admin.ModelAdmin):
    list_display = ["name", "color_display"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def color_display(self, obj):
        if obj.color:
            return format_html(
                '<span style="color: {}; font-weight: bold;">● {}</span>',
                obj.color,
                obj.color,
            )
        return "-"

    color_display.short_description = "Color"


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    fields = [
        "order",
        "name",
        "quantity",
        "unit",
        "preparation",
        "group",
        "is_optional",
        "product",
    ]
    ordering = ["order"]


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1
    fields = [
        "step_number",
        "title",
        "instruction",
        "step_type",
        "time_minutes",
        "equipment_needed",
    ]
    ordering = ["step_number"]


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "difficulty",
        "total_time",
        "servings",
        "rating_display",
        "is_public",
        "is_verified",
        "created_by",
    ]
    list_filter = [
        "category",
        "difficulty",
        "is_public",
        "is_verified",
        "is_vegetarian",
        "is_vegan",
        "is_gluten_free",
    ]
    search_fields = ["title", "description", "author"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["tags"]
    inlines = [RecipeIngredientInline, RecipeStepInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "slug", "description", "category", "tags")},
        ),
        (
            "Timing & Difficulty",
            {
                "fields": (
                    "prep_time",
                    "cook_time",
                    "total_time",
                    "difficulty",
                    "servings",
                    "serving_unit",
                )
            },
        ),
        (
            "Nutrition",
            {
                "fields": (
                    "calories_per_serving",
                    "protein_grams",
                    "carb_grams",
                    "fat_grams",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Media",
            {"fields": ("image", "image_url", "video_url"), "classes": ("collapse",)},
        ),
        (
            "Source",
            {
                "fields": ("source_name", "source_url", "author"),
                "classes": ("collapse",),
            },
        ),
        ("Status", {"fields": ("created_by", "is_public", "is_verified")}),
        (
            "Dietary Restrictions",
            {
                "fields": (
                    "is_vegetarian",
                    "is_vegan",
                    "is_gluten_free",
                    "is_dairy_free",
                    "is_nut_free",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def rating_display(self, obj):
        if obj.rating_count > 0:
            stars = "★" * int(obj.rating_average) + "☆" * (5 - int(obj.rating_average))
            return f"{stars} ({obj.rating_average:.1f}/5, {obj.rating_count} reviews)"
        return "No ratings"

    rating_display.short_description = "Rating"


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = [
        "recipe",
        "order",
        "name",
        "quantity",
        "unit",
        "preparation",
        "is_optional",
    ]
    list_filter = ["unit", "is_optional", "recipe__category"]
    search_fields = ["name", "recipe__title"]
    ordering = ["recipe", "order"]


@admin.register(RecipeStep)
class RecipeStepAdmin(admin.ModelAdmin):
    list_display = [
        "recipe",
        "step_number",
        "title",
        "step_type",
        "time_minutes",
        "is_critical",
    ]
    list_filter = ["step_type", "is_critical", "recipe__category"]
    search_fields = ["title", "instruction", "recipe__title"]
    ordering = ["recipe", "step_number"]


@admin.register(UserRecipeInteraction)
class UserRecipeInteractionAdmin(admin.ModelAdmin):
    list_display = ["user", "recipe", "interaction_type", "created_at"]
    list_filter = ["interaction_type", "created_at"]
    search_fields = ["user__username", "recipe__title"]
    date_hierarchy = "created_at"


@admin.register(RecipeReview)
class RecipeReviewAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "recipe",
        "rating",
        "difficulty_rating",
        "would_make_again",
        "is_verified_cook",
        "created_at",
    ]
    list_filter = [
        "rating",
        "difficulty_rating",
        "would_make_again",
        "is_verified_cook",
        "made_modifications",
    ]
    search_fields = ["user__username", "recipe__title", "title", "comment"]
    date_hierarchy = "created_at"
    readonly_fields = ["helpful_votes"]


@admin.register(CookingSession)
class CookingSessionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "recipe",
        "status",
        "servings_planned",
        "progress_display",
        "total_cooking_time",
        "created_at",
    ]
    list_filter = ["status", "would_repeat", "success_rating"]
    search_fields = ["user__username", "recipe__title"]
    date_hierarchy = "created_at"

    def progress_display(self, obj):
        if obj.current_step:
            return (
                f"{obj.progress_percentage:.0f}% (Step {obj.current_step.step_number})"
            )
        return "0%"

    progress_display.short_description = "Progress"
