from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()

class Command(BaseCommand):
    help = 'Check user account and optionally reset password'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email')
        parser.add_argument('--reset-password', type=str, help='New password to set')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(
                self.style.SUCCESS(f'User found: {user.email}')
            )
            self.stdout.write(f'ID: {user.id}')
            self.stdout.write(f'Active: {user.is_active}')
            self.stdout.write(f'Staff: {user.is_staff}')
            self.stdout.write(f'Last login: {user.last_login}')
            self.stdout.write(f'Date joined: {user.date_joined}')
            
            if options['reset_password']:
                user.password = make_password(options['reset_password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Password updated for {user.email}')
                )
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {email} not found')
            )
            
            # List all users
            self.stdout.write('\nAll users in database:')
            for user in User.objects.all():
                self.stdout.write(f'- {user.email} (ID: {user.id}, Active: {user.is_active})')