"""Carga de partidas validadas: solo cuenta una fila completa y coherente."""
from datetime import date

import pytest

from conftest import cargar_funciones
from partidas_validadas import cargar_validaciones

CAB = ("producto,subpartida,arancel_app_pct,iva_app_pct,arancel_validado_pct,iva_validado_pct,"
       "condiciones_especiales,fuente_normativa,fecha_vigencia,validado_por,observaciones\n")
HOY = date(2026, 10, 19)


def _csv(tmp_path, *filas):
  ruta = tmp_path / "v.csv"
  ruta.write_text(CAB + "\n".join(filas) + "\n", encoding="utf-8-sig")
  return str(ruta)


def test_fila_completa_queda_validada_con_coma_decimal(tmp_path):
  # coma decimal: "7,5" debe leerse como 7.5 (el CSV la trae entre comillas)
  ruta = _csv(tmp_path, 'A,6109.10.00.00,40,19,"7,5",19,,Decreto X,2026-10-01,Ana Pérez,')
  validadas, problemas = cargar_validaciones(ruta, HOY)
  assert problemas == []
  v = validadas["6109.10.00.00"]
  assert v["arancel"] == 7.5 and v["iva"] == 19.0
  assert v["fuente"] == "Decreto X" and v["vigencia"] == "2026-10-01"


def test_fila_sin_campos_de_validacion_es_pendiente_sin_problema(tmp_path):
  validadas, problemas = cargar_validaciones(_csv(tmp_path, "A,6109.10.00.00,40,19,,,,,,,"), HOY)
  assert validadas == {} and problemas == []


@pytest.mark.parametrize("fila,motivo", [
    ("A,6109.10.00.00,40,19,15,19,,,2026-10-01,Ana,", "fuente_normativa"),
    ("A,6109.10.00.00,40,19,15,19,,Dec,2026-10-01,,", "validado_por"),
    ("A,6109.10.00.00,40,19,150,19,,Dec,2026-10-01,Ana,", "inválido"),
    ("A,6109.10.00.00,40,19,abc,19,,Dec,2026-10-01,Ana,", "inválido"),
    ("A,6109.10.00.00,40,19,15,19,,Dec,01/10/2026,Ana,", "inválido"),
    ("A,6109.10.00.00,40,19,15,19,,Dec,2027-01-01,Ana,", "futuro"),
])
def test_fila_incompleta_o_invalida_nunca_valida(tmp_path, fila, motivo):
  validadas, problemas = cargar_validaciones(_csv(tmp_path, fila), HOY)
  assert validadas == {}
  assert len(problemas) == 1 and motivo in problemas[0]


def test_archivo_inexistente_no_valida_nada(tmp_path):
  validadas, problemas = cargar_validaciones(str(tmp_path / "no.csv"), HOY)
  assert validadas == {} and problemas


def test_el_csv_del_repositorio_esta_sincronizado_con_la_tabla_de_la_app():
  import csv
  from conftest import APP_PATH
  tabla = cargar_funciones("DATABASE_NANDINA")["DATABASE_NANDINA"]
  ruta = APP_PATH.parent / "docs" / "validacion-nandina.csv"
  filas = list(csv.DictReader(open(ruta, encoding="utf-8-sig")))
  codigos = [f["subpartida"] for f in filas]
  assert len(codigos) == len(set(codigos)), "subpartidas repetidas en el CSV"
  esperadas = {v["codigo"]: v for v in tabla.values() if v["codigo"]}
  por_codigo = {f["subpartida"]: f for f in filas}
  for codigo, v in esperadas.items():  # las 7 de referencia coinciden con la app
    assert float(por_codigo[codigo]["arancel_app_pct"]) == v["arancel"]
    assert float(por_codigo[codigo]["iva_app_pct"]) == v["iva"]
  candidatas = [f for f in filas if f["subpartida"] not in esperadas]
  assert len(candidatas) >= 25
  for f in candidatas:  # candidatas: sin cifras de referencia inventadas
    assert f["arancel_app_pct"] == "" and f["iva_app_pct"] == "" and f["producto"]
  _, problemas = cargar_validaciones(str(ruta), HOY)
  assert problemas == []


BASE = {"Camisetas": {"codigo": "6109.10.00.00", "arancel": 40.0, "iva": 19.0}}


def _validada(producto, **extra):
  v = {"producto": producto, "arancel": 15.0, "iva": 19.0, "fuente": "f", "vigencia": "2026-10-01",
       "validado_por": "x", "condiciones": ""}
  v.update(extra)
  return v


def test_el_catalogo_solo_suma_partidas_nuevas_ya_validadas():
  from partidas_validadas import catalogo_ampliado
  validadas = {
      "6203.42.00.00": _validada("Pantalones de algodón"),
      "6109.10.00.00": _validada("Camisetas validadas", arancel=7.0),  # ya está en la base
  }
  cat = catalogo_ampliado(BASE, validadas)
  assert list(cat) == ["Camisetas", "Pantalones de algodón"]
  assert cat["Pantalones de algodón"] == {"codigo": "6203.42.00.00", "arancel": 15.0, "iva": 19.0}
  assert catalogo_ampliado(BASE, {}) == BASE  # sin validaciones: nada nuevo


def test_el_catalogo_ignora_nombres_repetidos_o_vacios():
  from partidas_validadas import catalogo_ampliado
  cat = catalogo_ampliado(BASE, {"1111.11.11.11": _validada("Camisetas"), "2222.22.22.22": _validada("")})
  assert cat == BASE
