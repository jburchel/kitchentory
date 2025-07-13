"""
Base models for recipe system: categories and tags.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class RecipeCategory(models.Model):
    """
    Recipe categories (Italian, Mexican, Vegetarian, etc.).
    """

    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), unique=True)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, default="#6B7280")
    icon = models.CharField(_("icon"), max_length=50, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    order = models.IntegerField(_("display order"), default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recipe_categories"
        verbose_name = _("recipe category")
        verbose_name_plural = _("recipe categories")
        ordering = ["order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class RecipeTag(models.Model):
    """
    Tags for recipes (quick, healthy, budget-friendly, etc.).
    """

    name = models.CharField(_("name"), max_length=50, unique=True)
    slug = models.SlugField(_("slug"), unique=True)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, default="#6B7280")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recipe_tags"
        verbose_name = _("recipe tag")
        verbose_name_plural = _("recipe tags")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Convert name to lowercase
        self.name = self.name.lower()
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)