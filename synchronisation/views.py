from django.shortcuts import render
import concurrent.futures
import datetime
import logging
import sys
import re
from collections import defaultdict
import requests
from django.conf import settings
from Tabelle.models import TGast, TStudenten, PaxtonViewWeb

from synchronisation.Paxton_funk import _headers, logp, get_token, get_paxton_users, get_paxton_user_id_by_kartennummer, get_user_departments, get_user_accesslevels, get_access_level_by_id, delete_paxton_user, create_or_update_paxton_user, update_paxton_user, create_or_update_department, fetch_all_access_levels, create_access_level, _normalize_db_tokens, get_user_tokens, add_user_token, delete_token_from_paxton
from Tabelle.Paxton_all import save_to_paxton_Access_and_Depart, save_to_db

#Funktionen für die API-Synchronisation.


logger = logging.getLogger('paxton')

SKIP_BENUTZERGRUPPEN = {"259", "208", "209", "74", "144", "190"} 

def sync_db_to_paxton(token):

    if not token:
        raise RuntimeError("Kein Paxton-Token")

    stats = defaultdict(int)

    # 1) DB-Daten (Quelle)
    db_data = {}

    def _put_db_row(row, quelle):
        km = str(getattr(row, "kartennummer", "") or "").strip()
        if not km:
            return

        # du sagst: DB active ist 0/1 (bei dir manchmal bool)
        active_val = getattr(row, "active", None)
        if active_val is None:
            active_val = getattr(row, "karte_active", None)

        active = 1 if str(active_val).lower() in ("1", "true", "t", "yes") else 0

        db_data[km] = {
            "quelle": quelle,
            "kartennummer": km,
            "active": active,
            "department_id": getattr(row, "benutzergruppe", None),       # ID
            "access_group": getattr(row, "berechtigungsgruppe", None),   # kann ID oder "1,2"
            "givenname": getattr(row, "givenname", "") or "",
            "sn": getattr(row, "sn", "") or "",
            "employeenumber": getattr(row, "employeenumber", "") or "",
            "token_value": getattr(row, "token_value", None) if hasattr(row, "token_value") else None,
        }

    for r in PaxtonViewWeb.objects.all():
        _put_db_row(r, "Mitarbeiter")

    for r in TGast.objects.all():
        km = str(getattr(r, "kartennummer", "") or "").strip()
        if km and km not in db_data:
            _put_db_row(r, "Gast")

    for r in TStudenten.objects.all():
        km = str(getattr(r, "kartennummer", "") or "").strip()
        if km and km not in db_data:
            _put_db_row(r, "Student")


    # 2) Paxton Users holen + Map kartennummer -> user

    paxton_users = get_paxton_users(token) or []
    paxton_by_km = {}

    def _extract_km_from_paxton_user(u):
        cfs = u.get("customFields") or u.get("CustomFields") or []
        for f in cfs:
            fid = f.get("id") or f.get("Id")
            try:
                if fid is not None and int(fid) == 5:
                    v = f.get("value") or f.get("Value")
                    if v is not None and str(v).strip() != "":
                        return str(v).strip()
            except Exception:
                continue
        en = u.get("employeeNumber") or u.get("EmployeeNumber")
        if en is not None and str(en).strip() != "":
            return str(en).strip()
        return None

    for u in paxton_users:
        km = _extract_km_from_paxton_user(u)
        if km:
            paxton_by_km[km] = u

    # 3) helpers: normalize ids
    def _normalize_department_id(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        return int(s) if s.isdigit() else None

    def _normalize_access_ids(v):
        if v is None:
            return []
        s = str(v).strip()
        if s == "":
            return []
        parts = [p.strip() for p in re.split(r"[,\;\|\n]+", s) if p.strip()]
        ids = []
        for p in parts:
            if p.isdigit():
                ids.append(int(p))
        return sorted(set(ids))

    # 4) Sync pro kartennummer

    for km, db in db_data.items():
        stats["db_seen"] += 1

        dep_id_str = str(db.get("department_id") or "").strip()
        if dep_id_str in SKIP_BENUTZERGRUPPEN:
            stats["skipped"] += 1
            continue

        db_active = int(db.get("active") or 0)
        db_dep_id = _normalize_department_id(db.get("department_id"))
        db_access_ids = _normalize_access_ids(db.get("access_group"))
        db_tokens = _normalize_db_tokens(db.get("token_value"))

        px_user = paxton_by_km.get(km)
        px_user_id = (px_user.get("id") or px_user.get("Id")) if px_user else None

        # A) DB inaktiv -> löschen in Paxton
        if db_active == 0:
            if px_user_id:
                ok = delete_paxton_user(token, str(px_user_id))
                stats["deleted_inactive"] += 1 if ok else 0
                stats["delete_inactive_failed"] += 0 if ok else 1
            else:
                stats["inactive_missing"] += 1
            continue

        # B) DB aktiv -> erstellen, falls fehlt
        if not px_user_id:
            user_data = {
                "firstName": db.get("givenname") or "",
                "lastName": db.get("sn") or "",
                "employeeNumber": db.get("employeenumber") or km,
            }
            res = create_or_update_paxton_user(token, km, user_data)
            px_user_id = res.get("paxton_id")
            if not px_user_id:
                stats["create_failed"] += 1
                continue
            stats["created"] += 1

            # nach create: dept/access setzen (keine compare nötig, ist neu)
            save_to_paxton_Access_and_Depart(km, db_dep_id, ",".join(str(x) for x in db_access_ids), token)
            stats["dept_access_set_after_create"] += 1

        # C) existiert -> compare department/access in Paxton vs DB
        try:
            px_deps_dict = get_user_departments(token, px_user_id)  # dict[id]=name
            px_dep_ids = sorted(px_deps_dict.keys())
        except Exception:
            logger.exception("Failed reading departments for user=%s", px_user_id)
            px_dep_ids = []

        try:
            px_access_dict = get_user_accesslevels(token, px_user_id)  # dict[id]=name
            px_access_ids = sorted(px_access_dict.keys())
        except Exception:
            logger.exception("Failed reading accesslevels for user=%s", px_user_id)
            px_access_ids = []

        want_dep_ids = [] if db_dep_id is None else [db_dep_id]
        dep_diff = (px_dep_ids != want_dep_ids)
        access_diff = (px_access_ids != db_access_ids)

        if dep_diff or access_diff:
            save_to_paxton_Access_and_Depart(km, db_dep_id, ",".join(str(x) for x in db_access_ids), token)
            stats["dept_access_updated"] += 1
        else:
            stats["dept_access_ok"] += 1

        # D) Tokens compare/sync
        try:
            px_tokens = get_user_tokens(token, px_user_id) or []
        except Exception:
            logger.exception("Failed reading tokens for user=%s", px_user_id)
            px_tokens = []

        px_token_map = {}
        for t in px_tokens:
            v = t.get("token_value") or t.get("tokenValue")
            if v is not None:
                px_token_map[str(v)] = t

        px_token_values = sorted(set(px_token_map.keys()))
        token_diff = (px_token_values != db_tokens)

        if token_diff:
            # delete tokens that should not exist
            for val, tok_obj in px_token_map.items():
                if val not in db_tokens:
                    tid = tok_obj.get("id") or tok_obj.get("Id")
                    if tid is not None:
                        delete_token_from_paxton(token, px_user_id, tid)
                        stats["token_deleted"] += 1

            # add missing tokens
            for val in db_tokens:
                if val not in px_token_map:
                    add_user_token(token, px_user_id, val)
                    stats["token_added"] += 1
        else:
            stats["tokens_ok"] += 1

        # E) DB schreiben (nur IDs)
        # Department-ID und AccessIDs in DB speichern
        save_to_db(km, db_dep_id, ",".join(str(x) for x in db_access_ids))
        stats["db_written"] += 1

    logp("info", "sync_db_to_paxton fertig: %s", dict(stats))
    return dict(stats)
