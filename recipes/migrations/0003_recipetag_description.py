# Generated by Django 5.2.3 on 2025-06-22 19:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0002_recipe_instructions_recipe_name_alter_recipe_slug_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="recipetag",
            name="description",
            field=models.TextField(blank=True, verbose_name="description"),
        ),
    ]
