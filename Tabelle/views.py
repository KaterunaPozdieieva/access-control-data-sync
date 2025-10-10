import datetime
from django.shortcuts import render
from django.http import HttpResponseNotFound, JsonResponse
from .models import TGast, TStudenten, PaxtonViewWeb
from django.views.decorators.http import require_GET, require_POST
import requests
import re
from coolsite.api_config import *
from dateutil import parser
from django.db import connection



username = "OEM Client"
password = "GodotekAzikabu"
grant_type = "password"
client_id = "18a5f964-f120-4fe0-a31a-6ccd3995cb13"



def get_benutzer_liste(benutzertyp, page, per_page, sort_by, order):
    benutzer_liste = []

    # Model bestimmen
    if benutzertyp == "Gäste":
        model = TGast
    elif benutzertyp == "Studenten":
        model = TStudenten
    else:
        model = PaxtonViewWeb
    # Sortierung
    DEFAULT_SORT_FIELDS = {
        "t_Gast": "employeenumber",
        "t_studenten": "employeenumber",
        "paxton_view_web": "employeenumber",
    }
    sort_by = sort_by if sort_by else default_sort

    model_fields = [field.name for field in model._meta.fields]
    if sort_by not in model_fields:
        sort_by = default_sort if default_sort in model_fields else model_fields[0]

    offset = (page - 1) * per_page
    queryset = model.objects.all().order_by(
        f"{'-' if order.upper() == 'DESC' else ''}{sort_by}"
    )[offset:offset+per_page]

    for row in queryset:
        # Fülle die user_data je nach Typ
        if benutzertyp == "Gäste":
            individualPermissions = getattr(row, 'individualPermissions', None)
            individualPermissions_display = "Ja" if individualPermissions and str(individualPermissions).strip() else ""
            user_data = {
                "quelle": "Gast",
                "Personalnummer": "",
                "kartennummer": getattr(row, 'kartennummer', ''),
                "name_full": f"{getattr(row, 'givenname', '')} {getattr(row, 'sn', '')}".strip(),
                "active": getattr(row, 'karte_active', False),
                "abteilung": getattr(row, 'einrichtung', ''),
                "verlorene_karte": getattr(row, 'verlorene_karte', False),
                "funktion": getattr(row, 'funktion', ''),
                "gelesen_am": row.gelesen_am.strftime("%Y-%m-%d %H:%M") if getattr(row, 'gelesen_am', None) else "",
                "createtime": row.createtime.strftime("%Y-%m-%d %H:%M") if getattr(row, 'createtime', None) else "",
                "benutzergruppe_id": getattr(row, 'benutzergruppe', ''),
                "berechtigungsgruppe_id": getattr(row, 'berechtigungsgruppe', ''),
                'individualPermissions': individualPermissions_display,
                "schrank": getattr(row, 'schrank_nr_alt', ''),
            }
        elif benutzertyp == "Studenten":
            individualPermissions = getattr(row, 'individualPermissions', None)
            individualPermissions_display = "Ja" if individualPermissions and str(individualPermissions).strip() else ""
            user_data = {
                "quelle": "Student",
                "employeenumber": getattr(row, 'employeenumber', ''),
                "kartennummer": getattr(row, 'kartennummer', ''),
                "name_full": f"{getattr(row, 'givenname', '')} {getattr(row, 'sn', '')}".strip(),
                "active": getattr(row, 'karte_active', False),
                "abteilung": getattr(row, 'einrichtung', ''),
                "verlorene_karte": getattr(row, 'verlorene_karte', False),
                "funktion": getattr(row, 'funktion', ''),
                "gelesen_am": row.gelesen_am.strftime("%Y-%m-%d %H:%M") if getattr(row, 'gelesen_am', None) else "",
                "createtime": row.createtime.strftime("%Y-%m-%d %H:%M") if getattr(row, 'createtime', None) else "",
                "benutzergruppe_id": getattr(row, 'benutzergruppe', ''),
                "berechtigungsgruppe_id": getattr(row, 'berechtigungsgruppe', ''),
                'individualPermissions': individualPermissions_display,
                "schrank": getattr(row, 'schrank', ''),
            }
        else:  # Mitarbeiter (PaxtonViewWeb)
            if getattr(row, 'austritt', None):
                vertragsende = row.austritt.strftime("%Y-%m-%d")
            elif getattr(row, 'endofcontract', None):
                vertragsende = row.endofcontract.strftime("%Y-%m-%d")
            else:
                vertragsende = ""
            individualPermissions = getattr(row, 'individualPermissions', None)
            individualPermissions_display = "Ja" if individualPermissions and str(individualPermissions).strip() else ""
            user_data = {
                "quelle": "Mitarbeiter",
                "employeenumber": getattr(row, 'employeenumber', ''),
                "kartennummer": getattr(row, 'kartennummer', ''),
                "name_full": f"{getattr(row, 'givenname', '')} {getattr(row, 'sn', '')}".strip(),
                "active": getattr(row, 'karte_active', False),
                "karte_active": getattr(row, 'karte_active', False),
                "verlorene_karte": getattr(row, 'verlorene_karte', False),
                "abteilung": getattr(row, 'mstbroe', ''),
                "funktion": getattr(row, 'dvh_text', ''),
                "gelesen_am": getattr(row, 'gelesen_am', '') if hasattr(row, 'gelesen_am') else "",
                "createtime": row.createtime.strftime("%Y-%m-%d %H:%M") if getattr(row, 'createtime', None) else "",
                "vertragsende": vertragsende,
                "benutzergruppe_id": getattr(row, 'benutzergruppe', ''),
                "berechtigungsgruppe_id": getattr(row, 'berechtigungsgruppe', ''),
                "individualpermissions": individualPermissions_display,
                "schrank": getattr(row, 'schrank', ''),
            }
        benutzer_liste.append(clean_none(user_data))

    return benutzer_liste

