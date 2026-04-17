
from django.contrib import admin
from django.urls import path, include
from Formular.views import *
from Tabelle.views import *
from Tabelle.Paxton_all import *
from Tabelle.utils import get_benutzer_liste
from Neue_Berechtigungsname.views import *





urlpatterns = [
    #haupt seiten!
    path('admin/', admin.site.urls),
    path('Tabelle/', algemeineTabelle, name='algemeineTabelle'),
    path('Formular/', formular_view, name='formular'),
    path('Neue_Berechtigungsname/', Neue_Berechtigungsname, name='Neue_Berechtigungsname'),

    #Formular: 
    path('autocomplete_user', autocomplete_user, name='autocomplete_user'),  #Das die formulas suchfunktion aktiviert 
    path('Formular/api/accesslevels/', api_accesslevels, name="api_accesslevels"),
    path('Formular/api/departments/', api_departments, name="api_departments"),
    path('Formular/deaktiv_card/', deaktiv_card, name="deaktiv_card"),
    path('Formular/lost_card/', lost_card, name='lost_Card'),
    path('Formular/restore_card/', restore_card, name='restore_card'),
    path('Formular/save-data/', save_data, name='save_data'),
    #neue_berechtigungsname
    path('Neue_Berechtigungsname/api/accesslevels/', api_accesslevels, name="api_accesslevels_nb"),




]