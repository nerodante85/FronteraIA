"""Tabla NANDINA: aviso de validación pendiente y partidas validadas."""
from streamlit.testing.v1 import AppTest

from conftest import APP_PATH

PARTIDA = "Confecciones / Camisetas de Algodón"
AVISO = "pendientes de validación"


def test_partida_de_la_tabla_muestra_aviso_de_referencia(nueva_app):
  at = nueva_app()
  at.selectbox[0].set_value(PARTIDA).run()
  assert not at.exception
  assert any(AVISO in w.value for w in at.warning)


def test_opcion_personalizada_no_muestra_aviso_de_tabla(nueva_app):
  at = nueva_app()
  assert not any(AVISO in w.value for w in at.warning)


def test_partida_validada_muestra_fuente_y_vigencia(tmp_path):
  codigo = open(APP_PATH, encoding="utf-8").read()
  modificado = codigo.replace(
      "PARTIDAS_VALIDADAS = {}",
      'PARTIDAS_VALIDADAS = {"6109.10.00.00": {"fuente": "Arancel de prueba", "vigencia": "2026-10-01"}}',
  )
  assert modificado != codigo
  ruta = tmp_path / "app_validada.py"
  ruta.write_text(modificado, encoding="utf-8")
  at = AppTest.from_file(str(ruta), default_timeout=60).run()
  at.selectbox[0].set_value(PARTIDA).run()
  assert any("Arancel de prueba" in c.value and "2026-10-01" in c.value for c in at.caption)
  assert not any(AVISO in w.value for w in at.warning)


def test_todas_las_partidas_tienen_datos_completos(nueva_app):
  at = nueva_app()
  for opcion in at.selectbox[0].options:
    at.selectbox[0].set_value(opcion).run()
    assert not at.exception, opcion
