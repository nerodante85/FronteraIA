"""Tabla NANDINA: aviso de validación pendiente y partidas validadas."""
from streamlit.testing.v1 import AppTest

from conftest import APP_PATH

PARTIDA = "Confecciones / Camisetas de Algodón"
AVISO = "pendientes de validación"


def _app_con_csv(tmp_path, ruta_csv):
  codigo = open(APP_PATH, encoding="utf-8").read()
  modificado = codigo.replace(
      'os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "validacion-nandina.csv")',
      repr(str(ruta_csv)),
  )
  assert modificado != codigo
  ruta = tmp_path / "app_csv.py"
  ruta.write_text(modificado, encoding="utf-8")
  return AppTest.from_file(str(ruta), default_timeout=60).run()


def test_partida_de_la_tabla_sin_validacion_muestra_aviso_de_referencia(tmp_path):
  at = _app_con_csv(tmp_path, tmp_path / "no_existe.csv")
  at.selectbox[0].set_value(PARTIDA).run()
  assert not at.exception
  assert any(AVISO in w.value for w in at.warning)


def test_las_partidas_de_referencia_ya_estan_confirmadas_con_la_dian(nueva_app):
  at = nueva_app()
  at.selectbox[0].set_value(PARTIDA).run()
  assert not at.exception
  assert not any(AVISO in w.value for w in at.warning)
  assert any("DIAN" in c.value for c in at.caption)


def test_se_muestra_el_descargo_de_clasificacion_de_subpartida(nueva_app):
  at = nueva_app()
  at.selectbox[0].set_value(PARTIDA).run()
  assert any("no clasifica mercancías" in c.value for c in at.caption)


def test_calzado_usa_el_arancel_confirmado_por_la_dian(nueva_app):
  at = nueva_app()
  at.selectbox[0].set_value("Calzado con Suela de Caucho / Cuero").run()
  assert next(n for n in at.number_input if n.label == "Arancel (%)").value == 15.0


def test_portatiles_muestra_la_condicion_de_iva_por_uvt(nueva_app):
  at = nueva_app()
  at.selectbox[0].set_value("Computadores Portátiles / Laptops").run()
  assert next(n for n in at.number_input if n.label == "IVA (%)").value == 19.0
  assert any("50 UVT" in i.value for i in at.info)


def test_opcion_personalizada_no_muestra_aviso_de_tabla(nueva_app):
  at = nueva_app()
  assert not any(AVISO in w.value for w in at.warning)


def test_partida_validada_muestra_fuente_vigencia_y_usa_los_valores_validados(tmp_path):
  codigo = open(APP_PATH, encoding="utf-8").read()
  csv = tmp_path / "validacion.csv"
  csv.write_text(
      "producto,subpartida,arancel_app_pct,iva_app_pct,arancel_validado_pct,iva_validado_pct,"
      "condiciones_especiales,fuente_normativa,fecha_vigencia,validado_por,observaciones\n"
      "Camisetas,6109.10.00.00,40,19,15,19,,Arancel de prueba,2026-10-01,Agente Prueba,\n",
      encoding="utf-8",
  )
  modificado = codigo.replace(
      'os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "validacion-nandina.csv")',
      repr(str(csv)),
  )
  assert modificado != codigo
  ruta = tmp_path / "app_validada.py"
  ruta.write_text(modificado, encoding="utf-8")
  at = AppTest.from_file(str(ruta), default_timeout=60).run()
  at.selectbox[0].set_value(PARTIDA).run()
  assert not at.exception
  assert any("Arancel de prueba" in c.value and "2026-10-01" in c.value for c in at.caption)
  assert not any(AVISO in w.value for w in at.warning)
  # El arancel validado (15 %) reemplaza al de referencia (40 %)
  arancel = next(n for n in at.number_input if n.label == "Arancel (%)")
  assert arancel.value == 15.0


def test_todas_las_partidas_tienen_datos_completos(nueva_app):
  at = nueva_app()
  for opcion in at.selectbox[0].options:
    at.selectbox[0].set_value(opcion).run()
    assert not at.exception, opcion


def test_partida_nueva_aparece_en_el_selector_solo_cuando_esta_validada(tmp_path):
  codigo = open(APP_PATH, encoding="utf-8").read()
  cab = ("producto,subpartida,arancel_app_pct,iva_app_pct,arancel_validado_pct,iva_validado_pct,"
         "condiciones_especiales,fuente_normativa,fecha_vigencia,validado_por,observaciones\n")

  def opciones(filas):
    csv = tmp_path / "v.csv"
    csv.write_text(cab + filas, encoding="utf-8")
    ruta = tmp_path / "app_x.py"
    ruta.write_text(codigo.replace(
        'os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "validacion-nandina.csv")',
        repr(str(csv))), encoding="utf-8")
    at = AppTest.from_file(str(ruta), default_timeout=60).run()
    assert not at.exception
    return at, list(at.selectbox[0].options)

  _, sin_validar = opciones("Pantalones de algodón,6203.42.00.00,,,,,,,,,\n")
  assert "Pantalones de algodón" not in sin_validar
  at, validada = opciones("Pantalones de algodón,6203.42.00.00,,,12,19,,Decreto X,2026-10-01,Ana,\n")
  assert "Pantalones de algodón" in validada
  at.selectbox[0].set_value("Pantalones de algodón").run()
  assert not at.exception
  assert next(n for n in at.number_input if n.label == "Arancel (%)").value == 12.0
  assert not any(AVISO in w.value for w in at.warning)
