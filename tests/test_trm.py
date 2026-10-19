"""Consulta de la TRM: éxito, falla, caché y forma de la consulta."""
import time

import requests
import streamlit as st

from conftest import respuesta_trm


def numero_lateral(at):
  return next(n for n in at.sidebar.number_input if n.label.startswith("TRM"))


def test_trm_oficial_se_muestra_con_fecha(monkeypatch, nueva_app):
  monkeypatch.setattr(requests, "get", lambda *a, **k: respuesta_trm(3174.67, "2026-10-17T00:00:00.000"))
  at = nueva_app()
  assert numero_lateral(at).value == 3174.67
  assert any("2026-10-17" in c.value for c in at.sidebar.caption)
  assert not at.sidebar.warning


def test_si_falla_se_muestra_advertencia_y_respaldo(monkeypatch, nueva_app):
  def falla(*a, **k):
    raise requests.ConnectionError("sin red")

  monkeypatch.setattr(requests, "get", falla)
  at = nueva_app()
  assert not at.exception
  assert numero_lateral(at).value == 4000.0
  assert any("No se pudo consultar la TRM oficial" in w.value for w in at.sidebar.warning)


def test_un_fallo_no_queda_en_cache_y_se_reintenta_pasada_la_espera(monkeypatch, nueva_app):
  reloj = {"t": 1000.0}
  monkeypatch.setattr(time, "monotonic", lambda: reloj["t"])

  def falla(*a, **k):
    raise requests.ConnectionError("sin red")

  monkeypatch.setattr(requests, "get", falla)
  nueva_app()
  monkeypatch.setattr(requests, "get", lambda *a, **k: respuesta_trm(3174.67))
  reloj["t"] += 61  # pasada la espera, la TRM oficial vuelve a consultarse
  at = nueva_app()
  assert numero_lateral(at).value == 3174.67
  assert not at.sidebar.warning


def test_con_la_fuente_caida_no_se_reintenta_en_cada_interaccion(monkeypatch, nueva_app):
  reloj = {"t": 1000.0}
  monkeypatch.setattr(time, "monotonic", lambda: reloj["t"])
  llamadas = []

  def falla(*a, **k):
    llamadas.append(1)
    raise requests.ConnectionError("sin red")

  monkeypatch.setattr(requests, "get", falla)
  at = nueva_app()
  at.sidebar.number_input[0].set_value(4100.0).run()
  at.sidebar.number_input[0].set_value(4200.0).run()
  assert len(llamadas) == 1  # un solo intento dentro de los 60 s de espera
  assert any("No se pudo consultar la TRM oficial" in w.value for w in at.sidebar.warning)
  reloj["t"] += 61
  at.sidebar.number_input[0].set_value(4300.0).run()
  assert len(llamadas) == 2


def test_valor_fuera_de_rango_se_rechaza(monkeypatch, nueva_app):
  monkeypatch.setattr(requests, "get", lambda *a, **k: respuesta_trm(99999.0))
  at = nueva_app()
  assert any("No se pudo consultar la TRM oficial" in w.value for w in at.sidebar.warning)


def test_forma_de_la_consulta(monkeypatch, nueva_app):
  llamadas = []

  def captura(url, params=None, timeout=None):
    llamadas.append((url, params, timeout))
    return respuesta_trm()

  monkeypatch.setattr(requests, "get", captura)
  nueva_app()
  url, params, timeout = llamadas[0]
  assert "32sa-8pi3" in url and "\\" not in url  # dataset oficial de la TRM
  assert params["$order"] == "vigenciadesde DESC"
  assert params["$where"].startswith("vigenciadesde <= '")
  assert params["$limit"] == 1
  assert timeout is not None
