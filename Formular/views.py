from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render, redirect
from django.db import connection, transaction, DatabaseError
from django.contrib import messages
from django.http import HttpResponseNotFound, JsonResponse
import re
import logging
from django.urls import reverse

from Tabelle.models import PaxtonViewWeb, TGast, TStudenten
from Tabelle.utils import get_benutzer_liste, get_user_status
from Tabelle.Paxton_all import (
    get_token, get_user_tokens, get_departments_dict,
    get_access_levels_dict_from_fetch, fetch_all_access_levels,
    get_paxton_user_id_by_kartennummer, delete_paxton_user,
    create_or_update_paxton_user, add_user_token, create_or_update_department,
    create_paxton_user, create_access_level, update_paxton_user,
    save_to_paxton, save_to_db
)

logger = logging.getLogger('paxton')

def _normalize_token_value(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.startswith("0#"):
        s = s[2:]
    s = s.strip()
    return s[-8:] if len(s) >= 1 else None

@require_POST
def restore_card(request):
    """
    Restore a card: set active = 1 (and reset verlorene_karte if column exists)
    in all relevant tables and update/create the Paxton user.
    Reads values from request.POST and logs actions.
    """
    kartennummer = (request.POST.get('kartennummer') or "").strip()
    mifare = (request.POST.get('mifareid_paxton') or "").strip()
    employeeNumber = (request.POST.get('employeenumber') or request.POST.get('employeeNumber') or "").strip()

    givenname = (request.POST.get('givenname') or "").strip()
    sn = (request.POST.get('sn') or "").strip()
    abteilung = (request.POST.get('abteilung') or "").strip()
    funktion = (request.POST.get('funktion') or "").strip()
    einrichtung = (request.POST.get('einrichtung') or "").strip()
    benutzergruppe_id = (request.POST.get('benutzergruppe') or "").strip()
    access_levels_raw = (request.POST.get('berechtigungsgruppe') or "").strip()

    action_user = request.user.username if getattr(request.user, "is_authenticated", False) else 'anonymous'
    client_ip = request.META.get('REMOTE_ADDR', '')
    log_extra = {'username': action_user, 'clientip': client_ip}

    logger.info(
        "restore_card called: kartennummer=%r employeeNumber=%r mifare=%r by=%s",
        kartennummer, employeeNumber, mifare, action_user,
        extra=log_extra
    )

    if not kartennummer:
        messages.error(request, "Kartennummer fehlt.")
        return redirect(reverse('formular'))

    # initialize counters so they exist even if early exception occurs
    rc1 = rc2 = rc3 = rc4 = 0

    try:
        mk_has_verl = column_exists('dbo', 'mitarbeiterKarte', 'verlorene_karte')
        hcm_has_verl = column_exists('dbo', 'HCM_mitarbeiter', 'verlorene_karte')
        stu_has_verl = column_exists('dbo', 't_studenten', 'verlorene_karte')
        gast_has_verl = column_exists('dbo', 't_Gast', 'verlorene_karte')

        with transaction.atomic():
            with connection.cursor() as c:
                if mk_has_verl:
                    if mifare:
                        c.execute(
                            """
                            UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte]
                            SET active = 1, verlorene_karte = 0
                            WHERE kartennummer = %s
                              AND (mifareid_paxton = %s OR COALESCE(NULLIF(mifareid_paxton, ''), '') = %s)
                            """, (kartennummer, mifare, mifare)
                        )
                    else:
                        c.execute(
                            "UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte] SET active = 1, verlorene_karte = 0 WHERE kartennummer = %s",
                            (kartennummer,)
                        )
                else:
                    if mifare:
                        c.execute(
                            "UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte] SET active = 1 WHERE kartennummer = %s AND (mifareid_paxton = %s OR COALESCE(NULLIF(mifareid_paxton, ''), '') = %s)",
                            (kartennummer, mifare, mifare)
                        )
                    else:
                        c.execute("UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte] SET active = 1 WHERE kartennummer = %s", (kartennummer,))
                rc1 = c.rowcount
                logger.info("mitarbeiterKarte UPDATE rowcount=%s (mk_has_verl=%s)", rc1, mk_has_verl, extra=log_extra)

                params = [kartennummer]
                where_clause = "kartennummer = %s"
                if mifare:
                    where_clause += " AND (mifareid_paxton = %s OR COALESCE(NULLIF(mifareid_paxton, ''), '') = %s)"
                    params.extend([mifare, mifare])
                if employeeNumber:
                    where_clause += " AND employeeNumber = %s"
                    params.append(employeeNumber)
                if hcm_has_verl:
                    sql_hcm = f"UPDATE [HCM_Daten].[dbo].[HCM_mitarbeiter] SET active = 1, verlorene_karte = 0 WHERE id IN (SELECT mitarbeiter_id FROM [HCM_Daten].[dbo].[mitarbeiterKarte] WHERE {where_clause})"
                else:
                    sql_hcm = f"UPDATE [HCM_Daten].[dbo].[HCM_mitarbeiter] SET active = 1 WHERE id IN (SELECT mitarbeiter_id FROM [HCM_Daten].[dbo].[mitarbeiterKarte] WHERE {where_clause})"
                c.execute(sql_hcm, params)
                rc2 = c.rowcount
                logger.info("HCM_mitarbeiter UPDATE rowcount=%s (hcm_has_verl=%s)", rc2, hcm_has_verl, extra=log_extra)

                if stu_has_verl:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_studenten] SET active = 1, verlorene_karte = 0 WHERE kartennummer = %s", (kartennummer,))
                else:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_studenten] SET active = 1 WHERE kartennummer = %s", (kartennummer,))
                rc3 = c.rowcount
                logger.info("t_studenten UPDATE rowcount=%s (stu_has_verl=%s)", rc3, stu_has_verl, extra=log_extra)

                if gast_has_verl:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_Gast] SET active = 1, verlorene_karte = 0 WHERE kartennummer = %s", (kartennummer,))
                else:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_Gast] SET active = 1 WHERE kartennummer = %s", (kartennummer,))
                rc4 = c.rowcount
                logger.info("t_Gast UPDATE rowcount=%s (gast_has_verl=%s)", rc4, gast_has_verl, extra=log_extra)

        token = get_token()
        if token:
            user_payload = {
                "firstName": givenname or "",
                "lastName": sn or "",
                "employeeNumber": employeeNumber or "",
                "customFields": [
                    {"id": 5, "value": str(kartennummer)},
                    {"id": 14, "value": str(employeeNumber or "")},
                ]
            }
            if abteilung:
                user_payload["customFields"].append({"id": 1, "value": str(abteilung)})
            if funktion:
                user_payload["customFields"].append({"id": 4, "value": str(funktion)})
            if einrichtung:
                user_payload["customFields"].append({"id": 3, "value": str(einrichtung)})

            try:
                access_levels = []
                if access_levels_raw:
                    candidates = re.split(r'[,\;\|\s]+', access_levels_raw)
                    all_levels = fetch_all_access_levels(token) or []
                    name_to_id = { (l.get("name") or "").strip().lower(): str(l.get("id")) for l in all_levels if l and (l.get("id") or l.get("Id")) }
                    for p in candidates:
                        p = p.strip()
                        if not p:
                            continue
                        if p.isdigit():
                            access_levels.append(int(p))
                        else:
                            pid = name_to_id.get(p.lower())
                            if pid:
                                access_levels.append(int(pid))
                if access_levels:
                    user_payload["accessLevels"] = access_levels
            except Exception:
                logger.exception("Error resolving access levels", extra=log_extra)

            try:
                res = create_or_update_paxton_user(token, kartennummer, user_payload)
                paxton_id = res.get("paxton_id")
                logger.info("Paxton create_or_update result=%s", res, extra=log_extra)
            except Exception as e:
                logger.exception("Error in create_or_update_paxton_user", extra=log_extra)
                messages.warning(request, f"DB wiederhergestellt, aber Fehler beim Paxton-Update: {e}")
                return redirect(f"{reverse('formular')}?selected={kartennummer}")

            if paxton_id and mifare:
                try:
                    tokval = _normalize_token_value(mifare)
                    if tokval:
                        existing = get_user_tokens(token, paxton_id) or []
                        existing_vals = set()
                        for tkn in existing:
                            v = tkn.get("tokenValue") or tkn.get("token_value") or tkn.get("token") or ""
                            if v:
                                vv = str(v)
                                if vv.startswith("0#"):
                                    vv = vv[2:]
                                existing_vals.add(vv[-8:])
                        if tokval not in existing_vals:
                            r = add_user_token(token, paxton_id, tokval)
                            logger.info("add_user_token resp=%s text=%s", getattr(r, "status_code", None), getattr(r, "text", None), extra=log_extra)
                        else:
                            logger.info("Token %s already exists for paxton_id=%s", tokval, paxton_id, extra=log_extra)
                except Exception:
                    logger.exception("Error adding user token", extra=log_extra)

            if paxton_id and benutzergruppe_id:
                try:
                    department_map = get_departments_dict(token) or {}
                    department_name = None
                    department_id_for_api = None

                    if str(benutzergruppe_id).isdigit():
                        department_id_for_api = int(benutzergruppe_id)
                        department_name = department_map.get(str(department_id_for_api))
                    else:
                        for k, v in department_map.items():
                            if v and v.strip().lower() == str(benutzergruppe_id).strip().lower():
                                try:
                                    department_id_for_api = int(k)
                                except Exception:
                                    department_id_for_api = None
                                department_name = v
                                break

                    dept_id_to_pass = department_id_for_api if department_id_for_api is not None else 0
                    create_or_update_department(paxton_id, token, dept_id_to_pass, department_name or str(benutzergruppe_id))
                    logger.info("Department set for paxton_id=%s id=%s name=%s", paxton_id, dept_id_to_pass, department_name or benutzergruppe_id, extra=log_extra)
                except Exception:
                    logger.exception("Error setting department", extra=log_extra)

            messages.success(request, f"Karte {kartennummer} wiederhergestellt und Paxton aktualisiert.")
        else:
            messages.success(request, f"Karte {kartennummer} wiederhergestellt (kein Paxton-Token).")
            logger.warning("No Paxton token for restore_card", extra=log_extra)

        total_changed = sum(x or 0 for x in (rc1, rc2, rc3, rc4))
        logger.info("restore_card finished total_changed=%s", total_changed, extra=log_extra)

    except DatabaseError as e:
        logger.exception("DB error restoring card %s: %s", kartennummer, e, extra=log_extra)
        messages.error(request, f"Datenbank-Fehler: {e}")
    except Exception as e:
        logger.exception("Unexpected error restoring card %s: %s", kartennummer, e, extra=log_extra)
        messages.error(request, f"Interner Fehler: {e}")

    return redirect(f"{reverse('formular')}?selected={kartennummer}")

