# Generated by Django 5.2.3 on 2025-06-22 19:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="recipe",
            name="instructions",
            field=models.TextField(blank=True, verbose_name="instructions"),
        ),
        migrations.AddField(
            model_name="recipe",
            name="name",
            field=models.CharField(
                db_index=True,
                default="Untitled Recipe",
                max_length=200,
                verbose_name="name",
            ),
        ),
        migrations.AlterField(
            model_name="recipe",
            name="slug",
            field=models.SlugField(
                blank=True, max_length=220, unique=True, verbose_name="slug"
            ),
        ),
        migrations.AlterField(
            model_name="recipe",
            name="title",
            field=models.CharField(
                db_index=True,
                default="Untitled Recipe",
                max_length=200,
                verbose_name="title",
            ),
        ),
    ]
