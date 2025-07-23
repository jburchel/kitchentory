from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create temporary admin user'

    def handle(self, *args, **options):
        email = 'temp@admin.com'
        password = 'TempAdmin123!'
        
        # Delete existing temp admin if exists
        User.objects.filter(email=email).delete()
        
        # Create new temp admin
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Temp',
            last_name='Admin',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Temporary admin created successfully!')
        )
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Admin URL: /admin/')