# Bereinigte Utility-Funktionen für Benutzer-Suche / Liste
from datetime import datetime
from django.db.models import Q
from Tabelle.models import TGast, TStudenten, PaxtonViewWeb

def clean_none(data):
    """Ersetzt None durch leere Strings – für saubere Ausgabe."""
    return {k: ("" if v is None else v) for k, v in data.items()}

def _model_has_field(model, field_name):
    try:
        return field_name in [f.name for f in model._meta.fields]
    except Exception:
        return False

def _is_field_numeric(model, field_name):
    """Prüft, ob ein Feld ein numerischer Feldtyp ist (Integer/BigInt/SmallInt)."""
    try:
        f = model._meta.get_field(field_name)
        return f.get_internal_type() in ("IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField")
    except Exception:
        return False

def _apply_filters_to_queryset(model, qs, filters):
    if not filters:
        return qs

    q_obj = Q()

    # employeenumber (string)
    v = filters.get('employeenumber')
    if v and _model_has_field(model, 'employeenumber'):
        q_obj &= Q(employeenumber__icontains=str(v).strip())

    # kartennummer: handle numeric vs text fields safely
    kv = filters.get('kartennummer')
    if kv and _model_has_field(model, 'kartennummer'):
        kv_raw = str(kv).strip()
        if _is_field_numeric(model, 'kartennummer'):
            # try exact numeric match after normalizing
            kv_digits = kv_raw.replace(" ", "").lstrip("0")
            try:
                kv_int = int(kv_digits) if kv_digits != "" else int(kv_raw)
                q_obj &= Q(kartennummer=kv_int)
            except Exception:
                # fallback auf exact string match if numeric conversion fails
                q_obj &= Q(kartennummer__exact=kv_raw)
        else:
            q_obj &= Q(kartennummer__icontains=kv_raw)

    # name / Vorname / Nachname
    name_v = filters.get('name_full')
    if name_v:
        nv = str(name_v).strip()
        name_q = Q()
        if _model_has_field(model, 'givenname'):
            name_q |= Q(givenname__icontains=nv)
        if _model_has_field(model, 'sn'):
            name_q |= Q(sn__icontains=nv)
        if _model_has_field(model, 'employeenumber'):
            name_q |= Q(employeenumber__icontains=nv)
        if name_q.children:
            q_obj &= name_q

    # einrichtung / abteilung / mstbroe / department
    einr_v = filters.get('einrichtung')
    if einr_v:
        ev = str(einr_v).strip()
        einr_q = Q()
        if _model_has_field(model, 'einrichtung'):
            einr_q |= Q(einrichtung__icontains=ev)
        if _model_has_field(model, 'abteilung'):
            einr_q |= Q(abteilung__icontains=ev)
        if _model_has_field(model, 'mstbroe'):
            einr_q |= Q(mstbroe__icontains=ev)
        if _model_has_field(model, 'department'):
            einr_q |= Q(department__icontains=ev)
        if einr_q.children:
            q_obj &= einr_q

    # funktion / dvh_text / role / position
    funktion_v = filters.get('funktion')
    if funktion_v:
        fv = str(funktion_v).strip()
        f_q = Q()
        if _model_has_field(model, 'funktion'):
            f_q |= Q(funktion__icontains=fv)
        if _model_has_field(model, 'dvh_text'):
            f_q |= Q(dvh_text__icontains=fv)
        if _model_has_field(model, 'role'):
            f_q |= Q(role__icontains=fv)
        if _model_has_field(model, 'position'):
            f_q |= Q(position__icontains=fv)
        if f_q.children:
            q_obj &= f_q

    # schrank / schrank_nr_alt / schranknummer / locker
    schrank_v = filters.get('schrank')
    if schrank_v:
        sv = str(schrank_v).strip()
        s_q = Q()
        if _model_has_field(model, 'schrank'):
            s_q |= Q(schrank__icontains=sv)
        if _model_has_field(model, 'schrank_nr_alt'):
            s_q |= Q(schrank_nr_alt__icontains=sv)
        if _model_has_field(model, 'schranknummer'):
            s_q |= Q(schranknummer__icontains=sv)
        if _model_has_field(model, 'locker'):
            s_q |= Q(locker__icontains=sv)
        if s_q.children:
            q_obj &= s_q

    # Status-Filter (""/None/"Alle" oder "Aktiv","Inaktiv","VerloreneKarte")
    status_v = filters.get('status')
    if status_v and status_v not in ("", "Alle", None):
        status_q = Q()
        if status_v == "VerloreneKarte":
            if _model_has_field(model, 'verlorene_karte'):
                status_q &= Q(verlorene_karte__in=[1, True])
        elif status_v == "Aktiv":
            applied = False
            if _model_has_field(model, 'karte_active'):
                status_q &= Q(karte_active=True); applied = True
            if _model_has_field(model, 'active'):
                status_q &= Q(active=True); applied = True
            if _model_has_field(model, 'Active'):
                status_q &= Q(Active=True); applied = True
            if _model_has_field(model, 'verlorene_karte'):
                status_q &= ~Q(verlorene_karte__in=[1, True])
            # if nothing applied => no filter
        elif status_v == "Inaktiv":
            applied = False
            if _model_has_field(model, 'karte_active'):
                status_q &= Q(karte_active=False); applied = True
            if _model_has_field(model, 'active'):
                status_q &= Q(active=False); applied = True
            if _model_has_field(model, 'Active'):
                status_q &= Q(Active=False); applied = True
            if _model_has_field(model, 'verlorene_karte'):
                status_q &= ~Q(verlorene_karte__in=[1, True])
        if status_q.children:
            q_obj &= status_q

    if q_obj.children:
        try:
            return qs.filter(q_obj)
        except Exception:
            # Falls Filter auf Feldtyp nicht anwendbar (sicherer Fallback)
            return qs
    return qs


