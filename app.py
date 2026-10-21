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
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import licencias  # noqa: E402  (licencias por cliente, ver supabase/)
import importlib  # noqa: E402
import partidas_validadas as _pv  # noqa: E402
if not (hasattr(_pv, "cargar_validaciones") and hasattr(_pv, "catalogo_ampliado")):
  # Tras un redeploy, Streamlit Cloud puede conservar en memoria una versión antigua del módulo.
  importlib.reload(_pv)
from partidas_validadas import cargar_validaciones, catalogo_ampliado  # noqa: E402
import analitica  # noqa: E402
import dian_arancel  # noqa: E402

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(
    page_title="FronteraIQ Pro — Inteligencia Aduanera Cúcuta",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "favicon.png"),
    layout="wide",
    initial_sidebar_state="auto",
)

def num(valor, decimales=0):
  """Formato colombiano: punto de miles y coma decimal (1.234.567,89)."""
  txt = f"{valor:,.{decimales}f}"
  return txt.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


# ==================== ICONOS FRONTERAIQ ====================
# Set propio (ver Design System): rejilla de 24 px, trazo de 2 px, terminales redondeados.
ICONOS = {
    "contenedor": '<rect x="3" y="6" width="18" height="12"/><path d="M7 6v12M12 6v12M17 6v12"/>',
    "mercancia": '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    "valores": '<circle cx="12" cy="12" r="9"/><path d="M12 6v12M15.5 9H10a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H8.5"/>',
    "tributos": '<path d="M3 21h18M5 21V10M9 21V10M15 21V10M19 21V10M3 10l9-6 9 6z"/>',
    "logistica": '<path d="M2 6h12v10H2zM14 9h4l4 4v3h-8z"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
    "resultados": '<path d="M3 3v18h18M7 15l4-4 3 3 5-6"/>',
    "acciones": '<path d="M3 4h18v13H9l-6 4z"/>',
    "acceso": '<rect x="5" y="11" width="14" height="10"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "parametros": '<path d="M4 7h16M4 17h16"/><circle cx="8" cy="7" r="2"/><circle cx="16" cy="17" r="2"/>',
    "cambio": '<path d="M4 8h14l-3-3M20 16H6l3 3"/>',
    "buscar": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
    "validado": '<path d="M4 12l5 5L20 6"/>',
    "alerta": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.01"/>',
    "descargar": '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    "flecha": '<path d="M5 12h14M13 6l6 6-6 6"/>',
}


def icono(nombre, tamano=22):
  """SVG en línea del set FronteraIQ; toma el color del texto (currentColor)."""
  return (
      f'<svg class="fiq-icono" width="{tamano}" height="{tamano}" viewBox="0 0 24 24"'
      ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
      f' stroke-linejoin="round" aria-hidden="true">{ICONOS[nombre]}</svg>'
  )


def titulo(nombre, texto, nivel=3, destino=None):
  """Título con icono propio (reemplaza a los emoji)."""
  (destino or st).markdown(
      f'<h{nivel} class="fiq-titulo">{icono(nombre, 22 if nivel < 4 else 20)}{texto}</h{nivel}>',
      unsafe_allow_html=True,
  )


TELEFONO_WHATSAPP = "573156491042"  # <-- REEMPLAZA CON TU NÚMERO (Prefijo 57)

# ==================== INYECCIÓN CSS SEGURA ====================
css_code = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600..800&family=Atkinson+Hyperlegible+Next:wght@400;500;600;700;800&display=swap');

/* Design System FronteraIQ v2: lenguaje de producto financiero claro (referencia: Wise).
   Paneles menta, píldoras, un solo protagonista oscuro: el panel de cotización. */
:root {
    --fiq-page: #FFFFFF; --fiq-surface: #FFFFFF; --fiq-panel: #EEF4F2; --fiq-raised: #FFFFFF;
    --fiq-ink: #0B2527; --fiq-muted: #4A6769; --fiq-signal: #F5B700; --fiq-signal-hover: #FFC61A;
    --fiq-on-signal: #0B2527; --fiq-on-ink: #F2F7F5; --fiq-on-ink-muted: #B9CCCB;
    --fiq-line: #D3DFDC; --fiq-focus: #1F4FD8; --fiq-teal: #2E6F73; --fiq-teal-light: #6FB0B3;
    --fiq-success: #166A3E; --fiq-critical: #B3261E;
    --fiq-r-card: 28px; --fiq-r-field: 14px; --fiq-r-pill: 999px;
    --fiq-ease: cubic-bezier(0.23, 1, 0.32, 1);
}

html, body, [class*="css"],
.stApp :not([data-testid="stIconMaterial"]):not([class*="material" i]):not(:is(h1, h2, h3, h4, .metric-value, .hero-title, .fiq-display) *):not(h1):not(h2):not(h3):not(h4):not(.metric-value):not(.hero-title):not(.fiq-display) {
    font-family: 'Atkinson Hyperlegible Next', system-ui, sans-serif;
}
.stApp { background: var(--fiq-page); color: var(--fiq-ink); }
.block-container { max-width: 1240px !important; padding-top: 4.5rem !important; }
[data-testid="stHeader"] { background: transparent; }

h1, h2, h3, h4, .fiq-display {
    font-family: 'Bricolage Grotesque', system-ui, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    line-height: 1.08 !important;
    color: var(--fiq-ink);
}
h2 { font-size: 1.4rem !important; }
h3 { font-size: 1.7rem !important; }
h4 { font-size: 1.25rem !important; }
hr { border-color: var(--fiq-line) !important; }

/* Iconos en fichas redondas */
.fiq-icono { display: inline-block; vertical-align: -0.2em; flex: none; }
.fiq-titulo, .fiq-titulo > span { display: flex !important; align-items: center; gap: 12px; }
.fiq-titulo { margin: 0 0 4px !important; }
.fiq-titulo .fiq-icono { box-sizing: content-box; padding: 9px; background: var(--fiq-signal); color: var(--fiq-ink); border-radius: var(--fiq-r-pill); }

