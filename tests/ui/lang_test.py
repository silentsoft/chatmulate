import locale
from chatmulate.ui import lang


def test_get_system_language_without_underscore_valid(monkeypatch):
    monkeypatch.setattr(locale, 'getdefaultlocale', lambda: ("ko", "UTF-8"))
    assert lang.get_system_language() == "ko"


def test_get_system_language_with_underscore_valid(monkeypatch):
    monkeypatch.setattr(locale, 'getdefaultlocale', lambda: ("ko_KR", "UTF-8"))
    assert lang.get_system_language() == "ko"


def test_get_system_language_invalid_language(monkeypatch):
    monkeypatch.setattr(locale, 'getdefaultlocale', lambda: ("xxx", "UTF-8"))
    assert lang.get_system_language() == "en"


def test_get_system_language_none(monkeypatch):
    monkeypatch.setattr(locale, 'getdefaultlocale', lambda: (None, None))
    assert lang.get_system_language() == "en"
