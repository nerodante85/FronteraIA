import hashlib
import hmac
import io
from datetime import datetime, timedelta, timezone
import os
import re
import urllib.parse
from fpdf import FPDF
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import licencias  # noqa: E402  (licencias por cliente, ver supabase/)

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(
    page_title="FronteraIQ Pro — Inteligencia Aduanera Cúcuta",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

TELEFONO_WHATSAPP = "573156491042"  # <-- REEMPLAZA CON TU NÚMERO (Prefijo 57)

# ==================== INYECCIÓN CSS SEGURA ====================
css_code = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.hero-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    padding: 32px 40px;
    border-radius: 20px;
    color: #ffffff;
    margin-bottom: 28px;
    box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3);
}

.hero-title {
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 6px;
    color: #f8fafc;
}

.hero-subtitle {
    font-size: 15px;
    color: #94a3b8;
    font-weight: 500;
}

.metric-card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 22px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.metric-label {
    font-size: 12px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.metric-value {
    font-size: 26px;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 4px;
}

.metric-subtext {
    font-size: 12px;
    font-weight: 600;
    color: #10b981;
}

.whatsapp-btn {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #ffffff !important;
    font-weight: 700;
    padding: 14px 24px;
    border-radius: 12px;
    text-decoration: none;
    display: block;
    font-size: 15px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
}

div[data-baseweb="input"] {
    border-radius: 10px !important;
}

.stButton>button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    height: 48px !important;
}
</style>
"""

st.markdown(css_code, unsafe_allow_html=True)


# ==================== CONSULTA TRM OFICIAL ====================
TRM_RESPALDO = 4000.0
# Dataset oficial "Tasa de Cambio Representativa del Mercado - TRM" (datos.gov.co).
# Campos: valor, unidad, vigenciadesde, vigenciahasta.
TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
ZONA_COLOMBIA = timezone(timedelta(hours=-5))  # Colombia no usa horario de verano


@st.cache_data(ttl=3600)
def _consultar_trm():
  """Consulta la TRM vigente hoy. Lanza excepción si falla (los fallos no se cachean)."""
  hoy = datetime.now(ZONA_COLOMBIA).strftime("%Y-%m-%dT00:00:00")
  # La TRM de un día se publica con anticipación: se toma la última cuya
  # vigencia ya comenzó, no la más reciente publicada.
  response = requests.get(
      TRM_URL,
      params={
          "$where": f"vigenciadesde <= '{hoy}'",
          "$order": "vigenciadesde DESC",
          "$limit": 1,
      },
      timeout=5,
  )
  response.raise_for_status()
  registro = response.json()[0]
  valor = float(registro["valor"])
  if not 1000.0 <= valor <= 20000.0:
    raise ValueError(f"TRM fuera de un rango razonable: {valor}")
  fecha = str(registro.get("vigenciadesde", ""))[:10]
  return valor, fecha


def obtener_trm_actual():
  """Devuelve (valor, fecha, es_oficial). Si la consulta falla, usa el respaldo."""
  try:
    valor, fecha = _consultar_trm()
    return valor, fecha, True
  except Exception:
    return TRM_RESPALDO, "", False


trm_oficial, trm_fecha, trm_es_oficial = obtener_trm_actual()


# ==================== BASE DE DATOS NANDINA ====================
DATABASE_NANDINA = {
    "Personalizado / Otra partida": {
        "codigo": "",
        "arancel": 10.0,
        "iva": 19.0,
    },
    "Confecciones / Camisetas de Algodón": {
        "codigo": "6109.10.00.00",
        "arancel": 40.0,
        "iva": 19.0,
    },
    "Calzado con Suela de Caucho / Cuero": {
        "codigo": "6403.99.90.00",
        "arancel": 35.0,
        "iva": 19.0,
    },
    "Teléfonos Celulares / Smartphones": {
        "codigo": "8517.13.00.00",
        "arancel": 0.0,
        "iva": 19.0,
    },
    "Computadores Portátiles / Laptops": {
        "codigo": "8471.30.00.00",
        "arancel": 0.0,
        "iva": 0.0,
    },
    "Arroz Blanqueado / Pulido": {
        "codigo": "1006.30.00.00",
        "arancel": 15.0,
        "iva": 0.0,
    },
    "Repuestos y Autopartes": {
        "codigo": "8708.29.90.00",
        "arancel": 10.0,
        "iva": 19.0,
    },
    "Medicamentos de Uso Humano": {
        "codigo": "3004.90.99.00",
        "arancel": 0.0,
        "iva": 0.0,
    },
}

# Partidas cuyo arancel/IVA ya fueron validados por un agente de aduanas.
# Formato: "codigo": {"fuente": "norma o arancel consultado", "vigencia": "AAAA-MM-DD"}
# Mientras una partida no esté aquí, la interfaz la marca como "pendiente".
# Ver docs/validacion-nandina.csv.
PARTIDAS_VALIDADAS = {}


# ==================== GENERACIÓN DE PDF CORREGIDA ====================
_REEMPLAZOS_PDF = {
    "–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "€": "EUR", " ": " ",
}


def _texto_pdf(texto):
  """Adapta texto libre a Latin-1 (fuente estándar del PDF). Lo no soportado pasa a '?'."""
  texto = str(texto)
  for original, reemplazo in _REEMPLAZOS_PDF.items():
    texto = texto.replace(original, reemplazo)
  return texto.encode("latin-1", errors="replace").decode("latin-1")


CAMPOS_CODIGO = (
    "producto", "partida", "unidades", "fob_usd", "flete_usd", "seguro_usd",
    "trm", "pct_arancel", "pct_iva", "agenciamiento_cop", "bodegaje_cop",
    "transporte_local_cop", "otros_gastos_cop", "pct_margen",
)


def codigo_cotizacion(datos, emision):
  """Código de cotización determinístico: misma operación y mismo día, mismo código."""
  base = "|".join(str(datos[campo]) for campo in CAMPOS_CODIGO)
  huella = hashlib.sha256(base.encode("utf-8")).hexdigest()[:6].upper()
  return f"FIQ-{emision:%Y%m%d}-{huella}"


def origen_trm(trm, trm_oficial, trm_fecha, es_oficial):
  """Explica de dónde sale la TRM aplicada en la cotización."""
  if abs(trm - trm_oficial) > 1e-9:
    return "Ingresada manualmente por el usuario"
  if es_oficial:
    return f"TRM oficial vigente desde {trm_fecha} (datos.gov.co)"
  return "Valor de respaldo, NO es la TRM oficial"


def estado_aranceles(personalizada, ajustados, validacion):
  """Estado de los porcentajes de arancel e IVA usados en la cotización."""
  if personalizada:
    return "Ingresados por el usuario (partida personalizada)"
  if ajustados:
    return "Ajustados por el usuario respecto a la tabla de referencia"
  if validacion:
    return f"Validados. Fuente: {validacion['fuente']}. Vigencia: {validacion['vigencia']}"
  return "Valores de referencia, pendientes de validacion"


def lineas_liquidacion(d):
  """Filas (concepto, valor, destacada) de la liquidación, para el PDF."""
  usd = lambda v: f"${v:,.2f} USD"
  cop = lambda v: f"${v:,.0f} COP"
  return [
      ("Valor FOB", usd(d["fob_usd"]), False),
      ("Flete internacional", usd(d["flete_usd"]), False),
      ("Seguro internacional", usd(d["seguro_usd"]), False),
      ("Valor CIF", usd(d["cif_usd"]), False),
      ("Valor CIF en COP", cop(d["cif_cop"]), False),
      (f"Arancel DIAN ({d['pct_arancel']:g} %)", cop(d["arancel_cop"]), False),
      ("Base gravable del IVA (CIF + arancel)", cop(d["cif_cop"] + d["arancel_cop"]), False),
      (f"IVA DIAN ({d['pct_iva']:g} %)", cop(d["iva_cop"]), False),
      ("Total impuestos DIAN", cop(d["total_tributos_cop"]), False),
      ("Agenciamiento SIA", cop(d["agenciamiento_cop"]), False),
      ("Bodegaje / depósito", cop(d["bodegaje_cop"]), False),
      ("Transporte terrestre local", cop(d["transporte_local_cop"]), False),
      ("Otros gastos / inspecciones", cop(d["otros_gastos_cop"]), False),
      ("Total gastos logísticos Cúcuta", cop(d["gastos_locales_cop"]), False),
      ("COSTO TOTAL LANDED", cop(d["costo_total_landed_cop"]), True),
      ("COSTO LANDED UNITARIO", f"${d['costo_unitario_cop']:,.2f} COP", True),
      (f"Margen deseado ({d['pct_margen']:g} % sobre el precio)", "", False),
      ("PRECIO DE VENTA SUGERIDO (UNITARIO)", f"${d['precio_sugerido_unitario_cop']:,.2f} COP", True),
  ]


def fila_csv(d):
  """Una fila de CSV con todo lo necesario para reconstruir la cotización."""
  return {
      "Codigo cotizacion": d["codigo"],
      "Fecha emision": d["emision"].strftime("%Y-%m-%d %H:%M"),
      "Producto": d["producto"],
      "Partida": d["partida"],
      "Unidades": d["unidades"],
      "FOB USD": d["fob_usd"],
      "Flete USD": d["flete_usd"],
      "Seguro USD": d["seguro_usd"],
      "CIF USD": d["cif_usd"],
      "TRM COP/USD": d["trm"],
      "Origen TRM": d["origen_trm"],
      "Arancel %": d["pct_arancel"],
      "IVA %": d["pct_iva"],
      "Estado aranceles": d["estado_aranceles"],
      "CIF COP": d["cif_cop"],
      "Arancel COP": d["arancel_cop"],
      "IVA COP": d["iva_cop"],
      "Agenciamiento COP": d["agenciamiento_cop"],
      "Bodegaje COP": d["bodegaje_cop"],
      "Transporte local COP": d["transporte_local_cop"],
      "Otros gastos COP": d["otros_gastos_cop"],
      "Costo landed COP": d["costo_total_landed_cop"],
      "Costo unitario COP": d["costo_unitario_cop"],
      "Margen %": d["pct_margen"],
      "Precio sugerido unitario COP": d["precio_sugerido_unitario_cop"],
  }


def generar_pdf_cotizacion(datos):
  pdf = FPDF()
  pdf.add_page()
  pdf.set_font("Helvetica", "B", 16)
  pdf.cell(
      0, 10, "FronteraIQ - Reporte de Cotizacion Aduanera",
      new_x="LMARGIN", new_y="NEXT", align="C",
  )
  pdf.set_font("Helvetica", "I", 10)
  pdf.cell(
      0, 8, "Liquidacion de Costos Landed y Tributos DIAN (Cucuta - Frontera)",
      new_x="LMARGIN", new_y="NEXT", align="C",
  )
  pdf.ln(3)

  encabezado = [
      ("Codigo de cotizacion", datos["codigo"]),
      ("Fecha de emision", datos["emision"].strftime("%Y-%m-%d %H:%M") + " (hora de Colombia)"),
      ("Producto", datos["producto"]),
      ("Partida NANDINA", datos["partida"]),
      ("Cantidad", f"{datos['unidades']:,} uds"),
      ("TRM aplicada", f"${datos['trm']:,.2f} COP/USD"),
      ("Origen de la TRM", datos["origen_trm"]),
      ("Estado de arancel e IVA", datos["estado_aranceles"]),
  ]
  for etiqueta, valor in encabezado:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(48, 6, _texto_pdf(etiqueta + ":"))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, _texto_pdf(valor), new_x="LMARGIN", new_y="NEXT")
  pdf.ln(4)

  pdf.set_font("Helvetica", "B", 10)
  pdf.cell(120, 7, "Concepto", border=1)
  pdf.cell(70, 7, "Valor", border=1, new_x="LMARGIN", new_y="NEXT", align="R")

  for concepto, valor, destacada in lineas_liquidacion(datos):
    pdf.set_font("Helvetica", "B" if destacada else "", 9)
    pdf.cell(120, 6, _texto_pdf(concepto), border=1)
    pdf.cell(70, 6, _texto_pdf(valor), border=1, new_x="LMARGIN", new_y="NEXT", align="R")

  pdf.ln(6)
  pdf.set_font("Helvetica", "I", 8)
  pdf.multi_cell(
      0,
      4.5,
      "Notas: Este documento es una estimacion de costos proyectados para la"
      " operacion aduanera y logistica en la frontera de Cucuta. No constituye"
      " una liquidacion oficial de la DIAN. Los porcentajes de arancel e IVA"
      " deben confirmarse con la normativa vigente. El precio sugerido se calcula"
      " como costo unitario / (1 - margen) y no incluye el IVA de venta. El codigo"
      " de cotizacion se deriva de los datos de la operacion y de la fecha: dos"
      " cotizaciones con los mismos datos el mismo dia tienen el mismo codigo.",
      new_x="LMARGIN", new_y="NEXT",
  )

  # Retorna los bytes directamente usando el API actualizado de fpdf2
  return bytes(pdf.output())


# ==================== BARRA LATERAL (SIDEBAR) ====================
st.sidebar.header("🔐 Acceso de Usuario")
tipo_plan = st.sidebar.radio("Plan de Usuario", ["Gratuito", "Pro / Premium ⭐"])

def _clave_pro_configurada():
  """Lee la clave Pro desde st.secrets o la variable de entorno PRO_LICENSE_KEY."""
  try:
    clave = st.secrets.get("PRO_LICENSE_KEY")
  except Exception:
    clave = None
  return clave or os.environ.get("PRO_LICENSE_KEY")


def _config_licencias():
  """(url, clave de servicio) de Supabase, o None si las licencias por cliente no están configuradas."""
  try:
    url = st.secrets.get("SUPABASE_URL")
    llave = st.secrets.get("SUPABASE_SERVICE_KEY")
  except Exception:
    url = llave = None
  url = url or os.environ.get("SUPABASE_URL")
  llave = llave or os.environ.get("SUPABASE_SERVICE_KEY")
  return (url, llave) if url and llave else None


@st.cache_data(ttl=300, show_spinner=False)
def _consultar_licencia(clave, sesion, url, llave):
  """Valida contra Supabase. Si el servicio falla LANZA la excepción para no cachear el error;
  la caché de 5 minutos también renueva el puesto de uso de la sesión."""
  return licencias.validar_licencia(clave, sesion, url, llave)


def validar_licencia_pro(clave):
  """Devuelve (es_pro, mensaje_de_error). Falla cerrada: si no se puede verificar, no hay Pro."""
  config = _config_licencias()
  if config:
    if "sesion_id" not in st.session_state:
      st.session_state["sesion_id"] = uuid.uuid4().hex
    try:
      resultado = _consultar_licencia(clave, st.session_state["sesion_id"], *config)
    except Exception:
      return False, licencias.mensaje_de_rechazo("servicio_no_disponible")
    if resultado.get("valida"):
      return True, None
    return False, licencias.mensaje_de_rechazo(resultado.get("motivo"))

  clave_valida = _clave_pro_configurada()
  if clave_valida and hmac.compare_digest(
      clave.encode("utf-8"), str(clave_valida).encode("utf-8")
  ):
    return True, None
  return False, "⚠️ Clave de licencia no válida."


es_pro = False
if tipo_plan == "Pro / Premium ⭐":
  clave_pro = st.sidebar.text_input("Clave de Licencia Pro", type="password")
  if not _config_licencias() and not _clave_pro_configurada():
    st.sidebar.error("Las licencias Pro no están configuradas en este despliegue.")
  elif clave_pro:
    es_pro, error_licencia = validar_licencia_pro(clave_pro)
    if es_pro:
      st.sidebar.success("✅ Licencia Pro Activa")
    else:
      st.sidebar.warning(error_licencia)

st.sidebar.divider()
st.sidebar.header("⚙️ Parámetros de Monedas")
trm = st.sidebar.number_input(
    "TRM Oficial (COP / USD)", min_value=1000.0, value=trm_oficial, step=10.0
)
if trm_es_oficial:
  st.sidebar.caption(f"TRM oficial vigente desde {trm_fecha} (datos.gov.co)")
else:
  st.sidebar.warning(
      "⚠️ No se pudo consultar la TRM oficial. Se muestra un valor de respaldo"
      f" ({TRM_RESPALDO:,.0f} COP/USD), que NO es la TRM vigente. Ingresa la"
      " TRM actual manualmente."
  )

if es_pro:
  st.sidebar.subheader("💱 Tasa Fronteriza (Multi-moneda)")
  tasa_ves_cop = st.sidebar.number_input(
      "Tasa COP / Bolívares (VES)", value=0.08, step=0.01, format="%.4f"
  )
  tasa_usdt_cop = st.sidebar.number_input(
      "Tasa COP / USDT (Cripto)", value=4050.0, step=10.0
  )
else:
  tasa_ves_cop = 0.08
  tasa_usdt_cop = 4050.0


# ==================== ENCABEZADO PRINCIPAL ====================
st.markdown(
    """
    <div class="hero-header">
        <div class="hero-title">🚢 FronteraIQ Pro</div>
        <div class="hero-subtitle">Plataforma de Inteligencia Aduanera y Cálculo de Costos Landed en Cúcuta</div>
    </div>