@require_POST
def save_data(request):
    logger.debug("save_data: POST keys=%s", list(request.POST.keys()))
    kartennummer = (request.POST.get('kartennummer') or "").strip()

    try:
        kartennummer = (request.POST.get('kartennummer') or "").strip()
        if not kartennummer:
            messages.error(request, "Kartennummer ist erforderlich.")
            return redirect(f"{reverse('formular')}?selected=")

        mifareid_paxton = (request.POST.get('mifareid_paxton') or "").strip()
        employeeNumber = (request.POST.get('employeeNumber') or request.POST.get('employeenumber') or "").strip()

        benutzergruppe_value = (request.POST.get('benutzergruppe') or request.POST.get('benutzergruppe_name') or "").strip()
        berechtigungsgruppe_value = (request.POST.get('berechtigungsgruppe') or request.POST.get('berechtigungsgruppe_name') or "").strip()

        benutzergruppe = None
        berechtigungsgruppe = None
        if benutzergruppe_value:
            benutzergruppe = int(benutzergruppe_value) if str(benutzergruppe_value).isdigit() else benutzergruppe_value
        if berechtigungsgruppe_value:
            berechtigungsgruppe = int(berechtigungsgruppe_value) if str(berechtigungsgruppe_value).isdigit() else berechtigungsgruppe_value

        db_result = save_to_db(kartennummer, benutzergruppe, berechtigungsgruppe)

        token = get_token()
        if not token:
            messages.warning(request, "Daten in DB gespeichert, aber kein Paxton-Token vorhanden.")
            return redirect(f"{reverse('formular')}?selected={kartennummer}")

        save_to_paxton(kartennummer, db_result["benutzergruppe"], db_result["berechtigungsgruppe"], token)

        messages.success(request, "Daten erfolgreich in der Datenbank und Paxton gespeichert.")
        return redirect(f"{reverse('formular')}?selected={kartennummer}")

    except Exception as e:
        logger.exception("Fehler beim Speichern der Daten: %s", e)
        messages.error(request, f"Fehler beim Speichern: {e}")
        return redirect(f"{reverse('formular')}?selected={request.POST.get('kartennummer','')}")