# ?✓ 
def algemeineTabelle(request):
    benutzertyp = request.GET.get('benutzertyp', 'Alle')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 30))
    sort_by = request.GET.get('sort_by', 'kartennummer')
    order = request.GET.get('order', 'DESC')

    benutzer_liste = get_benutzer_liste(benutzertyp, page, per_page, sort_by, order)
    

    return render(request, 'Tabelle/paxton_tabelle.html', {
        'knopf': knopf, # für die zuseztliche buttons(paxton, szlte_schlagbaum und paarkkarten)
        'benutzer_liste': benutzer_liste,
        'benutzertyp': benutzertyp,
        'total': len(benutzer_liste),
        'page': page,
        'per_page': per_page,
        'menu': menu,
    })

#✓ 
def get_token():
    auth_data = {
        'grant_type': grant_type,
        'username': username,
        'password': password,
        'client_id': client_id
    }
    try:
        response = requests.post(TOKEN_URL, data=auth_data)
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Token-Abruf fehlgeschlagen: {e}")
        return None

# #  ✓ aber nicht in tabele angezeigt  """Holt alle User aus Paxton über die API."""
def get_paxton_users(token):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    try:
        response = requests.get(USER_URL, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Benutzerabruf fehlgeschlagen: {e}")
        return []




#    """Holt alle Berechtigungsgruppen aus Paxton."""
from coolsite.api_config import ACCESS_LEVELS_URL

def fetch_all_access_levels():
    print("fetch_all_access_levels() wird ausgeführt")
    try:
        response = requests.get(ACCESS_LEVELS_URL, headers={"Authorization": f"Bearer {get_token()}"})
        print("fetch_all_access_levels() wurde ausgeführt")
        response.raise_for_status()
        data = response.json()
        print("API-Daten:", data)
        if isinstance(data, list):
            return [{"id": item.get("id"), "name": item.get("name", "Unbekannte Berechtigungsgruppe")} for item in data]
        elif isinstance(data, dict) and "accessLevels" in data:
            return [{"id": item.get("id"), "name": item.get("name", "Unbekannte Berechtigungsgruppe")} for item in data["accessLevels"]]
        else:
            return []
    except Exception as e:
        print(f"Fehler beim Abrufen der Berechtigungsgruppen: {e}")

#    """Holt alle Benutzergruppen (Departments) als Dict {id: name} aus Paxton."""
def get_departments_dict(token):
    url = f"{API_URL}departments"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        departments = response.json()
        return {str(dep["id"]): dep.get("name", f'ID {dep["id"]}') for dep in departments}
    except Exception as e:
        print(f"Konnte Departments nicht holen: {e}")
        return {}


#    """Holt alle Berechtigungsgruppen als Dict {id: name} aus Paxton."""
def get_access_levels_dict(token):
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(ACCESS_LEVELS_URL, headers=headers)
        response.raise_for_status()
        levels = response.json()
        return {str(level["id"]): level.get("name", f'ID {level["id"]}') for level in levels}
    except Exception as e:
        print(f"Konnte AccessLevels nicht holen: {e}")
        return {}













# ?✓  filter funktion  """API-Endpunkt: Gibt Benutzerdaten inklusive aller Namen aufgelöst für die Tabelle zurück."""
@require_GET
def get_users(request):
    def safe_int(val, default):
        try:
            return int(val)
        except (TypeError, ValueError):
            return default
#  ?✓
    page = safe_int(request.GET.get('page', 1), 1)
    per_page = safe_int(request.GET.get('per_page', 30), 30)
    sort_by = request.GET.get('sort_by', 'createtime')
    order = request.GET.get('order', 'DESC')







    filters = {}
    for key, value in request.GET.items():
        if key.startswith("filter_") and value.strip():
            filters[key[7:]] = value.strip()
    filter_status = request.GET.get('status', '').strip()

    benutzertyp = filters.pop("DBFilter", None)
    tabellenname = None
    if benutzertyp == "Gäste":
        tabellenname = "t_Gast"
    elif benutzertyp == "Studenten":
        tabellenname = "t_studenten"
    else:
        tabellenname = "paxton_view_oweb"

    benutzer_liste = get_benutzer_liste(benutzertyp, page, per_page, sort_by, order)







    token = get_token()
    departments_dict = get_departments_dict(token) if token else {}
    access_levels_dict = get_access_levels_dict(token) if token else {}


#  ? ✓
    for user in benutzer_liste:
        benutzergruppe_id = user.get("benutzergruppe_id")
        berechtigungsgruppe_id = user.get("berechtigungsgruppe_id")
        user["benutzergruppe"] = departments_dict.get(str(benutzergruppe_id), "")
        user["berechtigungsgruppe"] = access_levels_dict.get(str(berechtigungsgruppe_id), "")
#alt
    # for user in benutzer_liste:
    #     benutzergruppe_id = user.get("benutzergruppe_id")
    #     berechtigungsgruppe_id = user.get("berechtigungsgruppe_id")
    #     user["benutzergruppe"] = (
    #         departments_dict.get(benutzergruppe_id, "")
    #         if benutzergruppe_id and benutzergruppe_id not in ("None", None) else ""
    #     )
    #     user["berechtigungsgruppe"] = (
    #         access_levels_dict.get(berechtigungsgruppe_id, "")
    #         if berechtigungsgruppe_id and berechtigungsgruppe_id not in ("None", None) else ""
    #     )






#  ✓ 
    if filters:
        benutzer_liste = filter_rows(benutzer_liste, filters)

    for user in benutzer_liste:
        status, status_color, status_class = get_status_from_row(user, tabellenname)
        user["Status"] = status
        user["StatusColor"] = status_color
        user["StatusClass"] = status_class
        print(user["Status"], user["StatusClass"])

    sort_mapping = {
        "createtime": "Erstellzeit",
        "austritt": "endofcontract",
        "employeenumber": "employeenumber",
        "kartennummer": "kartennummer"
    }
    sort_field = sort_mapping.get(sort_by, sort_by)








    if filter_status:
        benutzer_liste = [u for u in benutzer_liste if u['Status'] == filter_status]

    if sort_field:
        reverse = (order or '').upper() == 'DESC'
        try:
            benutzer_liste.sort(key=lambda user: get_sort_key_for_user(user, sort_field), reverse=reverse)
        except Exception:
            pass

    total_users = len(benutzer_liste)
    start = (page - 1) * per_page
    end = start + per_page
    page_users = benutzer_liste[start:end]

    return JsonResponse({
    "users": page_users,
    "current_page": page,
    "total_users": total_users
})


#  ?✓  """Filtern von Benutzerlisten nach Such-/Filterparametern."""
def filter_rows(data, filters):
    date_fields = ["createtime", "austritt", "endofcontract", "modifytime", "gedruckt_am", "gelesen_am"]
    def match(row):
        for key, value in filters.items():
            if not value:
                continue

            val = str(row.get(key, "")).strip() 

            # Name-Filter
            if key == "name_full":
                if value.lower() not in val.lower():
                    return False

            # Datumsfilter (Jahr/Monat/Text)
            elif key in date_fields:
                filter_val = value.strip()
                if re.fullmatch(r"\d{4}", filter_val) and val:
                    try:
                        jahr = int(filter_val)
                        parsed = parser.parse(val)
                        if parsed.year != jahr:
                            return False
                    except Exception:
                        return False
                elif re.fullmatch(r"\d{4}[\.\-]\d{2}", filter_val):
                    norm = filter_val.replace(".", "-")
                    if not val.startswith(norm):
                        return False
                elif filter_val.lower() not in val.lower():
                    return False

            # Status-Filter (Aktiv, Inaktiv, VerloreneKarte) - das wird im Feld "Status" erwartet!
            elif key == "status":
                if value.lower() != val.lower():
                    return False

            # Boolean-Filter für verlorene_karte 
            elif key == "verlorene_karte":
                val_bool = str(val).lower()
                value_bool = str(value).lower()
                if value_bool in ["1", "true", "ja"]:
                    if val_bool not in ["1", "true", "ja"]:
                        return False
                elif value_bool in ["0", "false", "nein"]:
                    if val_bool not in ["0", "false", "nein"]:
                        return False
                else:
                    if value_bool != val_bool:
                        return False

            # String-Filter für andere Felder
            else:
                if value.lower() not in val.lower():
                    return False
        return True

    return [row for row in data if match(row)]



#   ?✓  """API-Endpunkt: Gibt Werte-Listen für bestimmte Felder für die Filterauswahl zurück."""
@require_GET
def get_datalist_options(request):
    allowed_fields = {
        "mstbroe": "mstbroe",
        "dvh_text": "dvh_text",
        "schrank": "schrank",
        "employeenumber": "employeenumber",
        "createtime": "createtime",
        "Austritt": "Austritt"
    }
    field = request.GET.get("field")
    if field not in allowed_fields:
        return JsonResponse([], safe=False)

    sql = f"SELECT {allowed_fields[field]} FROM [HCM_Daten].[dbo].[paxton_view_web] WHERE {allowed_fields[field]} IS NOT NULL AND {allowed_fields[field]} != ''"
    datalist = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        values = [str(row[0]) for row in rows if row[0]]
        if field in ["createtime", "Austritt"]:
            years = {v[:4] for v in values if len(v) >= 4}
            year_months = {v[:7] for v in values if len(v) >= 7}
            datalist = sorted(years | year_months | set(values))
        else:
            datalist = sorted(set(values))
    return JsonResponse([datalist], safe=False)


#  ?✓  """API-Endpunkt: Liefert alle Namen für Autovervollständigung."""
@require_GET
def get_name_options(request):
    sql = """
        SELECT DISTINCT givenName, sn 
        FROM [HCM_Daten].[dbo].[paxton_view_web]
        WHERE kartennummer IS NOT NULL AND sn IS NOT NULL
    """
    name_list = []
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        name_list = [f"{row[0]} {row[1]}" for row in rows if row[0] and row[1]]
    return JsonResponse(name_list, safe=False)








# #  hab es nicht in html    """API-Endpunkt: Gibt Optionen für Berechtigungsgruppen zurück."""
# @app.route('/berechtigungen_verarbeitung', methods=['GET'])
# def get_options(request):
#     list_type = request.GET.get('type')
#     if not list_type:
#         return JsonResponse({"error": "Typ fehlt"}), 400
#     if list_type == 'access_levels':
#         return JsonResponse(fetch_all_access_levels())
#     return JsonResponse({"error": "Ungültiger Typ"}), 400




#    """API-Endpunkt: Liefert alle Berechtigungsgruppen (Name/ID) aus Paxton."""
@require_GET
def neue_name(request):
    token = get_token()
    if not token:
        return JsonResponse(data, safe=False)

    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(ACCESS_LEVELS_URL, headers=headers)

    if response.status_code == 200:
        levels = response.json()
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse([], safe=False)






#    """vertragender zusamen schreibt."""
def get_sort_key_for_user(user, sort_field):
    value = user.get(sort_field)
    if value is None:
        return ''
    if sort_field in ("Erstellzeit", "Vertragsende"):
        try:
            return parser.parse(value)
        except Exception:
            return value
    return value.lower() if isinstance(value, str) else value

 
#    """API-Endpunkt: Gibt alle verfügbaren Werte für Dropdown-Filter zurück."""
@require_GET
def get_filter_options(request):
    typ = request.GET.get('type')
    token = get_token()
    if typ == "benutzergruppen":
        benutzergruppen = []
        if token:
            departments = get_departments_dict(token)
            benutzergruppen = list(departments.values())
        return JsonResponse([], safe=False)

    if typ == "berechtigungsgruppen":
        berechtigungsgruppen = []
        if token:
            access_levels = get_access_levels_dict(token)
            berechtigungsgruppen = list(access_levels.values())
        return JsonResponse([], safe=False)
    return JsonResponse([], safe=False)










#  ✓   """Ermittelt den Status eines Benutzers anhand seiner Felder."""
def get_status_from_row(user, tabellenname="paxton_view_web"):
    # PaxtonViewWeb: Status über beide Felder
    if tabellenname == "paxton_view_web":
        mitarbeiter_active = user.get('active')
        karte_active = user.get('karte_active')
        verlorene_karte = user.get('verlorene_karte', 0)
        # Robust: True/False/"1"/"0"/1/0 werden erkannt
        if verlorene_karte in [1, "1", True, "True"]:
            return "VerloreneKarte", "red", "status-red"
        elif mitarbeiter_active in [1, "1", True, "True"] and karte_active in [1, "1", True, "True"]:
            return "Aktiv", "green", "status-green"
        elif (
            (mitarbeiter_active in [0, "0", False, "False"] and karte_active in [0, "0", False, "False"]) or
            (mitarbeiter_active in [1, "1", True, "True"] and karte_active in [0, "0", False, "False"]) or
            (mitarbeiter_active in [0, "0", False, "False"] and karte_active in [1, "1", True, "True"])
        ):
            return "Inaktiv", "grau", "status-gray"
        else:
            return "Unbekannt", "black", "status-black"
    # Gast und Studenten: Nur das active-Feld
    elif tabellenname in ("t_Gast", "t_studenten"):
        active = user.get('active')
        verlorene_karte = user.get('verlorene_karte', 0)
        if verlorene_karte in [1, "1", True, "True"]:
            return "VerloreneKarte", "red", "status-red"
        elif active in [1, "1", True, "True"]:
            return "Aktiv", "green", "status-green"
        elif active in [0, "0", False, "False"]:
            return "Inaktiv", "grau", "status-grau"
        else:
            return "Unbekannt", "black", "status-black"
    return "Unbekannt", "black", "status-black"



#✓ 
knopf = [{'title': "Paxton", 'url_name': 'formular'},
        #{'title': "Schulte_Schlagbaum", 'url_name': 'spind'},
        #{'title': "Parkkarten", 'url_name': 'parkkarten'},
]
# ✓
menu = [{'title': "Paxton - Berechtigungsname ändern", 'url_name': 'Neue_Berechtigungsname'}]
# ✓
abbrechen = [{'title': "Abbrechen und zurück", 'url_name': 'algemeineTabelle'}]


# ✓
def Neue_Berechtigungsname(request):
    return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html',
    {'abbrechen': abbrechen})



# ✓
def pageNotFound(request, exception):
    return HttpResponseNotFound('<h1>Seite nicht gefunden</h1>')
# ✓
def clean_none(user_dict):
    """Setzt alle None und 'None' Werte im Dict auf '' (leer)."""
    return {k: ("" if v is None or v == "None" else v) for k, v in user_dict.items()}