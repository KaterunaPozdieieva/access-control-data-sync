
import requests
from django.conf import settings
import json
import logging
from django.db import connection, transaction, DatabaseError
import os
import re
from synchronisation.Paxton_funk  import _session, fetch_all_access_levels,REQUEST_TIMEOUT, create_or_update_department, get_token, get_paxton_user_id_by_kartennummer, get_paxton_users, delete_paxton_user, get_user_tokens, get_access_level_by_id,  update_paxton_user, _headers, logp, create_access_level, ACCESS_LEVELS_URL, get_departments_dict 


#Funktionen, um Daten in der Datenbank und in Paxton Access zu speichern (über ein Formular).
logger = logging.getLogger('paxton')



def _normalize_payload(payload):
    if "customFields" in payload:
        out = []
        for cf in payload["customFields"]:
            try:
                cid = int(cf.get("id"))
                out.append({"id": cid, "value": str(cf.get("value") or "")})
            except Exception:
                continue
        payload["customFields"] = out
    if "accessLevels" in payload:
        payload["accessLevels"] = [int(x) for x in payload["accessLevels"] if str(x).isdigit()]
    return payload


def get_access_levels_dict_from_fetch():
    levels = fetch_all_access_levels()
    return {str(d["id"]): d["name"] for d in levels if "id" in d and "name" in d}



