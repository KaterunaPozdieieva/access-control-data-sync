from django.shortcuts import render

from django.http import HttpResponse, JsonResponse
from Tabelle import get_token, get_paxton_users, fetch_all_access_levels, get_departments_dict, get_access_levels_dict
import requests
import re
from coolsite.api_config import *
from dateutil import parser


username = "OEM Client"
password = "GodotekAzikabu"
grant_type = "password"
client_id = "18a5f964-f120-4fe0-a31a-6ccd3995cb13"


# API_URL = 'http://sr0041895.medi.local:8080/api/v1/'
# TOKEN_URL = f'{API_URL}authorization/tokens'
# ACCESS_LEVELS_URL = f'{API_URL}accesslevels'
# DEPARTMENTS_URL = f'{API_URL}departments'

# def get_token():
#     auth_data = {
#         'grant_type': grant_type,
#         'username': username,
#         'password': password,
#         'client_id': client_id
#     }
#     print("get_token: Sende Anfrage an Token-API...")
#     try:
#         response = requests.post(TOKEN_URL, data=auth_data)
#         print("get_token: Response-Code:", response.status_code)
#         response.raise_for_status()
#         token = response.json().get('access_token')
#         print("get_token: Token erhalten:", token)
#         return token
#     except requests.RequestException as e:
#         print("get_token: Fehler beim Token-Abruf:", e)
#         return None





# def Neue_Berechtigungsname(request):
#     """View zum Testen des Token-Abrufs und Anzeigen des Formulars"""
#     print(" View 'Neue_Berechtigungsname' wurde aufgerufen.")
#     token = get_token()
#     message = f"Token erfolgreich geladen: {bool(token)}"
#     print(" Token-Rückgabe in View:", token)

#     access_levels = fetch_all_access_levels(token) if token else []
#     print("Access Levels:", access_levels)


#     return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html', {
#         'message': message,
#         'selected_level': '',
#         'new_level_name': '',
#         'access_levels': access_levels,
#     })


# def fetch_all_access_levels(token):
#     headers = {'Authorization': f'Bearer {token}'}
#     try:
#         response = requests.get(ACCESS_LEVELS_URL, headers=headers)
#         response.raise_for_status()
#         data = response.json()
#         # Paxton liefert manchmal {"accessLevels": [...]}
#         if isinstance(data, dict) and "access_levels" in data:
#             data = data["access_levels"]
#             print("fetch_all_access_levels: data von API =", data)

#         return [{"id": item.get("id"), "name": item.get("name", "Unbekannte Berechtigungsgruppe")} for item in data]
#     except Exception as e:
#         print(f"Fehler beim Abrufen der Berechtigungsgruppen: {e}")
#         return []




def get_token():
    auth_data = {
        'grant_type': grant_type,
        'username': username,
        'password': password,
        'client_id': client_id
    }
    r = requests.post(TOKEN_URL, data=auth_data)
    print("Token Response:", r.status_code, r.text)
    r.raise_for_status()
    return r.json().get('access_token')

token = get_token()
headers = {'Authorization': f'Bearer {token}'}
r = requests.get(ACCESS_LEVELS_URL, headers=headers)
print("Access Levels Response:", r.status_code)
print(r.text)



def Neue_Berechtigungsname(request):
    print("View 'Neue_Berechtigungsname' wurde aufgerufen.")
    token = get_token()
    message = f"Token erfolgreich geladen: {bool(token)}"
    print("Token:", token)

    if token:
        import requests
        headers = {'Authorization': f'Bearer {token}'}
        r = requests.get(ACCESS_LEVELS_URL, headers=headers)
        print("Direkter API-Test -> Status:", r.status_code)
        print("Direkter API-Test -> Antworttext:", r.text[:500])  # Nur erste 500 Zeichen
    else:
        print("Kein Token erhalten — API-Test übersprungen.")

    levels = fetch_all_access_levels()    #(token) if token else []
    print("Access Levels:", access_levels)

    return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html', {
        'message': message,
        'selected_level': '',
        'new_level_name': '',
        'access_levels': access_levels,
    })


#test
def get_filter_options(request):
    filter_type = request.GET.get('type')

    if filter_type == 'accesslevels':
        levels = fetch_all_access_levels()
        print("DEBUG levels:", levels)  # <--- richtige Variable!
        if levels and isinstance(levels[0], dict):
            names = [level.get('name') for level in levels if level.get('name')]
        else:
            names = levels
        print("DEBUG extracted names:", names)  # <--- richtige Variable!
        return JsonResponse(names, safe=False)

    return JsonResponse([], safe=False)















# origen
# def get_filter_options(request):
#     """Gibt dynamische Listen für Datalists im Frontend zurück."""
#     filter_type = request.GET.get('type')