@require_POST
def deaktiv_card(request):
    kartennummer = (request.POST.get('kartennummer') or "").strip()
    mifare = (request.POST.get('mifareid_paxton') or "").strip()
    emp = (request.POST.get('employeeNumber') or "").strip()
    user = request.user.username if getattr(request.user, "is_authenticated", False) else 'unknown'

    if not kartennummer:
        messages.error(request, "Kartennummer fehlt.")
        return redirect('formular')

    try:
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute(
                    "UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte] "
                    "SET active = 0 "
                    "WHERE kartennummer = %s AND (mifareid_paxton = %s OR (mifareid_paxton IS NULL AND %s = ''))",
                    (kartennummer, mifare, mifare)
                )
                params = [kartennummer, mifare, mifare]
                where = "kartennummer = %s AND (mifareid_paxton = %s OR (mifareid_paxton IS NULL AND %s = ''))"
                if emp:
                    where += " AND employeeNumber = %s"
                    params.append(emp)
                c.execute(
                    f"UPDATE [HCM_Daten].[dbo].[HCM_mitarbeiter] SET active = 0 "
                    f"WHERE id IN (SELECT mitarbeiter_id FROM [HCM_Daten].[dbo].[mitarbeiterKarte] WHERE {where})",
                    params
                )
                c.execute("UPDATE [HCM_Daten].[dbo].[t_studenten] SET active = 0 WHERE kartennummer = %s", (kartennummer,))
                c.execute("UPDATE [HCM_Daten].[dbo].[t_Gast] SET active = 0 WHERE kartennummer = %s", (kartennummer,))
        try:
            token = get_token()
            if token:
                pid = get_paxton_user_id_by_kartennummer(kartennummer, token)
                if pid:
                    delete_paxton_user(token, pid)
                    messages.success(request, f"Karte {kartennummer} deaktiviert und Paxton-User entfernt.")
                else:
                    messages.success(request, f"Karte {kartennummer} deaktiviert (kein Paxton-User).")
            else:
                messages.success(request, f"Karte {kartennummer} deaktiviert (kein Paxton-Token).")
        except Exception:
            logger.exception("Paxton-Löschung fehlgeschlagen")
            messages.warning(request, f"Karte deaktiviert. Fehler beim Paxton-Löschen.")
    except DatabaseError as e:
        logger.exception("DB-Fehler beim Deaktivieren")
        messages.error(request, f"Datenbank-Fehler: {e}")
    except Exception as e:
        logger.exception("Unerwarteter Fehler beim Deaktivieren")
        messages.error(request, f"Interner Fehler: {e}")

    return redirect('formular')

