from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render, redirect
from django.db import connection, transaction, DatabaseError
from django.contrib import messages
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.utils.html import escape
import re
import logging
from django.urls import reverse

from Tabelle.models import PaxtonViewWeb, TGast, TStudenten
from Tabelle.utils import get_benutzer_liste, get_user_status
from Tabelle.Paxton_all import get_access_levels_dict_from_fetch, save_to_paxton, save_to_db


from synchronisation.Paxton_funk import create_or_update_department, get_token, get_user_tokens, fetch_all_access_levels, get_paxton_user_id_by_kartennummer, delete_paxton_user, create_or_update_paxton_user, add_user_token, create_access_level, update_paxton_user, get_departments_dict
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

    return ()


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
            benutzergruppe = int(benutzergruppe_value) if str(benutzergruppe_value).isdigit() else None
        if berechtigungsgruppe_value:
            berechtigungsgruppe = int(berechtigungsgruppe_value) if str(berechtigungsgruppe_value).isdigit() else None

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
        # DB-Teil komplett über Stored Procedure
        with transaction.atomic():
            with connection.cursor() as c:
                # Für SQL Server (pyodbc + Django): EXEC dbo.proc @p=?,@p=? ist zuverlässig
                c.execute(
                    "EXEC [dbo].[sp_deaktiv_card] %s, %s, %s",
                    [kartennummer, mifare or None, emp or None]
                )

        # Danach (außerhalb DB-Transaktion) Paxton
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
            messages.warning(request, "Karte deaktiviert. Fehler beim Paxton-Löschen.")

    except DatabaseError as e:
        logger.exception("DB-Fehler beim Deaktivieren")
        messages.error(request, f"Datenbank-Fehler: {e}")
    except Exception as e:
        logger.exception("Unerwarteter Fehler beim Deaktivieren")
        messages.error(request, f"Interner Fehler: {e}")

    return redirect('formular')


@require_POST
def lost_card(request):
    kartennummer = (request.POST.get('kartennummer') or "").strip()
    mifare = (request.POST.get('mifareid_paxton') or "").strip()
    emp = (request.POST.get('employeeNumber') or "").strip()

    if not kartennummer:
        messages.error(request, "Kartennummer fehlt.")
        return redirect(reverse('formular'))

    try:
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute(
                    "EXEC dbo.sp_lost_card %s, %s, %s",
                    [kartennummer, mifare or None, emp or None]
                )

        logger.info(
            "lost_card: DB erfolgreich aktualisiert (kartennummer=%s, mifare=%s, emp=%s)",
            kartennummer, mifare, emp,
        )

        # Paxton (außerhalb der DB-Transaktion)
        try:
            token = get_token()
            if token:
                paxtonid = get_paxton_user_id_by_kartennummer(kartennummer, token)
                if paxtonid:
                    ok = delete_paxton_user(token, paxtonid)
                    if ok:
                        messages.success(request, f"Karte {kartennummer} als verloren markiert und Paxton-User entfernt.")
                    else:
                        messages.warning(request, f"Karte {kartennummer} als verloren markiert. Paxton-Löschung fehlgeschlagen (siehe Logs).")
                else:
                    messages.success(request, f"Karte {kartennummer} als verloren markiert (kein Paxton-User gefunden).")
            else:
                messages.success(request, f"Karte {kartennummer} als verloren markiert (kein Paxton-Token).")
        except Exception:
            logger.exception("Fehler beim Paxton-Löschen für kartennummer=%s", kartennummer)
            messages.warning(request, "Karte als verloren markiert. Fehler beim Paxton-Löschen (siehe Logs).")

    except DatabaseError as e:
        logger.exception("DB-Fehler beim Markieren verloren kartennummer=%s: %s", kartennummer, e)
        messages.error(request, f"Datenbank-Fehler: {e}")
    except Exception as e:
        logger.exception("Unerwarteter Fehler beim Markieren verloren kartennummer=%s: %s", kartennummer, e)
        messages.error(request, f"Interner Fehler: {e}")

    return redirect(f"{reverse('formular')}?selected={kartennummer}")



