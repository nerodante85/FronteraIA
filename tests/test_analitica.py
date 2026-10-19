"""Medición de uso anónima: lista cerrada de eventos, sin datos personales y a prueba de fallos."""
import analitica
import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP_PATH

CONFIG = ("https://ejemplo.supabase.co", "sb_secret_prueba")


class Envios:
  def __init__(self):
    self.llamadas = []

  def post(self, url, headers=None, json=None, timeout=None):
    self.llamadas.append({"url": url, "headers": headers, "json": json, "timeout": timeout})


@pytest.fixture
def envios(monkeypatch):
  e = Envios()
  monkeypatch.setattr(analitica.requests, "post", e.post)
  return e


def test_registra_un_evento_valido_con_timeout_corto(envios):
  assert analitica.registrar("descarga_csv", "abc12345", CONFIG, en_segundo_plano=False)
  c = envios.llamadas[0]
  assert c["url"].endswith("/rest/v1/rpc/registrar_evento")
  assert c["json"] == {"p_sesion": "abc12345", "p_evento": "descarga_csv", "p_dato": None}
  assert c["timeout"] <= 5
  assert "Authorization" not in c["headers"]  # llaves sb_secret_ van solo en apikey


def test_ignora_eventos_fuera_de_la_lista_o_sin_configuracion(envios):
  assert not analitica.registrar("dato_personal", "abc12345", CONFIG, en_segundo_plano=False)
  assert not analitica.registrar("descarga_csv", "abc12345", None, en_segundo_plano=False)
  assert not analitica.registrar("descarga_csv", "", CONFIG, en_segundo_plano=False)
  assert envios.llamadas == []


def test_recorta_el_dato_y_nunca_lanza_si_el_servicio_falla(monkeypatch):
  recibido = {}

  def falla(url, headers=None, json=None, timeout=None):
    recibido.update(json)
    raise ConnectionError("sin red")

  monkeypatch.setattr(analitica.requests, "post", falla)
  assert analitica.registrar("partida_elegida", "abc12345", CONFIG, "x" * 100, en_segundo_plano=False)
  assert len(recibido["p_dato"]) == 40


def test_la_app_registra_visita_a_la_calculadora_una_vez_por_sesion(monkeypatch):
  eventos = []
  monkeypatch.setattr(analitica, "registrar", lambda ev, ses, cfg, dato=None, **k: eventos.append((ev, dato)))
  monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")
  monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sb_secret_prueba")
  at = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
  assert not at.exception
  at.selectbox[0].set_value("Confecciones / Camisetas de Algodón").run()
  at.number_input[0].set_value(2000.0).run()  # una interacción más: no debe duplicar
  assert eventos.count(("calculadora_vista", None)) == 1
  assert ("partida_elegida", "6109.10.00.00") in eventos
  assert ("multimercancia_teaser", None) in eventos
  # nada de lo registrado contiene montos ni nombres: solo eventos de la lista cerrada
  assert all(ev in analitica.EVENTOS for ev, _ in eventos)


def test_la_app_no_falla_ni_llama_a_la_red_sin_configuracion(envios):
  at = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
  assert not at.exception
  assert envios.llamadas == []
