from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
import requests
import re
from coolsite.api_config import *
from dateutil import parser
from django.db import connection



def formular_view(request):
    return render(request, 'Formular/paxton_formular.html', {'benutzerabbrechen': benutzerabbrechen})

benutzerabbrechen = [{'title': "Abbrechen und zurück", 'url_name': 'algemeineTabelle'}]
