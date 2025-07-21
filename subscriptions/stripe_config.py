"""
Stripe configuration and setup utilities.
"""

import stripe
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeConfig:
    """Configuration class for Stripe integration."""
    
    # Stripe product and price IDs (these will be created in Stripe dashboard)
    PRODUCTS = {
        'premium': {
            'product_id': 'prod_premium_kitchentory',  # Will be set after creating in Stripe
            'monthly_price_id': 'price_premium_monthly',
            'yearly_price_id': 'price_premium_yearly',
        },
        'pro': {
            'product_id': 'prod_pro_kitchentory',
            'monthly_price_id': 'price_pro_monthly', 
            'yearly_price_id': 'price_pro_yearly',
        }
    }
    
    # Subscription tiers with pricing (in cents)
    PRICING = {
        'premium': {
            'monthly': 499,  # $4.99
            'yearly': 4990,  # $49.90 (2 months free)
        },
        'pro': {
            'monthly': 999,  # $9.99
            'yearly': 9990,  # $99.90 (2 months free)
        }
    }
    
    @classmethod
    def get_price_id(cls, tier, billing_period='monthly'):
        """Get Stripe price ID for a tier and billing period."""
        if tier not in cls.PRODUCTS:
            return None
        
        if billing_period == 'yearly':
            return cls.PRODUCTS[tier]['yearly_price_id']
        else:
            return cls.PRODUCTS[tier]['monthly_price_id']
    
    @classmethod
    def get_product_id(cls, tier):
        """Get Stripe product ID for a tier."""
        return cls.PRODUCTS.get(tier, {}).get('product_id')
    
    @classmethod
    def get_price_amount(cls, tier, billing_period='monthly'):
        """Get price amount in cents for a tier and billing period."""
        if tier not in cls.PRICING:
            return 0
        return cls.PRICING[tier].get(billing_period, 0)
    
    @classmethod
    def get_price_amount_dollars(cls, tier, billing_period='monthly'):
        """Get price amount in dollars for a tier and billing period."""
        cents = cls.get_price_amount(tier, billing_period)
        return Decimal(cents) / 100


class StripeService:
    """Service class for Stripe operations."""
    
    @staticmethod
    def create_customer(user, **kwargs):
        """
        Create a Stripe customer for a user.
        
        Args:
            user: User instance
            **kwargs: Additional customer data
            
        Returns:
            Stripe Customer object or None
        """
        try:
            customer_data = {
                'email': user.email,
                'name': user.get_full_name(),
                'metadata': {
                    'user_id': str(user.id),
                    'username': user.username or user.email,
                }
            }
            customer_data.update(kwargs)
            
            customer = stripe.Customer.create(**customer_data)
            
            # Update user with customer ID
            user.stripe_customer_id = customer.id
            user.save(update_fields=['stripe_customer_id'])
            
            logger.info(f"Created Stripe customer for user {user.email}: {customer.id}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer for user {user.email}: {str(e)}")
            return None
    
    @staticmethod
    def get_or_create_customer(user):
        """
        Get existing Stripe customer or create a new one.
        
        Args:
            user: User instance
            
        Returns:
            Stripe Customer object or None
        """
        if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                if customer.deleted:
                    # Customer was deleted, create a new one
                    user.stripe_customer_id = None
                    user.save(update_fields=['stripe_customer_id'])
                    return StripeService.create_customer(user)
                return customer
            except stripe.error.InvalidRequestError:
                # Customer doesn't exist, create new one
                user.stripe_customer_id = None
                user.save(update_fields=['stripe_customer_id'])
        
        return StripeService.create_customer(user)
    
    @staticmethod
    def create_checkout_session(user, price_id, success_url, cancel_url, **kwargs):
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            user: User instance
            price_id: Stripe price ID
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            **kwargs: Additional session parameters
            
        Returns:
            Stripe Checkout Session or None
        """
        try:
            customer = StripeService.get_or_create_customer(user)
            if not customer:
                return None
            
            session_data = {
                'customer': customer.id,
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': {
                    'user_id': str(user.id),
                },
                'subscription_data': {
                    'metadata': {
                        'user_id': str(user.id),
                        'user_email': user.email,
                    }
                },
                'allow_promotion_codes': True,
                'billing_address_collection': 'auto',
                'tax_id_collection': {'enabled': True},
            }
            session_data.update(kwargs)
            
            session = stripe.checkout.Session.create(**session_data)
            
            logger.info(f"Created checkout session for user {user.email}: {session.id}")
            return session
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating checkout session for user {user.email}: {str(e)}")
            return None
    
    @staticmethod
    def create_customer_portal_session(customer_id, return_url):
        """
        Create a Stripe Customer Portal session.
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after managing subscription
            
        Returns:
            Stripe Customer Portal Session or None
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            logger.info(f"Created customer portal session for customer {customer_id}")
            return session
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating customer portal session: {str(e)}")
            return None
    
    @staticmethod
    def cancel_subscription(subscription_id, at_period_end=True):
        """
        Cancel a Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Whether to cancel at period end or immediately
            
        Returns:
            Updated Stripe Subscription or None
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.cancel(subscription_id)
            
            logger.info(f"Canceled subscription {subscription_id} (at_period_end={at_period_end})")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling subscription {subscription_id}: {str(e)}")
            return None
    
    @staticmethod
    def update_subscription(subscription_id, **kwargs):
        """
        Update a Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            **kwargs: Fields to update
            
        Returns:
            Updated Stripe Subscription or None
        """
        try:
            subscription = stripe.Subscription.modify(subscription_id, **kwargs)
            logger.info(f"Updated subscription {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Error updating subscription {subscription_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_upcoming_invoice(customer_id, subscription_id=None):
        """
        Get the upcoming invoice for a customer.
        
        Args:
            customer_id: Stripe customer ID
            subscription_id: Optional specific subscription ID
            
        Returns:
            Stripe Invoice or None
        """
        try:
            params = {'customer': customer_id}
            if subscription_id:
                params['subscription'] = subscription_id
                
            invoice = stripe.Invoice.upcoming(**params)
            return invoice
            
        except stripe.error.StripeError as e:
            logger.error(f"Error getting upcoming invoice: {str(e)}")
            return None


def validate_stripe_config():
    """Validate that Stripe is properly configured."""
    required_settings = [
        'STRIPE_PUBLISHABLE_KEY',
        'STRIPE_SECRET_KEY',
        'STRIPE_WEBHOOK_SECRET',
    ]
    
    missing_settings = []
    for setting in required_settings:
        if not getattr(settings, setting, None):
            missing_settings.append(setting)
    
    if missing_settings:
        logger.warning(f"Missing Stripe settings: {', '.join(missing_settings)}")
        return False
    
    # Test Stripe connection
    try:
        stripe.Account.retrieve()
        logger.info("Stripe configuration validated successfully")
        return True
    except stripe.error.AuthenticationError:
        logger.error("Stripe authentication failed - check API keys")
        return False
    except stripe.error.StripeError as e:
        logger.error(f"Stripe validation error: {str(e)}")
        return False


# Initialize Stripe configuration on import
if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
    validate_stripe_config()