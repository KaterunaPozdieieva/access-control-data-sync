import time
import datetim
import importlib
import logging
from django.shortcuts import render
from django.http import JsonResponse
from Tabelle.utils import get_benutzer_liste, get_user_status, _apply_filters_to_queryset

try:
    from Tabelle.utils import fill_status_fields_for_users
except Exception:
    fill_status_fields_for_users = None

logger = logging.getLogger('paxton')
def _user_createtime_value(user):
    """Extrahiert das Raw-createtime-Feld aus user (dict oder model instance)."""
    if isinstance(user, dict):
        return user.get('createtime') or user.get('create_time') or user.get('created_at') or user.get('createtimestamp')
    else:
        for attr in ('createtime', 'create_time', 'created_at', 'createtimestamp'):
            if hasattr(user, attr):
                try:
                    return getattr(user, attr)
                except Exception:
                    return None
    return None
def _import_paxton_module():
    candidates = [
        'Paxton_all',
        'Tabelle.Paxton_all',
        'web.coolsite.Paxton_all',
        'web.Paxton_all',
    ]
    for name in candidates:
        try:
            mod = importlib.import_module(name)
            logger.info("Paxton_all imported as %s", name)
            return mod
        except Exception as e:
            logger.debug("Import %s failed: %s", name, e)
    logger.warning("Paxton_all module not found among candidates: %s", candidates)
    return None

# globales Modul (oder None)
_PAXTON_MOD = _import_paxton_module()
MAX_FETCH_ALL = 100000

