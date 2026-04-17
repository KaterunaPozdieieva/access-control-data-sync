import os
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib import messages
from Tabelle.Paxton_all import update_access_level
from synchronisation.Paxton_funk import fetch_all_access_levels, get_token

logger = logging.getLogger('paxton')

@require_http_methods(["GET", "POST"])
def Neue_Berechtigungsname(request):
    token = get_token()
    access_levels = fetch_all_access_levels() if token else []
    benutzerabbrechen = [{'title': "Abbrechen und zurück", 'url_name': 'algemeineTabelle'}]

    if request.method == "POST":
        level_id = request.POST.get("access_level_id")
        selected_name = request.POST.get("accessLevelInput", "").strip()
        new_name = request.POST.get("newAccessLevel", "").strip()

        logger.debug("POST received: access_level_id=%s, accessLevelInput=%s, newAccessLevel=%s", level_id, selected_name, new_name)

        if not level_id and selected_name:
            matched = next((lvl for lvl in access_levels
                            if str(lvl.get("name", "")).strip().lower() == selected_name.lower()), None)
            if matched:
                level_id = matched.get("id")
                logger.debug("Matched access level id %s for name %s", level_id, selected_name)

        if not level_id or not new_name:
            messages.error(request, "Bitte wählen Sie eine Berechtigungsgruppe und geben einen neuen Namen ein.")
            logger.info("Validation failed: missing level_id or new_name (level_id=%r, new_name=%r)", level_id, new_name)
        else:
            try:
                try:
                    level_id_int = int(level_id)
                except Exception:
                    level_id_int = level_id

                ok, status, data = update_access_level(level_id_int, new_name, token)
                if ok:
                    messages.success(request, "Berechtigungsgruppe erfolgreich umbenannt.")
                    logger.info("Berechtigungsgruppe umbenannt: ID=%s | Alter Name='%s' | Neuer Name='%s' | Status=%s", level_id_int, selected_name, new_name, status)
                    return redirect("Neue_Berechtigungsname")
                else:
                    if status == 409 or (isinstance(data, str) and "already exists" in str(data).lower()):
                        messages.error(request, "Es existiert bereits eine Berechtigungsgruppe mit diesem Namen.")
                        logger.warning("Rename conflict: level=%s new_name=%s status=%s data=%s", level_id_int, new_name, status, data)
                    else:
                        messages.error(request, f"Fehler beim Speichern (Status {status}): {data}")
                        logger.error("Save error: level=%s new_name=%s status=%s data=%s", level_id_int, new_name, status, data)
            except Exception as e:
                messages.error(request, f"Unbekannter Fehler: {e}")
                logger.exception("Unexpected exception while renaming access level (level=%s new_name=%s)", level_id, new_name)

    return render(request, "Neue_Berechtigungsname/Neue_Berechtigungsname.html", {
        "access_levels": access_levels,
        "abbrechen": benutzerabbrechen
    })