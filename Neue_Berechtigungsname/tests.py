# from django.test import TestCase

# from django.test import RequestFactory
# from django.contrib.auth.models import AnonymousUser
# from django.contrib.messages.storage.fallback import FallbackStorage
# from django.http import HttpResponseRedirect
# import json
# import pytest

# from Neue_Berechtigungsname import views as nb_views


# def _attach_messages(request):
#     # minimal session + messages so messages.*() im View funktionieren
#     setattr(request, "session", {})
#     messages_storage = FallbackStorage(request)
#     setattr(request, "_messages", messages_storage)
#     return messages_storage


# @pytest.mark.unit
# def test_get_without_token_fetch_not_called(monkeypatch):
#     rf = RequestFactory()
#     req = rf.get("/neue")
#     req.user = AnonymousUser()

#     # token is None -> fetch_all_access_levels should not be called
#     monkeypatch.setattr(nb_views, "get_token", lambda: None)

#     called = {"fetch": False}

#     def _fetch_fail():
#         called["fetch"] = True
#         raise AssertionError("fetch_all_access_levels should not be called when no token")

#     monkeypatch.setattr(nb_views, "fetch_all_access_levels", _fetch_fail)

#     resp = nb_views.Neue_Berechtigungsname(req)
#     assert resp.status_code == 200
#     assert called["fetch"] is False


# @pytest.mark.unit
# def test_post_missing_fields_sets_error(monkeypatch):
#     rf = RequestFactory()
#     req = rf.post("/neue", data={})
#     req.user = AnonymousUser()
#     messages_storage = _attach_messages(req)

#     monkeypatch.setattr(nb_views, "get_token", lambda: "tok")
#     # provide at least one access level so name lookup path can run
#     monkeypatch.setattr(nb_views, "fetch_all_access_levels", lambda: [{"id": "1", "name": "Admin"}])

#     # ensure update_access_level is not called in this scenario
#     monkeypatch.setattr(nb_views, "update_access_level", lambda *a, **k: (_ for _ in ()).throw(AssertionError("update_access_level should not be called")))

#     resp = nb_views.Neue_Berechtigungsname(req)

#     # No redirect — view should re-render and set an error message
#     assert resp.status_code == 200
#     msgs = [m.message for m in list(messages_storage)]
#     assert any("Bitte wählen" in m for m in msgs)


# @pytest.mark.unit
# def test_post_success_with_id_redirects(monkeypatch):
#     rf = RequestFactory()
#     req = rf.post("/neue", data={"access_level_id": "42", "newAccessLevel": "NeuerName"})
#     req.user = AnonymousUser()
#     messages_storage = _attach_messages(req)

#     monkeypatch.setattr(nb_views, "get_token", lambda: "tok")
#     monkeypatch.setattr(nb_views, "fetch_all_access_levels", lambda: [{"id": "42", "name": "OldName"}])

#     captured = {}

#     def _update(level_id, new_name, token):
#         captured["level_id"] = level_id
#         captured["new_name"] = new_name
#         captured["token"] = token
#         return True, 200, {}

#     monkeypatch.setattr(nb_views, "update_access_level", _update)
#     # avoid reverse/URL resolution problems by replacing redirect used in the module
#     monkeypatch.setattr(nb_views, "redirect", lambda name: HttpResponseRedirect("/Neue_Berechtigungsname/"))

#     resp = nb_views.Neue_Berechtigungsname(req)

#     assert resp.status_code in (302, 303)
#     assert captured["level_id"] == 42  # converted to int
#     assert captured["new_name"] == "NeuerName"
#     assert captured["token"] == "tok"


# @pytest.mark.unit
# def test_post_success_with_name_matching_redirects(monkeypatch):
#     rf = RequestFactory()
#     # user submits name via datalist/input, not the hidden id
#     req = rf.post("/neue", data={"accessLevelInput": "admin", "newAccessLevel": "NeuerName"})
#     req.user = AnonymousUser()
#     messages_storage = _attach_messages(req)

#     monkeypatch.setattr(nb_views, "get_token", lambda: "tok")
#     # access_levels contain a matching name (case-insensitive)
#     monkeypatch.setattr(nb_views, "fetch_all_access_levels", lambda: [{"id": "7", "name": "Admin"}])

#     called = {}

#     def _update(level_id, new_name, token):
#         called["level_id"] = level_id
#         called["new_name"] = new_name
#         called["token"] = token
#         return True, 200, {}

#     monkeypatch.setattr(nb_views, "update_access_level", _update)
#     monkeypatch.setattr(nb_views, "redirect", lambda name: HttpResponseRedirect("/Neue_Berechtigungsname/"))

#     resp = nb_views.Neue_Berechtigungsname(req)

#     assert resp.status_code in (302, 303)
#     assert called["level_id"] == 7
#     assert called["new_name"] == "NeuerName"


# @pytest.mark.unit
# def test_api_accesslevels_filter(monkeypatch):
#     rf = RequestFactory()
#     req = rf.get("/api/accesslevels", {"name": "adm"})
#     req.user = AnonymousUser()

#     monkeypatch.setattr(nb_views, "get_token", lambda: "tok")
#     monkeypatch.setattr(nb_views, "fetch_all_access_levels", lambda: [
#         {"id": 1, "name": "Admin"},
#         {"id": 2, "name": "User"},
#         {"id": 3, "name": "ReadOnlyAdmin"},
#     ])

#     resp = nb_views.api_accesslevels(req)
#     assert resp.status_code == 200
#     # JsonResponse content is bytes — decode and load
#     payload = json.loads(resp.content.decode())
#     # only entries that contain "adm" (case-insensitive) should be present
#     names = [p.get("name") for p in payload]
#     assert "Admin" in names
#     assert "ReadOnlyAdmin" in names
#     assert "User" not in names