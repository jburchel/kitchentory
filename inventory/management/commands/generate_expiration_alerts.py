"""
Management command to generate expiration alerts for all users.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.expiration_utils import generate_expiration_alerts

User = get_user_model()


class Command(BaseCommand):
    help = "Generate expiration alerts for all users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id", type=int, help="Generate alerts for specific user ID only"
        )
        parser.add_argument(
            "--days-ahead",
            type=int,
            default=7,
            help="Number of days to look ahead for expiring items (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what alerts would be generated without creating them",
        )

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        days_ahead = options.get("days_ahead", 7)
        dry_run = options.get("dry_run", False)

        if user_id:
            try:
                users = [User.objects.get(id=user_id)]
                self.stdout.write(f"Generating expiration alerts for user {user_id}")
            except User.DoesNotExist:
                self.stderr.write(f"User with ID {user_id} not found")
                return
        else:
            users = User.objects.filter(is_active=True)
            self.stdout.write(f"Generating expiration alerts for {users.count()} users")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No alerts will be created"))

        total_stats = {
            "users_processed": 0,
            "total_alerts": 0,
            "expired": 0,
            "expiring_soon": 0,
            "use_first": 0,
            "opened_item": 0,
            "errors": [],
        }

        for user in users:
            try:
                if dry_run:
                    # For dry run, just count what would be generated
                    from inventory.models import InventoryItem
                    from django.utils import timezone
                    from datetime import timedelta

                    today = timezone.now().date()

                    # Count expired items
                    expired_count = InventoryItem.objects.filter(
                        user=user,
                        is_consumed=False,
                        quantity__gt=0,
                        expiration_date__lt=today,
                    ).count()

                    # Count expiring soon
                    expiring_soon_count = InventoryItem.objects.filter(
                        user=user,
                        is_consumed=False,
                        quantity__gt=0,
                        expiration_date__gte=today,
                        expiration_date__lte=today + timedelta(days=3),
                    ).count()

                    self.stdout.write(
                        f"User {user.username}: "
                        f"{expired_count} expired, "
                        f"{expiring_soon_count} expiring soon"
                    )

                    total_stats["users_processed"] += 1
                    total_stats["expired"] += expired_count
                    total_stats["expiring_soon"] += expiring_soon_count

                else:
                    # Generate actual alerts
                    alert_counts = generate_expiration_alerts(
                        user, days_ahead=days_ahead
                    )

                    self.stdout.write(
                        f"Generated alerts for {user.username}: "
                        f"{alert_counts.get('total', 0)} total alerts "
                        f"({alert_counts.get('expired', 0)} expired, "
                        f"{alert_counts.get('expiring_soon', 0)} expiring soon, "
                        f"{alert_counts.get('use_first', 0)} use first, "
                        f"{alert_counts.get('opened_item', 0)} opened items)"
                    )

                    # Aggregate stats
                    total_stats["users_processed"] += 1
                    total_stats["total_alerts"] += alert_counts.get("total", 0)
                    for alert_type in [
                        "expired",
                        "expiring_soon",
                        "use_first",
                        "opened_item",
                    ]:
                        total_stats[alert_type] += alert_counts.get(alert_type, 0)

            except Exception as e:
                error_msg = f"Error processing user {user.username}: {str(e)}"
                self.stderr.write(error_msg)
                total_stats["errors"].append(error_msg)

        # Print summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDRY RUN Summary:\n"
                    f"Users processed: {total_stats['users_processed']}\n"
                    f"Expired items found: {total_stats['expired']}\n"
                    f"Items expiring soon: {total_stats['expiring_soon']}\n"
                    f"Errors: {len(total_stats['errors'])}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSummary:\n"
                    f"Users processed: {total_stats['users_processed']}\n"
                    f"Total alerts generated: {total_stats['total_alerts']}\n"
                    f"Expired alerts: {total_stats['expired']}\n"
                    f"Expiring soon alerts: {total_stats['expiring_soon']}\n"
                    f"Use first alerts: {total_stats['use_first']}\n"
                    f"Opened item alerts: {total_stats['opened_item']}\n"
                    f"Errors: {len(total_stats['errors'])}"
                )
            )

        if total_stats["errors"]:
            self.stdout.write("\nErrors encountered:")
            for error in total_stats["errors"]:
                self.stderr.write(f"  - {error}")