/* Barra superior y encabezado de la calculadora */
.fiq-topbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px 20px; margin-bottom: 36px; }
.fiq-logo { display: flex; align-items: center; gap: 12px; font-family: 'Bricolage Grotesque', system-ui, sans-serif; font-weight: 800; font-size: 30px; letter-spacing: -0.03em; line-height: 1; }
.fiq-logo .fiq-icono { box-sizing: content-box; padding: 9px; background: var(--fiq-ink); color: var(--fiq-signal); border-radius: var(--fiq-r-pill); }
.fiq-logo .fiq-pro { background: var(--fiq-signal); padding: 3px 10px; border-radius: var(--fiq-r-pill); font-family: 'Atkinson Hyperlegible Next', sans-serif; font-size: 14px; letter-spacing: 0; }
.rate-chip { display: inline-flex; align-items: center; gap: 10px; background: var(--fiq-panel); padding: 9px 18px; border-radius: var(--fiq-r-pill); font-weight: 700; font-size: 14px; font-variant-numeric: tabular-nums; }
.rate-chip i { width: 9px; height: 9px; border-radius: 50%; background: var(--fiq-success); }
.rate-chip.is-warn { background: #FBE9E7; color: var(--fiq-critical); }
.rate-chip.is-warn i { background: var(--fiq-critical); }
.page-title { font-size: clamp(38px, 4.6vw, 62px); max-width: 860px; margin: 0 0 14px; }
.page-sub { font-size: 18px; color: var(--fiq-muted); max-width: 640px; margin: 0 0 36px; }

/* Pasos del formulario: paneles menta con campos blancos */
.st-key-paso-mercancia, .st-key-paso-valores, .st-key-paso-tributos, .st-key-paso-logistica {
    background: var(--fiq-panel); border-radius: var(--fiq-r-card); padding: 28px 28px 20px;
}
.st-key-paso-mercancia, .st-key-paso-valores, .st-key-paso-tributos { margin-bottom: 20px; }
[data-testid="stColumn"]:has(.st-key-quote) > [data-testid="stVerticalBlock"] { height: 100%; }
.st-key-quote { position: sticky; top: 1.25rem; }

/* Campos */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"] {
    border-radius: var(--fiq-r-field) !important;
}
[data-baseweb="input"], [data-baseweb="select"] > div {
    background: #FFFFFF !important; border: 1.5px solid transparent !important; min-height: 52px;
    transition: border-color 140ms var(--fiq-ease), box-shadow 140ms var(--fiq-ease);
}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
    border-color: var(--fiq-ink) !important; box-shadow: 0 0 0 4px rgba(245, 183, 0, 0.45);
}
[data-testid="stNumberInputContainer"] { border-radius: var(--fiq-r-field) !important; }
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input { font-size: 17px; font-weight: 600; font-variant-numeric: tabular-nums; }
[data-testid="stWidgetLabel"] p, label p { font-weight: 700; font-size: 14px; color: var(--fiq-ink); }
.st-key-in_fob input { font-family: 'Bricolage Grotesque', system-ui, sans-serif; font-size: 30px; font-weight: 800; letter-spacing: -0.02em; }
.st-key-in_fob [data-baseweb="input"] { min-height: 68px; }
[data-testid="stCaptionContainer"] { color: var(--fiq-muted); }
[data-testid="stAlert"] { border-radius: 20px; }
[data-testid="stDataFrame"] { border-radius: 20px; overflow: hidden; }

