from rest_framework import serializers
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
import uuid

from .models import Membership, UserProfile


# -------------------------
# Membership Serializer
# -------------------------
class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ['id', 'name', 'price', 'duration', 'description']


# -------------------------
# Register Serializer
# -------------------------
class RegisterSerializer(serializers.ModelSerializer):
    membership = serializers.CharField(write_only=True)
    company = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password',
            'membership',
            'company',
            'role',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    # -------------------------
    # Email validation
    # -------------------------
    def validate_email(self, value):
        value = value.lower()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )

        return value

    # -------------------------
    # Membership validation
    # -------------------------
    def validate_membership(self, value):
        if not Membership.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                "Invalid membership plan selected."
            )
        return value

    # -------------------------
    # Create user, profile & send email
    # -------------------------
    def create(self, validated_data):
        membership_name = validated_data.pop('membership')
        company = validated_data.pop('company')
        role = validated_data.pop('role')

        membership = Membership.objects.get(name=membership_name)

        # Use email as the username internally (keeps Django's auth happy)
        email = validated_data['email']

        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_active=True
        )

        # Generate email verification token
        email_token = uuid.uuid4()

        # Create user profile
        UserProfile.objects.create(
            user=user,
            membership=membership,
            company=company,
            role=role,
            email_token=email_token,
            email_verified=False
        )

        # Verification link
        verify_url = f"http://127.0.0.1:8000/api/verify-email/{email_token}/"

        # Send verification email
        send_mail(
            subject="Verify your email address | 805Intelligence",
            message=(
                f"Hi {user.first_name},\n\n"
                f"Please confirm your email address to complete your registration.\n\n"
                f"Verify Email Address:\n{verify_url}\n\n"
                f"This link will expire in 24 hours.\n\n"
                f"If you didn't create this account, you can ignore this email.\n\n"
                f"Thank you,\n"
                f"The 805Intelligence Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return user