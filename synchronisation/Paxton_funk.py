import requests
from django.conf import settings
import json
import logging
from django.db import connection, transaction, DatabaseError
import os
import re
import time
from collections import defaultdict
from Tabelle.models import TGast, TStudenten, PaxtonViewWeb

#Der Paxton-Server unterstützt nur TLS 1.2, 
#aber Python 3.14 versucht standardmäßig TLS 1.3 — das passt nicht zusammen
import ssl
import urllib3
from requests.adapters import HTTPAdapter
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TLS12Adapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

# Globale Session mit TLS12 Adapter
_session = requests.Session()
_session.mount('https://', TLS12Adapter())
_session.verify = False


logger = logging.getLogger("paxton")

#Meiste API-Funktionen für Paxton.



# Konfiguration 
PAXTON_BASE = getattr(settings, "PAXTON_API_BASE", "https://sr00041895.medi.local:8443/api/v1").rstrip("/")
REQUEST_TIMEOUT = getattr(settings, "PAXTON_REQUEST_TIMEOUT", 15)

TOKEN_URL = f"{PAXTON_BASE}/authorization/tokens"
USER_URL = f"{PAXTON_BASE}/users"
USER_TOKENS_URL = f"{PAXTON_BASE}/users/{{}}/tokens"
DEPARTMENT_URL = f"{PAXTON_BASE}/users/{{userId}}/departments"
ACCESS_LEVELS_URL = f"{PAXTON_BASE}/accesslevels"
DEPARTMENTS_URL = f"{PAXTON_BASE}/departments"
ACCESS_LEVELS_User = f"{PAXTON_BASE}/users/{{userId}}/accesslevels"

USERNAME = getattr(settings, "PAXTON_USERNAME", "OEM Client")
PASSWORD = getattr(settings, "PAXTON_PASSWORD", "GodotekAzikabu")
GRANT_TYPE = getattr(settings, "PAXTON_GRANT_TYPE", "password")
CLIENT_ID = getattr(settings, "PAXTON_CLIENT_ID", "18a5f964-f120-4fe0-a31a-6ccd3995cb13")



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


def _headers(token=None, content_type="application/json"):
    h = {"Accept": "application/json"}
    if content_type:
        h["Content-Type"] = content_type
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

_token_cache = {"token": None, "expires_at": 0}
def get_token():
    """Hole Access-Token (POST /authorization/tokens)."""
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    try:
        data = {
            "grant_type": GRANT_TYPE,
            "username": USERNAME,
            "password": PASSWORD,
            "client_id": CLIENT_ID,
        }
        resp = _session.post(TOKEN_URL, data=data, timeout=REQUEST_TIMEOUT, verify=False)
        resp.raise_for_status()
        d = resp.json()
        token = d.get("access_token") or d.get("accessToken") or d.get("token")
        if token:
            _token_cache["token"] = token
            _token_cache["expires_at"] = time.time() + 600  # 10 Minuten
        logger.debug("get_token: status=%s token_present=%s", getattr(resp, "status_code", None), bool(token))
        return token
    except requests.exceptions.RequestException as e:
        logger.exception("get_token failed: %s", e)
        return None



def get_paxton_users(token=None):
    token = token or get_token()
    if not token:
        print("Kein Token; Benutzerabruf abgebrochen.")
        return []

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    try:
        resp = _session.get(USER_URL, headers=headers)
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