""",
    unsafe_allow_html=True,
)


# ==================== FORMULARIO ====================
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
  st.subheader("📦 Mercancía y Partida NANDINA")

  producto_sel = st.selectbox(
      "🔍 Seleccionar o buscar tipo de producto",
      list(DATABASE_NANDINA.keys()),
  )
  partida_info = DATABASE_NANDINA[producto_sel]

  if producto_sel == "Personalizado / Otra partida":
    producto = st.text_input("Nombre / Referencia", value="Mercancía General")
    partida_arancelaria = st.text_input(
        "Subpartida Arancelaria", value="0000.00.00.00"
    )
    def_arancel = 10.0
    def_iva = 19.0
  else:
    producto = producto_sel
    partida_arancelaria = st.text_input(
        "Subpartida NANDINA (Autocompletada)", value=partida_info["codigo"]
    )
    def_arancel = partida_info["arancel"]
    def_iva = partida_info["iva"]
    validacion = PARTIDAS_VALIDADAS.get(partida_info["codigo"])
    if validacion:
      st.caption(
          f"✅ Arancel e IVA validados · Fuente: {validacion['fuente']} ·"
          f" Vigencia: {validacion['vigencia']}"
      )
    else:
      st.warning(
          "Arancel e IVA de **referencia**, pendientes de validación por un"
          " agente de aduanas. Confírmalos con la normativa vigente antes de"
          " operar; puedes ajustarlos en los campos de la derecha."
      )

  unidades = st.number_input(
      "Cantidad de Unidades", min_value=1, value=1000, step=1
  )

  st.markdown("#### 💰 Valores de la Carga (USD)")
  fob_usd = st.number_input(
      "Valor FOB Total (USD)", min_value=0.0, value=10000.0, step=100.0
  )
  flete_usd = st.number_input(
      "Flete Internacional (USD)", min_value=0.0, value=1200.0, step=50.0
  )
  seguro_usd = st.number_input(
      "Seguro Internacional (USD)", min_value=0.0, value=150.0, step=10.0
  )

with col_right:
  st.subheader("🏛️ Impuestos y Gastos Locales")

  col_imp1, col_imp2 = st.columns(2)
  with col_imp1:
    pct_arancel = st.number_input(
        "Arancel (%)",
        min_value=0.0,
        max_value=100.0,
        value=def_arancel,
        step=0.5,
    )
  with col_imp2:
    pct_iva = st.number_input(
        "IVA (%)", min_value=0.0, max_value=100.0, value=def_iva, step=1.0
    )

  st.markdown("#### 🚚 Logística Frontera Cúcuta (COP)")
  agenciamiento_cop = st.number_input(
      "Agenciamiento SIA (COP)", min_value=0.0, value=450000.0, step=50000.0
  )
  bodegaje_cop = st.number_input(
      "Bodegaje / Depósito (COP)", min_value=0.0, value=300000.0, step=25000.0
  )
  transporte_local_cop = st.number_input(
      "Transporte Terrestre Local (COP)",
      min_value=0.0,
      value=800000.0,
      step=50000.0,
  )
  otros_gastos_cop = st.number_input(
      "Otros Gastos / Inspecciones (COP)",
      min_value=0.0,
      value=200000.0,
      step=25000.0,
  )

  pct_margen = st.number_input(
      "Margen Deseado (%)",
      min_value=0.0,
      max_value=99.0,
      value=30.0,
      step=1.0,
  )


# ==================== CÁLCULOS ====================
cif_usd = fob_usd + flete_usd + seguro_usd
cif_cop = cif_usd * trm

arancel_cop = cif_cop * (pct_arancel / 100)
base_iva_cop = cif_cop + arancel_cop
iva_cop = base_iva_cop * (pct_iva / 100)
total_tributos_cop = arancel_cop + iva_cop

total_gastos_locales_cop = (
    agenciamiento_cop + bodegaje_cop + transporte_local_cop + otros_gastos_cop
)
costo_total_landed_cop = cif_cop + total_tributos_cop + total_gastos_locales_cop
costo_unitario_cop = costo_total_landed_cop / unidades if unidades > 0 else 0
precio_sugerido_unitario_cop = (
    costo_unitario_cop / (1 - (pct_margen / 100)) if pct_margen < 100 else 0
)

costo_total_ves = (
    costo_total_landed_cop / tasa_ves_cop if tasa_ves_cop > 0 else 0
)
costo_total_usdt = (
    costo_total_landed_cop / tasa_usdt_cop if tasa_usdt_cop > 0 else 0
)


# ==================== DATOS DE LA COTIZACIÓN (TRAZABILIDAD) ====================
es_personalizada = producto_sel == "Personalizado / Otra partida"
porcentajes_ajustados = (not es_personalizada) and (
    pct_arancel != def_arancel or pct_iva != def_iva
)
emision = datetime.now(ZONA_COLOMBIA)

datos_cotizacion = {
    "producto": producto,
    "partida": partida_arancelaria,
    "unidades": unidades,
    "fob_usd": fob_usd,
    "flete_usd": flete_usd,
    "seguro_usd": seguro_usd,
    "cif_usd": cif_usd,
    "cif_cop": cif_cop,
    "trm": trm,
    "pct_arancel": pct_arancel,
    "pct_iva": pct_iva,
    "arancel_cop": arancel_cop,
    "iva_cop": iva_cop,
    "total_tributos_cop": total_tributos_cop,
    "agenciamiento_cop": agenciamiento_cop,
    "bodegaje_cop": bodegaje_cop,
    "transporte_local_cop": transporte_local_cop,
    "otros_gastos_cop": otros_gastos_cop,
    "gastos_locales_cop": total_gastos_locales_cop,
    "costo_total_landed_cop": costo_total_landed_cop,
    "costo_unitario_cop": costo_unitario_cop,
    "pct_margen": pct_margen,
    "precio_sugerido_unitario_cop": precio_sugerido_unitario_cop,
    "emision": emision,
    "origen_trm": origen_trm(trm, trm_oficial, trm_fecha, trm_es_oficial),
    "estado_aranceles": estado_aranceles(
        es_personalizada,
        porcentajes_ajustados,
        None if es_personalizada else PARTIDAS_VALIDADAS.get(partida_info["codigo"]),
    ),
}
datos_cotizacion["codigo"] = codigo_cotizacion(datos_cotizacion, emision)


# ==================== PRESENTACIÓN DE RESULTADOS ====================
st.divider()
st.subheader("📈 Resumen de Resultados")

m1, m2, m3, m4 = st.columns(4)

m1.markdown(
    f"""
    <div class="metric-card">
        <div class="metric-label">Costo Total Landed</div>
        <div class="metric-value">$ {costo_total_landed_cop:,.0f}</div>
        <div class="metric-subtext">COP Puesto en Cúcuta</div>
    </div>