#die BerechtigungsID 
def update_access_level(level_id, new_name, token=None):
    token = token or get_token()
    if not token:
        return False, 500, "Kein Token"
    existing = get_access_level_by_id(level_id, token)
    if not existing:
        return False, 404, "Nicht gefunden"
    payload = {
        "id": existing.get("id", level_id),
        "name": new_name,
        "detailRows": existing.get("detailRows", []) if isinstance(existing, dict) else []
    }
    try:
        url = f"{ACCESS_LEVELS_URL}/{level_id}"
        resp = _session.put(url, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (200, 204):
            try:
                return True, resp.status_code, resp.json() if resp.text else {}
            except Exception:
                return True, resp.status_code, {}
        elif resp.status_code == 409:
            return False, 409, "Name already exists"
        else:
            try:
                return False, resp.status_code, resp.json()
            except Exception:
                return False, resp.status_code, resp.text
    except Exception:
        logger.exception("Fehler beim Update des AccessLevel %s", level_id)
        return False, 500, "Error"



def _to_int_or_none(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    if not s.isdigit():
        raise ValueError(f"Expected int value, got: {v!r}")
    return int(s)

def save_to_db(kartennummer, benutzergruppe, berechtigungsgruppe):
    if not kartennummer or str(kartennummer).strip() == "":
        raise ValueError("kartennummer required")

    bg_val = _to_int_or_none(benutzergruppe)
    ag_val = _to_int_or_none(berechtigungsgruppe)

    with transaction.atomic():
        with connection.cursor() as c:
            c.execute(
                "EXEC [Sap_Daten].[dbo].[sp_save_to_db] @kartennummer=%s, @benutzergruppe=%s, @berechtigungsgruppe=%s",
                [str(kartennummer).strip(), bg_val, ag_val],
            )
            row = c.fetchone() or (0, 0, 0, 0)

    rc_student, rc_gast, rc_paxton_accesslevels, rc_benutzergruppen = row

    return {
        "benutzergruppe": bg_val,
        "berechtigungsgruppe": ag_val,
        "rows": {
            "t_studenten": rc_student,
            "t_Gast": rc_gast,
            "paxton_AccessLevels": rc_paxton_accesslevels,
            "BenutzerGruppen": rc_benutzergruppen,
        },
    }


# Alias - wird von Formular/views.py save_data() aufgerufen
def save_to_paxton(card_number, department_input, access_group_input, token):
    return save_to_paxton_Access_and_Depart(card_number, department_input, access_group_input, token)


def save_to_paxton_Access_and_Depart(card_number, department_input, access_group_input, token):

    if not token:
        raise RuntimeError("Kein Paxton-Token")

    try:
        # Paxton user id finden
        paxton_user_id = get_paxton_user_id_by_kartennummer(card_number, token)
        if not paxton_user_id:
            raise ValueError(f"Paxton-User für Kartennummer {card_number} nicht gefunden")

        # --- Department setzen (wenn angegeben) ---
        if department_input:
            try:
                departments = get_departments_dict(token) or {}  # {id: name}
                departments_id = None
                departments_name = None
                # numeric id?
                if isinstance(department_input, int) or (isinstance(department_input, str) and department_input.isdigit()):
                    departments_id = str(int(department_input))
                    departments_name = departments.get(departments_id)
                else:
                    want = str(department_input).strip().lower()
                    for department_id, department_name in departments.items():
                        if department_name and department_name.strip().lower() == want:
                            departments_id = str(department_id)
                            departments_name = department_name
                            break
                if departments_id:
                    create_or_update_department(paxton_user_id, token, int(departments_id), departments_name or "")
                    logger.info("Paxton: Department gesetzt user=%s id=%s name=%s", paxton_user_id, departments_id, departments_name)
                else:
                    logger.warning("Paxton: Department '%s' nicht gefunden; übersprungen", department_input)
            except Exception:
                logger.exception("Paxton: Fehler beim Setzen des Departments (fortfahren)")

        # --- AccessLevels auflösen / erstellen ---
        final_access_ids = []
        if access_group_input is not None and str(access_group_input).strip() != "":
            # normalize candidates to list of strings
            if isinstance(access_group_input, (list, tuple)):
                candidates = [str(x).strip() for x in access_group_input if x is not None and str(x).strip() != ""]
            else:
                candidates = [p.strip() for p in re.split(r'[,\;\|\n]+', str(access_group_input)) if p.strip()]

            # vorhandene AccessLevels abfragen
            existing_levels = fetch_all_access_levels(token) or []
            name_to_id = { ((l.get("name") or "").strip().lower()): int(l.get("id")) for l in existing_levels if l and (l.get("id") or l.get("Id")) }

            for cand in candidates:
                if cand.isdigit():
                    final_access_ids.append(int(cand))
                    continue
                found_id = name_to_id.get(cand.lower())
                if found_id:
                    final_access_ids.append(found_id)
                    continue
                # wenn nicht gefunden: versuchen anzulegen (create_access_level kümmert sich um detailRows)
                try:
                    created = create_access_level(token, cand)
                    new_id = None
                    if isinstance(created, dict):
                        new_id = created.get("id") or created.get("Id") or created.get("accessLevelId")
                    if not new_id:
                        # fallback: erneut holen und suchen
                        refreshed = fetch_all_access_levels(token) or []
                        for l in refreshed:
                            if ((l.get("name") or "").strip().lower()) == cand.lower():
                                try:
                                    new_id = int(l.get("id"))
                                    break
                                except Exception:
                                    continue
                    if new_id:
                        final_access_ids.append(int(new_id))
                        logger.info("Paxton: AccessLevel '%s' erstellt -> id=%s", cand, new_id)
                    else:
                        logger.warning("Paxton: AccessLevel '%s' erstellt, aber ID unbekannt", cand)
                except requests.exceptions.HTTPError as he:
                    resp = getattr(he, "response", None)
                    logger.error("Paxton: create_access_level HTTP %s: %s", getattr(resp, "status_code", None), getattr(resp, "text", None))
                except Exception:
                    logger.exception("Paxton: Fehler beim Erstellen von AccessLevel '%s'", cand)

        # --- AccessLevels beim User setzen (wenn IDs vorhanden) ---
        if final_access_ids:
            payload = {"accessLevels": final_access_ids, "individualPermissions": []}
            # einige Paxton-APIs verlangen "id" im Body
            try:
                payload["id"] = int(paxton_user_id) if str(paxton_user_id).isdigit() else paxton_user_id
            except Exception:
                payload["id"] = paxton_user_id

            try:
                # Versuche das Update (API erwartet ggf. camelCase keys)
                update_paxton_user(token, paxton_user_id, payload)
                logger.info("Paxton: AccessLevels gesetzt user=%s ids=%s", paxton_user_id, final_access_ids)
            except requests.exceptions.HTTPError as http_err:
                resp = getattr(http_err, "response", None)
                logger.error("Paxton: update_paxton_user HTTP %s: %s", getattr(resp, "status_code", None), getattr(resp, "text", None))
                return False

        return True

    except Exception:
        logger.exception("save_to_paxton: unerwarteter Fehler für kartennummer=%s", card_number)
        raise







# E2E stub aktivierbar per Umgebungsvariable E2E_TEST=1
if os.getenv("E2E_TEST", "0") == "1":
    def get_token():
        return "E2E_TOKEN"

    def fetch_all_access_levels(token=None):
        # Testfreundliche IDs (keine 0/1)
        return [
            {"id": 42, "name": "Admin"},
            {"id": 43, "name": "User"},
            {"id": 44, "name": "ReadOnlyAdmin"},
        ]

    def update_access_level(level_id, new_name, token=None):
        # Simuliere erfolgreiches Update für Tests
        return True, 200, {}