def fill_status_fields_for_users(benutzer_liste):
    for user in benutzer_liste:
        try:
            status_label, status_class = get_user_status(user)
        except Exception:
            logger.exception("Fehler beim Ermitteln des User-Status für user %r", getattr(user, 'id', user))
            status_label, status_class = "unbekannt", "status-unknown"

        try:
            if isinstance(user, dict):
                user["Status"] = status_label
                user["StatusClass"] = status_class
            else:
                try:
                    setattr(user, "Status", status_label)
                    setattr(user, "StatusClass", status_class)
                except Exception:
                    logger.debug("Konnte Status-Felder nicht per setattr setzen für user %r", getattr(user, "id", user))
        except Exception:
            logger.exception("Fehler beim Setzen der Status-Felder für user %r", getattr(user, "id", user))


def get_benutzer_liste(benutzertyp, page, per_page, sort_by, order, filters=None):

    benutzer_liste = []
    default_sort = "kartennummer"

    # Entscheide, welche Modelle abgefragt werden
    if filters and any(v for v in filters.values()):
        models_to_query = [(PaxtonViewWeb, "Mitarbeiter"), (TGast, "Gast"), (TStudenten, "Student")]
    else:
        if benutzertyp in ("Gäste", "Gast", "t_Gast"):
            models_to_query = [(TGast, "Gast")]
        elif benutzertyp in ("Studenten", "Student", "t_studenten", "t_Studenten"):
            models_to_query = [(TStudenten, "Student")]
        elif benutzertyp in ("Mitarbeiter", "paxton_view_web", "Paxton"):
            models_to_query = [(PaxtonViewWeb, "Mitarbeiter")]
        else:
            models_to_query = [(PaxtonViewWeb, "Mitarbeiter"), (TGast, "Gast"), (TStudenten, "Student")]

    for model, quelle in models_to_query:
        qs = model.objects.all()
        qs = _apply_filters_to_queryset(model, qs, filters)
        qs = qs[:500000]  # Begrenze pro Modell

        for row in qs:
            if quelle == "Gast":
                user_data = {
                    "quelle": "Gast",
                    "employeenumber": "",
                    "kartennummer": getattr(row, "kartennummer", "") or "",
                    "name_full": f"{getattr(row, 'givenname', '')} {getattr(row, 'sn', '')}".strip(),
                    "active": getattr(row, "karte_active", None) or getattr(row, "active", None) or False,
                    "abteilung": getattr(row, "einrichtung", "") or getattr(row, "abteilung", ""),
                    "verlorene_karte": getattr(row, "verlorene_karte", False),
                    "funktion": getattr(row, "funktion", ""),
                    "gelesen_am": getattr(row, "gelesen_am", None),
                    "createtime": getattr(row, "createtime", None),
                    "benutzergruppe_id": getattr(row, "benutzergruppe", ""),
                    "berechtigungsgruppe_id": getattr(row, "berechtigungsgruppe", ""),
                    "schrank": getattr(row, "schrank_nr_alt", "") or getattr(row, "schrank", ""),
                }
            elif quelle == "Student":
                user_data = {
                    "quelle": "Student",
                    "employeenumber": getattr(row, "employeenumber", "") or "",
                    "kartennummer": getattr(row, "kartennummer", "") or "",
                    "name_full": f"{getattr(row, 'givenname', '')} {getattr(row, 'sn', '')}".strip(),
                    "active": getattr(row, "karte_active", None) or getattr(row, "active", None) or False,
                    "abteilung": getattr(row, "einrichtung", "") or getattr(row, "abteilung", ""),
                    "verlorene_karte": getattr(row, "verlorene_karte", False),
                    "funktion": getattr(row, "funktion", ""),
                    "gelesen_am": getattr(row, "gelesen_am", None),
                    "createtime": getattr(row, "createtime", None),
                    "benutzergruppe_id": getattr(row, "benutzergruppe", ""),
                    "berechtigungsgruppe_id": getattr(row, "berechtigungsgruppe", ""),
                    "schrank": getattr(row, "schrank", "") or "",
                }
            else:  # Mitarbeiter (PaxtonViewWeb)
                if getattr(row, "austritt", None):
                    vertragsende = getattr(row, "austritt")
                elif getattr(row, "endofcontract", None):
                    vertragsende = getattr(row, "endofcontract")
                else:
                    vertragsende = None

                user_data = {
                    "quelle": "Mitarbeiter",
                    "employeenumber": getattr(row, "employeenumber", "") or "",
                    "kartennummer": getattr(row, "kartennummer", "") or "",
                    "name_full": f"{getattr(row, 'givenname', '')} {getattr(row, 'sn', '')}".strip(),
                    "active": getattr(row, "karte_active", None) or getattr(row, "active", None) or False,
                    "abteilung": getattr(row, "mstbroe", "") or getattr(row, "einrichtung", ""),
                    "funktion": getattr(row, "dvh_text", "") or getattr(row, "funktion", ""),
                    "verlorene_karte": getattr(row, "verlorene_karte", False),
                    "vertragsende": vertragsende,
                    "gelesen_am": getattr(row, "gelesen_am", None),
                    "createtime": getattr(row, "createtime", None),
                    "benutzergruppe_id": getattr(row, "benutzergruppe", ""),
                    "berechtigungsgruppe_id": getattr(row, "berechtigungsgruppe", ""),
                    "schrank": getattr(row, "schrank", "") or "",
                }

            # Datumsformatierung
            if user_data.get("gelesen_am"):
                try:
                    user_data["gelesen_am"] = user_data["gelesen_am"].strftime("%Y-%m-%d %H:%M")
                except Exception:
                    user_data["gelesen_am"] = str(user_data["gelesen_am"])
            else:
                user_data["gelesen_am"] = ""

            if user_data.get("createtime"):
                try:
                    user_data["createtime"] = user_data["createtime"].strftime("%Y-%m-%d %H:%M")
                except Exception:
                    user_data["createtime"] = str(user_data["createtime"])
            else:
                user_data["createtime"] = ""

            if user_data.get("vertragsende"):
                try:
                    user_data["vertragsende"] = user_data["vertragsende"].strftime("%Y-%m-%d")
                except Exception:
                    user_data["vertragsende"] = str(user_data["vertragsende"])
            else:
                user_data.setdefault("vertragsende", "")

            benutzer_liste.append(clean_none(user_data))

    # Sortierung
    if not benutzer_liste:
        return [], 0

    if sort_by not in benutzer_liste[0]:
        sort_by = default_sort if default_sort in benutzer_liste[0] else list(benutzer_liste[0].keys())[0]

    try:
        reverse = True if str(order).upper() == "DESC" else False
        def _normalize_sort_value(v):
            if v is None or v == "":
                return ""
            if isinstance(v, str):
                for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(v, fmt)
                    except Exception:
                        pass
                s = v.replace(" ", "").lstrip("0")
                if s.isdigit():
                    return int(s)
                return v.lower()
            if isinstance(v, bool):
                return 1 if v else 0
            return v
        benutzer_liste.sort(key=lambda item: _normalize_sort_value(item.get(sort_by)), reverse=reverse)
    except Exception:
        pass

    # Pagination: 30 pro Seite (fix)