""",
    unsafe_allow_html=True,
)

m2.markdown(
    f"""
    <div class="metric-card">
        <div class="metric-label">Costo Unitario</div>
        <div class="metric-value" style="color:#60a5fa;">$ {costo_unitario_cop:,.2f}</div>
        <div class="metric-subtext" style="color:#94a3b8;">Por unidad importada</div>
    </div>
""",
    unsafe_allow_html=True,
)

m3.markdown(
    f"""
    <div class="metric-card">
        <div class="metric-label">Impuestos DIAN</div>
        <div class="metric-value" style="color:#f87171;">$ {total_tributos_cop:,.0f}</div>
        <div class="metric-subtext" style="color:#94a3b8;">Arancel + IVA</div>
    </div>
""",
    unsafe_allow_html=True,
)

m4.markdown(
    f"""
    <div class="metric-card">
        <div class="metric-label">Precio Venta Sugerido</div>
        <div class="metric-value">$ {precio_sugerido_unitario_cop:,.2f}</div>
        <div class="metric-subtext">Margen {pct_margen}%</div>
    </div>
""",
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

if es_pro:
  st.info(
      f"💱 **Equivalencia Fronteriza (Pro):** Costo Total en **USDT:**"
      f" `{costo_total_usdt:,.2f} USDT` | **Bolívares (VES):**"
      f" `{costo_total_ves:,.2f} VES`"
  )

col_chart, col_table = st.columns([1, 1], gap="large")

with col_chart:
  st.markdown("#### Distribución de Costos")
  df_chart = pd.DataFrame({
      "Concepto": ["CIF", "Tributos DIAN", "Gastos Locales"],
      "Monto_COP": [cif_cop, total_tributos_cop, total_gastos_locales_cop],
  })
  fig = px.pie(
      df_chart,
      values="Monto_COP",
      names="Concepto",
      hole=0.4,
      color_discrete_sequence=["#38bdf8", "#f87171", "#818cf8"],
  )
  st.plotly_chart(fig, width="stretch")

with col_table:
  st.markdown("#### Desglose de Liquidación")
  liquidacion_data = {
      "Concepto": [
          "Valor CIF (USD)",
          "Valor CIF (COP)",
          "Arancel DIAN (COP)",
          "IVA DIAN (COP)",
          "Total Impuestos",
          "Gastos Cúcuta",
          "COSTO TOTAL LANDED",
      ],
      "Monto": [
          f"$ {cif_usd:,.2f} USD",
          f"$ {cif_cop:,.0f} COP",
          f"$ {arancel_cop:,.0f} COP",
          f"$ {iva_cop:,.0f} COP",
          f"$ {total_tributos_cop:,.0f} COP",
          f"$ {total_gastos_locales_cop:,.0f} COP",
          f"$ {costo_total_landed_cop:,.0f} COP",
      ],
  }
  st.dataframe(
      pd.DataFrame(liquidacion_data), width="stretch", hide_index=True
  )


# ==================== ACCIONES Y REPORTES ====================
st.divider()
st.subheader("📲 Acciones Directas")
st.caption(
    f"Código de cotización: **{datos_cotizacion['codigo']}** · TRM:"
    f" {datos_cotizacion['origen_trm']}"
)

mensaje_whatsapp = f"""Hola, requiero asesoría aduanera para la siguiente operación en FronteraIQ:

