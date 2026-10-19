"""Cotización multimercancía (Pro): reparto de flete/seguro/gastos y liquidación por línea."""
import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP_PATH, cargar_funciones

F = cargar_funciones("calcular_embarque")
calcular = F["calcular_embarque"]


def item(producto, fob, unidades, arancel, iva=19.0):
  return {"producto": producto, "fob_usd": fob, "unidades": unidades,
          "pct_arancel": arancel, "pct_iva": iva}


def test_una_sola_linea_coincide_con_la_calculadora_individual():
  # Mismo caso que la calculadora: 61.178.600 de costo landed y precio sugerido 87.398
  lineas, tot = calcular([item("Camisetas", 10000, 1000, 10)], 1200, 150, 4000, 1750000, 30)
  assert lineas[0]["landed_cop"] == pytest.approx(61178600)
  assert lineas[0]["unitario_cop"] == pytest.approx(61178.6)
  assert lineas[0]["precio_sugerido_cop"] == pytest.approx(87398)
  assert tot["landed_cop"] == pytest.approx(61178600)


def test_reparto_por_peso_fob_con_dos_lineas():
  # Calculado a mano: A pesa 60 % y B 40 % del FOB
  items = [item("A", 6000, 100, 10), item("B", 4000, 50, 0)]
  lineas, tot = calcular(items, 1000, 100, 4000, 1000000, 20)
  a, b = lineas
  assert a["peso_fob"] == pytest.approx(0.6)
  assert a["cif_cop"] == pytest.approx(26640000)
  assert a["arancel_cop"] == pytest.approx(2664000)
  assert a["iva_cop"] == pytest.approx(5567760)
  assert a["gastos_cop"] == pytest.approx(600000)
  assert a["landed_cop"] == pytest.approx(35471760)
  assert b["cif_cop"] == pytest.approx(17760000)
  assert b["arancel_cop"] == 0
  assert b["iva_cop"] == pytest.approx(3374400)
  assert b["landed_cop"] == pytest.approx(21534400)
  assert tot["landed_cop"] == pytest.approx(57006160)
  assert tot["cif_cop"] == pytest.approx((10000 + 1000 + 100) * 4000)


def test_el_reparto_no_pierde_ni_inventa_dinero():
  items = [item("A", 1234.5, 10, 5), item("B", 987.65, 3, 15), item("C", 4321, 7, 0)]
  lineas, tot = calcular(items, 777, 33, 4123.5, 1750000, 25)
  assert sum(l["gastos_cop"] for l in lineas) == pytest.approx(1750000)
  assert sum(l["peso_fob"] for l in lineas) == pytest.approx(1)
  assert tot["cif_cop"] == pytest.approx((1234.5 + 987.65 + 4321 + 777 + 33) * 4123.5)


def test_fob_total_cero_reparte_en_partes_iguales():
  lineas, _ = calcular([item("A", 0, 1, 0), item("B", 0, 1, 0)], 100, 0, 4000, 1000, 0)
  assert lineas[0]["peso_fob"] == pytest.approx(0.5)
  assert lineas[0]["gastos_cop"] == pytest.approx(500)


def test_unidades_cero_no_divide_por_cero():
  lineas, _ = calcular([item("A", 1000, 0, 10)], 0, 0, 4000, 0, 30)
  assert lineas[0]["unitario_cop"] == 0
  assert lineas[0]["precio_sugerido_cop"] == 0


def test_la_seccion_muestra_aviso_pro_a_usuarios_gratis(monkeypatch):
  at = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
  assert not at.exception
  texto = " ".join(str(e.value) for e in at.info) + " ".join(str(e.value) for e in at.markdown)
  assert "Cotización multimercancía" in texto
  assert "Disponible con licencia Pro" in texto
  assert len(at.get("arrow_data_frame")) == 0
