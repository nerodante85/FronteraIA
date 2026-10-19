"""Conversor Pro a bolívares y USDT: sin tasa no hay cifra, y la cuenta pasa por dólares."""
import pytest

from conftest import cargar_funciones

eq = cargar_funciones("equivalencias_moneda")["equivalencias_moneda"]


def test_bolivares_via_dolares_a_mano():
  # 61.178.600 COP / TRM 4.000 = 15.294,65 USD; × 879 Bs/USD = 13.443.997,35 Bs
  r = eq(61178600, 4000, 879, 4000)
  assert r["usd"] == pytest.approx(15294.65)
  assert r["ves"] == pytest.approx(13443997.35, rel=1e-9)
  assert r["usdt"] == pytest.approx(15294.65)


def test_sin_tasa_de_bolivares_no_hay_cifra_inventada():
  for tasa in (None, 0, 0.0):
    assert eq(61178600, 4000, tasa, 4000)["ves"] is None


def test_usdt_usa_su_propia_tasa():
  assert eq(4050000, 4000, None, 4050)["usdt"] == pytest.approx(1000)


def test_tasas_invalidas_no_dividen_por_cero():
  r = eq(1000000, 0, 879, 0)
  assert r["usd"] is None and r["ves"] is None and r["usdt"] is None


def _textos(at):
  return " ".join(str(e.value) for e in at.info)


def test_en_la_app_pro_los_bolivares_arrancan_sin_cifra_y_aparecen_al_ingresar_la_tasa(app_pro):
  tasa = next(n for n in app_pro.sidebar.number_input if n.label == "Bolívares por dólar (Bs/USD)")
  assert tasa.value is None
  assert "ingresa la tasa Bs/USD" in _textos(app_pro)
  assert " VES`" not in _textos(app_pro)
  tasa.set_value(879.0).run()
  assert not app_pro.exception
  assert " VES`" in _textos(app_pro)
  usdt = next(n for n in app_pro.sidebar.number_input if n.label == "Tasa COP / USDT (Cripto)")
  assert usdt.value == 4000.0  # por defecto sigue a la TRM, no un valor fijo
