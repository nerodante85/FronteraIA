"""Trazabilidad de la cotización: código, origen de la TRM, filas del PDF/CSV."""
import re
from datetime import datetime, timedelta, timezone

import pytest

from conftest import cargar_funciones

ZONA = timezone(timedelta(hours=-5))
EMISION = datetime(2026, 10, 17, 9, 5, tzinfo=ZONA)

F = cargar_funciones(
    "CAMPOS_CODIGO", "codigo_cotizacion", "origen_trm", "estado_aranceles",
    "lineas_liquidacion", "fila_csv", "generar_pdf_cotizacion", "_texto_pdf",
    "_REEMPLAZOS_PDF", "num", "ICONOS", "icono",
)


def datos_base(**cambios):
  datos = {
      "producto": "Camisetas de algodón", "partida": "6109.10.00.00", "unidades": 1000,
      "fob_usd": 10000.0, "flete_usd": 1200.0, "seguro_usd": 150.0, "cif_usd": 11350.0,
      "cif_cop": 45400000.0, "trm": 4000.0, "pct_arancel": 10.0, "pct_iva": 19.0,
      "arancel_cop": 4540000.0, "iva_cop": 9488600.0, "total_tributos_cop": 14028600.0,
      "agenciamiento_cop": 450000.0, "bodegaje_cop": 300000.0,
      "transporte_local_cop": 800000.0, "otros_gastos_cop": 200000.0,
      "gastos_locales_cop": 1750000.0, "costo_total_landed_cop": 61178600.0,
      "costo_unitario_cop": 61178.6, "pct_margen": 30.0,
      "precio_sugerido_unitario_cop": 87398.0, "emision": EMISION,
      "origen_trm": "TRM oficial vigente desde 2026-10-17 (datos.gov.co)",
      "estado_aranceles": "Valores de referencia, pendientes de validacion",
  }
  datos.update(cambios)
  datos["codigo"] = F["codigo_cotizacion"](datos, datos["emision"])
  return datos


# --- Código de cotización -------------------------------------------------
def test_codigo_tiene_formato_y_fecha():
  codigo = F["codigo_cotizacion"](datos_base(), EMISION)
  assert re.fullmatch(r"FIQ-20261017-[0-9A-F]{6}", codigo)


def test_mismo_dato_mismo_dia_mismo_codigo():
  assert datos_base()["codigo"] == datos_base()["codigo"]


@pytest.mark.parametrize("campo,valor", [
    ("unidades", 1001), ("fob_usd", 10001.0), ("trm", 4001.0), ("pct_arancel", 11.0),
    ("pct_iva", 5.0), ("agenciamiento_cop", 1.0), ("pct_margen", 31.0), ("producto", "Otro"),
])
def test_cualquier_cambio_en_la_operacion_cambia_el_codigo(campo, valor):
  assert datos_base(**{campo: valor})["codigo"] != datos_base()["codigo"]


def test_otro_dia_otro_codigo():
  manana = EMISION + timedelta(days=1)
  assert F["codigo_cotizacion"](datos_base(), manana) != F["codigo_cotizacion"](datos_base(), EMISION)


# --- Origen de la TRM y estado de aranceles ------------------------------
def test_origen_trm():
  origen = F["origen_trm"]
  assert "oficial vigente desde 2026-10-17" in origen(3174.67, 3174.67, "2026-10-17", True)
  assert "respaldo" in origen(4000.0, 4000.0, "", False)
  assert "manualmente" in origen(3200.0, 3174.67, "2026-10-17", True)


def test_estado_aranceles():
  estado = F["estado_aranceles"]
  assert "usuario" in estado(True, False, None)
  assert "Ajustados" in estado(False, True, None)
  assert "pendientes" in estado(False, False, None)
  validado = estado(False, False, {"fuente": "Arancel X", "vigencia": "2026-10-01"})
  assert "Validados" in validado and "Arancel X" in validado and "2026-10-01" in validado


