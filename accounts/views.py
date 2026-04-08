from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import uuid

from .models import Membership, UserProfile


# -------------------------
# Helper: recalculate all reports for a user
# -------------------------
def _recalculate_user_reports(user):
    try:
        from reports.models import Report, ReportFarm, ReportResult
        from reports.calculator import calculate_metrics
        from properties.models import Property

        reports = Report.objects.filter(user=user, status="generated")
        for report in reports:
            props = Property.objects.all()
            if report.county_id:
                props = props.filter(county_id=report.county_id)
            if report.city_id:
                props = props.filter(city_id=report.city_id)
            farm_ids = list(ReportFarm.objects.filter(report=report).values_list("farm_id", flat=True))
            if farm_ids:
                props = props.filter(farm_id__in=farm_ids)

            metric_data = calculate_metrics(props, report.metrics)
            ReportResult.objects.update_or_create(
                report=report,
                defaults={
                    "inventory":                metric_data.get("inventory"),
                    "avg_dom":                  metric_data.get("avg_dom"),
                    "median_dom":               metric_data.get("median_dom"),
                    "market_action_index":      metric_data.get("market_action_index"),
                    "market_type":              metric_data.get("market_type", ""),
                    "price_per_sqft":           metric_data.get("price_per_sqft"),
                    "price_decreased_pct":      metric_data.get("price_decreased_pct"),
                    "price_increased_pct":      metric_data.get("price_increased_pct"),
                    "median_list_price":        metric_data.get("median_list_price"),
                    "median_new_listing_price": metric_data.get("median_new_listing_price"),
                }
            )
    except Exception:
        # Never block login if recalculation fails
        pass
from .serializers import MembershipSerializer, RegisterSerializer


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
# Verify Email
# -------------------------
class VerifyEmailAPI(APIView):
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
# Membership list API
# -------------------------
class MembershipListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = Membership.objects.all()
        serializer = MembershipSerializer(plans, many=True)
        return Response(serializer.data)


# -------------------------
# Register API
# -------------------------
class RegisterAPI(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                "message": "User registered successfully",
                "tokens": tokens
            }, status=201)
        return Response(serializer.errors, status=400)


# -------------------------
# Login API (email + password)
# -------------------------
class LoginAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {"error": "Email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_obj = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = authenticate(username=user_obj.username, password=password)

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

        # Recalculate all reports on login
        _recalculate_user_reports(user)

        return Response(
            {
                "message": "Login successful",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "membership": profile.membership.name if profile.membership else None,
                    "role": profile.role,
                }
            },
            status=status.HTTP_200_OK
        )


# -------------------------
# Forgot Password
# POST /api/forgot-password/
# Body: { "email": "user@gmail.com" }
# -------------------------
class ForgotPasswordAPI(APIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email.lower())
            profile = UserProfile.objects.get(user=user)
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            # Return success anyway to avoid exposing which emails are registered
            return Response(
                {"message": "If that email exists, a reset link has been sent."},
                status=status.HTTP_200_OK
            )

        # Generate reset token valid for 1 hour
        token = uuid.uuid4()
        profile.password_reset_token = token
        profile.password_reset_expires = timezone.now() + timedelta(hours=1)
        profile.save()

        reset_url = f"http://127.0.0.1:8000/api/reset-password/{token}/"

        send_mail(
            subject="Reset Your Password | 805Intelligence",
            message=(
                f"Hi {user.first_name},\n\n"
                f"We received a request to reset your password.\n\n"
                f"Click the link below to set a new password:\n"
                f"{reset_url}\n\n"
                f"This link expires in 1 hour.\n\n"
                f"If you didn't request this, you can safely ignore this email.\n\n"
                f"Thank you,\n"
                f"The 805Intelligence Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "If that email exists, a reset link has been sent."},
            status=status.HTTP_200_OK
        )


# -------------------------
# Reset Password
# POST /api/reset-password/<token>/
# Body: { "password": "NewPass123", "confirm_password": "NewPass123" }
# -------------------------
class ResetPasswordAPI(APIView):
    def post(self, request, token):
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        if not password or not confirm_password:
            return Response(
                {"error": "Password and confirm_password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != confirm_password:
            return Response(
                {"error": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            profile = UserProfile.objects.get(password_reset_token=token)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Invalid or expired reset link"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check token hasn't expired
        if timezone.now() > profile.password_reset_expires:
            profile.password_reset_token = None
            profile.password_reset_expires = None
            profile.save()
            return Response(
                {"error": "Reset link has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password and clear the token
        user = profile.user
        user.set_password(password)
        user.save()

        profile.password_reset_token = None
        profile.password_reset_expires = None
        profile.save()

        return Response(
            {"message": "Password reset successfully. You can now log in."},
            status=status.HTTP_200_OK
        )


# -------------------------
# User Profile API
# GET  /api/profile/  → view own profile
# PATCH /api/profile/ → edit first_name, last_name, email, company
# -------------------------
class UserProfileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = UserProfile.objects.select_related('user', 'membership').get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        from .serializers import UserProfileSerializer
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        from .serializers import UpdateProfileSerializer
        serializer = UpdateProfileSerializer(
            profile,
            data=request.data,
            partial=True,          # all fields optional
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Profile updated successfully"},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------
# Change Password API
# POST /api/change-password/
# Body: { "current_password": "...", "new_password": "...", "confirm_new_password": "..." }
# -------------------------
class ChangePasswordAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_new_password = request.data.get('confirm_new_password')

        # Check all fields are provided
        if not current_password or not new_password or not confirm_new_password:
            return Response(
                {"error": "current_password, new_password and confirm_new_password are all required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check current password is correct
        if not request.user.check_password(current_password):
            return Response(
                {"error": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check new passwords match
        if new_password != confirm_new_password:
            return Response(
                {"error": "New passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check new password is not the same as current
        if current_password == new_password:
            return Response(
                {"error": "New password must be different from your current password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check minimum length
        if len(new_password) < 8:
            return Response(
                {"error": "New password must be at least 8 characters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Save new password
        request.user.set_password(new_password)
        request.user.save()

        return Response(
            {"message": "Password changed successfully. Please log in again with your new password."},
            status=status.HTTP_200_OK
        )


# -------------------------
# Change Password API
# POST /api/change-password/
# Body: { "current_password": "...", "new_password": "...", "confirm_password": "..." }
# -------------------------
class ChangePasswordAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            return Response(
                {"error": "current_password, new_password and confirm_password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check current password is correct
        if not request.user.check_password(current_password):
            return Response(
                {"error": "Current password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {"error": "New passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {"error": "New password must be at least 8 characters"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if current_password == new_password:
            return Response(
                {"error": "New password must be different from current password"},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_password)
        request.user.save()

        return Response(
            {"message": "Password changed successfully. Please log in again."},
            status=status.HTTP_200_OK
        )