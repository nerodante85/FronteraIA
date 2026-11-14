"""Costo de capital del inventario (puro): valor × tasa anual × días / 365."""
import pytest

import dfi


def test_formula_base():
  assert dfi.costo_capital(61_178_600, 12, 30) == pytest.approx(61_178_600 * 0.12 * 30 / 365)


def test_un_año_completo_es_la_tasa_anual():
  assert dfi.costo_capital(1_000_000, 10, 365) == pytest.approx(100_000)


@pytest.mark.parametrize("valor,tasa,dias", [(1e6, 0, 30), (1e6, 12, 0), (0, 12, 30)])
def test_tasa_dias_o_valor_cero_dan_cero(valor, tasa, dias):
  assert dfi.costo_capital(valor, tasa, dias) == 0


@pytest.mark.parametrize("valor,tasa,dias", [(-1e6, 12, 30), (1e6, -12, 30), (1e6, 12, -30)])
def test_valores_negativos_dan_cero(valor, tasa, dias):
  assert dfi.costo_capital(valor, tasa, dias) == 0
