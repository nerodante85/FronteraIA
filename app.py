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


def generar_pdf_cotizacion(datos):
  datos = {
      **datos,
      "producto": _texto_pdf(datos["producto"]),
      "partida": _texto_pdf(datos["partida"]),
  }
  pdf = FPDF()
  pdf.add_page()
  pdf.set_font("Helvetica", "B", 16)

  pdf.cell(
      0,
      10,
      "FronteraIQ - Reporte de Cotizacion Aduanera",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )
  pdf.set_font("Helvetica", "I", 10)
  pdf.cell(
      0,
      8,
      "Liquidacion de Costos Landed y Tributos DIAN (Cucuta - Frontera)",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )
  pdf.ln(5)

  pdf.set_font("Helvetica", "B", 11)
  pdf.cell(0, 7, f"Producto: {datos['producto']}", new_x="LMARGIN", new_y="NEXT")
  pdf.set_font("Helvetica", "", 10)
  pdf.cell(
      0,
      6,
      f"Partida NANDINA: {datos['partida']} | Cantidad: {datos['unidades']:,}"
      " uds",
      new_x="LMARGIN",
      new_y="NEXT",
  )
  pdf.cell(
      0,
      6,
      f"TRM Aplicada: ${datos['trm']:,.2f} COP/USD",
      new_x="LMARGIN",
      new_y="NEXT",
  )
  pdf.ln(5)

  pdf.set_font("Helvetica", "B", 10)
  pdf.cell(120, 7, "Concepto", border=1)
  pdf.cell(70, 7, "Valor (COP)", border=1, new_x="LMARGIN", new_y="NEXT", align="R")

  pdf.set_font("Helvetica", "", 9)
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
    pdf.cell(120, 6, concepto, border=1)
    pdf.cell(
        70, 6, valor, border=1, new_x="LMARGIN", new_y="NEXT", align="R"
    )

  pdf.ln(8)
  pdf.set_font("Helvetica", "I", 9)
  pdf.multi_cell(
      0,
      5,
      "Nota: Este documento es una estimacion de costos proyectados para la"
      " operacion aduanera y logistica en la frontera de Cucuta. No constituye"
      " una liquidacion oficial de la DIAN.",
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


es_pro = False
if tipo_plan == "Pro / Premium ⭐":
  clave_pro = st.sidebar.text_input("Clave de Licencia Pro", type="password")
  clave_valida = _clave_pro_configurada()
  if not clave_valida:
    st.sidebar.error("Las licencias Pro no están configuradas en este despliegue.")
  elif clave_pro and hmac.compare_digest(
      clave_pro.encode("utf-8"), str(clave_valida).encode("utf-8")
  ):
    st.sidebar.success("✅ Licencia Pro Activa")
    es_pro = True
  elif clave_pro:
    st.sidebar.warning("⚠️ Clave de licencia no válida.")

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
  st.plotly_chart(fig, use_container_width=True)

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
      pd.DataFrame(liquidacion_data), use_container_width=True, hide_index=True
  )


# ==================== ACCIONES Y REPORTES ====================
st.divider()
st.subheader("📲 Acciones Directas")

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
    datos_pdf = {
        "producto": producto,
        "partida": partida_arancelaria,
        "unidades": unidades,
        "trm": trm,
        "cif_usd": cif_usd,
        "cif_cop": cif_cop,
        "arancel_cop": arancel_cop,
        "iva_cop": iva_cop,
        "total_tributos_cop": total_tributos_cop,
        "gastos_locales_cop": total_gastos_locales_cop,
        "costo_total_landed_cop": costo_total_landed_cop,
        "costo_unitario_cop": costo_unitario_cop,
    }
    try:
      pdf_bytes = generar_pdf_cotizacion(datos_pdf)
    except Exception:
      pdf_bytes = None
      st.error("No se pudo generar el PDF. Revisa el nombre del producto.")
    if pdf_bytes:
      nombre_seguro = re.sub(r"[^A-Za-z0-9_-]+", "_", producto).strip("_")
      st.download_button(
          label="📄 Descargar Cotización PDF (Pro)",
          data=pdf_bytes,
          file_name=f"cotizacion_{nombre_seguro or 'producto'}.pdf",
          mime="application/pdf",
          use_container_width=True,
      )
  else:
    st.button(
        "📄 Descargar PDF (Licencia Pro 🔒)",
        disabled=True,
        use_container_width=True,
    )

with c3:
  df_export = pd.DataFrame([{
      "Producto": producto,
      "Partida": partida_arancelaria,
      "Unidades": unidades,
      "Costo Landed COP": costo_total_landed_cop,
      "Costo Unitario COP": costo_unitario_cop,
  }])
  csv = df_export.to_csv(index=False).encode("utf-8")
  st.download_button(
      label="📥 Exportar a CSV",
      data=csv,
      file_name="cotizacion.csv",
      mime="text/csv",
      use_container_width=True,
  )
