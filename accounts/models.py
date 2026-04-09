import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.mail import send_mail


class Membership(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('pro', 'Pro'),
    ]

    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    duration = models.CharField(max_length=20, default='yearly')
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('agent', 'Real Estate Agent'),
        ('broker', 'Broker'),
        ('escrow', 'Escrow / Title'),
        ('lender', 'Lender'),
        ('appraiser', 'Appraiser'),
        ('investor', 'Investor'),
        ('enterprise', 'Enterprise'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    membership = models.ForeignKey('Membership', on_delete=models.SET_NULL, null=True)
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # Portfolio admin flag
    is_portfolio_admin = models.BooleanField(default=False)

    # 🔐 Email verification
    email_verified = models.BooleanField(default=False)
    email_token = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True)

    # 🔑 Password reset
    password_reset_token = models.UUIDField(null=True, blank=True, unique=True)
    password_reset_expires = models.DateTimeField(null=True, blank=True)

    # -----------------------------
    # Send email verification
    # -----------------------------
    def send_verification_email(self):
        verification_url = f"http://127.0.0.1:8000/api/verify-email/{self.email_token}/"
        send_mail(
            subject="Confirm Your Email Address",
            message=f"Hi {self.user.first_name},\n\n"
                    f"Please verify your email by clicking the link below:\n"
                    f"{verification_url}\n\n"
                    f"This link will expire in 24 hours.\n\n"
                    f"Thank you, The 805Intelligence Team",
            from_email='805Intelligence <your-email@gmail.com>',
            recipient_list=[self.user.email],
            fail_silently=False,
        )

    def __str__(self):
        return self.user.username


class PortfolioUser(models.Model):
    """
    Sub-users added by a Portfolio Administrator.
    Each sub-user belongs to one portfolio (the admin who created them).
    """

    ACCESS_CHOICES = [
        ('no_access',      'No Access'),
        ('read_only',      'Read Only'),
        ('account_admin',  'Account Admin'),
    ]

    # The portfolio admin who created this sub-user
    portfolio_admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='managed_users'
    )

    # The actual Django user account for the sub-user
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='portfolio_membership',
        null=True, blank=True
    )

    # Basic info (stored here before user accepts invite)
    first_name = models.CharField(max_length=150)
    last_name  = models.CharField(max_length=150)
    email      = models.EmailField(unique=True)

    # Permission level
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_CHOICES,
        default='no_access'
    )

    # Is this user a Portfolio Administrator themselves?
    is_portfolio_admin = models.BooleanField(default=False)

    # Invite tracking
    invite_token   = models.UUIDField(default=uuid.uuid4, unique=True)
    invite_sent_at = models.DateTimeField(null=True, blank=True)
    invite_accepted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def send_invite_email(self):
        setup_url = f"http://127.0.0.1:8000/api/accept-invite/{self.invite_token}/"
        send_mail(
            subject="You've been added to 805Intelligence",
            message=(
                f"Hi {self.first_name},\n\n"
                f"You have been invited to join 805Intelligence.\n\n"
                f"Click the link below to set up your password and activate your account:\n"
                f"{setup_url}\n\n"
                f"This link will expire in 48 hours.\n\n"
                f"Thank you,\n"
                f"The 805Intelligence Team"
            ),
            from_email='805Intelligence <your-email@gmail.com>',
            recipient_list=[self.email],
            fail_silently=False,
        )