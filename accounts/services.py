import logging
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import User, Household
from kitchentory.utils.supabase_client import sync_user_to_supabase

logger = logging.getLogger(__name__)


class AccountService:
    """
    Service layer for account management.
    Handles user and household operations.
    """

    @staticmethod
    def create_household(name: str, user: User) -> Household:
        """
        Create a new household with the user as the owner.

        Args:
            name: Household name
            user: User creating the household

        Returns:
            Household: Created household
        """
        try:
            with transaction.atomic():
                logger.info(f"Creating household '{name}' for user {user.email}")

                if user.household:
                    raise ValidationError("User already belongs to a household")

                # Create household
                household = Household.objects.create(name=name, created_by=user)

                # Assign user to household
                user.household = household
                user.save()

                logger.info(f"Successfully created household {household.id}")
                return household

        except Exception as e:
            logger.error(f"Error creating household: {e}", exc_info=True)
            raise

    @staticmethod
    def join_household(invite_code: str, user: User) -> bool:
        """
        Join a household using an invite code.

        Args:
            invite_code: Household invite code
            user: User joining the household

        Returns:
            bool: True if join was successful
        """
        try:
            with transaction.atomic():
                logger.info(
                    f"User {user.email} attempting to join household with code {invite_code}"
                )

                if user.household:
                    raise ValidationError("User already belongs to a household")

                # Find household by invite code
                try:
                    household = Household.objects.get(invite_code=invite_code)
                except Household.DoesNotExist:
                    raise ValidationError("Invalid invite code")

                # Join household
                user.household = household
                user.save()

                logger.info(
                    f"User {user.email} successfully joined household {household.id}"
                )
                return True

        except Exception as e:
            logger.error(f"Error joining household: {e}", exc_info=True)
            raise

    @staticmethod
    def sync_user_profile(user: User) -> bool:
        """
        Sync user profile to external services (Supabase).

        Args:
            user: User to sync

        Returns:
            bool: True if sync was successful
        """
        try:
            logger.info(f"Syncing profile for user {user.email}")

            # Sync to Supabase
            success = sync_user_to_supabase(user)

            if success:
                logger.info(f"Successfully synced user {user.email}")
            else:
                logger.warning(f"Failed to sync user {user.email} to Supabase")

            return success

        except Exception as e:
            logger.error(f"Error syncing user profile: {e}", exc_info=True)
            return False