def _try_parse_datetime(val):
    if val is None:
        return None
    if isinstance(val, datetime.datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        if s.isdigit():
            ts = int(s)
            if ts > 1000000000:
                return datetime.datetime.fromtimestamp(ts)
    except Exception:
        pass
    return None


def _sort_users_by_createtime_with_nulls_last(users, descending=True):

    has_date = []
    no_date = []
    for u in users:
        ct = None
        if isinstance(u, dict):
            ct = u.get('createtime') or u.get('create_time') or u.get('created_at') or u.get('createtimestamp')
        else:
            for attr in ('createtime','create_time','created_at','createtimestamp'):
                if hasattr(u, attr):
                    ct = getattr(u, attr)
                    break
        dt = _try_parse_datetime(ct)
        if dt is None:
            no_date.append(u)
        else:
            has_date.append((dt, u))
    has_date.sort(key=lambda t: t[0], reverse=descending)
    sorted_users = [u for _, u in has_date] + no_date
    return sorted_users

def _get_paxton_func(name):
    if not _PAXTON_MOD:
        return None
    try:
        return getattr(_PAXTON_MOD, name, None)
    except Exception:
        return None

get_paxton_users = _get_paxton_func('get_paxton_users')
get_departments_dict = _get_paxton_func('get_departments_dict')
get_access_levels_dict = _get_paxton_func('get_access_levels_dict')
fetch_all_access_levels = _get_paxton_func('fetch_all_access_levels')
get_access_levels_dict_from_fetch = _get_paxton_func('get_access_levels_dict_from_fetch')
get_departments_dict_from_fetch = _get_paxton_func('get_departments_dict_from_fetch')


_MAPPINGS_CACHE = {
    'access_levels': {},
    'departments': {},
    'loaded_at': 0
}
_MAPPINGS_TTL = 10 * 60  

def load_mappings(force=False):
    now = time.time()
    if not force and (now - _MAPPINGS_CACHE.get('loaded_at', 0) < _MAPPINGS_TTL):
        return _MAPPINGS_CACHE['access_levels'], _MAPPINGS_CACHE['departments']

    access_levels = {}
    departments = {}

    try:
        if callable(get_access_levels_dict):
            res = get_access_levels_dict() or {}
            if isinstance(res, list):
                access_levels = {str(d.get('id') or d.get('Id')): (d.get('name') or d.get('Name') or "") for d in res if isinstance(d, dict)}
            elif isinstance(res, dict):
                access_levels = res
            logger.info("get_access_levels_dict returned %d entries", len(access_levels))
    except Exception:
        logger.exception("get_access_levels_dict() raised exception")
    try:
        if callable(get_departments_dict):
            res = get_departments_dict() or {}
            if isinstance(res, list):
                departments = {str(d.get('id') or d.get('Id')): (d.get('name') or d.get('Name') or "") for d in res if isinstance(d, dict)}
            elif isinstance(res, dict):
                departments = res
            logger.info("get_departments_dict returned %d entries", len(departments))
    except Exception:
        logger.exception("get_departments_dict() raised exception")
    if not access_levels and callable(get_access_levels_dict_from_fetch):
        try:
            res = get_access_levels_dict_from_fetch() or {}
            if isinstance(res, dict):
                access_levels = res
            logger.info("get_access_levels_dict_from_fetch returned %d entries", len(access_levels))
        except Exception:
            logger.exception("get_access_levels_dict_from_fetch() raised exception")
    if not departments and callable(get_departments_dict_from_fetch):
        try:
            res = get_departments_dict_from_fetch() or {}
            if isinstance(res, dict):
                departments = res
            logger.info("get_departments_dict_from_fetch returned %d entries", len(departments))
        except Exception:
            logger.exception("get_departments_dict_from_fetch() raised exception")
    if not access_levels and callable(fetch_all_access_levels):
        try:
            levels = fetch_all_access_levels() or []
            if isinstance(levels, list):
                access_levels = {str(d.get('id') or d.get('Id')): (d.get('name') or d.get('Name') or "") for d in levels if isinstance(d, dict)}
            logger.info("fetch_all_access_levels returned %d entries", len(access_levels))
        except Exception:
            logger.exception("fetch_all_access_levels() raised exception")
    try:
        access_levels = {str(k): v for k, v in (access_levels or {}).items()}
    except Exception:
        access_levels = {}
    try:
        departments = {str(k): v for k, v in (departments or {}).items()}
    except Exception:
        departments = {}

    _MAPPINGS_CACHE['access_levels'] = access_levels
    _MAPPINGS_CACHE['departments'] = departments
    _MAPPINGS_CACHE['loaded_at'] = now
    logger.debug("load_mappings finished: access=%d dept=%d", len(access_levels), len(departments))
    return access_levels, departments





def map_access_and_dept_for_users(benutzer_liste):
    access_levels, departments = load_mappings()
    logger.debug("AccessLevels keys sample: %s", list(access_levels.keys())[:10])
    logger.debug("Departments keys sample: %s", list(departments.keys())[:10])

    for idx, user in enumerate(benutzer_liste):
        try:
            access_val = _get_model_access_value(user)
            dept_val = _get_model_dept_value(user)
        except Exception:
            logger.exception("Fehler beim Lesen der Raw-Werte access/dept für user idx %d", idx)
            access_val = None
            dept_val = None

        access_name = "-"
        dept_name = "-"

        if access_val not in (None, ""):
            try:
                key = str(_to_int_safe(access_val) or access_val)
                if access_levels:
                    mapped = access_levels.get(key)
                    access_name = mapped if mapped else str(access_val)
                else:
                    access_name = str(access_val)
                logger.debug("User idx=%d access_val=%r -> key=%r -> %r", idx, access_val, key, access_name)
            except Exception:
                logger.exception("Fehler beim Bestimmen des access_name für user idx %d", idx)
                access_name = str(access_val)

        if dept_val not in (None, ""):
            try:
                key = str(_to_int_safe(dept_val) or dept_val)
                if departments:
                    mapped = departments.get(key)
                    dept_name = mapped if mapped else str(dept_val)
                else:
                    dept_name = str(dept_val)
                logger.debug("User idx=%d dept_val=%r -> key=%r -> %r", idx, dept_val, key, dept_name)
            except Exception:
                logger.exception("Fehler beim Bestimmen des dept_name für user idx %d", idx)
                dept_name = str(dept_val)
        try:
            if isinstance(user, dict):
                user['berechtigungsgruppe'] = access_name
                user['benutzergruppe'] = dept_name
            else:
                try:
                    setattr(user, 'berechtigungsgruppe', access_name)
                except Exception:
                    logger.debug("Konnte berechtigungsgruppe nicht per setattr setzen für user %r", getattr(user, "id", user))
                try:
                    setattr(user, 'benutzergruppe', dept_name)
                except Exception:
                    logger.debug("Konnte benutzergruppe nicht per setattr setzen für user %r", getattr(user, "id", user))
        except Exception:
            logger.exception("Fehler beim Setzen der Anzeige-Felder für user idx %d", idx)


def parse_table_request_params(request):
    benutzertyp = request.GET.get('benutzertyp', 'Alle')
    try:
        page = int(request.GET.get('page', 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.GET.get('per_page', 30))
    except Exception:
        per_page = 30
    sort_by = request.GET.get('sort_by', 'createtime')
    order = request.GET.get('order', 'DESC')
    sort_mode = request.GET.get('sort_mode', '')

    action = request.GET.get('action') or request.POST.get('action')

    # neue Präsenz-Filter (values: '', 'with', 'without')
    has_benutzergruppe = request.GET.get('has_benutzergruppe', '').strip()  # expected 'with' or 'without' or ''
    has_berechtigungsgruppe = request.GET.get('has_berechtigungsgruppe', '').strip()  # same

    filters = {
        "employeenumber": request.GET.get('employeenumber', '').strip(),
        "kartennummer": request.GET.get('kartennummer', '').strip(),
        "name_full": request.GET.get('name_full', '').strip(),
        "einrichtung": request.GET.get('einrichtung', '').strip(),
        "funktion": request.GET.get('funktion', '').strip(),
        "schrank": request.GET.get('schrank', '').strip(),
        "status": request.GET.get('status', '').strip(),
        # Präsenz-Filter als separate keys (werden an get_benutzer_liste weitergereicht wenn unterstützt)
        "has_benutzergruppe": has_benutzergruppe,
        "has_berechtigungsgruppe": has_berechtigungsgruppe,
    }

    try:
        username = request.user.username if getattr(request, "user", None) and request.user.is_authenticated else "anonymous"
    except Exception:
        username = "anonymous"

    active_filters = {k: v for k, v in filters.items() if v and k not in ("has_benutzergruppe", "has_berechtigungsgruppe")}
    # Präsenz-Filter separat in active_filters, wenn gesetzt:
    if has_benutzergruppe:
        active_filters['has_benutzergruppe'] = has_benutzergruppe
    if has_berechtigungsgruppe:
        active_filters['has_berechtigungsgruppe'] = has_berechtigungsgruppe

    return {
        'benutzertyp': benutzertyp,
        'page': page,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_mode': sort_mode,
        'order': order,
        'action': action,
        'filters': filters,
        'username': username,
        'active_filters': active_filters,
    }

# +
def fetch_benutzer_liste(benutzertyp, page, per_page, sort_by, order, filters, sort_mode=None):
    """
    Robust wrapper:
    - delegiert an get_benutzer_liste (wenn möglich),
    - falls nötig: lädt bis MAX_FETCH_ALL Datensätze und wendet presence/benutzertyp-Filer
      lokal an VOR der createtime-Sortierung,
    - wenn sort_by == 'createtime' werden nur Benutzer mit createtime angezeigt (wie gewünscht).
    Rückgabe: (page_slice, total)
    """
    # 1) delegiere zuerst an utils (DB-side, schnell)
    try:
        try:
            result = get_benutzer_liste(benutzertyp, page, per_page, sort_by, order,
                                        sort_mode=sort_mode, filters=filters)
        except TypeError:
            result = get_benutzer_liste(benutzertyp, page, per_page, sort_by, order,
                                        filters=filters)
    except Exception:
        logger.exception("Fehler beim Laden der Benutzerliste (delegiert)")
        return [], 0

    # presence flags
    has_bg = bool(filters.get('has_benutzergruppe'))
    has_ag = bool(filters.get('has_berechtigungsgruppe'))

    # Wenn kein createtime-Sort und keine presence-filter, gib delegiertes Ergebnis direkt zurück
    if str(sort_by).lower() != 'createtime' and not (has_bg or has_ag):
        if isinstance(result, tuple) and len(result) == 2:
            return result
        else:
            return (result or [], len(result or []))

    # Entpacke delegiertes Result (kann page-limited sein)
    users, total = (result if isinstance(result, tuple) and len(result) == 2 else (result or [], len(result or [])))

    # Heuristik: falls delegiertes Result plausibel gefiltert ist (best-effort) und kein createtime-Special, zurückgeben
    def _matches_filters_sample(lst):
        if not lst:
            return True
        sample = lst[:min(5, len(lst))]
        for u in sample:
            if has_bg:
                want = filters.get('has_benutzergruppe')
                ok = _user_has_benutzergruppe(u)
                if want == 'with' and not ok:
                    return False
                if want == 'without' and ok:
                    return False
            if has_ag:
                want = filters.get('has_berechtigungsgruppe')
                ok = _user_has_berechtigungsgruppe(u)
                if want == 'with' and not ok:
                    return False
                if want == 'without' and ok:
                    return False
        return True

    if _matches_filters_sample(users) and str(sort_by).lower() != 'createtime':
        return users, total

    # Sonst: lade (bis Grenze) viele Datensätze und filtere lokal bevor sortieren
    try:
        try:
            _, total_all = get_benutzer_liste(benutzertyp, 1, 1, sort_by, order,
                                              sort_mode=sort_mode, filters=filters)
        except TypeError:
            _, total_all = get_benutzer_liste(benutzertyp, 1, 1, sort_by, order, filters=filters)
        total_all_int = int(total_all or 0)
    except Exception:
        total_all_int = 0

    fetch_count = total_all_int if (0 < total_all_int <= MAX_FETCH_ALL) else MAX_FETCH_ALL

    try:
        try:
            all_res = get_benutzer_liste(benutzertyp, 1, fetch_count, sort_by, order,
                                         sort_mode=sort_mode, filters=filters)
        except TypeError:
            all_res = get_benutzer_liste(benutzertyp, 1, fetch_count, sort_by, order, filters=filters)
    except Exception:
        logger.exception("Fehler beim Laden aller Benutzer (für lokale Filter/Sort)")
        return [], 0

    if isinstance(all_res, tuple) and len(all_res) == 2:
        all_users, _ = all_res
    else:
        all_users = all_res or []

    # Jetzt: presence- und benutzertyp-filter ANWENDEN (best-effort)
    benutzertyp_filter = benutzertyp

    def _matches_presence_and_type(u):
        if has_bg:
            want = filters.get('has_benutzergruppe')
            has = _user_has_benutzergruppe(u)
            if want == 'with' and not has: return False
            if want == 'without' and has: return False
        if has_ag:
            want = filters.get('has_berechtigungsgruppe')
            has = _user_has_berechtigungsgruppe(u)
            if want == 'with' and not has: return False
            if want == 'without' and has: return False
        if benutzertyp_filter and benutzertyp_filter != 'Alle':
            t = None
            if isinstance(u, dict):
                t = u.get('benutzertyp') or u.get('type') or u.get('role')
            else:
                t = getattr(u, 'benutzertyp', None) or getattr(u, 'type', None) or getattr(u, 'role', None)
            if t is not None and str(t) != str(benutzertyp_filter):
                return False
        return True

    all_users = [u for u in all_users if _matches_presence_and_type(u)]

    # Wenn sort_by == createtime: nur rows mit createtime behalten und nach Datum sortieren
    if str(sort_by).lower() == 'createtime':
        descending = (str(order or "").upper() == "DESC")
        timed = []
        for u in all_users:
            ct_raw = _user_createtime_value(u)
            dt = _try_parse_datetime(ct_raw)
            if dt is not None:
                timed.append((dt, u))
        timed.sort(key=lambda t: t[0], reverse=descending)
        all_sorted = [u for _, u in timed]
        total_with_dates = len(all_sorted)
        # paginieren
        try:
            p = max(1, int(page or 1))
        except Exception:
            p = 1
        try:
            pp = max(1, int(per_page or 30))
        except Exception:
            pp = 30
        start = (p - 1) * pp
        end = start + pp
        page_slice = all_sorted[start:end]
        return page_slice, total_with_dates

    # sonst: paginiere filtered-liste
    total_filtered = len(all_users)
    try:
        p = max(1, int(page or 1))
    except Exception:
        p = 1
    try:
        pp = max(1, int(per_page or 30))
    except Exception:
        pp = 30
    start = (p - 1) * pp
    end = start + pp
    page_slice = all_users[start:end]
    return page_slice, total_filtered

    

def algemeineTabelle(request):
    params = parse_table_request_params(request)
    logger.info("Tabelle geöffnet von=%s benutzertyp=%s page=%d per_page=%d sort=%s order=%s sort_mode=%s action=%r filters=%s",
                params['username'], params['benutzertyp'], params['page'], params['per_page'],
                params['sort_by'], params['order'], params.get('sort_mode'), params['action'], params['active_filters'])

    benutzer_liste, total = fetch_benutzer_liste(
        params['benutzertyp'], params['page'], params['per_page'],
        params['sort_by'], params['order'], params['filters'], params.get('sort_mode')
    )

    try:
        map_access_and_dept_for_users(benutzer_liste)
    except Exception:
        logger.exception("Fehler beim Mappen von Access/Dept auf Benutzerliste")

    try:
        if callable(fill_status_fields_for_users):
            fill_status_fields_for_users(benutzer_liste)
        else:
            for u in benutzer_liste:
                try:
                    status_label, status_class = get_user_status(u)
                except Exception:
                    status_label, status_class = "unbekannt", "status-unknown"
                if isinstance(u, dict):
                    u["Status"] = status_label
                    u["StatusClass"] = status_class
                else:
                    try:
                        setattr(u, "Status", status_label)
                        setattr(u, "StatusClass", status_class)
                    except Exception:
                        pass
    except Exception:
        logger.exception("Fehler beim Füllen der Status-Felder für Benutzerliste")

    if request.GET.get('debug_mappings') == '1':
        access, depts = load_mappings(force=True)
        return JsonResponse({'access_sample': list(access.items())[:200], 'dept_sample': list(depts.items())[:200]}, safe=True)

    if request.GET.get('debug_users') == '1':
        serial = []
        for u in benutzer_liste[:20]:
            if isinstance(u, dict):
                serial.append(u)
            else:
                d = {}
                for a in ('employeenumber','kartennummer','name_full','berechtigungsgruppe','benutzergruppe','Status'):
                    d[a] = getattr(u, a, None)
                serial.append(d)
        return JsonResponse({'sample_users': serial}, safe=True)

    try:
        total_pages = (int(total) + int(params['per_page']) - 1) // int(params['per_page']) if int(params['per_page']) > 0 else 1
    except Exception:
        total_pages = 1
        logger.debug("Fehler bei Berechnung total_pages; setze auf 1")

    return render(request, 'Tabelle/paxton_tabelle.html', {
        'benutzer_liste': benutzer_liste,
        'benutzertyp': params['benutzertyp'],
        'total': total,
        'page': params['page'],
        'per_page': params['per_page'],
        'total_pages': total_pages,
        'knopf': [{'title': "Paxton", 'url_name': 'formular'}],
        'menu': [{'title': "Paxton - Berechtigungsname ändern", 'url_name': 'Neue_Berechtigungsname'}],
        'filters': params['filters'],
    })

















































knopf = [{'title': "Paxton", 'url_name': 'formular'}]
menu = [{'title': "Paxton - Berechtigungsname ändern", 'url_name': 'Neue_Berechtigungsname'}]
abbrechen = [{'title': "Abbrechen und zurück", 'url_name': 'algemeineTabelle'}]

def Neue_Berechtigungsname(request):
    return render(request, 'Neue_Berechtigungsname/Neue_Berechtigungsname.html', {'abbrechen': abbrechen})
def _value_has(v):
    if v is None:
        return False
    s = str(v).strip()
    if s == '':
        return False
    # eventuell dein Fallback-Symbol '-' behandeln:
    if s == '-':
        return False
    return True

# Prüfe Presence direkt aus "raw" Feldern (IDs, strings)
def _user_has_benutzergruppe(user):
    # prüfe mögliche Felder; benutze _get_model_dept_value falls verfügbar
    try:
        val = _get_model_dept_value(user)
    except Exception:
        val = None
    return _value_has(val)

def _user_has_berechtigungsgruppe(user):
    try:
        val = _get_model_access_value(user)
    except Exception:
        val = None
    return _value_has(val)

def _to_int_safe(s):
    if s is None:
        return None
    s2 = str(s).strip()
    if s2 == "":
        return None
    s2_clean = s2.replace(" ", "").lstrip("0")
    if s2_clean.isdigit():
        try:
            return int(s2_clean)
        except Exception:
            logger.debug("Fehler beim int-convert von %r", s2_clean, exc_info=True)
            return None
    return None
def _get_field_value(user, keys):
    for k in keys:
        if isinstance(user, dict):
            try:
                if k in user and user.get(k) not in (None, ""):
                    return user.get(k)
            except Exception:
                logger.debug("Fehler beim Zugriff auf dict-Feld %s bei user %r", k, user, exc_info=True)
        try:
            val = getattr(user, k, None)
            if val not in (None, ""):
                return val
        except Exception:
            logger.debug("Fehler beim getattr %s bei user %r", k, user, exc_info=True)
    return None

def _get_model_access_value(user):
    return _get_field_value(user, [
        'berechtigungsgruppe', 'berechtigungsgruppe_id', 'accesslevel_id', 'access_level_id',
        'accessLevelId', 'accesslevelid', 'zugriffsgruppe_id', 'accesslevel', 'access_level',
        'access_id', 'zugriffsgruppe', 'berechtigungsgruppeName', 'accessname'
    ])

def _get_model_dept_value(user):
    return _get_field_value(user, [
        'benutzergruppe', 'benutzergruppe_id', 'department_id', 'departments_id',
        'departmentId', 'dept_id', 'department'
    ])