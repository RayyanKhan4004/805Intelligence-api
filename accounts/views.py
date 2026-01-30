from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Membership, UserProfile
from .serializers import MembershipSerializer, RegisterSerializer
from django.utils import timezone

class VerifyEmailAPI(APIView):
    """
    Verify email using token
    """

    def get(self, request, token):
        try:
            profile = UserProfile.objects.get(email_token=token)

            if profile.email_verified:
                return Response(
                    {"message": "Email already verified"},
                    status=status.HTTP_200_OK
                )

            profile.email_verified = True
            profile.email_token = None
            profile.save()

            return Response(
                {"message": "Email verified successfully"},
                status=status.HTTP_200_OK
            )

        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST
            )

# -------------------------
# Helper: Generate JWT tokens
# -------------------------
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# -------------------------
# Membership list API
# -------------------------
class MembershipListAPI(APIView):
    permission_classes = [IsAuthenticated]  # <-- NEW: Protect endpoint with JWT

    def get(self, request):
        plans = Membership.objects.all()
        serializer = MembershipSerializer(plans, many=True)
        return Response(serializer.data)

# -------------------------
# Register API (signup)
# -------------------------
class RegisterAPI(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # <-- create user
            tokens = get_tokens_for_user(user)  # <-- NEW: generate JWT tokens
            return Response({
                "message": "User registered successfully",
                "tokens": tokens
            }, status=201)
        return Response(serializer.errors, status=400)

# -------------------------
# Login API
# -------------------------
class LoginAPI(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User profile not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not profile.email_verified:
            return Response(
                {"error": "Please verify your email before logging in"},
                status=status.HTTP_403_FORBIDDEN
            )

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Login successful",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "membership": profile.membership.name if profile.membership else None,
                    "role": profile.role,
                }
            },
            status=status.HTTP_200_OK
        )
