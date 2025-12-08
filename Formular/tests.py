
from django.test import RequestFactory
# (Nur die geänderten/erweiterten Test-Abschnitte)
import pytest
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage

from Formular import views as formular_views

@pytest.mark.unit
def test_normalize_token_value_unit():
    assert formular_views._normalize_token_value(None) is None
    # Die Implementierung schneidet die letzten 8 Zeichen ab (nach Entfernen von "0#")
    assert formular_views._normalize_token_value("0#0000123456") == "00123456"
    assert formular_views._normalize_token_value("abc") == "abc"
    assert formular_views._normalize_token_value(" 0#ABCDEF ") == "ABCDEF"

@pytest.mark.unit
def test__normalize_id_list_various():
    assert formular_views._normalize_id_list(None) == []
    assert formular_views._normalize_id_list("12, 34;56") == ["12", "34", "56"]
    assert formular_views._normalize_id_list("A B,C;D|E") == ["A", "B", "C", "D", "E"]
    assert formular_views._normalize_id_list([1, "2", None, "  "]) == ["1", "2"]

@pytest.mark.unit
def test__map_ids_to_names_basic():
    mapping = {"1": "Sales", "2": "IT", "3": "HR"}
    assert formular_views._map_ids_to_names(["1", "3"], mapping) == ["Sales", "HR"]
    assert formular_views._map_ids_to_names(["1", "99"], mapping) == ["Sales"]
    assert formular_views._map_ids_to_names([2], mapping) == ["IT"]

@pytest.mark.unit
def test_row_to_dict_with_object_and_typ():
    # Create a dummy object with _meta.get_fields() returning objects with .name
    class Field:
        def __init__(self, name):
            self.name = name

    # Make _meta.get_fields a callable that takes no params for simplicity
    class MMeta:
        @staticmethod
        def get_fields():
            return [Field("a"), Field("b"), Field("callable_attr")]

    class Dummy:
        _meta = MMeta()
        def __init__(self):
            self.a = 1
            self.b = "two"
        def callable_attr(self):
            return "call"

    d = Dummy()
    res = formular_views.row_to_dict(d, typ="Mitarbeiter")
    assert isinstance(res, dict)
    assert res["a"] == 1
    assert res["b"] == "two"
    assert res["quelle"] == "Mitarbeiter"
    assert "callable_attr" not in res

@pytest.mark.unit
def test_restore_card_missing_kartennummer_redirects(monkeypatch):
    # Patch reverse to avoid NoReverseMatch
    monkeypatch.setattr(formular_views, "reverse", lambda name: "/formular/")
    rf = RequestFactory()
    request = rf.post("/restore", data={})
    request.user = AnonymousUser()
    # Attach a messages storage to the request so messages.*() works
    setattr(request, "session", {})  # messages middleware may expect session; keep minimal
    messages_storage = FallbackStorage(request)
    setattr(request, "_messages", messages_storage)

    response = formular_views.restore_card(request)
    assert response.status_code in (302, 303)
    assert response["Location"].startswith("/formular")