📌 *Producto:* {producto}
🔢 *Partida:* {partida_arancelaria}
📦 *Cantidad:* {unidades:,} uds
💵 *Valor CIF:* ${cif_usd:,.2f} USD
🏛️ *Tributos DIAN:* ${total_tributos_cop:,.0f} COP
🚚 *Costo Landed Total:* ${costo_total_landed_cop:,.0f} COP"""

mensaje_encoded = urllib.parse.quote(mensaje_whatsapp)
url_whatsapp = (
    f"https://api.whatsapp.com/send?phone={TELEFONO_WHATSAPP}&text={mensaje_encoded}"
)

c1, c2, c3 = st.columns([1, 1, 1])

with c1:
  st.markdown(
      f'<a href="{url_whatsapp}" target="_blank" class="whatsapp-btn">💬'
      " Contactar por WhatsApp</a>",
      unsafe_allow_html=True,
  )

with c2:
  if es_pro:
    try:
      pdf_bytes = generar_pdf_cotizacion(datos_cotizacion)
    except Exception:
      pdf_bytes = None
      st.error("No se pudo generar el PDF. Revisa el nombre del producto.")
    if pdf_bytes:
      nombre_seguro = re.sub(r"[^A-Za-z0-9_-]+", "_", producto).strip("_")
      st.download_button(
          label="📄 Descargar Cotización PDF (Pro)",
          data=pdf_bytes,
          file_name=f"{datos_cotizacion['codigo']}_{nombre_seguro or 'producto'}.pdf",
          mime="application/pdf",
          width="stretch",
      )
  else:
    st.button(
        "📄 Descargar PDF (Licencia Pro 🔒)",
        disabled=True,
        width="stretch",
    )

with c3:
  df_export = pd.DataFrame([fila_csv(datos_cotizacion)])
  csv = df_export.to_csv(index=False).encode("utf-8-sig")  # BOM: Excel lee bien las tildes
  st.download_button(
      label="📥 Exportar a CSV",
      data=csv,
      file_name=f"{datos_cotizacion['codigo']}.csv",
      mime="text/csv",
      width="stretch",
  )
