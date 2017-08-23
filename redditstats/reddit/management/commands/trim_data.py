from django.core.management.base import BaseCommand

from ...actions import trim_data


class Command(BaseCommand):
    help = 'Trim snapshot data from Reddit.'

    def handle(self, **options):
        trim_data()
