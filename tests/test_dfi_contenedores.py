"""Calculadora de contenedores (pura): cuántos y qué tan llenos, por volumen y peso."""
import pytest

import dfi


def test_capacidades_del_dfi():
  assert {k: (v["volumen_m3"], v["peso_kg"]) for k, v in dfi.CONTENEDORES.items()} == {
      "40HC": (76.35, 26660), "40R": (67.95, 29400), "ST20": (33.2, 28280), "ST40": (67.72, 26840)}


def test_un_contenedor_limitado_por_volumen():
  r = dfi.contenedores_necesarios(30, 20_000, "ST20")
  assert r["cantidad"] == 1
  assert r["ocupacion_volumen_pct"] == pytest.approx(30 / 33.2 * 100)
  assert r["ocupacion_peso_pct"] == pytest.approx(20_000 / 28_280 * 100)
  assert r["limitante"] == "volumen"


def test_carga_mayor_que_un_contenedor_pide_varios_por_volumen():
  r = dfi.contenedores_necesarios(100, 1_000, "ST40")
  assert r["cantidad"] == 2
  assert r["limitante"] == "volumen"


def test_carga_pesada_se_limita_por_peso():
  r = dfi.contenedores_necesarios(10, 40_000, "ST20")
  assert r["cantidad"] == 2
  assert r["limitante"] == "peso"


@pytest.mark.parametrize("volumen,peso", [(0, 0), (-5, -5)])
def test_sin_carga_no_hay_contenedores_ni_division_por_cero(volumen, peso):
  r = dfi.contenedores_necesarios(volumen, peso, "40HC")
  assert r == {"cantidad": 0, "ocupacion_volumen_pct": 0.0, "ocupacion_peso_pct": 0.0, "limitante": None}


def test_solo_peso_o_solo_volumen_cuenta():
  assert dfi.contenedores_necesarios(0, 30_000, "40HC")["cantidad"] == 2
  assert dfi.contenedores_necesarios(80, 0, "40HC")["cantidad"] == 2


def test_tipo_desconocido_lanza_keyerror():
  with pytest.raises(KeyError):
    dfi.contenedores_necesarios(10, 10, "ST60")


@pytest.mark.parametrize("tipo", list(dfi.CONTENEDORES))
@pytest.mark.parametrize("n", [3, 15, 30, 31, 55])
def test_multiplos_exactos_no_pasan_un_contenedor_de_mas(tipo, n):
  volumen = dfi.CONTENEDORES[tipo]["volumen_m3"] * n
  assert dfi.contenedores_necesarios(volumen, 0, tipo)["cantidad"] == n