def create_paxton_user(token: str, payload: dict) -> dict:
    """POST /users - create user; loggt status & body bei Erfolg und Fehler."""
    try:
        logp('debug', "create_paxton_user payload=%s", json.dumps(payload, ensure_ascii=False))
        resp = _session.post(USER_URL, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
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



def get_user_departments(token, user_id):


    url = DEPARTMENT_URL.format(userId=user_id)
    resp = _session.get(url, headers=_headers(token), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    # data kann list oder dict sein (je nach API)
    if isinstance(data, list):
        arr = data
    elif isinstance(data, dict):
        arr = data.get("departments") or data.get("data") or data.get("items") or []
    else:
        arr = []

    result: dict[int, str] = {}
    for d in arr:
        if not isinstance(d, dict):
            continue
        _id = d.get("id") or d.get("Id")
        name = d.get("name") or d.get("Name") or d.get("description") or d.get("Description")
        if _id is None or name is None:
            continue
        try:
            result[int(_id)] = str(name)
        except Exception:
            continue
    return result



def get_departments_dict(token=None):

    token = token or get_token()
    if not token:
        logger.warning("get_departments_dict: kein Token verfügbar")
        return {}
    try:
        resp = _session.get(DEPARTMENTS_URL, headers=_headers(token), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            arr = data
        elif isinstance(data, dict):
            arr = data.get("departments") or data.get("data") or data.get("items") or []
        else:
            arr = []
        result = {}
        for d in arr:
            if not isinstance(d, dict):
                continue
            _id = d.get("id") or d.get("Id")
            name = d.get("name") or d.get("Name") or d.get("description") or d.get("Description")
            if _id is not None and name is not None:
                try:
                    result[str(int(_id))] = str(name)
                except Exception:
                    continue
        logger.debug("get_departments_dict: %d Einträge geladen", len(result))
        return result
    except Exception:
        logger.exception("get_departments_dict fehlgeschlagen")
        return {}



def get_user_accesslevels(token, user_id):

    url = ACCESS_LEVELS_User.format(userId=user_id)
    resp = _session.get(url, headers=_headers(token), timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    # API kann list oder dict liefern -> robust parsen
    if isinstance(data, list):
        arr = data
    elif isinstance(data, dict):
        arr = data.get("accessLevels") or data.get("data") or data.get("items") or []
    else:
        arr = []

    result: dict[int, str] = {}
    for a in arr:
        if not isinstance(a, dict):
            continue
        _id = a.get("id") or a.get("Id")
        name = a.get("name") or a.get("Name") or a.get("description") or a.get("Description")
        if _id is None or name is None:
            continue
        try:
            result[int(_id)] = str(name)
        except Exception:
            continue
    return result



def get_access_level_by_id(level_id, token=None):
    """Hole ein einzelnes accesslevel (falls API /accesslevels/{id} unterstützt). Fallback: suche in fetch_all_access_levels."""
    token = token or get_token()
    if not token:
        return None
    try:
        url = f"{ACCESS_LEVELS_URL}/{level_id}"
        resp = _session.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT)
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
        resp = _session.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
        logp('info', "delete_paxton_user response status=%s body=%s", resp.status_code, resp.text)
        return resp.status_code in (200, 202, 204)
    except Exception as e:
        logp('exception', "delete_paxton_user RequestException: %s", str(e))
        return False


#create User oder nach Status enderung
def create_or_update_paxton_user(token: str, kartennummer: str, user_data: dict) -> dict:

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


        
def update_paxton_user(token, user_id, payload):
    """PUT /users/{id} - update user; loggt response body bei Fehler."""
    try:
        url = f"{USER_URL}/{user_id}"
        logp('debug', "update_paxton_user url=%s payload=%s", url, json.dumps(payload, ensure_ascii=False))
        resp = _session.put(url, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
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



def create_or_update_department(user_id, token, department_id, department_name):
    try:
        url = DEPARTMENT_URL.format(userId=user_id)
        data = {"Name": department_name or "", "Id": int(department_id)}
        resp = _session.put(url, headers=_headers(token), json=data, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        logp('info', "create_or_update_department: user=%s dept=%s name=%s", user_id, department_id, department_name)
        return resp.json() if resp.text else {}
    except Exception:
        logp('exception', "Fehler beim Anlegen/Aktualisieren Department user=%s", user_id)
        raise

#DIe name des BerechtigungsID
def fetch_all_access_levels(token=None):
    token = token or get_token()
    if not token:
        return []
    try:
        resp = _session.get(ACCESS_LEVELS_URL, headers=_headers(token), timeout=REQUEST_TIMEOUT)
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



def create_access_level(token: str, name: str, area_ids: list = None, timezone_id: int = 1):

    token = token or get_token()
    if not token:
        raise RuntimeError("Kein Paxton-Token")

    # Wenn keine area_ids angegeben, versuche eine area aus der API zu holen
    if not area_ids:
        try:
            areas_url = f"{PAXTON_BASE}/accesslevels/areas"
            resp = _session.get(areas_url, headers=_headers(token), timeout=REQUEST_TIMEOUT)
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
        resp = _session.post(ACCESS_LEVELS_URL, headers=_headers(token), json=payload, timeout=REQUEST_TIMEOUT)
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

def _normalize_db_tokens(token_value):
    if token_value is None:
        return []
    if isinstance(token_value, (list, tuple)):
        toks = [str(x).strip() for x in token_value if x is not None and str(x).strip() != ""]
    else:
        s = str(token_value).strip()
        toks = [] if s == "" else [s]
    return sorted(set([t.lstrip("0#") for t in toks if t])) 
def get_user_tokens(token: str, user_id):
    try:
        url = USER_TOKENS_URL.format(user_id)
        resp = _session.get(url, headers=_headers(token), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json() or []
    except Exception:
        logp('exception', "Error fetching tokens for user_id=%s", user_id)
        return []

def add_user_token(token, user_id, token_value):
    url = USER_TOKENS_URL.format(user_id)
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        "tokenType": "Unspecified",
        "tokenValue": token_value,  # max 8 Zeichen, kein '0#'
        "isLost": False
    }
    response = _session.post(url, headers=headers, json=payload)
    return response       

def delete_token_from_paxton(token: str, user_id, token_id) -> None:
    """
    Löscht ein Token eines Users in Paxton.
    Wirft Exception bei HTTP-Fehlern.
    """
    delete_url = f"{USER_TOKENS_URL.format(user_id)}/{token_id}"
    resp = _session.delete(delete_url, headers=_headers(token), timeout=REQUEST_TIMEOUT)

    if resp.status_code == 204:
        logger.info("Paxton: Token %s für Benutzer %s gelöscht.", token_id, user_id)
        return

    # raise with details
    try:
        body = resp.json()
    except Exception:
        body = resp.text

    raise requests.HTTPError(
        f"Delete token failed: status={resp.status_code} user_id={user_id} token_id={token_id} body={body}",
        response=resp,
    )





