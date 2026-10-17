"""Licencias por cliente: módulo `licencias.py` y su integración con la app (sin red real)."""
import re

import pytest
import requests

import licencias

URL = "https://proyecto.supabase.co"
LLAVE = "llave-de-servicio-de-prueba"


class Resp:
  def __init__(self, datos, status=200):
    self._datos, self.status_code = datos, status

  def raise_for_status(self):
    if self.status_code >= 400:
      raise requests.HTTPError(str(self.status_code))

  def json(self):
    return self._datos


# ---------- módulo ----------
def test_clave_generada_tiene_formato_y_no_repite():
  claves = {licencias.generar_clave() for _ in range(50)}
  assert len(claves) == 50
  assert all(re.fullmatch(r"FIQ-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", c) for c in claves)
  assert not any(set("01OI") & set(c.replace("FIQ-", "").replace("-", "")) for c in claves)


def test_hash_ignora_mayusculas_y_espacios():
  assert licencias.hash_clave(" fiq-abcd-efgh-jklm ") == licencias.hash_clave("FIQ-ABCD-EFGH-JKLM")
  assert len(licencias.hash_clave("x")) == 64


def test_validar_envia_solo_el_hash_y_la_llave_de_servicio(monkeypatch):
  capturado = {}

  def falso(url, headers, json, timeout):
    capturado.update(url=url, headers=headers, json=json, timeout=timeout)
    return Resp({"valida": True, "nivel": "pro"})

  monkeypatch.setattr(requests, "post", falso)
  r = licencias.validar_licencia("FIQ-AAAA-BBBB-CCCC", "sesion1", URL + "/", LLAVE)
  assert r["valida"] is True
  assert capturado["url"] == URL + "/rest/v1/rpc/validar_licencia"
  assert capturado["headers"]["apikey"] == LLAVE
  assert "FIQ-AAAA" not in str(capturado["json"])
  assert capturado["json"] == {"p_hash": licencias.hash_clave("FIQ-AAAA-BBBB-CCCC"), "p_sesion": "sesion1"}


def test_clave_secret_nueva_va_solo_en_apikey(monkeypatch):
  capturado = {}

  def falso(url, headers, json, timeout):
    capturado.update(headers=headers)
    return Resp({"valida": True})

  monkeypatch.setattr(requests, "post", falso)
  licencias.validar_licencia("x", "s", URL, "sb_secret_abc")
  assert capturado["headers"]["apikey"] == "sb_secret_abc"
  assert "Authorization" not in capturado["headers"]


def test_validar_lanza_si_el_servicio_falla(monkeypatch):
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({}, 500))
  with pytest.raises(requests.HTTPError):
    licencias.validar_licencia("x", "s", URL, LLAVE)


def test_validar_rechaza_respuesta_inesperada(monkeypatch):
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({"otra": 1}))
  with pytest.raises(ValueError):
    licencias.validar_licencia("x", "s", URL, LLAVE)


# ---------- integración con la app ----------
def _abrir_pro(at, clave):
  at.sidebar.radio[0].set_value("Pro / Premium").run()
  at.sidebar.text_input[0].set_value(clave).run()
  return at


@pytest.fixture
def con_supabase(monkeypatch):
  monkeypatch.setenv("SUPABASE_URL", URL)
  monkeypatch.setenv("SUPABASE_SERVICE_KEY", LLAVE)


def test_licencia_valida_activa_pro(monkeypatch, con_supabase, nueva_app):
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({"valida": True, "nivel": "pro"}))
  at = _abrir_pro(nueva_app(), "FIQ-AAAA-BBBB-CCCC")
  assert at.sidebar.success
  assert len(at.get("download_button")) == 2


@pytest.mark.parametrize(
    "motivo,texto",
    [("no_encontrada", "no válida"), ("revocada", "revocada"), ("vencida", "venció"),
     ("sin_puestos", "máximo de usuarios")],
)
def test_licencia_rechazada_muestra_el_motivo(monkeypatch, con_supabase, nueva_app, motivo, texto):
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({"valida": False, "motivo": motivo}))
  at = _abrir_pro(nueva_app(), "FIQ-AAAA-BBBB-CCCC")
  assert not at.sidebar.success
  assert any(texto in w.value for w in at.sidebar.warning)
  assert len(at.get("download_button")) == 1


def test_si_supabase_falla_no_hay_pro_y_el_error_no_se_cachea(monkeypatch, con_supabase, nueva_app):
  llamadas = []

  def falla_y_luego_responde(*a, **k):
    llamadas.append(1)
    return Resp({}, 503) if len(llamadas) == 1 else Resp({"valida": True, "nivel": "pro"})

  monkeypatch.setattr(requests, "post", falla_y_luego_responde)
  at = _abrir_pro(nueva_app(), "FIQ-AAAA-BBBB-CCCC")
  assert not at.sidebar.success
  assert any("No pudimos verificar" in w.value for w in at.sidebar.warning)
  at.sidebar.text_input[0].set_value("FIQ-AAAA-BBBB-CCCC ").run()  # nuevo intento
  assert len(llamadas) == 2 and at.sidebar.success


def test_con_supabase_la_clave_unica_ya_no_vale(monkeypatch, con_supabase, nueva_app):
  monkeypatch.setenv("PRO_LICENSE_KEY", "clave-antigua")
  monkeypatch.setattr(requests, "post", lambda *a, **k: Resp({"valida": False, "motivo": "no_encontrada"}))
  at = _abrir_pro(nueva_app(), "clave-antigua")
  assert not at.sidebar.success


def test_sin_supabase_sigue_funcionando_la_clave_unica(monkeypatch, nueva_app):
  monkeypatch.setenv("PRO_LICENSE_KEY", "clave-de-prueba")
  at = _abrir_pro(nueva_app(), "clave-de-prueba")
  assert at.sidebar.success
