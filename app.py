import io
import urllib.parse
from fpdf import FPDF
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ==================== CONFIGURACIÓN DE LA PÁGINA ====================
st.set_page_config(
    page_title="FronteraIQ Pro - Inteligencia Aduanera Cúcuta",
    page_icon="🚢",
    layout="wide",
)

# Configuración de tu WhatsApp
TELEFONO_WHATSAPP = "573156491042"  # <-- REEMPLAZA CON TU NÚMERO (Prefijo 57)


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

  # Encabezado
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

  # Datos generales
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

  # Tabla de Resumen
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


# ==================== ESTILOS Y INTERFAZ ====================
st.markdown(
    """
    <style>
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; }
    .sub-header { font-size: 14px; color: #4B5563; margin-bottom: 20px; }
    .whatsapp-btn {
        background-color: #25D366; color: white !important; font-weight: bold;
        padding: 12px 24px; border-radius: 8px; text-decoration: none;
        display: inline-block; font-size: 16px; text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

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
    "TRM Oficial (COP / USD)", min_value=1000.0, value=trm_oficial, step=10.0
)

# === CONVERSOR FRONTERIZO (FUNCIONALIDAD C) ===
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

# ==================== ENCABEZADO Y FORMULARIO ====================
st.markdown(
    '<div class="main-header">🚢 FronteraIQ Pro — Inteligencia'
    " Aduanera</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">Calculadora Lended Cost, Arancel NANDINA y'
    " Cotización Fronteriza Cúcuta</div>",
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
  st.subheader("📦 Mercancía y Partida NANDINA")

  # BUSCADOR DE PARTIDAS (FUNCIONALIDAD B)
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
        "Subpartida Arancelaria (Autocompletada)", value=partida_info["codigo"]
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

# Conversiones Multi-moneda (C)
costo_total_ves = (
    costo_total_landed_cop / tasa_ves_cop if tasa_ves_cop > 0 else 0
)
costo_total_usdt = (
    costo_total_landed_cop / tasa_usdt_cop if tasa_usdt_cop > 0 else 0
)

# ==================== RESULTADOS ====================
st.divider()
st.subheader("📈 Resumen de Resultados y Multi-Moneda")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Costo Landed (COP)", f"$ {costo_total_landed_cop:,.0f}")
m2.metric("Costo Unitario (COP)", f"$ {costo_unitario_cop:,.2f}")
m3.metric("Impuestos DIAN (COP)", f"$ {total_tributos_cop:,.0f}")
m4.metric("Precio Sugerido / Ud.", f"$ {precio_sugerido_unitario_cop:,.2f}")

# MOSTRAR MULTI-MONEDA SI ES PRO (C & D)
if es_pro:
  st.info(
      f"💱 **Equivalencia Fronteriza (Pro):** Costo Total en **USDT:**"
      f" `{costo_total_usdt:,.2f} USDT` | Costo Total en **Bolívares (VES):**"
      f" `{costo_total_ves:,.2f} VES`"
  )
else:
  st.caption("🔒 *Activa el Plan Pro en la barra lateral para ver conversiones automáticas en Bolívares (VES) y USDT (Cripto).*")

col_chart, col_table = st.columns([1, 1], gap="large")

with col_chart:
  st.markdown("#### Distribución del Costo Landed")
  df_chart = pd.DataFrame({
      "Concepto": ["CIF", "Impuestos DIAN", "Gastos Cúcuta"],
      "Monto_COP": [cif_cop, total_tributos_cop, total_gastos_locales_cop],
  })
  fig = px.pie(
      df_chart,
      values="Monto_COP",
      names="Concepto",
      hole=0.4,
      color_discrete_sequence=px.colors.qualitative.Set2,
  )
  st.plotly_chart(fig, use_container_width=True)

with col_table:
  st.markdown("#### Liquidación Detallada")
  liquidacion_data = {
      "Concepto": [
          "Valor CIF (USD)",
          "Valor CIF (COP)",
          "Arancel (COP)",
          "IVA (COP)",
          "Total Impuestos DIAN",
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
st.subheader("📲 Exportar y Asesoría Directa")

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
      " Solicitar Asesoría por WhatsApp</a>",
      unsafe_allow_html=True,
  )

with c2:
  # DESCARGA DE PDF (FUNCIONALIDAD A)
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
    pdf_bytes = generar_pdf_cotizacion(datos_pdf)
    st.download_button(
        label="📄 Descargar Cotización en PDF (Pro)",
        data=pdf_bytes,
        file_name=f"cotizacion_{producto.replace(' ', '_')}.pdf",
        mime="application/pdf",
    )
  else:
    st.button("📄 Descargar PDF (Solo Plan Pro 🔒)", disabled=True)

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
      label="📥 Descargar Resumen CSV",
      data=csv,
      file_name="cotizacion.csv",
      mime="text/csv",
  )
