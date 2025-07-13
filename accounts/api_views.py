from django.contrib.auth import authenticate
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def login_api(request):
    """
    Simple login endpoint for browser extension
    Returns authentication token
    """
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Authenticate user
    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "Account is disabled"}, status=status.HTTP_401_UNAUTHORIZED
        )

    # Get or create token
    token, created = Token.objects.get_or_create(user=user)

    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    return Response(
        {
            "token": token.key,
            "user": {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "household": user.household.name if user.household else None,
            },
        }
    )


@api_view(["POST"])
def logout_api(request):
    """
    Logout endpoint that deletes the token
    """
    try:
        request.user.auth_token.delete()
    except:
        pass

    return Response({"message": "Logged out successfully"})


@api_view(["GET"])
def user_info(request):
    """
    Get current user information
    """
    return Response(
        {
            "user": {
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "household": (
                    request.user.household.name if request.user.household else None
                ),
            }
        }
    )
