# Generated migration to enable PostgreSQL search extensions

from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        # Enable trigram extension for fuzzy text search
        TrigramExtension(),
        # Enable unaccent extension for better text matching
        UnaccentExtension(),
    ]