def formular_view(request):
    selected = request.GET.get("selected", "").strip()
    benutzer_info = {}

    if selected:
        for model, typ in [(PaxtonViewWeb, "Mitarbeiter"), (TGast, "Gast"), (TStudenten, "Student")]:
            try:
                obj = model.objects.filter(kartennummer=selected).order_by('-row_id').first()
            except Exception:
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
    # vertragsende aus austritt oder endofcontract befüllen
    if not d.get('vertragsende'):
        raw = d.get('austritt') or d.get('endofcontract')
        if raw:
            try:
                d['vertragsende'] = raw.strftime('%Y-%m-%d')
            except Exception:
                d['vertragsende'] = str(raw)
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
def autocomplete_user_html(request):
    """Server-Side Autocomplete — gibt fertige HTML <li> zurück für HTMX."""
    term = request.GET.get("term", "").strip().lower()
    field = request.GET.get("field", "")  # employeenumber / kartennummer / name_full

    # term aus dem richtigen Feld lesen
    if not term:
        val = (request.GET.get("employeeNumber") or request.GET.get("kartennummer") or request.GET.get("name_full") or "").strip().lower()
        term = val

    if not term:
        return HttpResponse("")

    results = []
    seen_keys = set()

    for typ in ["paxton_view_web", "t_studenten", "t_Gast"]:
        try:
            users, _ = get_benutzer_liste(typ, 1, 500000, "employeenumber", "ASC")
        except Exception:
            users = []

        for u in users:
            if isinstance(u, dict):
                kart = str(u.get("kartennummer") or "").lower()
                emp  = str(u.get("employeenumber") or "").lower()
                name = str(u.get("name_full") or "").lower()
                kartennummer   = u.get("kartennummer") or ""
                employeenumber = u.get("employeenumber") or ""
                name_full      = u.get("name_full") or ""
            else:
                kart = str(getattr(u, "kartennummer", "") or "").lower()
                emp  = str(getattr(u, "employeenumber", "") or "").lower()
                gn   = getattr(u, "givenname", "") or ""
                sn   = getattr(u, "sn", "") or ""
                name = (f"{gn} {sn}").strip().lower()
                kartennummer   = getattr(u, "kartennummer", "") or ""
                employeenumber = getattr(u, "employeenumber", "") or ""
                name_full      = f"{gn} {sn}".strip()

            if term not in kart and term not in emp and term not in name:
                continue

            key = kart or emp or (name + "_" + typ)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            status_label, status_color = get_user_status(u)
            results.append({
                "kartennummer": kartennummer,
                "employeenumber": employeenumber,
                "name_full": name_full,
                "status": status_label,
                "statusColor": status_color,
            })

            if len(results) >= 50:  # max 50 Ergebnisse reichen
                break
        if len(results) >= 50:
            break

    # HTML rendern
    from django.utils.html import escape
    html_parts = []
    for r in results:
        kart = escape(str(r["kartennummer"]))
        name = escape(str(r["name_full"]))
        emp  = escape(str(r["employeenumber"]))
        stat = escape(str(r["status"]))
        color = escape(str(r["statusColor"]))
        url = f"/Formular/?selected={kart}"
        html_parts.append(
            f'<li onclick="window.location.href=\'{url}\'" class="{color}" style="cursor:pointer;list-style:none;padding:4px 8px;">' +
            f'<span class="name">{name}</span>' +
            f' | <span class="status">{stat}</span>' +
            f' | Karten-Nr: <span class="kartennummer">{kart}</span>' +
            f' | Pers-Nr: <span class="employeenumber">{emp}</span>' +
            f'</li>'
        )

    if not html_parts:
        return HttpResponse('<li>Keine Ergebnisse gefunden.</li>')

    from django.http import HttpResponse
    return HttpResponse("".join(html_parts))

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