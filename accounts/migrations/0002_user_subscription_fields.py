# Generated manually to add subscription fields to User model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('subscriptions', '0001_initial'),  # This will be created next
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='current_plan',
            field=models.ForeignKey(
                blank=True,
                help_text='Current subscription plan (cached for quick access)',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='subscriptions.subscriptionplan'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='subscription_end_date',
            field=models.DateTimeField(
                blank=True,
                help_text='End date of current subscription period',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='subscription_status',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Current subscription status (cached for quick access)',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='trial_end_date',
            field=models.DateTimeField(
                blank=True,
                help_text='End date of trial period',
                null=True
            ),
        ),
    ]