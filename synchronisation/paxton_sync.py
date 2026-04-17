from django.core.management.base import BaseCommand

from synchronisation.views import sync_db_to_paxton  
from synchronisation.Paxton_funk import get_token  

#um es anzurufen, muss cron angepast werden

class Command(BaseCommand):
    help = "Synchronisiert DB -> Paxton (daily job)."

    def handle(self, *args, **options):
        token = get_token()
        if not token:
            raise RuntimeError("Token konnte nicht abgerufen werden.")
        sync_db_to_paxton(token)