/* Barra lateral: plan y monedas */
[data-testid="stSidebar"] { background: var(--fiq-panel); }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] { background: #FFFFFF; padding: 5px; border-radius: var(--fiq-r-pill); gap: 4px; flex-wrap: nowrap; width: 100%; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] p { white-space: nowrap; font-size: 14px; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div { flex: 1; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] { width: 100%; justify-content: center; margin: 0; padding: 9px 6px; border-radius: var(--fiq-r-pill); cursor: pointer; transition: background-color 140ms var(--fiq-ease); }
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child { display: none; }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background: var(--fiq-ink); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p { color: #FFFFFF; }

/* Panel de cotización: el protagonista oscuro */
.st-key-quote > [data-testid="stVerticalBlock"], .st-key-quote { gap: 0 !important; }
.quote { background: var(--fiq-ink); color: var(--fiq-on-ink); border-radius: var(--fiq-r-card); padding: 30px 30px 26px; }
.quote-top { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.quote-top .quote-label { font-size: 16px; font-weight: 700; color: var(--fiq-on-ink-muted); }
.quote .rate-chip { background: rgba(255, 255, 255, 0.1); color: var(--fiq-on-ink); font-size: 13px; padding: 6px 14px; }
.quote .rate-chip i { background: #6BD39B; }
.quote .rate-chip.is-warn { background: #FBE9E7; color: var(--fiq-critical); }
.quote .rate-chip.is-warn i { background: var(--fiq-critical); }
.quote .metric-value.is-hero { font-size: clamp(36px, 3.7vw, 54px); color: var(--fiq-signal); margin: 10px 0 4px; letter-spacing: -0.03em; }
.quote .metric-subtext { color: var(--fiq-on-ink-muted); opacity: 1; }
.quote-barra { display: flex; height: 12px; border-radius: var(--fiq-r-pill); overflow: hidden; background: rgba(255, 255, 255, 0.12); margin: 22px 0 14px; gap: 2px; }
.quote-barra i { display: block; }
.quote-leyenda { display: grid; gap: 8px; font-size: 14px; font-variant-numeric: tabular-nums; }
.quote-leyenda div { display: flex; align-items: center; gap: 10px; }
.quote-leyenda b { width: 10px; height: 10px; border-radius: 50%; flex: none; }
.quote-leyenda span:last-child { margin-left: auto; font-weight: 700; }
.quote-filas { margin-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.16); }
.quote-fila { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.16); }
.quote-fila .quote-nombre { font-weight: 700; font-size: 15px; }
.quote-fila .metric-subtext { font-size: 13px; }
.quote-fila .metric-value { font-size: 24px; text-align: right; }
.quote-nota { font-size: 12.5px; color: var(--fiq-on-ink-muted); margin: 16px 0 18px; }

.metric-value {
    font-family: 'Bricolage Grotesque', system-ui, sans-serif;
    font-weight: 800; letter-spacing: -0.02em; line-height: 1.05; white-space: nowrap;
    font-variant-numeric: tabular-nums; color: inherit;
    animation: fiq-asentar 260ms var(--fiq-ease);
}
.metric-subtext { font-size: 14px; font-weight: 600; color: var(--fiq-muted); }
@keyframes fiq-asentar { from { opacity: 0.35; transform: translateY(4px); } to { opacity: 1; transform: none; } }

/* Botones: píldoras */
[data-testid^="stBaseButton"], .stButton > button, .stDownloadButton > button {
    border-radius: var(--fiq-r-pill) !important; min-height: 52px !important; font-weight: 800 !important; padding: 0 28px !important;
    transition: transform 140ms var(--fiq-ease), background-color 140ms var(--fiq-ease);
}
[data-testid="stBaseButton-primary"] { background: var(--fiq-signal) !important; border: 0 !important; color: var(--fiq-on-signal) !important; }
[data-testid="stBaseButton-primary"] p { color: var(--fiq-on-signal) !important; }
[data-testid="stBaseButton-primary"]:hover { background: var(--fiq-signal-hover) !important; }
[data-testid="stBaseButton-secondary"] { background: transparent !important; border: 2px solid var(--fiq-ink) !important; color: var(--fiq-ink) !important; }
[data-testid="stBaseButton-secondary"]:hover { background: var(--fiq-panel) !important; }
[data-testid^="stBaseButton"]:disabled { background: var(--fiq-panel) !important; border: 2px solid var(--fiq-line) !important; color: var(--fiq-muted) !important; }
[data-testid^="stBaseButton"]:active:not(:disabled) { transform: scale(0.97); }

.whatsapp-btn {
    background: var(--fiq-signal); color: var(--fiq-on-signal) !important; font-weight: 800;
    padding: 12px 28px; min-height: 52px; box-sizing: border-box; border-radius: var(--fiq-r-pill);
    text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 10px;
    font-size: 16px; text-align: center;
    transition: transform 140ms var(--fiq-ease), background-color 140ms var(--fiq-ease);
}
.whatsapp-btn, .whatsapp-btn:hover { text-decoration: none !important; }
.whatsapp-btn:hover { background: var(--fiq-signal-hover); }
.whatsapp-btn .fiq-icono { margin: 0; transition: transform 160ms var(--fiq-ease); }
.whatsapp-btn:hover .fiq-icono { transform: translateX(3px); }
button:focus-visible, a:focus-visible { outline: 3px solid var(--fiq-focus) !important; outline-offset: 3px; }
.whatsapp-btn:active { transform: scale(0.97); }

/* Detalle de la liquidación */
.st-key-detalle { background: var(--fiq-panel); border-radius: var(--fiq-r-card); padding: 28px; }

@media (max-width: 900px) {
    .st-key-quote { position: static; }
    .st-key-paso-mercancia, .st-key-paso-valores, .st-key-paso-tributos, .st-key-paso-logistica { padding: 20px 18px 14px; }
    .quote { padding: 24px 20px 20px; }
}
@media (prefers-reduced-motion: reduce) {
    [data-testid^="stBaseButton"], .whatsapp-btn, .whatsapp-btn .fiq-icono, [data-baseweb="input"], [data-baseweb="select"] > div { transition: none; }
    [data-testid^="stBaseButton"]:active:not(:disabled), .whatsapp-btn:active { transform: none; }
    .metric-value { animation: none; }
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


ESPERA_TRAS_FALLO_S = 60


@st.cache_resource
def _estado_trm():
  """Estado compartido entre sesiones: cuándo se puede volver a intentar tras un fallo."""
  return {"reintentar_desde": 0.0}


def obtener_trm_actual(ahora=time.monotonic):
  """Devuelve (valor, fecha, es_oficial). Si la consulta falla, usa el respaldo.

  Tras un fallo no se vuelve a consultar durante ESPERA_TRAS_FALLO_S segundos: así una
  fuente caída no añade hasta 5 s de espera a cada interacción. El fallo nunca se guarda
  como si fuera una TRM; pasado ese tiempo se reintenta.
  """
  estado = _estado_trm()
  if ahora() < estado["reintentar_desde"]:
    return TRM_RESPALDO, "", False
  try:
    valor, fecha = _consultar_trm()
    return valor, fecha, True
  except Exception:
    estado["reintentar_desde"] = ahora() + ESPERA_TRAS_FALLO_S
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
        "arancel": 15.0,
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
        "iva": 19.0,
    },
    "Arroz Blanqueado - Grano Corto o Mediano": {
        "codigo": "1006.30.00.10",
        "arancel": 15.0,
        "iva": 0.0,
    },
    "Arroz Blanqueado - Los Demás Granos": {
        "codigo": "1006.30.00.90",
        "arancel": 80.0,
        "iva": 0.0,
    },
    "Repuestos y Autopartes": {
        "codigo": "8708.29.90.00",
        "arancel": 10.0,
        "iva": 19.0,
    },
    "Medicamentos de Uso Humano - Los Demás": {
        "codigo": "3004.90.29.00",
        "arancel": 10.0,
        "iva": 0.0,
    },
}

# Partidas cuyo arancel/IVA fueron contrastados con una fuente oficial (DIAN) o por un agente.
# Se carga de docs/validacion-nandina.csv (ver docs/GUIA-VALIDACION-ARANCELES.md).
# Mientras una partida no esté aquí, la interfaz la marca como "pendiente".
PARTIDAS_VALIDADAS, _PROBLEMAS_VALIDACION = cargar_validaciones(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "validacion-nandina.csv")
)

# Selector: las 7 de referencia + las partidas nuevas que un agente ya validó.
CATALOGO_NANDINA = catalogo_ampliado(DATABASE_NANDINA, PARTIDAS_VALIDADAS)


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


@st.cache_resource
def cliente_dian():
  return dian_arancel.ClienteDian()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def dian_consulta(codigo):
  return cliente_dian().consultar(codigo)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def dian_subdivisiones(prefijo):
  return cliente_dian().subdivisiones(prefijo)


def etiqueta_iva(o):
  condicion = o.producto or "Tarifa general"
  return f"{o.porcentaje:g} %{' · ' + o.etiqueta.lower() if o.etiqueta else ''} — {condicion}"


def etiqueta_acuerdo(a):
  return f"{a.pais} — {a.acuerdo}: {a.porcentaje:g} %"


def bloque_dian_en_vivo():
  """Subpartida libre consultada en la DIAN. Devuelve (consulta, arancel, iva, origen) o None si hay que ingresar a mano."""
  entrada = st.text_input(
      "Subpartida Arancelaria (6, 8 o 10 dígitos)", value="", placeholder="6109.10.00.00",
      help="Se consulta la tarifa vigente en el Arancel de Aduanas de la DIAN.",
  )
  if not entrada.strip():
    st.caption("Escribe la subpartida para traer arancel e IVA de la DIAN, o ingrésalos a mano a la derecha.")
    return None
  try:
    codigo = dian_arancel.normalizar_codigo(entrada)
  except ValueError as error:
    st.error(str(error))
    return None
  try:
    if len(codigo) < 10:
      with st.spinner("Buscando subdivisiones en la DIAN (puede tardar hasta un minuto)..."):
        opciones = dian_subdivisiones(codigo)
      if not opciones:
        st.error("La DIAN no tiene subpartidas con ese código. Revísalo con tu agente de aduanas.")
        return None
      if len(opciones) == 1:
        codigo = opciones[0][0]
      else:
        elegido = st.selectbox("Subdivisión", opciones,
                               format_func=lambda o: f"{dian_arancel.formatear_codigo(o[0])} — {o[1][:90]}")
        codigo = elegido[0]
    with st.spinner("Consultando la DIAN..."):
      consulta = dian_consulta(codigo)
  except dian_arancel.DianNoDisponible:
    st.warning("No pude consultar la DIAN ahora. Ingresa arancel e IVA a mano (valores de referencia 10 % / 19 %)"
               " y confírmalos con tu agente de aduanas.")
    return None
  if consulta is None:
    st.error(f"La subpartida {dian_arancel.formatear_codigo(codigo)} no existe en el Arancel de la DIAN."
             " Escribe solo los primeros 6 u 8 dígitos para ver las subpartidas reales de esa partida.")
    return None

  st.caption(f"**{dian_arancel.formatear_codigo(consulta.codigo)}** — {consulta.descripcion}")
  arancel = consulta.arancel_aplicable
  if consulta.arancel_variable is not None:
    st.info(f"**Arancel variable vigente: {consulta.arancel_variable:g} %** (el general es"
            f" {consulta.arancel_general:g} %). Cambia cada quincena según el precio de referencia.")
  iva_opciones = sorted(consulta.iva, key=lambda o: -o.porcentaje)
  iva = iva_opciones[0].porcentaje
  if len(iva_opciones) > 1:
    elegida = st.selectbox("IVA según la condición del producto", iva_opciones, format_func=etiqueta_iva)
    iva = elegida.porcentaje
    st.caption("Esa subpartida tiene tarifas de IVA distintas según el producto. Se propone la más alta;"
               " elige la que corresponda a tu mercancía.")
  origen = "Tarifa general"
  if consulta.acuerdos:
    sin = "Sin acuerdo (tarifa general)"
    acuerdo = st.selectbox("País de origen / acuerdo comercial", [sin, *consulta.acuerdos],
                           format_func=lambda a: a if a == sin else etiqueta_acuerdo(a))
    if acuerdo != sin:
      arancel = acuerdo.porcentaje
      origen = etiqueta_acuerdo(acuerdo)
      st.caption("La preferencia exige certificado de origen válido; sin él se paga la tarifa general.")
  st.caption(f"Fuente: DIAN, Consulta de Arancel en línea (MUISCA) · consultado {date_hoy_texto()}")
  return consulta, arancel, iva, origen


def date_hoy_texto():
  return datetime.now(ZONA_COLOMBIA).strftime("%Y-%m-%d")


def estado_aranceles(personalizada, ajustados, validacion, dian=None):
  """Estado de los porcentajes de arancel e IVA usados en la cotización."""
  if dian:
    base = f"Consultados en vivo en la DIAN (MUISCA) el {date_hoy_texto()}. Tarifa: {dian}"
    return base + (". Ajustados luego por el usuario" if ajustados else "")
  if personalizada:
    return "Ingresados por el usuario (partida personalizada)"
  if ajustados:
    return "Ajustados por el usuario respecto a la tabla de referencia"
  if validacion:
    return f"Validados. Fuente: {validacion['fuente']}. Consultado: {validacion['vigencia']}"
  return "Valores de referencia, pendientes de validacion"


def lineas_liquidacion(d):
  """Filas (concepto, valor, destacada) de la liquidación, para el PDF."""
  usd = lambda v: f"${num(v, 2)} USD"
  cop = lambda v: f"${num(v)} COP"
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
      ("COSTO LANDED UNITARIO", f"${num(d['costo_unitario_cop'], 2)} COP", True),
      (f"Margen deseado ({d['pct_margen']:g} % sobre el precio)", "", False),
      ("PRECIO DE VENTA SUGERIDO (UNITARIO)", f"${num(d['precio_sugerido_unitario_cop'], 2)} COP", True),
  ]


