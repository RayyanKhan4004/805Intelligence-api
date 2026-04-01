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