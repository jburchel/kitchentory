# Generated manually to add stripe_customer_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_subscription_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='stripe_customer_id',
            field=models.CharField(blank=True, default='', help_text='Stripe customer ID for payment processing', max_length=255),
        ),
    ]