#     if filter_type == 'accesslevels':
#         # Zugriffsebenen holen (z. B. aus deiner bestehenden Funktion)
#         access_levels = fetch_all_access_levels()
#         # Zugriffsebenen-Namen extrahieren (falls Objekte)
#         if access_levels and isinstance(access_levels[0], dict):
#             names = [level.get('name') for level in access_levels if level.get('name')]
#         else:
#             names = access_levels
#         return JsonResponse(names, safe=False)

#     # Fallback, falls kein Typ gefunden
#     return JsonResponse([], safe=False)


#test
# def Neue_Berechtigungsname(request):
#     print("View 'Neue_Berechtigungsname' wurde aufgerufen.")
#     message = "View wird ausgeführt!"
#     access_levels = fetch_all_access_levels()
#     print("Access Levels:", access_levels)
#     return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html', {
#         'message': message,
#         'selected_level': '',
#         'new_level_name': '',
#         'access_levels': access_levels,
#     })

































# def Neue_Berechtigungsname(request):
#     token = get_token()
#     print("Token:", token)
#     if not token:
#         print("Kein Token erhalten")
#         return JsonResponse({"error": "Kein Token erhalten"}, status=401)


#     access_levels = get_access_levels_dict(token)
#     print("Access Levels:", access_levels)

#     departments = get_departments_dict(token)
#     print("Departments:", departments)

#     # Ausgabe zum Testen
#     print("Access Levels:", access_levels)
#     print("Departments:", departments)

#     # An Template weitergeben
#     return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html', {
#         'message': f"Token erfolgreich geladen: {bool(token)}",
#         'access_levels': access_levels,
#         'selected_level': selected_level,
#         'new_level_name': new_level_name,
#     })

# #
# def get_token():
#     auth_data = {
#         'grant_type': grant_type,
#         'username': username,
#         'password': password,
#         'client_id': client_id
#     }
#     try:
#         response = requests.post(TOKEN_URL, data=auth_data)
#         response.raise_for_status()
#         return response.json().get('access_token')
#     except requests.RequestException as e:
#         print(f"Token-Abruf fehlgeschlagen: {e}")
#         return None

# def fetch_all_access_levels(token):
#     headers = {'Authorization': f'Bearer {token}'}
#     try:
#         response = requests.get(ACCESS_LEVELS_URL, headers=headers)
#         response.raise_for_status()
#         data = response.json()
#         # Paxton liefert manchmal {"accessLevels": [...]}
#         if isinstance(data, dict) and "accessLevels" in data:
#             data = data["accessLevels"]
#         return [{"id": item.get("id"), "name": item.get("name", "Unbekannte Berechtigungsgruppe")} for item in data]
#     except Exception as e:
#         print(f"Fehler beim Abrufen der Berechtigungsgruppen: {e}")
#         return response.json()


# def update_access_level(token, level_id, new_name, detailRows=None):
#     headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
#     url = f"{API_URL}accesslevels/{level_id}"
#     payload = {
#         "id": level_id,
#         "name": new_name,
#         "detailRows": detailRows or []
#     }
#     response = requests.put(url, headers=headers, json=payload)
#     return response


# def get_access_levels_dict(token):
#     levels = fetch_all_access_levels(token)
#     return {str(level["id"]): level.get("name", f'ID {level["id"]}') for level in levels}

# @require_http_methods(["GET", "POST"])
# def Neue_Berechtigungsname(request):
#     message = ""
#     selected_level = ""
#     new_level_name = ""

#     token = get_token()
#     if not token:
#         message = "Kein Token erhalten"
#         access_levels = []
#     else:
#         # Access Levels als "ID - Name" für datalist
#         all_levels = fetch_all_access_levels(token)
#         access_levels = [f"{level['id']} - {level['name']}" for level in all_levels]

#     if request.method == "POST":
#         selected_level = request.POST.get("accessLevelInput", "").strip()
#         new_level_name = request.POST.get("newAccessLevel", "").strip()
#         # Extrahiere die ID aus "ID - Name"
#         try:
#             level_id = int(selected_level.split('-')[0].strip())
#         except Exception:
#             level_id = None

#         if not selected_level or not new_level_name or not level_id:
#             message = "Bitte geben Sie sowohl die ausgewählte Berechtigungsgruppe als auch den neuen Namen ein."
#         else:
#             headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
#             # Hole Details des Levels
#             all_levels = fetch_all_access_levels(token)
#             level_to_update = next((level for level in all_levels if level.get("id") == level_id), None)
#             if not level_to_update:
#                 message = f"Berechtigungsgruppe mit ID '{level_id}' wurde nicht gefunden."
#             else:
#                 if level_id in [0, 1]: # Standardgruppen dürfen nicht geändert werden
#                     message = f"Die Berechtigungsgruppe mit ID {level_id} kann nicht geändert werden."
#                 else:
#                     payload = {
#                         "id": level_id,
#                         "name": new_level_name,
#                         "detailRows": level_to_update.get("detailRows", [])
#                     }
#                     update_response = requests.put(f"{ACCESS_LEVELS_URL}/{level_id}", headers=headers, json=payload)
#                     if update_response.status_code == 200:
#                         message = "Änderungen erfolgreich gespeichert!"
#                         # Aktualisiere Vorschlagsliste nach Änderung
#                         all_levels = fetch_all_access_levels(token)
#                         access_levels = [f"{level['id']} - {level['name']}" for level in all_levels]
#                     elif update_response.status_code == 409:
#                         message = "Es existiert bereits eine Berechtigungsgruppe mit diesem Namen. Bitte wählen Sie einen anderen Namen!"
#                     else:
#                         message = "Unbekannter Fehler beim Speichern."

