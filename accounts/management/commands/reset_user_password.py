from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate password reset link for a user'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Print reset URL
            reset_url = f"https://kitchentory.onrender.com/accounts/password/reset/confirm/{uid}/{token}/"
            
            self.stdout.write(self.style.SUCCESS(f'User found: {email}'))
            self.stdout.write(f'Reset URL: {reset_url}')
            self.stdout.write('This URL is valid for a limited time.')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {email}'))