def texto_para_csv(valor):
  """Neutraliza la inyección de fórmulas: Excel interpreta como fórmula un texto que
  empiece por = + - @ (o tabulación / retorno). Se antepone un apóstrofo."""
  if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
    return "'" + valor
  return valor


def fila_csv(d):
  """Una fila de CSV con todo lo necesario para reconstruir la cotización."""
  return {k: texto_para_csv(v) for k, v in {
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
  }.items()}


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
      ("Cantidad", f"{num(datos['unidades'])} uds"),
      ("TRM aplicada", f"${num(datos['trm'], 2)} COP/USD"),
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


def registrar_evento(evento, dato=None):
  """Mide uso anónimo (una vez por sesión y evento/dato). Nunca interrumpe la app."""
  try:
    if "sesion_id" not in st.session_state:
      st.session_state["sesion_id"] = uuid.uuid4().hex
    visto = st.session_state.setdefault("_eventos_enviados", set())
    clave = (evento, dato)
    if clave in visto:
      return
    visto.add(clave)
    analitica.registrar(evento, st.session_state["sesion_id"], _config_licencias(), dato)
  except Exception:
    pass


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
  return False, "Clave de licencia no válida."




def equivalencias_moneda(costo_cop, trm, bs_por_usd, cop_por_usdt):
  """Costo landed en USDT y en bolívares.

  Los bolívares se calculan vía dólares (costo COP / TRM × Bs por USD), con la tasa que
  escribe el usuario; sin tasa no hay cifra (None) en lugar de un valor inventado.
  """
  usd = costo_cop / trm if trm and trm > 0 else None
  ves = usd * bs_por_usd if usd is not None and bs_por_usd and bs_por_usd > 0 else None
  usdt = costo_cop / cop_por_usdt if cop_por_usdt and cop_por_usdt > 0 else None
  return {"usd": usd, "ves": ves, "usdt": usdt}


