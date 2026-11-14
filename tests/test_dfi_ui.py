"""Interfaz del módulo DFI en la calculadora (AppTest, sin red real)."""
import pytest

from conftest import cargar_funciones, metricas

F = cargar_funciones("lineas_liquidacion", "fila_csv", "texto_para_csv", "num", "CAMPOS_CODIGO", "CAMPOS_CODIGO_DFI", "codigo_cotizacion")


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


# ---------- contenedores (Pro) ----------
def _tabla_contenedores(at):
  for df in at.dataframe:
    if "Contenedor" in df.value.columns:
      return df.value
  return None


def test_gratuito_ve_el_teaser_de_contenedores(nueva_app):
  at = nueva_app()
  assert any("contenedores" in i.value.lower() for i in at.info)
  assert _tabla_contenedores(at) is None
  assert metricas(at)[0] == "61.178.600"


def test_pro_calcula_contenedores_para_la_carga(app_pro):
  app_pro.number_input(key="cont_volumen").set_value(30.0).run()
  app_pro.number_input(key="cont_peso").set_value(20000.0).run()
  assert not app_pro.exception
  tabla = _tabla_contenedores(app_pro)
  fila = tabla[tabla["Contenedor"].str.contains("20")].iloc[0]
  assert int(fila["Cantidad"]) == 1
  assert metricas(app_pro)[0] == "61.178.600"  # no altera ninguna cifra de costo


def test_pro_sin_carga_muestra_cero_contenedores(app_pro):
  assert not app_pro.exception
  assert (_tabla_contenedores(app_pro)["Cantidad"].astype(int) == 0).all()


def test_csv_y_liquidacion_incluyen_el_contenedor_elegido():
  d = _datos(contenedor="CONTENEDOR ST 20'", contenedores_cantidad=2)
  fila = F["fila_csv"](d)
  assert fila["Contenedor"] == "CONTENEDOR ST 20'" and fila["Contenedores cantidad"] == 2
  assert ("Contenedores", "2 x CONTENEDOR ST 20'", False) in F["lineas_liquidacion"](d)


def test_sin_contenedor_no_hay_linea():
  assert all(c != "Contenedores" for c, _, _ in F["lineas_liquidacion"](_datos()))
  assert F["fila_csv"](_datos())["Contenedor"] == ""


# ---------- gastos desglosados (Agencia) ----------
import requests as _requests  # noqa: E402

import analitica as _analitica  # noqa: E402
from test_licencias_cliente import LLAVE as _LLAVE, URL as _URL, Resp as _Resp, _abrir_pro  # noqa: E402


@pytest.fixture
def app_agencia(monkeypatch, nueva_app):
  monkeypatch.setattr(_analitica, "registrar", lambda *a, **k: False)
  monkeypatch.setenv("SUPABASE_URL", _URL)
  monkeypatch.setenv("SUPABASE_SERVICE_KEY", _LLAVE)
  monkeypatch.setattr(_requests, "post", lambda *a, **k: _Resp({"valida": True, "nivel": "agencia"}))
  return _abrir_pro(nueva_app(), "FIQ-AAAA-BBBB-CCCC")


def _casilla_desglose(at):
  return [c for c in at.checkbox if c.key == "desglose_activo"]


def test_gratuito_y_pro_solo_ven_el_teaser_del_desglose(nueva_app, app_pro):
  for at in (nueva_app(), app_pro):
    assert _casilla_desglose(at) == []
    assert any("desglos" in i.value.lower() for i in at.info)
    assert metricas(at)[0] == "61.178.600"


def test_agencia_con_desglose_igual_al_actual_no_cambia_el_landed(app_agencia):
  app_agencia.checkbox(key="desglose_activo").set_value(True).run()
  assert not app_agencia.exception
  assert metricas(app_agencia)[0] == "61.178.600"


def test_agencia_editar_una_fila_cambia_los_gastos_y_el_landed(app_agencia):
  app_agencia.checkbox(key="desglose_activo").set_value(True).run()
  # La fila 0 (Agentes) pasa de 450.000 a 950.000: los gastos locales suben 500.000 (sin impuestos).
  app_agencia.session_state["desglose_gastos"] = {
      "edited_rows": {0: {"Valor (COP)": 950000.0}}, "added_rows": [], "deleted_rows": []}
  app_agencia.run()
  assert not app_agencia.exception
  assert metricas(app_agencia)[0] == F["num"](61_178_600 + 500_000)