#     return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html', {
#         'message': message,
#         'access_levels': access_levels,
#         'selected_level': selected_level,
#         'new_level_name': new_level_name,
#     })
# #    """API-Endpunkt: Ändert den Namen einer Berechtigungsgruppe in Paxton."""
# @require_POST
# def change_access_level(request):
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Keine Daten empfangen. Prüfen Sie das Frontend."}), 400

#     selected_level = data.get("selected_level")
#     new_level_name = data.get("new_level_name")

#     if not selected_level or not new_level_name:
#         print(f"Berechtigungsgruppe oder neuer Name fehlt.")
#         return JsonResponse({"error": "Sowohl die ausgewählte Berechtigungsgruppe als auch der neue Name sind erforderlich."}), 400

#     token = get_token()
#     if not token:
#         print(f"Token konnte nicht abgerufen werden.")
#         return JsonResponse({"error": "Fehler beim Abrufen des Tokens"}), 500

#     headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
#     response = requests.get(ACCESS_LEVELS_URL, headers=headers)
#     if response.status_code != 200:
#         print(f"Fehler beim Abrufen der Berechtigungsgruppen.")
#         return JsonResponse({"error": "Fehler beim Abrufen der Berechtigungsgruppen"}), response.status_code

#     access_levels = response.json()
#     if isinstance(access_levels, dict) and "accessLevels" in access_levels:
#         access_levels = access_levels["accessLevels"]

#     level_to_update = next((
#         level for level in access_levels
#         if level.get("name", "").strip().lower() == selected_level.strip().lower()
#     ), None)
#     if not level_to_update:
#         print(f"Berechtigungsgruppe '{selected_level}' wurde nicht gefunden.")
#         return JsonResponse({"error": f"Die ausgewählte Berechtigungsgruppe '{selected_level}' wurde nicht gefunden."}), 404

#     level_id = level_to_update["id"]
#     if level_id in [0, 1]:
#         print(f"Berechtigungsgruppe mit ID {level_id} darf nicht geändert werden.")
#         return JsonResponse({"error": f"Die Berechtigungsgruppe mit ID {level_id} kann nicht geändert werden."}), 400

#     payload = {
#         "id": level_id,
#         "name": new_level_name,
#         "detailRows": level_to_update.get("detailRows", [])
#     }

#     update_response = requests.put(f"{ACCESS_LEVELS_URL}{level_id}", headers=headers, json=payload)

#     if update_response.status_code == 200:
#         print(f"Berechtigungsgruppe '{selected_level}' wurde in '{new_level_name}' geändert.")
#         neue_liste = requests.get(ACCESS_LEVELS_URL, headers=headers).json()
#         return JsonResponse({
#             "message": "Berechtigungsgruppe erfolgreich aktualisiert.",
#             "access_levels": neue_liste
#         }), 200
#     else:
#         print(f"Fehler beim Aktualisieren von Berechtigungsgruppe ID {level_id}.")
#         return JsonResponse({
#             "error": "Fehler beim Aktualisieren der Berechtigungsgruppe",
#             "details": update_response.text
#         }), update_response.status_code

# @require_GET
# def neue_name(request):
#     token = get_token()
#     if not token:
#         return JsonResponse(data, safe=False)

#     headers = {'Authorization': f'Bearer {token}'}
#     response = requests.get(ACCESS_LEVELS_URL, headers=headers)

#     if response.status_code == 200:
#         levels = response.json()
#         return JsonResponse(data, safe=False)
#     else:
#         return JsonResponse([], safe=False)

# @require_GET
# def get_filter_options(request):
#     typ = request.GET.get('type')
#     token = get_token()
#     if typ == "benutzergruppen":
#         benutzergruppen = []
#         if token:
#             departments = get_departments_dict(token)
#             benutzergruppen = list(departments.values())
#         return JsonResponse([], safe=False)

#     if typ == "berechtigungsgruppen":
#         berechtigungsgruppen = []
#         if token:
#             access_levels = get_access_levels_dict(token)
#             berechtigungsgruppen = list(access_levels.values())
#         return JsonResponse([], safe=False)
#     return JsonResponse([], safe=False)



# # ✓ 
def formular_view(request):
    return render(request, 'Formular/paxton_formular.html', {'benutzerabbrechen': benutzerabbrechen})

benutzerabbrechen = [{'title': "Abbrechen und zurück", 'url_name': 'algemeineTabelle'}]