def calcular_embarque(items, flete_usd, seguro_usd, trm, gastos_locales_cop, pct_margen):
  """Liquida un embarque con varias mercancías.

  Flete, seguro y gastos locales se reparten entre las líneas según su peso en el
  FOB total (si el FOB total es 0, en partes iguales). Cada línea lleva su propio
  arancel e IVA. Devuelve (lineas, totales); cada línea es un dict.
  """
  n = len(items)
  fob_total = sum(max(float(i["fob_usd"]), 0.0) for i in items)
  lineas = []
  for i in items:
    fob = max(float(i["fob_usd"]), 0.0)
    unidades = max(float(i["unidades"]), 0.0)
    peso = (fob / fob_total) if fob_total > 0 else (1 / n if n else 0)
    cif_usd = fob + flete_usd * peso + seguro_usd * peso
    cif_cop = cif_usd * trm
    pct_arancel = min(max(float(i["pct_arancel"]), 0.0), 100.0)
    pct_iva = min(max(float(i["pct_iva"]), 0.0), 100.0)
    arancel_cop = cif_cop * (pct_arancel / 100)
    iva_cop = (cif_cop + arancel_cop) * (pct_iva / 100)
    gastos_cop = gastos_locales_cop * peso
    landed_cop = cif_cop + arancel_cop + iva_cop + gastos_cop
    unitario = landed_cop / unidades if unidades > 0 else 0.0
    precio = unitario / (1 - pct_margen / 100) if pct_margen < 100 else 0.0
    lineas.append({
        "producto": i["producto"], "partida": i.get("partida", ""),
        "peso_fob": peso, "unidades": unidades, "cif_cop": cif_cop,
        "arancel_cop": arancel_cop, "iva_cop": iva_cop, "gastos_cop": gastos_cop,
        "landed_cop": landed_cop, "unitario_cop": unitario, "precio_sugerido_cop": precio,
    })
  totales = {
      k: sum(l[k] for l in lineas)
      for k in ("cif_cop", "arancel_cop", "iva_cop", "gastos_cop", "landed_cop")
  }
  return lineas, totales


def seccion_multimercancia(es_pro, trm, flete_usd, seguro_usd, gastos_locales_cop, pct_margen, def_arancel, def_iva):
  """Cotización de un embarque con varias mercancías (función Pro)."""
  st.divider()
  titulo("mercancia", "Cotización multimercancía (Pro)", 3)
  registrar_evento("multimercancia_vista" if es_pro else "multimercancia_teaser")
  if not es_pro:
    st.info(
        "Cotiza un embarque con varias mercancías: cada producto con su arancel e IVA, "
        "y el flete, el seguro y los gastos locales repartidos según el valor de cada una. "
        "Disponible con licencia Pro."
    )
    return
  st.caption(
      "Usa el flete, el seguro, los gastos locales, el margen y la TRM de arriba. "
      "El flete, el seguro y los gastos se reparten según el peso de cada línea en el FOB total."
  )
  base = pd.DataFrame([
      {"Producto": "Mercancía 1", "Partida": "", "FOB (USD)": 5000.0, "Unidades": 100.0,
       "Arancel (%)": float(def_arancel), "IVA (%)": float(def_iva)},
      {"Producto": "Mercancía 2", "Partida": "", "FOB (USD)": 3000.0, "Unidades": 50.0,
       "Arancel (%)": float(def_arancel), "IVA (%)": float(def_iva)},
  ])
  editado = st.data_editor(
      base, num_rows="dynamic", key="embarque_items", width="stretch",
      column_config={
          "FOB (USD)": st.column_config.NumberColumn(min_value=0.0, max_value=1_000_000_000.0, step=100.0),
          "Unidades": st.column_config.NumberColumn(min_value=0.0, max_value=1_000_000_000.0, step=1.0),
          "Arancel (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.5),
          "IVA (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0),
      },
  )
  items = []
  for _, f in editado.iterrows():
    if pd.isna(f["FOB (USD)"]) or f["FOB (USD)"] <= 0:
      continue
    items.append({
        "producto": str(f["Producto"] or "Sin nombre"), "partida": str(f["Partida"] or ""),
        "fob_usd": f["FOB (USD)"], "unidades": 0 if pd.isna(f["Unidades"]) else f["Unidades"],
        "pct_arancel": 0 if pd.isna(f["Arancel (%)"]) else f["Arancel (%)"],
        "pct_iva": 0 if pd.isna(f["IVA (%)"]) else f["IVA (%)"],
    })
  if not items:
    st.warning("Agrega al menos una mercancía con valor FOB mayor que cero.")
    return
  lineas, totales = calcular_embarque(items, flete_usd, seguro_usd, trm, gastos_locales_cop, pct_margen)
  tabla = pd.DataFrame([{
      "Producto": l["producto"], "% del FOB": f"{num(l['peso_fob'] * 100, 1)} %",
      "CIF (COP)": num(l["cif_cop"]), "Arancel (COP)": num(l["arancel_cop"]),
      "IVA (COP)": num(l["iva_cop"]), "Gastos locales (COP)": num(l["gastos_cop"]),
      "Costo landed (COP)": num(l["landed_cop"]), "Costo unitario (COP)": num(l["unitario_cop"]),
      "Precio sugerido (COP)": num(l["precio_sugerido_cop"]),
  } for l in lineas])
  st.dataframe(tabla, hide_index=True, width="stretch")
  m1, m2, m3 = st.columns(3)
  m1.metric("Costo landed del embarque", f"$ {num(totales['landed_cop'])}")
  m2.metric("Tributos (arancel + IVA)", f"$ {num(totales['arancel_cop'] + totales['iva_cop'])}")
  m3.metric("Gastos locales", f"$ {num(totales['gastos_cop'])}")
  csv = pd.DataFrame([{
      "producto": texto_para_csv(l["producto"]), "partida": texto_para_csv(l["partida"]),
      "peso_fob": l["peso_fob"],
      "unidades": l["unidades"], "cif_cop": l["cif_cop"], "arancel_cop": l["arancel_cop"],
      "iva_cop": l["iva_cop"], "gastos_locales_cop": l["gastos_cop"],
      "costo_landed_cop": l["landed_cop"], "costo_unitario_cop": l["unitario_cop"],
      "precio_sugerido_cop": l["precio_sugerido_cop"],
  } for l in lineas]).to_csv(index=False).encode("utf-8-sig")
  st.download_button("Exportar embarque a CSV", data=csv, file_name="embarque.csv",
                     mime="text/csv", width="stretch",
                     on_click=registrar_evento, args=("descarga_csv_embarque",))


