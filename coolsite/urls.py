
from django.contrib import admin
from django.urls import path, include
from Formular.views import formular_view
from Tabelle.views import *
from Neue_Berechtigungsname import * 
from coolsite.api_config import *

#from Schulte_Schlagbaum.views import *
#from Parkkarten.views import *


#url seiten
urlpatterns = [
    path('Tabelle/', algemeineTabelle, name='algemeineTabelle'),
    path('Formular/', formular_view, name='formular'), 
    #path('Schulte_Schlagbaum/', Schulte_Schlagbaum, name='spind'),
    #path('Parkkarten/', Parkkarten, name='parkkarten'),
    path('Neue_Berechtigungsname/', Neue_Berechtigungsname, name='Neue_Berechtigungsname'),
    path('get_filter_options', get_filter_options, name='get_filter_options'),









    path('get_users', get_users, name='get_users'),    # Zweite Seite: Formular
    path('get_datalist_options', get_datalist_options, name='get_datalist_options' ),
    path('get_name_options', get_name_options, name='get_name_options' ),
    path('api/access_level_names/', get_access_levels_dict, name='get_access_level_names'),
]
handler404 = 'Tabelle.views.pageNotFound' 