"""Si un redeploy deja en memoria una versión antigua de partidas_validadas, la app debe seguir arrancando."""
import sys
import types

from streamlit.testing.v1 import AppTest

from conftest import APP_PATH


def test_la_app_arranca_con_un_modulo_partidas_validadas_obsoleto():
  original = sys.modules.pop("partidas_validadas", None)
  obsoleto = types.ModuleType("partidas_validadas")
  obsoleto.__file__ = str(APP_PATH.parent / "partidas_validadas.py")
  obsoleto.cargar_validaciones = lambda *a, **k: ({}, [])  # versión vieja: sin catalogo_ampliado
  sys.modules["partidas_validadas"] = obsoleto
  try:
    at = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    assert not at.exception
  finally:
    sys.modules.pop("partidas_validadas", None)
    if original is not None:
      sys.modules["partidas_validadas"] = original