# Pagination: nutze den übergebenen per_page-Parameter (fallback 30)
    try:
        page = int(page)
    except Exception:
        page = 1
    try:
        per_page = int(per_page)
    except Exception:
        per_page = 30
    if page < 1:
        page = 1

    total_count = len(benutzer_liste)
    offset = (page - 1) * per_page
    paged = benutzer_liste[offset: offset + per_page]
    return paged, total_count

def get_user_status(row):
    """
    Liefert (label, css_class) z.B. ("Aktiv","active").
    Akzeptiert dict (aus get_benutzer_liste) oder Model-Instanz.
    """
    if isinstance(row, dict):
        active = row.get("active", None)
        verlorene_karte = row.get("verlorene_karte", None)
    else:
        active = None
        for f in ('active', 'karte_active', 'karteactive', 'Active'):
            val = getattr(row, f, None)
            if val not in (None, ""):
                active = val
                break
        verlorene_karte = None
        for f in ('verlorene_karte', 'verlorenekarte', 'lost', 'lost_card'):
            val = getattr(row, f, None)
            if val not in (None, ""):
                verlorene_karte = val
                break

    if str(verlorene_karte).lower() in ("1", "true", "t", "yes"):
        return "Verlorene Karte", "lost"
    if str(active).lower() in ("1", "true", "t", "yes"):
        return "Aktiv", "active"
    if str(active).lower() in ("0", "false", "f", "no"):
        return "Inaktiv", "inactive"
    return "Unbekannt", "unknown"