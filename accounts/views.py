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


# -------------------------
# Portfolio User Management
# Only Portfolio Admins can access these endpoints
# -------------------------

def _is_portfolio_admin(user):
    try:
        return UserProfile.objects.get(user=user).is_portfolio_admin
    except UserProfile.DoesNotExist:
        return False


class PortfolioUserListCreateAPI(APIView):
    """
    GET  /api/portfolio/users/       → list all sub-users
    POST /api/portfolio/users/       → add a new sub-user & send invite email
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_portfolio_admin(request.user):
            return Response(
                {"error": "Only Portfolio Administrators can manage users."},
                status=status.HTTP_403_FORBIDDEN
            )

        from .models import PortfolioUser
        users = PortfolioUser.objects.filter(portfolio_admin=request.user).order_by('last_name')

        data = [
            {
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "access_level": u.access_level,
                "is_portfolio_admin": u.is_portfolio_admin,
                "invite_accepted": u.invite_accepted,
                "created_at": u.created_at,
            }
            for u in users
        ]
        return Response(data)

    def post(self, request):
        if not _is_portfolio_admin(request.user):
            return Response(
                {"error": "Only Portfolio Administrators can add users."},
                status=status.HTTP_403_FORBIDDEN
            )

        from .models import PortfolioUser
        from django.utils import timezone as tz

        first_name         = request.data.get('first_name', '').strip()
        last_name          = request.data.get('last_name', '').strip()
        email              = request.data.get('email', '').strip().lower()
        access_level       = request.data.get('access_level', 'no_access')
        is_portfolio_admin = request.data.get('is_portfolio_admin', False)
        send_email_flag    = request.data.get('send_invite_email', True)

        # Validate required fields
        if not first_name:
            return Response({"error": "first_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not last_name:
            return Response({"error": "last_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return Response({"error": "email is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate access level
        valid_levels = {'no_access', 'read_only', 'account_admin'}
        if access_level not in valid_levels:
            return Response(
                {"error": f"Invalid access_level. Choose from: {sorted(valid_levels)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check email not already used
        if PortfolioUser.objects.filter(email=email).exists():
            return Response({"error": "A user with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "This email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

        # Create portfolio user
        portfolio_user = PortfolioUser.objects.create(
            portfolio_admin    = request.user,
            first_name         = first_name,
            last_name          = last_name,
            email              = email,
            access_level       = access_level,
            is_portfolio_admin = is_portfolio_admin,
            invite_sent_at     = tz.now() if send_email_flag else None,
        )

        # Send invite email
        if send_email_flag:
            portfolio_user.send_invite_email()

        return Response(
            {
                "message": "User added successfully. Invite email sent.",
                "user": {
                    "id": portfolio_user.id,
                    "first_name": portfolio_user.first_name,
                    "last_name": portfolio_user.last_name,
                    "email": portfolio_user.email,
                    "access_level": portfolio_user.access_level,
                    "is_portfolio_admin": portfolio_user.is_portfolio_admin,
                    "invite_token": portfolio_user.invite_token,
                }
            },
            status=status.HTTP_201_CREATED
        )


class PortfolioUserDetailAPI(APIView):
    """
    PATCH  /api/portfolio/users/<id>/  → update access level
    DELETE /api/portfolio/users/<id>/  → remove user
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, request, user_id):
        from .models import PortfolioUser
        from django.shortcuts import get_object_or_404
        return get_object_or_404(PortfolioUser, id=user_id, portfolio_admin=request.user)

    def patch(self, request, user_id):
        if not _is_portfolio_admin(request.user):
            return Response(
                {"error": "Only Portfolio Administrators can update users."},
                status=status.HTTP_403_FORBIDDEN
            )

        portfolio_user = self.get_object(request, user_id)

        access_level       = request.data.get('access_level')
        is_portfolio_admin = request.data.get('is_portfolio_admin')

        valid_levels = {'no_access', 'read_only', 'account_admin'}
        if access_level:
            if access_level not in valid_levels:
                return Response(
                    {"error": f"Invalid access_level. Choose from: {sorted(valid_levels)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            portfolio_user.access_level = access_level

        if is_portfolio_admin is not None:
            portfolio_user.is_portfolio_admin = is_portfolio_admin

        portfolio_user.save()

        return Response({
            "message": "User updated successfully.",
            "user": {
                "id": portfolio_user.id,
                "first_name": portfolio_user.first_name,
                "last_name": portfolio_user.last_name,
                "email": portfolio_user.email,
                "access_level": portfolio_user.access_level,
                "is_portfolio_admin": portfolio_user.is_portfolio_admin,
            }
        })

    def delete(self, request, user_id):
        if not _is_portfolio_admin(request.user):
            return Response(
                {"error": "Only Portfolio Administrators can delete users."},
                status=status.HTTP_403_FORBIDDEN
            )

        portfolio_user = self.get_object(request, user_id)

        # Also delete their Django user account if they accepted the invite
        if portfolio_user.user:
            portfolio_user.user.delete()

        portfolio_user.delete()
        return Response({"message": "User removed successfully."}, status=status.HTTP_200_OK)


class AcceptInviteAPI(APIView):
    """
    POST /api/accept-invite/<token>/
    Body: { "password": "NewPass123", "confirm_password": "NewPass123" }
    Sub-user sets their password and activates their account.
    """

    def post(self, request, token):
        from .models import PortfolioUser

        password         = request.data.get('password', '').strip()
        confirm_password = request.data.get('confirm_password', '').strip()

        if not password or not confirm_password:
            return Response(
                {"error": "password and confirm_password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            portfolio_user = PortfolioUser.objects.get(invite_token=token)
        except PortfolioUser.DoesNotExist:
            return Response({"error": "Invalid or expired invite link."}, status=status.HTTP_400_BAD_REQUEST)

        if portfolio_user.invite_accepted:
            return Response({"error": "This invite has already been used."}, status=status.HTTP_400_BAD_REQUEST)

        # Create Django user account
        user = User.objects.create_user(
            username   = portfolio_user.email,
            email      = portfolio_user.email,
            password   = password,
            first_name = portfolio_user.first_name,
            last_name  = portfolio_user.last_name,
            is_active  = True,
        )

        # Create UserProfile for sub-user
        from .models import UserProfile, Membership
        UserProfile.objects.create(
            user               = user,
            company            = '',
            role               = 'other',
            email_verified     = True,    # already verified via invite
            is_portfolio_admin = portfolio_user.is_portfolio_admin,
        )

        # Link and mark invite accepted
        portfolio_user.user           = user
        portfolio_user.invite_accepted = True
        portfolio_user.save()

        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Account activated successfully. You can now log in.",
                "access": tokens["access"],
                "refresh": tokens["refresh"],
            },
            status=status.HTTP_201_CREATED
        )