"""Niveles de licencia: `pro` y `agencia` (agencia incluye todo lo de pro). Sin red real."""
import pytest
import requests

import analitica
import licencias
from test_licencias_cliente import LLAVE, URL, Resp, _abrir_pro


@pytest.fixture(autouse=True)
def _sin_analitica(monkeypatch):
  monkeypatch.setattr(analitica, "registrar", lambda *a, **k: False)


@pytest.fixture
def con_supabase(monkeypatch):
  monkeypatch.setenv("SUPABASE_URL", URL)
  monkeypatch.setenv("SUPABASE_SERVICE_KEY", LLAVE)


@pytest.mark.parametrize(
    "nivel,requerido,esperado",
    [("agencia", "pro", True), ("pro", "pro", True), ("agencia", "agencia", True),
     ("pro", "agencia", False), (None, "pro", False), ("desconocido", "pro", False)],
)
def test_nivel_permite(nivel, requerido, esperado):
  assert licencias.nivel_permite(nivel, requerido) is esperado


def test_licencia_agencia_guarda_su_nivel(monkeypatch, con_supabase, nueva_app):
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({"valida": True, "nivel": "agencia"}))
  at = _abrir_pro(nueva_app(), "FIQ-AAAA-BBBB-CCCC")
  assert at.session_state["nivel_licencia"] == "agencia"
  assert at.sidebar.success


def test_si_supabase_falla_el_nivel_es_none(monkeypatch, con_supabase, nueva_app):
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({}, 503))
  at = _abrir_pro(nueva_app(), "FIQ-AAAA-BBBB-CCCC")
  assert at.session_state["nivel_licencia"] is None
  assert any("No pudimos verificar" in w.value for w in at.sidebar.warning)


def test_plan_gratuito_no_tiene_nivel(nueva_app):
  at = nueva_app()
  assert at.session_state["nivel_licencia"] is None


def test_clave_de_respaldo_es_nivel_pro(monkeypatch, nueva_app):
  monkeypatch.setenv("PRO_LICENSE_KEY", "clave-de-prueba")
  at = _abrir_pro(nueva_app(), "clave-de-prueba")
  assert at.session_state["nivel_licencia"] == "pro"
