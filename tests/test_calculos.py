"""Cadena de cálculo del costo landed (valores verificados a mano)."""
from conftest import metricas, numero


def test_caso_por_defecto(nueva_app):
  # TRM 4.000, FOB 10.000, flete 1.200, seguro 150 -> CIF 11.350 USD
  # arancel 10 % = 4.540.000; IVA 19 % sobre (CIF + arancel) = 9.488.600
  # gastos locales = 450.000 + 300.000 + 800.000 + 200.000 = 1.750.000
  at = nueva_app()
  assert not at.exception
  landed, unitario, tributos, precio = metricas(at)
  assert landed == "61.178.600"
  assert unitario == "61.178,60"
  assert tributos == "14.028.600"
  assert precio == "87.398,00"  # 61.178,60 / (1 - 0,30)


def test_arancel_e_iva_en_cero(nueva_app):
  at = nueva_app()
  numero(at, "Arancel (%)").set_value(0.0)
  numero(at, "IVA (%)").set_value(0.0)
  at.run()
  landed, _, tributos, _ = metricas(at)
  assert tributos == "0"
  assert landed == "47.150.000"  # CIF 45.400.000 + gastos 1.750.000


def test_la_base_del_iva_incluye_el_arancel(nueva_app):
  at = nueva_app()
  numero(at, "Arancel (%)").set_value(40.0)
  numero(at, "IVA (%)").set_value(19.0)
  at.run()
  # arancel = 18.160.000; IVA = (45.400.000 + 18.160.000) * 0,19 = 12.076.400
  assert metricas(at)[2] == "30.236.400"


def test_casos_limite_no_producen_excepciones(nueva_app):
  for etiqueta, valor in [
      ("Cantidad de Unidades", 1),
      ("Valor FOB Total (USD)", 0.0),
      ("Margen Deseado (%)", 99.0),
  ]:
    at = nueva_app()
    numero(at, etiqueta).set_value(valor).run()
    assert not at.exception, etiqueta
