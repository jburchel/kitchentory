"""
Management command to automatically update shopping lists with depleted and recurring items.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shopping.utils import auto_update_shopping_lists

User = get_user_model()


class Command(BaseCommand):
    help = "Automatically update shopping lists with depleted inventory and recurring items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            help="Update shopping lists for specific user ID only",
        )
        parser.add_argument(
            "--threshold-days",
            type=int,
            default=7,
            help="Number of days to look ahead for depletion (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        threshold_days = options.get("threshold_days", 7)
        dry_run = options.get("dry_run", False)

        if user_id:
            try:
                users = [User.objects.get(id=user_id)]
                self.stdout.write(f"Updating shopping lists for user {user_id}")
            except User.DoesNotExist:
                self.stderr.write(f"User with ID {user_id} not found")
                return
        else:
            users = User.objects.filter(is_active=True)
            self.stdout.write(f"Updating shopping lists for {users.count()} users")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        total_stats = {
            "users_processed": 0,
            "depleted_items_found": 0,
            "recurring_items_due": 0,
            "lists_updated": 0,
            "new_lists_created": 0,
        }

        for user in users:
            if dry_run:
                # For dry run, just show what would be found
                from shopping.utils import (
                    detect_depleted_items,
                    get_recurring_items_due,
                )

                depleted_items = detect_depleted_items(
                    user, threshold_days=threshold_days
                )
                recurring_items = get_recurring_items_due(user)

                self.stdout.write(
                    f"User {user.username}: "
                    f"{len(depleted_items)} depleted items, "
                    f"{len(recurring_items)} recurring items due"
                )

                total_stats["users_processed"] += 1
                total_stats["depleted_items_found"] += len(depleted_items)
                total_stats["recurring_items_due"] += len(recurring_items)
            else:
                try:
                    stats = auto_update_shopping_lists(user)

                    self.stdout.write(
                        f"Updated user {user.username}: "
                        f"{stats['depleted_items_found']} depleted, "
                        f"{stats['recurring_items_due']} recurring, "
                        f"{stats['lists_updated']} lists updated, "
                        f"{stats['new_lists_created']} lists created"
                    )

                    # Aggregate stats
                    total_stats["users_processed"] += 1
                    for key in [
                        "depleted_items_found",
                        "recurring_items_due",
                        "lists_updated",
                        "new_lists_created",
                    ]:
                        total_stats[key] += stats[key]

                except Exception as e:
                    self.stderr.write(
                        f"Error updating shopping lists for user {user.username}: {str(e)}"
                    )

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"Users processed: {total_stats['users_processed']}\n"
                f"Depleted items found: {total_stats['depleted_items_found']}\n"
                f"Recurring items due: {total_stats['recurring_items_due']}\n"
                f"Lists updated: {total_stats['lists_updated']}\n"
                f"New lists created: {total_stats['new_lists_created']}"
            )
        )