def column_exists(schema: str, table: str, column: str) -> bool:
    with connection.cursor() as c:
        c.execute(
            "SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (schema, table, column)
        )
        return c.fetchone() is not None

@require_POST
def lost_card(request):
    kartennummer = (request.POST.get('kartennummer') or "").strip()
    mifare = (request.POST.get('mifareid_paxton') or "").strip()
    emp = (request.POST.get('employeeNumber') or "").strip()
    action_user = request.user.username if getattr(request.user, "is_authenticated", False) else 'anonymous'
    client_ip = request.META.get('REMOTE_ADDR', '')
    log_extra = {'username': action_user, 'clientip': client_ip}
    logger.info("lost_card start: kartennummer=%r mifare=%r emp=%r", kartennummer, mifare, emp, extra=log_extra)

    if not kartennummer:
        messages.error(request, "Kartennummer fehlt.")
        return redirect(reverse('formular'))

    try:
        mk_has_verl = column_exists('dbo', 'mitarbeiterKarte', 'verlorene_karte')
        hcm_has_verl = column_exists('dbo', 'HCM_mitarbeiter', 'verlorene_karte')
        stu_has_verl = column_exists('dbo', 't_studenten', 'verlorene_karte')
        gast_has_verl = column_exists('dbo', 't_Gast', 'verlorene_karte')

        with transaction.atomic():
            with connection.cursor() as c:
                if mk_has_verl:
                    if mifare:
                        c.execute(
                            """
                            UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte]
                            SET active = 0, verlorene_karte = 1
                            WHERE kartennummer = %s
                              AND (mifareid_paxton = %s OR COALESCE(NULLIF(mifareid_paxton, ''), '') = %s)
                            """, (kartennummer, mifare, mifare)
                        )
                    else:
                        c.execute(
                            "UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte] SET active = 0, verlorene_karte = 1 WHERE kartennummer = %s",
                            (kartennummer,)
                        )
                else:
                    if mifare:
                        c.execute(
                            """
                            UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte]
                            SET active = 0
                            WHERE kartennummer = %s
                              AND (mifareid_paxton = %s OR COALESCE(NULLIF(mifareid_paxton, ''), '') = %s)
                            """, (kartennummer, mifare, mifare)
                        )
                    else:
                        c.execute(
                            "UPDATE [HCM_Daten].[dbo].[mitarbeiterKarte] SET active = 0 WHERE kartennummer = %s",
                            (kartennummer,)
                        )
                rc1 = c.rowcount
                logger.info("mitarbeiterKarte UPDATE rowcount=%s (mk_has_verl=%s)", rc1, mk_has_verl, extra=log_extra)

                params = [kartennummer]
                where_clause = "kartennummer = %s"
                if mifare:
                    where_clause += " AND (mifareid_paxton = %s OR COALESCE(NULLIF(mifareid_paxton, ''), '') = %s)"
                    params.extend([mifare, mifare])
                if emp:
                    where_clause += " AND employeeNumber = %s"
                    params.append(emp)
                if hcm_has_verl:
                    sql_hcm = f"UPDATE [HCM_Daten].[dbo].[HCM_mitarbeiter] SET active = 0, verlorene_karte = 1 WHERE id IN (SELECT mitarbeiter_id FROM [HCM_Daten].[dbo].[mitarbeiterKarte] WHERE {where_clause})"
                else:
                    sql_hcm = f"UPDATE [HCM_Daten].[dbo].[HCM_mitarbeiter] SET active = 0 WHERE id IN (SELECT mitarbeiter_id FROM [HCM_Daten].[dbo].[mitarbeiterKarte] WHERE {where_clause})"
                c.execute(sql_hcm, params)
                rc2 = c.rowcount
                logger.info("HCM_mitarbeiter UPDATE rowcount=%s (hcm_has_verl=%s)", rc2, hcm_has_verl, extra=log_extra)

                if stu_has_verl:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_studenten] SET active = 0, verlorene_karte = 1 WHERE kartennummer = %s", (kartennummer,))
                else:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_studenten] SET active = 0 WHERE kartennummer = %s", (kartennummer,))
                rc3 = c.rowcount
                logger.info("t_studenten UPDATE rowcount=%s (stu_has_verl=%s)", rc3, stu_has_verl, extra=log_extra)

                if gast_has_verl:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_Gast] SET active = 0, verlorene_karte = 1 WHERE kartennummer = %s", (kartennummer,))
                else:
                    c.execute("UPDATE [HCM_Daten].[dbo].[t_Gast] SET active = 0 WHERE kartennummer = %s", (kartennummer,))
                rc4 = c.rowcount
                logger.info("t_Gast UPDATE rowcount=%s (gast_has_verl=%s)", rc4, gast_has_verl, extra=log_extra)

        try:
            token = get_token()
            logger.info("lost_card: get_token present=%s", bool(token), extra=log_extra)
            if token:
                paxtonid = get_paxton_user_id_by_kartennummer(kartennummer, token)
                logger.info("lost_card: paxton lookup kartennummer=%s -> paxtonid=%s", kartennummer, paxtonid, extra=log_extra)
                if paxtonid:
                    ok = delete_paxton_user(token, paxtonid)
                    logger.info("lost_card: delete_paxton_user returned %s for paxtonid=%s", ok, paxtonid, extra=log_extra)
                    if ok:
                        messages.success(request, f"Karte {kartennummer} als verloren markiert und Paxton-User entfernt.")
                    else:
                        messages.warning(request, f"Karte {kartennummer} als verloren markiert. Paxton-Löschung fehlgeschlagen (siehe Logs).")
                else:
                    messages.success(request, f"Karte {kartennummer} als verloren markiert (kein Paxton-User gefunden).")
                    logger.info("lost_card: kein Paxton-User für kartennummer=%s", kartennummer, extra=log_extra)
            else:
                messages.success(request, f"Karte {kartennummer} als verloren markiert (kein Paxton-Token).")
                logger.warning("lost_card: kein Paxton token - Löschung übersprungen", extra=log_extra)
        except Exception:
            logger.exception("Fehler beim Paxton-Löschen für kartennummer=%s", kartennummer, extra=log_extra)
            messages.warning(request, f"Karte als verloren markiert. Fehler beim Paxton-Löschen (siehe Logs).")

        total = sum(x or 0 for x in (rc1, rc2, rc3, rc4))
        logger.info("lost_card abgeschlossen: total_changed=%s (mk=%s,hcm=%s,stu=%s,gast=%s)", total, rc1, rc2, rc3, rc4, extra=log_extra)

    except DatabaseError as e:
        logger.exception("DB-Fehler beim Markieren verloren kartennummer=%s: %s", kartennummer, e, extra=log_extra)
        messages.error(request, f"Datenbank-Fehler: {e}")
    except Exception as e:
        logger.exception("Unerwarteter Fehler beim Markieren verloren kartennummer=%s: %s", kartennummer, e, extra=log_extra)
        messages.error(request, f"Interner Fehler: {e}")

    return redirect(f"{reverse('formular')}?selected={kartennummer}")


