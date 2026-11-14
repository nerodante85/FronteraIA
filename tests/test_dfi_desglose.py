"""Gastos desglosados por componente DFI (puro)."""
import pytest

import dfi


def fila(componente, valor):
  return {"componente": componente, "valor_cop": valor}


def test_componentes_de_importacion():
  assert dfi.COMPONENTES_IMPORTACION == (
      "Transporte importador", "Almacenaje", "Aduaneros", "Agentes", "Bancarios",
      "Documentación", "Seguro local", "Manipuleo de desembarque", "Otros")


def test_total_suma_los_componentes():
  assert dfi.total_gastos([fila("Almacenaje", 300_000), fila("Agentes", 450_000)]) == 750_000


@pytest.mark.parametrize("malo", [None, float("nan"), -100.0, "abc"])
def test_valores_vacios_nan_negativos_o_texto_cuentan_cero(malo):
  assert dfi.total_gastos([fila("Almacenaje", malo), fila("Agentes", 450_000)]) == 450_000


def test_lista_vacia_da_cero():
  assert dfi.total_gastos([]) == 0


def test_gastos_por_componente_agrupa_repetidos_y_manda_desconocidos_a_otros():
  r = dfi.gastos_por_componente(
      [fila("Almacenaje", 100), fila("Almacenaje", 50), fila("Cosa rara", 30), fila(None, 20)])
  assert r == {"Almacenaje": 150.0, "Otros": 50.0}
