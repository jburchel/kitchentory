"""
Management command to send scheduled digest emails.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from notifications.models import DigestSchedule
from notifications.utils import send_daily_digest, send_weekly_digest

User = get_user_model()


class Command(BaseCommand):
    help = "Send scheduled digest emails to users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--digest-type",
            choices=["daily", "weekly", "monthly"],
            help="Send specific type of digest only",
        )
        parser.add_argument(
            "--user-id", type=int, help="Send digest to specific user ID only"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what digests would be sent without actually sending them",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force send digests even if not scheduled",
        )

    def handle(self, *args, **options):
        digest_type = options.get("digest_type")
        user_id = options.get("user_id")
        dry_run = options.get("dry_run", False)
        force = options.get("force", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No emails will be sent"))

        now = timezone.now()

        # Get digest schedules that are due
        schedules_query = DigestSchedule.objects.filter(is_enabled=True)

        if user_id:
            schedules_query = schedules_query.filter(user_id=user_id)

        if digest_type:
            schedules_query = schedules_query.filter(digest_type=digest_type)

        if not force:
            # Only get schedules that are actually due
            schedules_query = schedules_query.filter(next_send__lte=now)

        schedules = schedules_query.select_related("user")

        self.stdout.write(f"Found {schedules.count()} digest schedules to process")

        stats = {
            "daily_sent": 0,
            "weekly_sent": 0,
            "monthly_sent": 0,
            "failed": 0,
            "errors": [],
        }

        for schedule in schedules:
            try:
                user = schedule.user

                if dry_run:
                    self.stdout.write(
                        f"Would send {schedule.digest_type} digest to {user.username} ({user.email})"
                    )
                    stats[f"{schedule.digest_type}_sent"] += 1
                    continue

                # Send the appropriate digest
                success = False

                if schedule.digest_type == "daily":
                    success = send_daily_digest(user)
                elif schedule.digest_type == "weekly":
                    success = send_weekly_digest(user)
                elif schedule.digest_type == "monthly":
                    # Monthly digests not implemented yet
                    success = False

                if success:
                    # Update schedule
                    schedule.last_sent = now
                    schedule.calculate_next_send()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Sent {schedule.digest_type} digest to {user.username}"
                        )
                    )
                    stats[f"{schedule.digest_type}_sent"] += 1

                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Failed to send {schedule.digest_type} digest to {user.username}"
                        )
                    )
                    stats["failed"] += 1

            except Exception as e:
                error_msg = f"Error processing schedule {schedule.id}: {str(e)}"
                self.stderr.write(error_msg)
                stats["errors"].append(error_msg)
                stats["failed"] += 1

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary:\n"
                f"Daily digests sent: {stats['daily_sent']}\n"
                f"Weekly digests sent: {stats['weekly_sent']}\n"
                f"Monthly digests sent: {stats['monthly_sent']}\n"
                f"Failed: {stats['failed']}\n"
                f"Errors: {len(stats['errors'])}"
            )
        )

        if stats["errors"]:
            self.stdout.write("\nErrors encountered:")
            for error in stats["errors"]:
                self.stderr.write(f"  - {error}")

        # Create missing digest schedules for users who don't have them
        if not user_id and not digest_type:
            self._create_missing_schedules()

    def _create_missing_schedules(self):
        """Create missing digest schedules for users."""
        users_without_weekly = User.objects.filter(is_active=True).exclude(
            digest_schedules__digest_type="weekly"
        )

        created_count = 0
        for user in users_without_weekly:
            try:
                # Check if user has notification preferences that enable weekly digest
                from inventory.expiration_models import UserNotificationPreferences

                preferences = UserNotificationPreferences.get_or_create_for_user(user)

                if preferences.weekly_digest:
                    schedule = DigestSchedule.objects.create(
                        user=user,
                        digest_type="weekly",
                        is_enabled=True,
                        send_time=preferences.digest_email_time,
                        weekday=0,  # Monday
                    )
                    schedule.calculate_next_send()
                    created_count += 1

            except Exception as e:
                self.stderr.write(
                    f"Error creating schedule for user {user.username}: {str(e)}"
                )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} missing digest schedules")
            )