def formular_view(request):
    selected = request.GET.get("selected", "").strip()
    benutzer_info = {}

    if selected:
        for model, typ in [(PaxtonViewWeb, "Mitarbeiter"), (TGast, "Gast"), (TStudenten, "Student")]:
            obj = model.objects.filter(kartennummer=selected).first()
            if obj is not None:
                benutzer_info = row_to_dict(obj, typ)
                break

        if benutzer_info:
            try:
                status_label, status_class = get_user_status(benutzer_info)
                benutzer_info['Status'] = status_label
                benutzer_info['StatusClass'] = str(status_class).lower()
            except Exception:
                benutzer_info.setdefault('Status', '')
                benutzer_info.setdefault('StatusClass', '')

            try:
                departments_map = get_departments_dict() or {}
            except Exception:
                departments_map = {}
            try:
                accesslevels_map = get_access_levels_dict_from_fetch() or {}
            except Exception:
                accesslevels_map = {}

            try:
                bg_ids = _normalize_id_list(benutzer_info.get("benutzergruppe") or benutzer_info.get("benutzergruppe_id"))
                benutzer_info["benutzergruppe_name"] = ", ".join(_map_ids_to_names(bg_ids, departments_map)) if bg_ids else ""
            except Exception:
                benutzer_info.setdefault("benutzergruppe_name", "")

            try:
                al_ids = _normalize_id_list(benutzer_info.get("berechtigungsgruppe") or benutzer_info.get("berechtigungsgruppe_id"))
                benutzer_info["berechtigungsgruppe_name"] = ", ".join(_map_ids_to_names(al_ids, accesslevels_map)) if al_ids else ""
            except Exception:
                benutzer_info.setdefault("berechtigungsgruppe_name", "")

    benutzer_info.setdefault('mifareid_paxton', '')
    benutzer_info.setdefault('quelle', '')
    benutzer_info.setdefault('employeenumber', '')
    benutzer_info.setdefault('kartennummer', '')
    benutzer_info.setdefault('name_full', '')
    benutzer_info.setdefault('Status', '')
    benutzer_info.setdefault('StatusClass', '')
    benutzer_info.setdefault('abteilung', '')
    benutzer_info.setdefault('funktion', '')
    benutzer_info.setdefault('createtime', '')
    benutzer_info.setdefault('vertragsende', '')
    benutzer_info.setdefault('schrank', '')
    benutzer_info.setdefault('benutzergruppe', '')
    benutzer_info.setdefault('berechtigungsgruppe', '')

    return render(request, "Formular/paxton_formular.html", {
        "benutzer_info": benutzer_info,
        "benutzerabbrechen": [{'title': "Abbrechen und zurück", 'url_name': 'algemeineTabelle'}],
        "request": request,
    })


