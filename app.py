import io
import urllib.parse
from fpdf import FPDF
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ==================== CONFIGURACIÓN DE LA PÁGINA ====================
st.set_page_config(
    page_title="FronteraIQ Pro — Inteligencia Aduanera Cúcuta",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

TELEFONO_WHATSAPP = "573156491042"  # <-- REEMPLAZA CON TU NÚMERO (Prefijo 57)


# ==================== INYECCIÓN CSS: VARIACIÓN 1 (MODERN SAAS / FINTECH) ====================
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
    /* Estilos Generales y Tipografía */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    /* Encabezado Principal */
    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 32px 40px;
        border-radius: 20px;
        color: white;
        margin-bottom: 28px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.1);
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

    /* Tarjetas de Métricas Flotantes */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }
    .metric-label {
        font-size: 12px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .metric-subtext {
        font-size: 12px;
        font-weight: 600;
        color: #10b981;
    }

    /* Botón Principal de WhatsApp */
    .whatsapp-btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white !important;
        font-weight: 700;
        padding: 14px 24px;
        border-radius: 12px;
        text-decoration: none;
        display: block;
        font-size: 15px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
        transition: all 0.2s ease;
    }
    .whatsapp-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
    }

    /* Ajustes de componentes nativos de Streamlit */
    div[data-baseweb="input"] {
        border-radius: 10px !important;
    }
    .stButton>button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        height: 48px !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ==================== TRM EN TIEMPO REAL ====================
@st.cache_data(ttl=3600)
def obtener_trm_actual():
  try:
    url = (
        "https://www.datos.gov.co/resource/32sa-213a.json?$order=vigenciasta\%20DESC&$limit=1"
    )
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      return float(data[0]["valor"])
  except Exception:
    pass
  return 4000.0


trm_oficial = obtener_trm_actual()


# ==================== BASE DE DATOS DE PARTIDAS (FUNCIONALIDAD B) ====================
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


# ==================== GENERADOR DE PDF (FUNCIONALIDAD A) ====================
def generar_pdf_cotizacion(datos):
  pdf = FPDF()
  pdf.add_page()
  pdf.set_font("Arial", "B", 16)

  pdf.cell(
      0,
      10,
      "FronteraIQ - Reporte de Cotizacion Aduanera",
      ln=True,
      align="C",
  )
  pdf.set_font("Arial", "I", 10)
  pdf.cell(
      0,
      8,
      "Liquidacion de Costos Landed y Tributos DIAN (Cucuta - Frontera)",
      ln=True,
      align="C",
  )
  pdf.ln(5)

  pdf.set_font("Arial", "B", 11)
  pdf.cell(0, 7, f"Producto: {datos['producto']}", ln=True)
  pdf.set_font("Arial", "", 10)
  pdf.cell(
      0,
      6,
      f"Partida NANDINA: {datos['partida']} | Cantidad: {datos['unidades']:,}"
      " uds",
      ln=True,
  )
  pdf.cell(0, 6, f"TRM Aplicada: ${datos['trm']:,.2f} COP/USD", ln=True)
  pdf.ln(5)

  pdf.set_font("Arial", "B", 10)
  pdf.cell(120, 7, "Concepto", 1)
  pdf.cell(70, 7, "Valor (COP)", 1, ln=True, align="R")

  pdf.set_font("Arial", "", 9)
  items = [
      ("Valor CIF (USD)", f"${datos['cif_usd']:,.2f} USD"),
      ("Valor CIF (COP)", f"${datos['cif_cop']:,.0f} COP"),
      ("Arancel DIAN", f"${datos['arancel_cop']:,.0f} COP"),
      ("IVA DIAN", f"${datos['iva_cop']:,.0f} COP"),
      ("Total Impuestos DIAN", f"${datos['total_tributos_cop']:,.0f} COP"),
      ("Gastos Logísticos Cúcuta", f"${datos['gastos_locales_cop']:,.0f} COP"),
      ("COSTO TOTAL LANDED", f"${datos['costo_total_landed_cop']:,.0f} COP"),
      ("COSTO LANDED UNITARIO", f"${datos['costo_unitario_cop']:,.2f} COP"),
  ]

  for concepto, valor in items:
    pdf.cell(120, 6, concepto, 1)
    pdf.cell(70, 6, valor, 1, ln=True, align="R")

  pdf.ln(8)
  pdf.set_font("Arial", "I", 9)
  pdf.multi_cell(
      0,
      5,
      "Nota: Este documento es una estimacion de costos proyectados para la"
      " operacion aduanera y logistica en la frontera de Cucuta. No constituye"
      " una liquidacion oficial de la DIAN.",
  )

  return pdf.output(dest="S").encode("latin-1")


# ==================== SIDEBAR: CONTROL DE ACCESO (FUNCIONALIDAD D) ====================
st.sidebar.header("🔐 Acceso de Usuario")
tipo_plan = st.sidebar.radio("Plan de Usuario", ["Gratuito", "Pro / Premium ⭐"])

es_pro = False
if tipo_plan == "Pro / Premium ⭐":
  clave_pro = st.sidebar.text_input(
      "Clave de Licencia Pro",
      type="password",
      help="Ingresa 'PRO2026' para probar la versión Premium",
  )
  if clave_pro == "PRO2026":
    st.sidebar.success("✅ Licencia Pro Activa")
    es_pro = True
  else:
    st.sidebar.warning("⚠️ Clave de prueba Pro: PRO2026")

st.sidebar.divider()
st.sidebar.header("⚙️ Parámetros de Monedas")
trm = st.sidebar.number_input(
    "TRM Oficial (COP / USD
