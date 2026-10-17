"""Configuración común de las pruebas.

Las pruebas ejecutan la app con el arnés `AppTest` de Streamlit y NUNCA usan la
red real: `requests.get` se reemplaza por una respuesta simulada de la TRM.
"""
import os
import sys
from pathlib import Path

import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

# Permite probar otra copia de la app (por ejemplo, para pruebas de mutación).
APP_PATH = Path(os.environ.get("APP_PATH") or Path(__file__).resolve().parent.parent / "app.py")

# Para que las copias temporales de la app también encuentren `licencias.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRM_PRUEBA = 4000.0


class RespuestaSimulada:
  def __init__(self, datos):
    self._datos = datos

  def raise_for_status(self):
    pass

  def json(self):
    return self._datos


def respuesta_trm(valor=TRM_PRUEBA, desde="2026-10-16T00:00:00.000"):
  return RespuestaSimulada(
      [{"valor": str(valor), "unidad": "COP", "vigenciadesde": desde,
        "vigenciahasta": "2026-10-19T00:00:00.000"}]
  )


@pytest.fixture(autouse=True)
def entorno_aislado(monkeypatch):
  """Sin red, sin caché compartida y sin clave Pro heredada del entorno."""
  st.cache_data.clear()
  monkeypatch.delenv("PRO_LICENSE_KEY", raising=False)
  monkeypatch.delenv("SUPABASE_URL", raising=False)
  monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
  # Las pruebas de la calculadora arrancan en esa página (la landing es la página por defecto).
  monkeypatch.setenv("FIQ_PAGINA_INICIAL", "calculadora")
  monkeypatch.setattr(requests, "get", lambda *a, **k: respuesta_trm())
  yield
  st.cache_data.clear()


@pytest.fixture
def nueva_app():
  """Fábrica de instancias de la app ya ejecutadas una vez."""

  def _crear(ruta=APP_PATH):
    return AppTest.from_file(str(ruta), default_timeout=60).run()

  return _crear


@pytest.fixture
def app_pro(monkeypatch, nueva_app):
  """App con el plan Pro activado mediante una clave de prueba."""
  monkeypatch.setenv("PRO_LICENSE_KEY", "clave-de-prueba")
  at = nueva_app()
  at.sidebar.radio[0].set_value("Pro / Premium").run()
  at.sidebar.text_input[0].set_value("clave-de-prueba").run()
  return at


def numero(at, etiqueta):
  return next(n for n in at.number_input if n.label == etiqueta)


def metricas(at):
  """Valores de las tarjetas de resultados, en orden."""
  import re

  texto = " ".join(m.value for m in at.markdown)
  return re.findall(r"metric-value[^>]*>\$ ([\d,\.]+)", texto)


def cargar_funciones(*nombres):
  """Carga funciones y constantes puras de app.py sin ejecutar la interfaz.

  Ejecuta los imports del archivo y solo las definiciones pedidas por nombre.
  """
  import ast

  fuente = APP_PATH.read_text(encoding="utf-8")
  arbol = ast.parse(fuente)
  pedidos = set(nombres)
  nodos = []
  for nodo in arbol.body:
    if isinstance(nodo, (ast.Import, ast.ImportFrom)):
      nodos.append(nodo)
    elif isinstance(nodo, ast.FunctionDef) and nodo.name in pedidos and not nodo.decorator_list:
      nodos.append(nodo)
    elif isinstance(nodo, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id in pedidos for t in nodo.targets
    ):
      nodos.append(nodo)
  espacio = {}
  exec(compile(ast.Module(body=nodos, type_ignores=[]), str(APP_PATH), "exec"), espacio)
  faltan = pedidos - set(espacio)
  assert not faltan, f"No se encontraron en app.py: {faltan}"
  return espacio
