from django.core.management.base import BaseCommand

from ...actions import fetch_data


class Command(BaseCommand):
    help = 'Fetch post data from Reddit.'

    def handle(self, **options):
        fetch_data()
