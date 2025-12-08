

from django.contrib import admin
from Tabelle.models import TGast, TStudenten, PaxtonViewWeb


class TStudentenAdmin(admin.ModelAdmin):
    #angezeigte spalten 
    list_display = (
    
        'employeenumber',     
        'givenname',           
        'sn',                
        'createtime',       
        'kartennummer',        
        'active',             
        'verlorene_karte',    
        'abteilung',          
        'funktion',           
        'gelesen_am',          
        'schrank',            
        # weitere Felder wie im Model
    )
    #wie information button, damit man kann aufmachen
    list_display_links = ('employeenumber', 'kartennummer')
    #über welchen felden mann suchen kann
    search_fields = ('employeenumber', 'kartennummer', 'abteilung', 'funktion', 'gelesen_am', 'createtime', 'schrank')
    #die liste was mann bearbeiten kann
    list_editable = ('verlorene_karte', 'active')


#in reiche 17 in boolen keine bollen, ->ERROR!
class PaxtonViewWebAdmin(admin.ModelAdmin):
    list_display = (
        'employeenumber',
        'givenname',
        'sn',
        'austritt',
        'endofcontract',
        'oelong',
        'mstbroe',
        'createtime',
        'dvh_text',
        'kartennummer',
        'schrank',
        # NICHT: 'karte_active', 'verlorene_karte', 'karte_active_bool', ...
    )
    list_display_links = ('employeenumber', 'kartennummer')
    search_fields = (
        'employeenumber', 'givenname', 'sn', 'austritt', 'endofcontract',
        'oelong', 'mstbroe', 'createtime', 'dvh_text', 'kartennummer', 'schrank'
    )
    # list_editable = ()  # KEINE Methoden!

class TGastAdmin(admin.ModelAdmin):
    #angezeigte spalten 
    list_display = (
        'employeenumber',      
        'givenname',        
        'sn',                  
        'createtime',        
        'kartennummer',        
        'active',            
        'verlorene_karte',    
        'abteilung',          
        'funktion',            
        'gelesen_am',          
        'schrank',             
        # weitere Felder wie im Model
    )
    #wie information button, damit man kann aufmachen
    list_display_links = ('employeenumber', 'kartennummer')
    #über welchen felden mann suchen kann
    search_fields = ('employeenumber', 'kartennummer', 'abteilung', 'funktion', 'gelesen_am', 'createtime', 'schrank')
    #die liste was mann bearbeiten kann
    list_editable = ('verlorene_karte', 'active')


admin.site.register(TGast, TGastAdmin)
admin.site.register(PaxtonViewWeb, PaxtonViewWebAdmin)
admin.site.register(TStudenten, TStudentenAdmin)