# --- Filas de la liquidación y CSV ---------------------------------------
def test_liquidacion_muestra_porcentajes_y_desglose():
  filas = {c: v for c, v, _ in F["lineas_liquidacion"](datos_base())}
  assert filas["Arancel DIAN (10 %)"] == "$4.540.000 COP"
  assert filas["IVA DIAN (19 %)"] == "$9.488.600 COP"
  assert filas["Base gravable del IVA (CIF + arancel)"] == "$49.940.000 COP"
  assert filas["Agenciamiento SIA"] == "$450.000 COP"
  assert filas["Total gastos logísticos Cúcuta"] == "$1.750.000 COP"
  assert filas["COSTO TOTAL LANDED"] == "$61.178.600 COP"
  assert filas["PRECIO DE VENTA SUGERIDO (UNITARIO)"] == "$87.398,00 COP"


def test_csv_incluye_todo_para_reconstruir():
  fila = F["fila_csv"](datos_base())
  assert fila["Codigo cotizacion"] == datos_base()["codigo"]
  assert fila["Fecha emision"] == "2026-10-17 09:05"
  for columna in ["TRM COP/USD", "Origen TRM", "Arancel %", "IVA %", "Estado aranceles",
                  "Agenciamiento COP", "Bodegaje COP", "Transporte local COP", "Otros gastos COP",
                  "Margen %", "Precio sugerido unitario COP"]:
    assert columna in fila, columna
  assert fila["Costo landed COP"] == 61178600.0


# --- PDF -----------------------------------------------------------------
def _pdf_sin_comprimir(datos):
  base = F["FPDF"]

  class SinCompresion(base):
    def __init__(self, *a, **k):
      super().__init__(*a, **k)
      self.set_compression(False)

  F["FPDF"] = SinCompresion
  try:
    return F["generar_pdf_cotizacion"](datos)
  finally:
    F["FPDF"] = base


def test_pdf_contiene_la_trazabilidad():
  pdf = _pdf_sin_comprimir(datos_base())
  assert pdf.startswith(b"%PDF")
  # En el PDF los paréntesis de las cadenas de texto van escapados.
  texto = pdf.decode("latin-1").replace("\\(", "(").replace("\\)", ")")
  for esperado in [
      datos_base()["codigo"], "2026-10-17 09:05", "TRM oficial vigente desde 2026-10-17",
      "pendientes de validacion", "Arancel DIAN (10 %)", "IVA DIAN (19 %)",
      "Agenciamiento SIA", "PRECIO DE VENTA SUGERIDO", "no incluye el IVA de venta",
  ]:
    assert esperado in texto, esperado


@pytest.mark.parametrize("producto", ["Camisetas – verano", "Perfume €50", "Camisetas 👕", "Niño ñandú"])
def test_pdf_tolera_texto_especial(producto):
  assert _pdf_sin_comprimir(datos_base(producto=producto)).startswith(b"%PDF")


# --- En la interfaz ------------------------------------------------------
def test_la_interfaz_muestra_el_codigo_de_cotizacion(nueva_app):
  at = nueva_app()
  assert any("Código de cotización: **FIQ-" in c.value for c in at.caption)


def test_trm_manual_se_refleja_en_el_origen(nueva_app):
  at = nueva_app()
  next(n for n in at.sidebar.number_input if n.label.startswith("TRM")).set_value(3500.0).run()
  assert any("manualmente" in c.value for c in at.caption)


def test_formato_colombiano_de_cifras():
  assert F["num"](61178600) == "61.178.600"
  assert F["num"](61178.6, 2) == "61.178,60"
  assert F["num"](0) == "0"
  assert F["num"](-1234.5, 2) == "-1.234,50"


def test_iconos_son_svg_validos():
  import xml.etree.ElementTree as ET
  assert len(F["ICONOS"]) >= 10
  for nombre in F["ICONOS"]:
    svg = F["icono"](nombre)
    assert "currentColor" in svg
    ET.fromstring(svg)  # XML bien formado
