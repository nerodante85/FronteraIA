import urllib.parse
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="FronteraIQ - Calculadora Aduanera Cúcuta",
    page_icon="🚢",
    layout="wide",
)


# === FUNCIÓN PARA CONSULTAR LA TRM EN TIEMPO REAL ===
@st.cache_data(ttl=3600)  # Guarda el resultado 1 hora para no saturar la API
def obtener_trm_actual():
  try:
    url = (
        'https://www.datos.gov.co/resource/32sa-213a.json?$order=vigenciasta%20DESC&$limit=1'
    )
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      return float(data[0]['valor'])
  except Exception:
    pass
  return 4000.0  # Valor de respaldo si no hay conexión a la API


# Obtener la TRM del día
trm_oficial = obtener_trm_actual()

# Estilo personalizado básico
st.markdown(
    """
    <style>
    .main-header {
        font-size: 28px;
        font-weight: bold;
        color: #1E3A8A;
    }
    .sub-header {
        font-size: 14px;
        color: #4B5563;
        margin-bottom: 20px;
    }
    .whatsapp-btn {
        background-color: #25D366;
        color: white !important;
        font-weight: bold;
        padding: 12px 24px;
        border-radius: 8px;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .whatsapp-btn:hover {
        background-color: #128C7E;
        color: white !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Configuración del Número de WhatsApp (Ingresa tu número con prefijo 57 de Colombia)
TELEFONO_WHATSAPP = "573156491042"  # <-- REEMPLAZA ESTE NÚMERO CON EL TUYO

# Encabezado principal
st.markdown(
    '<div class="main-header">🚢 FronteraIQ — Inteligencia Aduanera y'
    " Costos Landed</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">Optimización de liquidación de importaciones y'
    " costes logísticos para la frontera Cúcuta - Venezuela</div>",
    unsafe_allow_html=True,
)

st.divider()

# Sidebar: Configuración de Parámetros Generales
st.sidebar.header("⚙️ Parámetros Generales")

# Muestra y permite ajustar la TRM (cargada en tiempo real)
trm = st.sidebar.number_input(
    "TRM Oficial / Proyectada (COP / USD)",
    min_value=1000.0,
    value=trm_oficial,
    step=10.0,
    help=(
        "Obtenida en tiempo real desde la API oficial de la Superintendencia"
        " Financiera de Colombia."
    ),
)
st.sidebar.caption(
    f"💡 *TRM detectada hoy: ${trm_oficial:,.2f} COP* (puedes editarla si"
    " proyectas otra tasa)."
)

operacion = st.sidebar.selectbox(
    "Tipo de Operación",
    ["Importación a Colombia", "Exportación a Venezuela"],
)

# Formulario de Entrada de Datos
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
  st.subheader("📦 Datos de la Mercancía")

  producto = st.text_input(
      "Nombre / Referencia del Producto", value="Textiles / Confecciones"
  )
  partida_arancelaria = st.text_input(
      "Partida Arancelaria (NANDINA - 10 dígitos)", value="6109.10.00.00"
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
        "Arancel (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5
    )
  with col_imp2:
    pct_iva = st.number_input(
        "IVA (%)", min_value=0.0, max_value=100.0, value=19.0, step=1.0
    )

  st.markdown("#### 🚚 Gastos Operativos y Logísticos Cúcuta (COP)")
  agenciamiento_cop = st.number_input(
      "Agenciamiento Aduanero / SIA (COP)",
      min_value=0.0,
      value=450000.0,
      step=50000.0,
  )
  bodegaje_cop = st.number_input(
      "Bodegaje / Depósito en Frontera (COP)",
      min_value=0.0,
      value=300000.0,
      step=25000.0,
  )
  transporte_local_cop = st.number_input(
      "Transporte Terrestre Local / Destino (COP)",
      min_value=0.0,
      value=800000.0,
      step=50000.0,
  )
  otros_gastos_cop = st.number_input(
      "Vistos Buenos / Inspección / Otros (COP)",
      min_value=0.0,
      value=200000.0,
      step=25000.0,
  )

  st.markdown("#### 📊 Comercialización")
  pct_margen = st.number_input(
      "Margen de Ganancia Deseado (%)",
      min_value=0.0,
      max_value=99.0,
      value=30.0,
      step=1.0,
  )

# ==================== MOTOR DE CÁLCULO ====================

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

# ==================== PRESENTACIÓN DE RESULTADOS ====================

st.divider()
st.subheader("📈 Resumen de Resultados y Rentabilidad")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Costo Total Landed (COP)", f"$ {costo_total_landed_cop:,.0f}")
m2.metric("Costo Unitario (COP)", f"$ {costo_unitario_cop:,.2f}")
m3.metric("Total Impuestos DIAN (COP)", f"$ {total_tributos_cop:,.0f}")
m4.metric(
    "Precio Sugerido Venta / Ud.", f"$ {precio_sugerido_unitario_cop:,.2f}"
)

st.markdown("<br>", unsafe_allow_html=True)

col_chart, col_table = st.columns([1, 1], gap="large")

with col_chart:
  st.markdown("#### Distribución del Costo Landed")

  df_chart = pd.DataFrame({
      "Concepto": [
          "Mercancía CIF (Valor + Flete + Seg)",
          "Tributos DIAN (Arancel + IVA)",
          "Gastos Operativos Cúcuta",
      ],
      "Monto_COP": [cif_cop, total_tributos_cop, total_gastos_locales_cop],
  })

  fig = px.pie(
      df_chart,
      values="Monto_COP",
      names="Concepto",
      hole=0.4,
      color_discrete_sequence=px.colors.qualitative.Set2,
  )
  fig.update_traces(textposition="inside", textinfo="percent+label")
  fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
  st.plotly_chart(fig, use_container_width=True)

with col_table:
  st.markdown("#### Liquidación Detallada de Importación")

  liquidacion_data = {
      "Concepto": [
          "Valor FOB (USD)",
          "Flete Internacional (USD)",
          "Seguro Internacional (USD)",
          "Valor CIF (USD)",
          "TRM Utilizada",
          "Valor CIF (COP)",
          "Gravamen Arancelario (COP)",
          "Base Gravable IVA (COP)",
          "Impuesto IVA (COP)",
          "Total Impuestos DIAN (COP)",
          "Total Gastos Logísticos Locales (COP)",
          "COSTO TOTAL LANDED (COP)",
          "COSTO LANDED UNITARIO (COP)",
      ],
      "Valor / Monto": [
          f"$ {fob_usd:,.2f} USD",
          f"$ {flete_usd:,.2f} USD",
          f"$ {seguro_usd:,.2f} USD",
          f"$ {cif_usd:,.2f} USD",
          f"$ {trm:,.2f} COP",
          f"$ {cif_cop:,.0f} COP",
          f"$ {arancel_cop:,.0f} COP",
          f"$ {base_iva_cop:,.0f} COP",
          f"$ {iva_cop:,.0f} COP",
          f"$ {total_tributos_cop:,.0f} COP",
          f"$ {total_gastos_locales_cop:,.0f} COP",
          f"$ {costo_total_landed_cop:,.0f} COP",
          f"$ {costo_unitario_cop:,.2f} COP",
      ],
  }

  df_liq = pd.DataFrame(liquidacion_data)
  st.dataframe(df_liq, use_container_width=True, hide_index=True)

# ==================== BOTÓN DE WHATSAPP Y EXPORTAR ====================
st.divider()
st.subheader("📲 ¿Necesitas Asesoría Profesional para esta Operación?")

mensaje_whatsapp = f"""Hola, requiero asesoría aduanera y logística para la siguiente operación calculada en FronteraIQ:

📌 *Producto:* {producto}
🔢 *Partida:* {partida_arancelaria}
📦 *Cantidad:* {unidades:,} unidades
💵 *Valor CIF (USD):* ${cif_usd:,.2f} USD
💱 *TRM:* ${trm:,.2f} COP
🏛️ *Tributos DIAN (COP):* ${total_tributos_cop:,.0f} COP
🚚 *Costo Total Landed:* ${costo_total_landed_cop:,.0f} COP
🏷️ *Costo Unitario:* ${costo_unitario_cop:,.2f} COP

¿Me podrías ayudar con los trámites de agenciamiento y logística en Cúcuta?"""

mensaje_encoded = urllib.parse.quote(mensaje_whatsapp)
url_whatsapp = (
    f"https://api.whatsapp.com/send?phone={TELEFONO_WHATSAPP}&text={mensaje_encoded}"
)

col_ws, col_csv = st.columns([1, 1], gap="medium")

with col_ws:
  st.markdown(
      f'<a href="{url_whatsapp}" target="_blank" class="whatsapp-btn">💬'
      " Solicitar Asesoría por WhatsApp</a>",
      unsafe_allow_html=True,
  )

with col_csv:
  df_export = pd.DataFrame({
      "Producto": [producto],
      "Partida Arancelaria": [partida_arancelaria],
      "Unidades": [unidades],
      "TRM": [trm],
      "Valor CIF USD": [cif_usd],
      "Valor CIF COP": [cif_cop],
      "Arancel COP": [arancel_cop],
      "IVA COP": [iva_cop],
      "Gastos Locales COP": [total_gastos_locales_cop],
      "Costo Total Landed COP": [costo_total_landed_cop],
      "Costo Unitario COP": [costo_unitario_cop],
      "Precio Venta Sugerido COP": [precio_sugerido_unitario_cop],
  })

  csv = df_export.to_csv(index=False).encode("utf-8")

  st.download_button(
      label="📥 Descargar Cotización en CSV",
      data=csv,
      file_name=f"cotizacion_{producto.replace(' ', '_')}.csv",
      mime="text/csv",
  )
