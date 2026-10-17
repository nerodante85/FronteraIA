"""La landing se muestra por defecto y enlaza a la calculadora."""
from streamlit.testing.v1 import AppTest

from conftest import APP_PATH


def _landing(monkeypatch):
  monkeypatch.delenv("FIQ_PAGINA_INICIAL", raising=False)
  return AppTest.from_file(str(APP_PATH), default_timeout=60).run()


def test_la_landing_es_la_pagina_por_defecto(monkeypatch):
  at = _landing(monkeypatch)
  assert not at.exception
  assert len(at.number_input) == 0  # la calculadora no se ejecuta en la landing
  texto = " ".join(str(e.value) for e in at.get("html"))
  assert "Cuánto te cuesta realmente la mercancía puesta en Cúcuta" in texto
  assert "Starter" in texto and "Pro Fronterizo" in texto and "Agencia / Corporativo" in texto


def test_la_demo_usa_la_misma_cadena_de_calculo(monkeypatch):
  at = _landing(monkeypatch)
  assert not at.exception
  # TRM simulada 4.000, FOB 10.000, arancel 10 %: igual que la calculadora (61.178.600)
  texto = " ".join(str(e.value) for e in at.get("html"))
  assert "$ 61.178.600" in texto
