from django.core.management.base import BaseCommand
from accounts.models import Membership


class Command(BaseCommand):
    help = 'Create default membership plans'

    def handle(self, *args, **options):
        memberships = [
            {'name': 'basic', 'price': 29.99, 'duration': 'monthly', 'description': 'Basic plan for individual agents'},
            {'name': 'premium', 'price': 79.99, 'duration': 'monthly', 'description': 'Premium plan with advanced features'},
            {'name': 'pro', 'price': 199.99, 'duration': 'monthly', 'description': 'Professional plan for brokers and teams'},
        ]

        for mem in memberships:
            membership, created = Membership.objects.get_or_create(
                name=mem['name'],
                defaults={
                    'price': mem['price'],
                    'duration': mem['duration'],
                    'description': mem['description']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created membership: {membership.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'✓ Membership already exists: {membership.name}')
                )

        self.stdout.write(self.style.SUCCESS('All memberships are ready!'))
