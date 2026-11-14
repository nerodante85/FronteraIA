"""Interfaz del módulo DFI en la calculadora (AppTest, sin red real)."""
import pytest

from conftest import cargar_funciones, metricas

F = cargar_funciones("lineas_liquidacion", "fila_csv", "texto_para_csv", "num")


def _datos(**extra):
  from datetime import datetime
  d = dict(
      codigo="FIQ-20261113-ABC123", emision=datetime(2026, 11, 13, 9, 5), producto="Camisetas",
      partida="6109.10.00.00", unidades=1000, fob_usd=10000.0, flete_usd=1200.0, seguro_usd=150.0,
      cif_usd=11350.0, cif_cop=45400000.0, trm=4000.0, origen_trm="TRM oficial",
      pct_arancel=10.0, pct_iva=19.0, arancel_cop=4540000.0, iva_cop=9488600.0,
      total_tributos_cop=14028600.0, agenciamiento_cop=450000.0, bodegaje_cop=300000.0,
      transporte_local_cop=800000.0, otros_gastos_cop=200000.0, gastos_locales_cop=1750000.0,
      costo_total_landed_cop=61178600.0, costo_unitario_cop=61178.6, pct_margen=30.0,
      precio_sugerido_unitario_cop=87398.0, estado_aranceles="Validados")
  d.update(extra)
  return d


def test_gratuito_ve_el_asistente_de_incoterm(nueva_app):
  at = nueva_app()
  assert not at.exception
  assert any("INCOTERM" in e.label for e in at.expander)


def test_asistente_no_cambia_ninguna_cifra(nueva_app):
  at = nueva_app()
  at.selectbox(key="incoterm_acordado").set_value("CIF").run()
  assert not at.exception
  assert metricas(at)[0] == "61.178.600"


def test_csv_y_liquidacion_incluyen_el_incoterm():
  d = _datos(incoterm="FOB")
  assert F["fila_csv"](d)["INCOTERM"] == "FOB"
  assert ("INCOTERM acordado", "FOB", False) in F["lineas_liquidacion"](d)


def test_sin_incoterm_la_liquidacion_no_cambia():
  assert all(c != "INCOTERM acordado" for c, _, _ in F["lineas_liquidacion"](_datos()))
  assert F["fila_csv"](_datos())["INCOTERM"] == ""


# ---------- costo de capital (Pro) ----------
def _landed_esperado(capital=0.0):
  return F["num"](61_178_600 + capital)


def test_gratuito_ve_el_teaser_de_capital_y_el_landed_no_cambia(nueva_app):
  at = nueva_app()
  assert any("costo de capital" in i.value.lower() for i in at.info)
  assert len(at.checkbox) == 0  # ninguna casilla de capital para el plan gratuito
  assert metricas(at)[0] == "61.178.600"


def test_pro_con_capital_apagado_no_cambia_el_landed(app_pro):
  assert metricas(app_pro)[0] == "61.178.600"


def test_pro_con_capital_suma_al_landed(app_pro):
  import dfi
  app_pro.checkbox(key="capital_activo").set_value(True).run()
  app_pro.number_input(key="capital_tasa").set_value(12.0).run()
  app_pro.number_input(key="capital_dias").set_value(30).run()
  assert not app_pro.exception
  capital = dfi.costo_capital(61_178_600, 12.0, 30)
  assert metricas(app_pro)[0] == _landed_esperado(capital)


def test_pro_con_tasa_cero_el_landed_no_cambia(app_pro):
  app_pro.checkbox(key="capital_activo").set_value(True).run()
  app_pro.number_input(key="capital_tasa").set_value(0.0).run()
  assert not app_pro.exception
  assert metricas(app_pro)[0] == "61.178.600"


def test_csv_y_liquidacion_incluyen_el_capital():
  d = _datos(costo_capital_cop=603405.0, tasa_capital_pct=12.0, dias_capital=30)
  fila = F["fila_csv"](d)
  assert fila["Costo capital COP"] == 603405.0
  assert fila["Tasa capital %"] == 12.0 and fila["Dias capital"] == 30
  assert any(c == "Costo de capital del inventario" for c, _, _ in F["lineas_liquidacion"](d))


def test_sin_capital_no_hay_linea_ni_cifras_en_el_csv():
  assert all("capital" not in c.lower() for c, _, _ in F["lineas_liquidacion"](_datos()))
  fila = F["fila_csv"](_datos())
  assert fila["Costo capital COP"] == 0