def row_to_dict(obj, typ=None):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.copy()
    d = {}
    for field in obj._meta.get_fields():
        if hasattr(obj, field.name):
            val = getattr(obj, field.name)
            if callable(val):
                continue
            d[field.name] = val
    if typ:
        d['quelle'] = typ
    return d

@require_GET
def autocomplete_user(request):
    term = request.GET.get("term", "").strip().lower()
    all_flag = request.GET.get("all", "0") == "1"
    MAX_RESULTS = 500000

    results = []
    seen_keys = set()

    try:
        departments_map = get_departments_dict() or {}
    except Exception:
        departments_map = {}
    try:
        accesslevels_map = get_access_levels_dict_from_fetch() or {}
    except Exception:
        accesslevels_map = {}

    if not term and not all_flag:
        return JsonResponse([], safe=False)

    for typ in ["paxton_view_web", "t_studenten", "t_Gast"]:
        try:
            users, total = get_benutzer_liste(typ, 1, 500000, "employeenumber", "ASC")
        except Exception:
            maybe = get_benutzer_liste(typ, 1, 500000, "employeenumber", "ASC")
            if isinstance(maybe, tuple) and len(maybe) == 2:
                users, total = maybe
            else:
                users = maybe or []
                total = len(users)

        logger.debug("autocomplete: typ=%s -> users_type=%s count=%d total_hint=%s", typ, type(users), len(users), total)

        for u in users:
            if isinstance(u, dict):
                kart_raw = u.get("kartennummer", "")
                emp_raw = u.get("employeenumber", "")
                name_raw = u.get("name_full", "")
                bg_raw = u.get("benutzergruppe") or u.get("benutzergruppe_id")
                al_raw = u.get("berechtigungsgruppe") or u.get("berechtigungsgruppe_id")
            else:
                kart_raw = getattr(u, "kartennummer", "") or ""
                emp_raw = getattr(u, "employeenumber", "") or ""
                name_raw = getattr(u, "name_full", "") or f"{getattr(u,'givenname','')} {getattr(u,'sn','')}".strip()
                bg_raw = getattr(u, "benutzergruppe", "") or getattr(u, "benutzergruppe_id", "")
                al_raw = getattr(u, "berechtigungsgruppe", "") or getattr(u, "berechtigungsgruppe_id", "")

            try:
                kart = str(kart_raw).lower()
            except Exception:
                kart = ""
            emp = str(emp_raw).lower() if emp_raw is not None else ""
            name = str(name_raw).lower() if name_raw is not None else ""

            if not all_flag and term:
                if term not in kart and term not in emp and term not in name:
                    continue

            key = kart if kart else (emp if emp else (name + "_" + typ))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            bg_ids = _normalize_id_list(bg_raw)
            bg_names = _map_ids_to_names(bg_ids, departments_map)
            al_ids = _normalize_id_list(al_raw)
            al_names = _map_ids_to_names(al_ids, accesslevels_map)

            if isinstance(u, dict):
                name_full = u.get("name_full", "") or ""
                employeenumber = u.get("employeenumber", "") or ""
                kartennummer = u.get("kartennummer", "") or ""
            else:
                name_full = getattr(u, "name_full", "") or f"{getattr(u,'givenname','')} {getattr(u,'sn','')}".strip()
                employeenumber = getattr(u, "employeenumber", "") or ""
                kartennummer = getattr(u, "kartennummer", "") or ""

            status_label, status_color = get_user_status(u)

            results.append({
                "status": status_label,
                "statusColor": status_color,
                "kartennummer": kartennummer,
                "name_full": name_full,
                "employeenumber": employeenumber,
                "quelle": typ,
                "benutzergruppe_name": ", ".join(bg_names) if bg_names else "",
                "berechtigungsgruppe_name": ", ".join(al_names) if al_names else "",
                "funktion": (u.get("funktion") if isinstance(u, dict) else getattr(u, "funktion", "")),
                "gelesen_am": (u.get("gelesen_am") if isinstance(u, dict) else getattr(u, "gelesen_am", "")),
                "abteilung": (u.get("abteilung") if isinstance(u, dict) else getattr(u, "abteilung", "")),
                "mifareid_paxton": (u.get("mifareid_paxton") if isinstance(u, dict) else getattr(u, "mifareid_paxton", "")),
                "createtime": (u.get("createtime") if isinstance(u, dict) else getattr(u, "createtime", "")),
                "schrank": (u.get("schrank") if isinstance(u, dict) else getattr(u, "schrank", "")),
            })

            if len(results) >= MAX_RESULTS:
                break
        if len(results) >= MAX_RESULTS:
            break

    return JsonResponse(results, safe=False)