def test_agencia_apagado_conserva_los_cuatro_campos(app_agencia):
  assert not app_agencia.exception
  assert metricas(app_agencia)[0] == "61.178.600"


def test_csv_y_liquidacion_con_desglose_usan_los_componentes():
  d = _datos(desglose_activo=True, desglose={"Almacenaje": 300000.0, "Agentes": 450000.0})
  fila = F["fila_csv"](d)
  assert fila["Gasto Almacenaje COP"] == 300000.0 and fila["Gasto Agentes COP"] == 450000.0
  assert fila["Gasto Bancarios COP"] == 0
  conceptos = [c for c, _, _ in F["lineas_liquidacion"](d)]
  assert "Almacenaje" in conceptos and "Agentes" in conceptos
  assert "Agenciamiento SIA" not in conceptos


def test_sin_desglose_siguen_los_cuatro_gastos_fijos():
  conceptos = [c for c, _, _ in F["lineas_liquidacion"](_datos())]
  assert "Agenciamiento SIA" in conceptos
  assert "Gasto Almacenaje COP" not in F["fila_csv"](_datos())


# ---------- correcciones de la revisión final ----------
def _fijos_en_csv(fila):
  return [fila[k] for k in ("Agenciamiento COP", "Bodegaje COP", "Transporte local COP", "Otros gastos COP")]


def test_desglose_activo_con_todo_en_cero_no_vuelve_a_los_gastos_fijos():
  d = _datos(desglose_activo=True, desglose={}, gastos_locales_cop=0.0)
  conceptos = [c for c, _, _ in F["lineas_liquidacion"](d)]
  assert not {"Agenciamiento SIA", "Bodegaje / depósito"} & set(conceptos)
  assert F["fila_csv"](d)["Gastos locales COP"] == 0.0


def test_csv_con_desglose_vacia_los_cuatro_gastos_fijos_y_trae_el_total():
  d = _datos(desglose_activo=True, desglose={"Agentes": 950000.0}, gastos_locales_cop=950000.0)
  fila = F["fila_csv"](d)
  assert _fijos_en_csv(fila) == ["", "", "", ""]
  assert fila["Gastos locales COP"] == 950000.0 and fila["Gasto Agentes COP"] == 950000.0


def test_csv_sin_desglose_conserva_los_cuatro_gastos_y_el_total():
  fila = F["fila_csv"](_datos())
  assert _fijos_en_csv(fila) == [450000.0, 300000.0, 800000.0, 200000.0]
  assert fila["Gastos locales COP"] == 1750000.0


@pytest.mark.parametrize("cambio", [
    dict(costo_capital_cop=603405.0, tasa_capital_pct=12.0, dias_capital=30),
    dict(incoterm="DDP"),
    dict(contenedor="CONTENEDOR ST 20'", contenedores_cantidad=1),
    dict(desglose_activo=True, desglose={"Agentes": 950000.0}, gastos_locales_cop=950000.0),
    dict(desglose_activo=True, desglose={}, gastos_locales_cop=0.0),
])
def test_el_codigo_de_cotizacion_cambia_con_las_cifras_nuevas(cambio):
  base = _datos()
  assert F["codigo_cotizacion"](_datos(**cambio), base["emision"]) != F["codigo_cotizacion"](base, base["emision"])


def test_el_codigo_no_cambia_si_no_se_usan_las_funciones_nuevas():
  base = _datos()
  apagado = _datos(incoterm="", costo_capital_cop=0.0, contenedor="", desglose={}, desglose_activo=False)
  assert F["codigo_cotizacion"](apagado, base["emision"]) == F["codigo_cotizacion"](base, base["emision"])


def test_con_desglose_activo_los_cuatro_campos_fijos_quedan_deshabilitados(app_agencia):
  def fijos(at):
    return [n for n in at.number_input if n.label.split(" (")[0] in
            ("Agenciamiento SIA", "Bodegaje / Depósito", "Transporte Terrestre Local", "Otros Gastos / Inspecciones")]
  assert len(fijos(app_agencia)) == 4 and not any(n.proto.disabled for n in fijos(app_agencia))
  app_agencia.checkbox(key="desglose_activo").set_value(True).run()
  assert all(n.proto.disabled for n in fijos(app_agencia))


def test_multimercancia_avisa_que_no_incluye_el_capital(app_pro):
  app_pro.checkbox(key="capital_activo").set_value(True).run()
  assert any("no incluye el costo de capital" in c.value.lower() for c in app_pro.caption)