def calculadora():
  """Página de la calculadora de costo landed."""
  registrar_evento("calculadora_vista")
  st.sidebar.page_link(_PAGINAS["inicio"], label="Volver al inicio", icon=":material/arrow_back:")
  # ==================== BARRA LATERAL (SIDEBAR) ====================
  titulo("acceso", "Acceso de Usuario", 2, st.sidebar)
  tipo_plan = st.sidebar.radio("Plan de Usuario", ["Gratuito", "Pro / Premium"], horizontal=True)

  es_pro = False
  if tipo_plan == "Pro / Premium":
    clave_pro = st.sidebar.text_input("Clave de Licencia Pro", type="password")
    if not _config_licencias() and not _clave_pro_configurada():
      st.sidebar.error("Las licencias Pro no están configuradas en este despliegue.")
    elif clave_pro:
      es_pro, error_licencia = validar_licencia_pro(clave_pro)
      if es_pro:
        registrar_evento("licencia_pro_activada")
        st.sidebar.success("Licencia Pro activa")
      else:
        st.sidebar.warning(error_licencia)

  st.sidebar.divider()
  titulo("parametros", "Parámetros de Monedas", 2, st.sidebar)
  trm = st.sidebar.number_input(
      "TRM Oficial (COP / USD)", min_value=1000.0, value=trm_oficial, step=10.0
  )
  if trm_es_oficial:
    st.sidebar.caption(f"TRM oficial vigente desde {trm_fecha} (datos.gov.co)")
  else:
    st.sidebar.warning(
        "No se pudo consultar la TRM oficial. Se muestra un valor de respaldo"
        f" ({num(TRM_RESPALDO)} COP/USD), que NO es la TRM vigente. Ingresa la"
        " TRM actual manualmente."
    )

  if es_pro:
    titulo("cambio", "Tasa Fronteriza (Multi-moneda)", 3, st.sidebar)
    bs_por_usd = st.sidebar.number_input(
        "Bolívares por dólar (Bs/USD)",
        min_value=0.0, value=None, step=1.0, format="%.2f", placeholder="Ej.: la tasa de hoy",
        help="Escribe la tasa del día. La oficial (BCV) y la paralela pueden diferir bastante; "
             "usa la que aplique a tu operación. Cambia a diario.",
    )
    tasa_usdt_cop = st.sidebar.number_input(
        "Tasa COP / USDT (Cripto)", min_value=1.0, value=float(trm), step=10.0
    )
  else:
    bs_por_usd = None
    tasa_usdt_cop = float(trm)


  # ==================== ENCABEZADO PRINCIPAL ====================
  if abs(trm - trm_oficial) > 1e-9:
    trm_etiqueta, trm_alerta = "TRM manual", False
  elif trm_es_oficial:
    trm_etiqueta, trm_alerta = f"TRM oficial · {trm_fecha}", False
  else:
    trm_etiqueta, trm_alerta = "TRM de respaldo", True
  chip_trm = (
      f'<span class="rate-chip{" is-warn" if trm_alerta else ""}"><i></i>'
      f"1 USD = $ {num(trm)} COP · {trm_etiqueta}</span>"
  )
  st.markdown(
      f"""
      <div class="fiq-topbar">
          <div class="fiq-logo">{icono('contenedor', 22)}<span>FronteraIQ</span><span class="fiq-pro">Pro</span></div>
      </div>
      <h1 class="page-title fiq-display">Cuánto cuesta realmente tu importación puesta en Cúcuta</h1>
      <p class="page-sub">Plataforma de inteligencia aduanera: costo landed, impuestos DIAN y precio de venta. Cambia cualquier valor y el resultado se actualiza al instante.</p>
  """,
      unsafe_allow_html=True,
  )


  # ==================== FORMULARIO ====================
  col_form, col_quote = st.columns([1.3, 1], gap="large")
  with col_quote:
    panel = st.container(key="quote")

  with col_form:
    with st.container(key="paso-mercancia"):
      titulo("mercancia", "Mercancía y Partida NANDINA")

      producto_sel = st.selectbox(
          "Seleccionar o buscar tipo de producto",
          list(CATALOGO_NANDINA.keys()),
      )
      partida_info = CATALOGO_NANDINA[producto_sel]
      if partida_info["codigo"]:
        registrar_evento("partida_elegida", partida_info["codigo"])

      if producto_sel == "Personalizado / Otra partida":
        producto = st.text_input("Nombre / Referencia", value="Mercancía General")
        en_vivo = bloque_dian_en_vivo()
        if en_vivo:
          consulta_dian, def_arancel, def_iva, origen_dian = en_vivo
          partida_arancelaria = dian_arancel.formatear_codigo(consulta_dian.codigo)
        else:
          consulta_dian, origen_dian = None, None
          partida_arancelaria = "0000.00.00.00"
          def_arancel = 10.0
          def_iva = 19.0
      else:
        consulta_dian, origen_dian = None, None
        producto = producto_sel
        partida_arancelaria = st.text_input(
            "Subpartida NANDINA (Autocompletada)", value=partida_info["codigo"]
        )
        validacion = PARTIDAS_VALIDADAS.get(partida_info["codigo"])
        def_arancel = validacion["arancel"] if validacion else partida_info["arancel"]
        def_iva = validacion["iva"] if validacion else partida_info["iva"]
        if validacion:
          st.caption(
              f"Arancel e IVA validados · Fuente: {validacion['fuente']} ·"
              f" Vigencia: {validacion['vigencia']}"
          )
          st.caption(
              "Tarifa general de importación. La subpartida correcta de tu producto la"
              " defines tú o tu agente de aduanas; esta herramienta no clasifica mercancías"
              " ni considera rebajas por acuerdos comerciales."
          )
          if validacion["condiciones"]:
            st.info(f"**Condición de la tarifa:** {validacion['condiciones']}")
        else:
          st.warning(
              "Arancel e IVA de **referencia**, pendientes de validación por un"
              " agente de aduanas. Confírmalos con la normativa vigente antes de"
              " operar; puedes ajustarlos en los campos de la derecha."
          )

      unidades = st.number_input(
          "Cantidad de Unidades", min_value=1, max_value=1_000_000_000, value=1000, step=1
      )
    with st.container(key="paso-valores"):
      titulo("valores", "Valores de la Carga (USD)", 4)
      fob_usd = st.number_input(
          "Valor FOB Total (USD)", min_value=0.0, max_value=1_000_000_000.0, value=10000.0, step=100.0,
          key="in_fob",
      )
      col_flete, col_seguro = st.columns(2)
      with col_flete:
        flete_usd = st.number_input(
            "Flete Internacional (USD)", min_value=0.0, max_value=1_000_000_000.0, value=1200.0, step=50.0
        )
      with col_seguro:
        seguro_usd = st.number_input(
            "Seguro Internacional (USD)", min_value=0.0, max_value=1_000_000_000.0, value=150.0, step=10.0
        )
    with st.container(key="paso-tributos"):
      titulo("tributos", "Arancel e IVA")

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
    with st.container(key="paso-logistica"):
      titulo("logistica", "Logística Frontera Cúcuta (COP)", 4)
      st.caption(
          "Ingresa estos gastos con su IVA incluido. Si tu negocio no puede descontar ese IVA,"
          " es parte de tu costo real."
      )
      col_g1, col_g2 = st.columns(2)
      with col_g1:
        agenciamiento_cop = st.number_input(
            "Agenciamiento SIA (COP)", min_value=0.0, max_value=1_000_000_000_000.0, value=450000.0, step=50000.0
        )
      with col_g2:
        bodegaje_cop = st.number_input(
            "Bodegaje / Depósito (COP)", min_value=0.0, max_value=1_000_000_000_000.0, value=300000.0, step=25000.0
        )
      col_g3, col_g4 = st.columns(2)
      with col_g3:
        transporte_local_cop = st.number_input(
            "Transporte Terrestre Local (COP)",
            min_value=0.0,
            max_value=1_000_000_000_000.0,
            value=800000.0,
            step=50000.0,
        )
      with col_g4:
        otros_gastos_cop = st.number_input(
            "Otros Gastos / Inspecciones (COP)",
            min_value=0.0,
            max_value=1_000_000_000_000.0,
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

  equivalencias = equivalencias_moneda(costo_total_landed_cop, trm, bs_por_usd, tasa_usdt_cop)
  costo_total_ves = equivalencias["ves"]
  costo_total_usdt = equivalencias["usdt"]


  # ==================== DATOS DE LA COTIZACIÓN (TRAZABILIDAD) ====================
  es_personalizada = producto_sel == "Personalizado / Otra partida"
  porcentajes_ajustados = (consulta_dian is not None or not es_personalizada) and (
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
          None if consulta_dian is None else f"{origen_dian}, subpartida {partida_arancelaria}",
      ),
  }
  datos_cotizacion["codigo"] = codigo_cotizacion(datos_cotizacion, emision)


  # ==================== ENLACE A WHATSAPP ====================
  mensaje_whatsapp = f"""Hola, requiero asesoría aduanera para la siguiente operación en FronteraIQ:

  📌 *Producto:* {producto}
  🔢 *Partida:* {partida_arancelaria}
  📦 *Cantidad:* {num(unidades)} uds
  💵 *Valor CIF:* ${num(cif_usd, 2)} USD
  🏛️ *Tributos DIAN:* ${num(total_tributos_cop)} COP
  🚚 *Costo Landed Total:* ${num(costo_total_landed_cop)} COP"""

  mensaje_encoded = urllib.parse.quote(mensaje_whatsapp)
  url_whatsapp = (
      f"https://api.whatsapp.com/send?phone={TELEFONO_WHATSAPP}&text={mensaje_encoded}"
  )


  # ==================== PANEL DE COTIZACIÓN (SE ACTUALIZA EN VIVO) ====================
  base_barra = costo_total_landed_cop if costo_total_landed_cop > 0 else 1
  pct_cif = cif_cop / base_barra * 100
  pct_trib = total_tributos_cop / base_barra * 100
  pct_gastos = total_gastos_locales_cop / base_barra * 100

  with panel:
    st.markdown(
        f"""
        <div class="quote">
            <div class="quote-top"><span class="quote-label">Costo total landed</span>{chip_trm}</div>
            <div class="metric-value is-hero">$ {num(costo_total_landed_cop)}</div>
            <div class="metric-subtext">COP puesto en Cúcuta, todo incluido</div>
            <div class="quote-barra" role="img" aria-label="Proporción de CIF, tributos y gastos locales en el costo landed">
                <i style="width:{pct_cif:.2f}%;background:var(--fiq-teal-light)"></i><i style="width:{pct_trib:.2f}%;background:var(--fiq-signal)"></i><i style="width:{pct_gastos:.2f}%;background:#B9CCCB"></i>
            </div>
            <div class="quote-leyenda">
                <div><b style="background:var(--fiq-teal-light)"></b><span>Valor CIF en pesos</span><span>$ {num(cif_cop)}</span></div>
                <div><b style="background:var(--fiq-signal)"></b><span>Arancel + IVA</span><span>$ {num(total_tributos_cop)}</span></div>
                <div><b style="background:#B9CCCB"></b><span>Gastos en Cúcuta</span><span>$ {num(total_gastos_locales_cop)}</span></div>
            </div>
            <div class="quote-filas">
                <div class="quote-fila"><div><div class="quote-nombre">Costo unitario</div><div class="metric-subtext">Por unidad importada</div></div><div class="metric-value">$ {num(costo_unitario_cop, 2)}</div></div>
                <div class="quote-fila"><div><div class="quote-nombre">Impuestos DIAN</div><div class="metric-subtext">Arancel + IVA</div></div><div class="metric-value">$ {num(total_tributos_cop)}</div></div>
                <div class="quote-fila"><div><div class="quote-nombre">Precio de venta sugerido</div><div class="metric-subtext">Con margen de {pct_margen}%</div></div><div class="metric-value">$ {num(precio_sugerido_unitario_cop, 2)}</div></div>
            </div>
            <p class="quote-nota">Estimación de costos, no es una liquidación oficial de la DIAN.</p>
            <a href="{url_whatsapp}" target="_blank" class="whatsapp-btn">Pedir asesoría por WhatsApp {icono('flecha', 20)}</a>
        </div>
    """,
        unsafe_allow_html=True,
    )


  # ==================== DETALLE DE LA LIQUIDACIÓN ====================
  st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
  titulo("resultados", "Detalle de la liquidación")

  if es_pro:
    texto_ves = (
        f"`{num(costo_total_ves, 2)} VES`" if costo_total_ves is not None
        else "ingresa la tasa Bs/USD en la barra lateral"
    )
    st.info(
        f"**Equivalencia Fronteriza (Pro):** Costo Total en **USDT:**"
        f" `{num(costo_total_usdt, 2)} USDT` | **Bolívares (VES):** {texto_ves}"
    )

  with st.container(key="detalle"):
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
          hole=0.55,
          color_discrete_sequence=["#2E6F73", "#F5B700", "#9DB1B1"],
      )
      fig.update_traces(marker=dict(line=dict(color="#EEF4F2", width=3)))
      fig.update_layout(
          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(family="Atkinson Hyperlegible Next, sans-serif", color="#0B2527", size=14),
          margin=dict(t=10, b=10, l=10, r=10),
          legend=dict(orientation="h", y=-0.05),
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
              f"$ {num(cif_usd, 2)} USD",
              f"$ {num(cif_cop)} COP",
              f"$ {num(arancel_cop)} COP",
              f"$ {num(iva_cop)} COP",
              f"$ {num(total_tributos_cop)} COP",
              f"$ {num(total_gastos_locales_cop)} COP",
              f"$ {num(costo_total_landed_cop)} COP",
          ],
      }
      st.dataframe(
          pd.DataFrame(liquidacion_data), width="stretch", hide_index=True
      )


  # ==================== ACCIONES Y REPORTES ====================
  st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
  titulo("acciones", "Exporta tu cotización")
  st.caption(
      f"Código de cotización: **{datos_cotizacion['codigo']}** · TRM:"
      f" {datos_cotizacion['origen_trm']}"
  )

  c2, c3 = st.columns(2)

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
            label="Descargar Cotización PDF (Pro)",
            data=pdf_bytes,
            file_name=f"{datos_cotizacion['codigo']}_{nombre_seguro or 'producto'}.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch",
            on_click=registrar_evento,
            args=("descarga_pdf",),
        )
    else:
      st.button(
          "Descargar PDF (requiere licencia Pro)",
          disabled=True,
          width="stretch",
      )

  with c3:
    df_export = pd.DataFrame([fila_csv(datos_cotizacion)])
    csv = df_export.to_csv(index=False).encode("utf-8-sig")  # BOM: Excel lee bien las tildes
    st.download_button(
        label="Exportar a CSV",
        data=csv,
        file_name=f"{datos_cotizacion['codigo']}.csv",
        mime="text/csv",
        width="stretch",
        on_click=registrar_evento,
        args=("descarga_csv",),
    )


  seccion_multimercancia(
      es_pro, trm, flete_usd, seguro_usd, total_gastos_locales_cop, pct_margen, def_arancel, def_iva
  )


# ==================== NAVEGACIÓN: INICIO (LANDING) + CALCULADORA ====================
import landing  # noqa: E402

_PAGINAS = {}


def inicio():
  registrar_evento("landing_vista")
  landing.mostrar_landing(_PAGINAS["calculadora"], trm_oficial, trm_fecha, trm_es_oficial)


_INICIO_ES_CALCULADORA = os.environ.get("FIQ_PAGINA_INICIAL") == "calculadora"  # solo para las pruebas
_PAGINAS["inicio"] = st.Page(
    inicio, title="Inicio", icon=":material/home:",
    url_path="inicio" if _INICIO_ES_CALCULADORA else "", default=not _INICIO_ES_CALCULADORA,
)
_PAGINAS["calculadora"] = st.Page(
    calculadora, title="Calculadora", icon=":material/calculate:",
    url_path="" if _INICIO_ES_CALCULADORA else "calculadora", default=_INICIO_ES_CALCULADORA,
)
st.navigation(list(_PAGINAS.values()), position="hidden").run()