@require_GET
def api_departments(request):
    try:
        departments = get_departments_dict()
        result = sorted(list(departments.values()))
        return JsonResponse(result, safe=False)
    except Exception as e:
        logger.exception("api_departments error")
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def api_accesslevels(request):
    try:
        from Tabelle.Paxton_all import fetch_all_access_levels, get_token
        token = get_token()
        levels = fetch_all_access_levels() if token else []
        clean_levels = []
        for lvl in levels:
            if isinstance(lvl, dict):
                clean_levels.append({
                    "id": lvl.get("id"),
                    "name": lvl.get("name") or lvl.get("Name") or lvl.get("AccessLevelName"),
                })
        return JsonResponse(clean_levels, safe=False)
    except Exception as e:
        logger.exception("api_accesslevels error")
        return JsonResponse({"error": str(e)}, status=500)


def _normalize_id_list(val):
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [str(x).strip() for x in val if x is not None and str(x).strip() != ""]
    s = str(val).strip()
    if s == "":
        return []
    nums = re.findall(r'\d+', s)
    if nums:
        return [n for n in nums]
    parts = re.split(r'[,\;\|\s]+', s)
    parts = [p.strip() for p in parts if p.strip() != ""]
    return parts


def _map_ids_to_names(ids, mapping):
    out = []
    for i in ids:
        if i is None:
            continue
        key = str(i)
        name = mapping.get(key)
        if name is None:
            if key.isdigit():
                name = mapping.get(str(int(key)))
        if name:
            out.append(name)
    return out