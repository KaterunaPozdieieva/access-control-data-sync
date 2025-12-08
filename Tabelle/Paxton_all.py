
import requests
from django.conf import settings
import json
import logging
from django.db import connection, transaction, DatabaseError
import os
import re

# Konfiguration 
PAXTON_BASE = getattr(settings, "PAXTON_API_BASE", "**").rstrip("/")
REQUEST_TIMEOUT = getattr(settings, "PAXTON_REQUEST_TIMEOUT", 15)

TOKEN_URL = f"{PAXTON_BASE}/authorization/tokens"
USER_URL = f"{PAXTON_BASE}/users"
USER_TOKENS_URL = f"{PAXTON_BASE}/users/{{}}/tokens"
DEPARTMENT_URL = f"{PAXTON_BASE}/users/{{userId}}/departments"
ACCESS_LEVELS_URL = f"{PAXTON_BASE}/accesslevels"
DEPARTMENTS_URL = f"{PAXTON_BASE}/departments"

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
        resp = requests.put(url, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
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





USERNAME = getattr(settings, "PAXTON_USERNAME", "**")
PASSWORD = getattr(settings, "PAXTON_PASSWORD", "**")
GRANT_TYPE = getattr(settings, "PAXTON_GRANT_TYPE", "password")
CLIENT_ID = getattr(settings, "PAXTON_CLIENT_ID", "*")



# Utility that writes to logger and prints so you see output in console
def logp(level: str, msg: str, *args):
    try:
        getattr(logger, level)(msg, *args)
    except Exception:
        logger.debug("log call failed: " + msg)
    try:
        if args:
            print(msg % args)
        else:
            print(msg)
    except Exception:
        print(msg)

def create_or_update_department(user_id, token, department_id, department_name):
    try:
        url = DEPARTMENT_URL.format(userId=user_id)
        data = {"Name": department_name or "", "Id": int(department_id)}
        resp = requests.put(url, headers=_headers(token), json=data, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        logp('info', "create_or_update_department: user=%s dept=%s name=%s", user_id, department_id, department_name)
        return resp.json() if resp.text else {}
    except Exception:
        logp('exception', "Fehler beim Anlegen/Aktualisieren Department user=%s", user_id)
        raise


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

def _headers(token=None, content_type="application/json"):
    h = {"Accept": "application/json"}
    if content_type:
        h["Content-Type"] = content_type
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def get_token():
    """Hole Access-Token (POST /authorization/tokens)."""
    try:
        data = {
            "grant_type": GRANT_TYPE,
            "username": USERNAME,
            "password": PASSWORD,
            "client_id": CLIENT_ID,
        }
        resp = requests.post(TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        d = resp.json()
        token = d.get("access_token") or d.get("accessToken") or d.get("token")
        logger.debug("get_token: status=%s token_present=%s", getattr(resp, "status_code", None), bool(token))
        return token
    except requests.exceptions.RequestException as e:
        logger.exception("get_token failed: %s", e)
        return None


def create_paxton_user(token: str, payload: dict) -> dict:
    """POST /users - create user; loggt status & body bei Erfolg und Fehler."""
    try:
        logp('debug', "create_paxton_user payload=%s", json.dumps(payload, ensure_ascii=False))
        resp = requests.post(USER_URL, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
        # Log status & body always for debugging
        try:
            body = resp.text
        except Exception:
            body = "<unreadable body>"
        logp('info', "create_paxton_user response status=%s body=%s", getattr(resp, "status_code", None), body)
        resp.raise_for_status()
        # Return parsed JSON if present, else empty dict
        try:
            return resp.json() if resp.text else {}
        except Exception:
            return {}
    except requests.exceptions.HTTPError:
        try:
            logp('error', "create_paxton_user HTTP %s: %s", resp.status_code, resp.text)
        except Exception:
            logp('exception', "create_paxton_user HTTPError but couldn't read response")
        raise
    except Exception:
        logp('exception', "create_paxton_user failed")
        raise
def update_paxton_user(token: str, user_id, payload: dict) -> dict:
    """PUT /users/{id} - update user; loggt response body bei Fehler."""
    try:
        url = f"{USER_URL}/{user_id}"
        logp('debug', "update_paxton_user url=%s payload=%s", url, json.dumps(payload, ensure_ascii=False))
        resp = requests.put(url, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
    except requests.exceptions.HTTPError:
        try:
            logp('error', "update_paxton_user HTTP %s: %s", resp.status_code, resp.text)
        except Exception:
            logp('exception', "update_paxton_user HTTPError but couldn't read response")
        raise
    except Exception:
        logp('exception', "update_paxton_user failed")
        raise
def create_or_update_paxton_user(token: str, kartennummer: str, user_data: dict) -> dict:
    """
    Create or update Paxton user.
    - stellt sicher, dass beim CREATE mindestens ein Name gesetzt wird (Fallback)
    - falls POST zurückkommt ohne ID, führt eine Suche nach kartennummer aus, um die neue ID zu finden
    """
    try:
        pid = get_paxton_user_id_by_kartennummer(kartennummer, token)

        # Build payload
        payload = {}
        first = (user_data.get("firstName") or user_data.get("givenName") or user_data.get("Vorname") or "").strip()
        last = (user_data.get("lastName") or user_data.get("sn") or user_data.get("Nachname") or "").strip()

        # Fallback name beim CREATE (Paxton verlangt mind. one name)
        if not pid and not first and not last:
            fallback = str(user_data.get("employeeNumber") or kartennummer or "Unbekannt")
            last = fallback

        if first:
            payload["firstName"] = first
        if last:
            payload["lastName"] = last
        if user_data.get("employeeNumber"):
            payload["employeeNumber"] = str(user_data.get("employeeNumber"))

        # customFields
        custom = []
        provided_custom = user_data.get("customFields") or user_data.get("CustomFields") or []
        if isinstance(provided_custom, list):
            for cf in provided_custom:
                cid = cf.get("id") or cf.get("Id")
                cval = cf.get("value") or cf.get("Value")
                if cid is not None and cval is not None:
                    try:
                        custom.append({"id": int(cid), "value": str(cval)})
                    except Exception:
                        continue

        if not any(int(cf.get("id", 0)) == 5 for cf in custom):
            custom.append({"id": 5, "value": str(kartennummer)})

        if user_data.get("department") or user_data.get("abteilung"):
            val = user_data.get("department") or user_data.get("abteilung")
            if not any(int(cf.get("id", 0)) == 1 for cf in custom):
                custom.append({"id": 1, "value": str(val)})
        if user_data.get("role") or user_data.get("funktion"):
            val = user_data.get("role") or user_data.get("funktion")
            if not any(int(cf.get("id", 0)) == 4 for cf in custom):
                custom.append({"id": 4, "value": str(val)})
        if user_data.get("employeeNumber") and not any(int(cf.get("id", 0)) == 14 for cf in custom):
            custom.append({"id": 14, "value": str(user_data.get("employeeNumber"))})

        if custom:
            payload["customFields"] = custom

        if user_data.get("accessLevels"):
            payload["accessLevels"] = user_data.get("accessLevels")

        # Debug payload
        try:
            logp('debug', "create_or_update_paxton_user sending payload: %s", json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

        # perform create or update
        if pid:
            resp = update_paxton_user(token, pid, payload)
            return {"created": False, "paxton_id": pid, "response": resp}
        else:
            resp = create_paxton_user(token, payload)
            # Try to read id from response
            new_id = None
            try:
                if isinstance(resp, dict):
                    new_id = resp.get("id") or resp.get("Id") or resp.get("userId")
            except Exception:
                new_id = None

            # If no id returned, try to find user by kartennummer (the API may not return body)
            if not new_id:
                try:
                    logp('debug', "create_or_update_paxton_user: no id in response, re-querying by kartennummer")
                    new_id = get_paxton_user_id_by_kartennummer(kartennummer, token)
                except Exception:
                    new_id = None

            return {"created": True, "paxton_id": new_id, "response": resp}
    except Exception:
        logp('exception', "create_or_update_paxton_user failed for kartennummer=%s", kartennummer)
        raise

def get_user_tokens(token: str, user_id):
    try:
        url = USER_TOKENS_URL.format(user_id)
        resp = requests.get(url, headers=_headers(token), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json() or []
    except Exception:
        logp('exception', "Error fetching tokens for user_id=%s", user_id)
        return []
def delete_paxton_user(token: str, paxton_user_id: str) -> bool:
    base = getattr(settings, "PAXTON_API_BASE", "").rstrip("/")
    if not base:
        logp('error', "PAXTON_API_BASE nicht gesetzt")
        return False
    delete_path_template = getattr(settings, "PAXTON_USER_DELETE_PATH", "/users/{id}")
    if delete_path_template.startswith("http://") or delete_path_template.startswith("https://"):
        url = delete_path_template.format(id=paxton_user_id)
    else:
        url = f"{base}{delete_path_template.format(id=paxton_user_id)}"
    headers = _headers(token, content_type=None)
    try:
        logp('info', "[delete_paxton_user] DELETE %s", url)
        resp = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
        logp('info', "delete_paxton_user response status=%s body=%s", resp.status_code, resp.text)
        return resp.status_code in (200, 202, 204)
    except Exception as e:
        logp('exception', "delete_paxton_user RequestException: %s", str(e))
        return False

def add_user_token(token, user_id, token_value):
    url = USER_TOKENS_URL.format(user_id)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        "tokenType": "Unspecified",
        "tokenValue": token_value,  # max 8 Zeichen, kein '0#'
        "isLost": False
    }
    response = requests.post(url, headers=headers, json=payload)
    return response
def create_access_level(token: str, name: str, area_ids: list = None, timezone_id: int = 1):

    token = token or get_token()
    if not token:
        raise RuntimeError("Kein Paxton-Token")

    # Wenn keine area_ids angegeben, versuche eine area aus der API zu holen
    if not area_ids:
        try:
            areas_url = f"{PAXTON_BASE}/accesslevels/areas"
            resp = requests.get(areas_url, headers=_headers(token), timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            areas = resp.json() if resp.text else []
            # areas may be list of dicts with id/areaID etc. Take first numeric id
            first_area_id = None
            if isinstance(areas, list) and areas:
                # try common keys
                for a in areas:
                    for key in ("id","areaID","AreaId","AreaID"):
                        if isinstance(a, dict) and key in a and a[key]:
                            try:
                                first_area_id = int(a[key])
                                break
                            except Exception:
                                continue
                    if first_area_id:
                        break
            if first_area_id:
                area_ids = [first_area_id]
                logger.info("create_access_level: using area_id %s (from /accesslevels/areas)", first_area_id)
        except Exception:
            logger.exception("create_access_level: konnte areas nicht holen; kein area_id gesetzt")

    payload = {"name": str(name)}
    if area_ids:
        detail_rows = []
        for aid in area_ids:
            try:
                area_int = int(aid)
            except Exception:
                continue
            detail_rows.append({"areaID": area_int, "timezoneID": int(timezone_id)})
        if detail_rows:
            payload["detailRows"] = detail_rows

    try:
        logp('debug', "create_access_level POST %s payload=%s", ACCESS_LEVELS_URL, json.dumps(payload, ensure_ascii=False))
        resp = requests.post(ACCESS_LEVELS_URL, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
        logp('info', "create_access_level response status=%s body=%s", resp.status_code, resp.text)
        resp.raise_for_status()
        try:
            return resp.json() if resp.text else {}
        except Exception:
            return {}
    except requests.exceptions.HTTPError:
        try:
            logp('error', "create_access_level HTTP %s: %s", resp.status_code, resp.text)
        except Exception:
            logp('exception', "create_access_level HTTPError but couldn't read response")
        raise
    except Exception:
        logp('exception', "create_access_level failed for name=%s", name)
        raise









def get_access_level_by_id(level_id, token=None):
    """Hole ein einzelnes accesslevel (falls API /accesslevels/{id} unterstützt). Fallback: suche in fetch_all_access_levels."""
    token = token or get_token()
    if not token:
        return None
    try:
        url = f"{ACCESS_LEVELS_URL}/{level_id}"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        # fallback to full list if single endpoint not available
    except Exception:
        pass
    # Fallback: suche in gesamter Liste
    levels = fetch_all_access_levels(token)
    for l in levels:
        if l.get("id") == level_id or str(l.get("id")) == str(level_id):
            return l
    return None


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
        resp = requests.put(url, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
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


def get_access_levels_dict_from_fetch():
    levels = fetch_all_access_levels()
    return {str(d["id"]): d["name"] for d in levels if "id" in d and "name" in d}



def get_paxton_users(token=None):
    token = token or get_token()
    if not token:
        print("Kein Token; Benutzerabruf abgebrochen.")
        return []

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    try:
        resp = requests.get(USER_URL, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("users", "data", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return []
    except requests.exceptions.RequestException as e:
        print(f"Benutzerabruf fehlgeschlagen: {e}")
        return []
    except ValueError as e:
        print(f"Fehler beim Parsen der Benutzer-Response: {e}")
        return []





def fetch_all_access_levels(token=None):
    token = token or get_token()
    if not token:
        return []
    try:
        resp = requests.get(ACCESS_LEVELS_URL, headers=_headers(token), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [{"id": d.get("id") or d.get("Id"), "name": d.get("name") or d.get("Name", "")} for d in data]
        if isinstance(data, dict):
            for key in ("accessLevels", "data", "items"):
                if key in data and isinstance(data[key], list):
                    return [{"id": d.get("id") or d.get("Id"), "name": d.get("name") or d.get("Name", "")} for d in data[key]]
        return []
    except Exception:
        logger.exception("fetch_all_access_levels failed")
        return []


def get_departments_dict(token=None):
    token = token or get_token()
    if not token:
        logp('warning', "get_departments_dict: no token")
        return {}

    try:
        resp = requests.get(DEPARTMENTS_URL, headers=_headers(token), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        arr = data if isinstance(data, list) else (data.get("departments") or data.get("data") or data.get("items") or [])
        return {str(d.get("id") or d.get("Id")): d.get("name") or d.get("Name", "") for d in arr}
    except Exception:
        logp('exception', "get_departments_dict failed")
        return {}



def get_paxton_user_id_by_kartennummer(kartennummer, token=None):
    """Sucht Paxton User nach Kartennummer (customField id=5 oder Fallbacks)."""
    token = token or get_token()
    if not token:
        return None
    try:
        users = get_paxton_users(token)
        km = str(kartennummer).strip()
        for u in users:
            cfs = u.get("customFields") or u.get("CustomFields") or []
            for f in cfs:
                fid = f.get("id") or f.get("Id")
                fval = f.get("value") or f.get("Value") or ""
                try:
                    if fid is not None and int(fid) == 5 and str(fval).strip() == km:
                        return u.get("id") or u.get("Id")
                except Exception:
                    continue
        # fallback: any custom field match
        for u in users:
            cfs = u.get("customFields") or u.get("CustomFields") or []
            for f in cfs:
                fval = f.get("value") or f.get("Value") or ""
                if fval and str(fval).strip() == km:
                    return u.get("id") or u.get("Id")
        # fallback2: top-level employeeNumber
        for u in users:
            en = u.get("employeeNumber") or u.get("EmployeeNumber") or ""
            if en and str(en).strip() == km:
                return u.get("id") or u.get("Id")
    except Exception:
        logp('exception', "get_paxton_user_id_by_kartennummer failed")
    return None










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

logger = logging.getLogger('paxton')








def save_to_db(kartennummer, benutzergruppe, berechtigungsgruppe):

    if not kartennummer or str(kartennummer).strip() == "":
        raise ValueError("kartennummer required")

    # defensive mapping lookup
    try:
        departments = get_departments_dict() or {}
        name_to_departments_id = { (name or "").strip().lower(): id for id, name in departments.items() if name }
    except Exception:
        name_to_departments_id = {}

    try:
        levels = fetch_all_access_levels() or []
        name_to_level_id = { ((l.get("name") or "").strip().lower()): str(l.get("id")) for l in levels if l and (l.get("id") or l.get("Id")) }
    except Exception:
        name_to_level_id = {}

    def resolve_bg(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        if s.isdigit():
            return int(s)
        return int(name_to_departments_id[s.lower()]) if s.lower() in name_to_departments_id else s

    def resolve_ag(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        parts = [p.strip() for p in s.split(",") if p.strip()]
        ids = []
        names = []
        for p in parts:
            if p.isdigit():
                ids.append(int(p))
            else:
                pid = name_to_level_id.get(p.lower())
                if pid:
                    ids.append(int(pid))
                else:
                    names.append(p)
        if ids and not names:
            return ids[0] if len(ids) == 1 else ",".join(str(x) for x in ids)
        if ids and names:
            return ",".join(str(x) for x in ids) + ("," + ",".join(names) if names else "")
        return ",".join(names) if names else None

    bg_val = resolve_bg(benutzergruppe)
    ag_val = resolve_ag(berechtigungsgruppe)
    logger.info("save_to_db: resolved benutzergruppe=%r berechtigungsgruppe=%r", bg_val, ag_val)

    rc_student = rc_gast = 0
    try:
        with transaction.atomic():
            with connection.cursor() as c:
                if bg_val is not None or ag_val is not None:
                    set_parts = []
                    params = []
                    if bg_val is not None:
                        set_parts.append("benutzergruppe = %s"); params.append(bg_val)
                    if ag_val is not None:
                        set_parts.append("berechtigungsgruppe = %s"); params.append(ag_val)
                    set_sql = ", ".join(set_parts)
                    # t_studenten
                    c.execute(f"UPDATE [HCM_Daten].[dbo].[t_studenten] SET {set_sql} WHERE kartennummer = %s", tuple(params) + (kartennummer,))
                    rc_student = c.rowcount
                    # t_Gast
                    c.execute(f"UPDATE [HCM_Daten].[dbo].[t_Gast] SET {set_sql} WHERE kartennummer = %s", tuple(params) + (kartennummer,))
                    rc_gast = c.rowcount
    except Exception:
        logger.exception("Fehler in save_to_db for kartennummer=%s", kartennummer)
        raise

    return {"benutzergruppe": bg_val, "berechtigungsgruppe": ag_val,
            "rows": {"t_studenten": rc_student, "t_Gast": rc_gast}}
def save_to_paxton(card_number, department_input, access_group_input, token):

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
