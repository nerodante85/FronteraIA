"""Página de inicio (landing) de FronteraIQ Pro, dentro de la misma app de Streamlit."""
import os

import streamlit as st

WA = "https://wa.me/573156491042?text="


def _config(nombre, defecto):
  """Lee un valor de st.secrets o de una variable de entorno (para poner los links de pago de Wompi)."""
  try:
    valor = st.secrets.get(nombre)
  except Exception:
    valor = None
  return valor or os.environ.get(nombre) or defecto


LINK_PRO_MENSUAL = lambda: _config("LINK_PRO_MENSUAL", WA + "Hola%2C%20quiero%20el%20plan%20Pro%20mensual%20de%20FronteraIQ")
LINK_PRO_ANUAL = lambda: _config("LINK_PRO_ANUAL", WA + "Hola%2C%20quiero%20el%20plan%20Pro%20anual%20de%20FronteraIQ")
LINK_AGENCIA = lambda: _config("LINK_AGENCIA", WA + "Hola%2C%20quiero%20informaci%C3%B3n%20del%20plan%20Agencia%20de%20FronteraIQ")

CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
.stApp { background: var(--fiq-page); }
section.stMain { overflow-x: hidden; }
.block-container { max-width: 1200px !important; padding: 0 24px 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
.fiq-land { color: var(--fiq-ink); line-height: 1.55; }
.fiq-land .l-h1, .fiq-land .l-h2, .fiq-land .l-h3, .fiq-land .l-num {
    font-family: 'Bricolage Grotesque', system-ui, sans-serif !important;
    font-weight: 800 !important; letter-spacing: -0.03em; margin: 0; color: inherit;
}
.fiq-land .l-h1 { font-size: clamp(38px, 3.7vw, 56px) !important; line-height: 1; }
.fiq-land .l-h2 { font-size: clamp(34px, 3.8vw, 52px) !important; line-height: 1.04; }
.fiq-land .l-h3 { font-size: 24px !important; line-height: 1.1; letter-spacing: -0.02em; }
.fiq-land p { margin: 0; }
.fiq-band { border-radius: 40px; }
.fiq-band-dark { background: #0B2527; color: #F2F7F5; }
.fiq-cadena { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-top: 44px; }
.fiq-cadena > div { padding: 24px; background: rgba(255, 255, 255, 0.07); border-radius: 24px; }
.fiq-cadena .l-h3 { color: #F5B700; font-size: 28px !important; }
.fiq-cadena p { margin-top: 10px; font-size: 15px; color: #B9CCCB; }
.fiq-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); margin-top: 44px; }
.fiq-grid > div { background: var(--fiq-panel); border-radius: 28px; padding: 32px; }
.fiq-grid p { margin-top: 10px; color: #26474A; }
.fiq-quien { background: var(--fiq-panel); border-radius: 36px; padding: 44px; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 32px; }
.fiq-quien .l-h3 { font-size: 28px !important; }
.fiq-quien p { margin-top: 8px; color: #26474A; font-size: 15px; }
.l-precio { font-size: 38px !important; white-space: nowrap; margin-top: 8px !important; font-variant-numeric: tabular-nums; }
.l-precio small { font-family: 'Atkinson Hyperlegible Next', sans-serif; font-size: 16px; font-weight: 600; letter-spacing: 0; }
.l-nota { font-size: 14px; color: #3C5C5F; }
.l-fila span:last-child { white-space: nowrap; }
.l-fila { display: flex; justify-content: space-between; gap: 16px; padding: 5px 0; font-size: 15px; font-variant-numeric: tabular-nums; }
.l-barra { display: flex; height: 12px; border-radius: 999px; overflow: hidden; background: #D3DEDC; margin-top: 16px; gap: 2px; }
.l-barra i { display: block; transition: width 250ms cubic-bezier(0.23, 1, 0.32, 1); }
.l-chip { display: inline-block; background: var(--fiq-panel); padding: 7px 16px; border-radius: 999px; font-size: 14px; font-weight: 700; }
.l-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }
@media (prefers-reduced-motion: reduce) { .l-barra i { transition: none; } }

/* Tarjetas (contenedores con clave) */
.st-key-demo { background: #FFFFFF; border: 1px solid var(--fiq-line); border-radius: 32px; padding: 32px; box-shadow: 0 28px 56px -28px rgba(11, 37, 39, 0.35); }
.st-key-plan-starter, .st-key-plan-pro, .st-key-plan-agencia { background: var(--fiq-panel); border-radius: 32px; padding: 32px; }
.st-key-plan-pro { background: #F5B700; }
.st-key-plan-starter, .st-key-plan-pro, .st-key-plan-agencia { height: 100%; }
[data-testid="stColumn"] > div { height: 100%; }
.st-key-plan-starter [data-testid="stVerticalBlock"], .st-key-plan-pro [data-testid="stVerticalBlock"], .st-key-plan-agencia [data-testid="stVerticalBlock"] { gap: 0.75rem !important; }

/* Botones: píldoras, igual que la calculadora */
.fiq-land a.l-btn, [data-testid="stPageLink"] a, [data-testid="stLinkButton"] a {
    min-height: 52px; border: 2px solid var(--fiq-ink) !important; border-radius: 999px !important;
    font-weight: 800 !important; text-decoration: none !important; justify-content: center;
    transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1), background-color 160ms;
}
[data-testid="stPageLink"] a:active, [data-testid="stLinkButton"] a:active { transform: scale(0.97); }
.st-key-cta-hero [data-testid="stPageLink"] a { background: #F5B700; border-color: #F5B700 !important; color: #0B2527 !important; padding: 12px 32px; font-size: 17px; }
.st-key-cta-hero [data-testid="stPageLink"] a:hover { background: #FFC61A; }
.st-key-cta-final [data-testid="stPageLink"] a { background: #0B2527; color: #F2F7F5 !important; padding: 12px 32px; font-size: 17px; }
.st-key-cta-starter [data-testid="stPageLink"] a, .st-key-cta-agencia [data-testid="stLinkButton"] a { background: transparent; color: #0B2527 !important; }
.st-key-cta-pro-m [data-testid="stLinkButton"] a { background: #0B2527; color: #F2F7F5 !important; }
.st-key-cta-pro-a [data-testid="stLinkButton"] a { background: transparent; color: #0B2527 !important; }
.st-key-nav [data-testid="stPageLink"] a { background: #0B2527; padding: 8px 22px; min-height: 46px; }
.st-key-nav [data-testid="stPageLink"] a *, .st-key-cta-final [data-testid="stPageLink"] a *, .st-key-cta-pro-m [data-testid="stLinkButton"] a * { color: #F2F7F5 !important; }
.st-key-cta-hero [data-testid="stPageLink"] a *, .st-key-cta-starter [data-testid="stPageLink"] a *, .st-key-cta-agencia [data-testid="stLinkButton"] a *, .st-key-cta-pro-a [data-testid="stLinkButton"] a * { color: #0B2527 !important; }
.st-key-cta-starter, .st-key-cta-agencia, .st-key-cta-pro-m { margin-top: 20px; }
.st-key-cta-pro-a { margin-top: 8px; }
@media (min-width: 900px) { .st-key-plan-starter, .st-key-plan-pro, .st-key-plan-agencia { min-height: 790px; } }
.st-key-band-final { background: #F5B700; border-radius: 40px; padding: 64px 56px; }
@media (max-width: 700px) { .st-key-band-final { padding: 44px 24px; } .fiq-quien { padding: 28px 22px; } }
</style>
"""


def _cop(v):
  return "$ " + f"{round(v):,}".replace(",", ".")


def _num(v, dec=0):
  t = f"{v:,.{dec}f}"
  return t.replace(",", "\0").replace(".", ",").replace("\0", ".")


def liquidacion_demo(fob, arancel, trm):
  """Misma cadena de cálculo de la calculadora, con los supuestos fijos del ejemplo."""
  flete, seguro, unidades, gastos, margen = 1200, 150, 1000, 1750000, 0.30
  cif_usd = fob + flete + seguro
  cif = cif_usd * trm
  aran = cif * arancel / 100
  iva = (cif + aran) * 0.19
  trib = aran + iva
  landed = cif + trib + gastos
  precio = (landed / unidades) / (1 - margen)
  return {"cif_usd": cif_usd, "cif": cif, "aran": aran, "iva": iva, "trib": trib,
          "gastos": gastos, "landed": landed, "precio": precio}


def mostrar_landing(pagina_calculadora, trm, trm_fecha, trm_es_oficial):
  st.html(CSS)

  c1, c2 = st.columns([3, 1], vertical_alignment="center")
  with c1:
    st.html('<div class="fiq-land" style="padding:20px 0"><span class="l-h3" style="font-size:34px!important">FronteraIQ</span> <span style="background:#F5B700;padding:1px 8px;border-radius:999px;font-size:15px;font-weight:700;vertical-align:6px">Pro</span></div>')
  with c2:
    with st.container(key="nav"):
      st.page_link(pagina_calculadora, label="Abrir la app", width="stretch")

  # HERO
  izq, der = st.columns([1.05, 1], gap="large")
  with izq:
    st.html("""<div class="fiq-land" style="padding-top:36px">
<h1 class="l-h1">Cuánto te cuesta realmente la mercancía puesta en Cúcuta.</h1>
<p style="margin-top:28px;font-size:19px;max-width:520px;color:#26474A">Calcula el costo landed de tus importaciones a Colombia en segundos: CIF, arancel, IVA y gastos de frontera, con la TRM oficial del día y un precio de venta que sí deja margen.</p></div>""")
    with st.container(key="cta-hero"):
      st.html('<div style="height:32px"></div>')
      st.page_link(pagina_calculadora, label="Calcular mi primera importación")
    st.html('<p class="fiq-land l-nota" style="margin-top:20px;font-size:15px">Plan gratuito sin registro. Para pymes, comerciantes, agencias aduaneras y agentes de carga.</p>')
    st.html('<div class="fiq-land l-chips"><span class="l-chip">Confecciones</span><span class="l-chip">Calzado</span><span class="l-chip">Celulares</span><span class="l-chip">Portátiles</span><span class="l-chip">Arroz</span><span class="l-chip">Autopartes</span><span class="l-chip">Medicamentos</span></div><p class="fiq-land l-nota" style="margin-top:10px;font-size:13px">Partidas ya cargadas. Cualquier otra la consultas en vivo en la DIAN.</p>')
  with der:
    with st.container(key="demo"):
      origen = f"TRM oficial {trm_fecha}: {_cop(trm).replace('$ ', '$')}" if trm_es_oficial else f"TRM de respaldo: {_cop(trm).replace('$ ', '$')}"
      st.html(f'<div class="fiq-land" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:baseline;border-bottom:1px solid #D3DFDC;padding-bottom:14px"><span class="l-h3" style="font-size:29px!important">Liquidación de ejemplo</span><span class="l-nota">{origen}</span></div>')
      fob = st.slider("Valor FOB de la carga (USD)", 2000, 50000, 10000, 500, key="demo_fob")
      arancel = st.segmented_control("Arancel aplicable", [0, 5, 10, 15, 35], default=10,
                                     format_func=lambda v: f"{v} %", key="demo_arancel")
      arancel = 10 if arancel is None else arancel
      r = liquidacion_demo(fob, arancel, trm)
      pct = lambda v: f"{v / r['landed'] * 100:.1f}%"
      st.html(f"""<div class="fiq-land" style="margin-top:12px">
<div class="l-fila"><span>Valor CIF (FOB + flete + seguro)</span><span>{_num(r['cif_usd'])} USD</span></div>
<div class="l-fila"><span>CIF en pesos</span><span>{_cop(r['cif'])}</span></div>
<div class="l-fila"><span>Arancel ({arancel} %)</span><span>{_cop(r['aran'])}</span></div>
<div class="l-fila"><span>IVA 19 % sobre CIF + arancel</span><span>{_cop(r['iva'])}</span></div>
<div class="l-fila"><span>Gastos en frontera</span><span>{_cop(r['gastos'])}</span></div>
<div class="l-barra" role="img" aria-label="Proporción de CIF, tributos y gastos locales en el costo landed"><i style="width:{pct(r['cif'])};background:#0B2527"></i><i style="width:{pct(r['trib'])};background:#F5B700"></i><i style="width:{pct(r['gastos'])};background:#5E7A7C"></i></div>
<div class="l-nota" style="margin-top:8px;font-size:13px;display:flex;flex-wrap:wrap;gap:6px 18px"><span>Negro: CIF</span><span>Amarillo: tributos DIAN</span><span>Gris: gastos locales</span></div>
<div style="margin-top:20px;padding-top:16px;border-top:2px solid #0B2527;display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:flex-end">
<div><div style="font-size:14px;font-weight:600">Costo total landed</div><div class="l-num" style="font-size:52px;line-height:1.05">{_cop(r['landed'])}</div></div>
<div style="text-align:right"><div style="font-size:14px;font-weight:600">Precio sugerido por unidad</div><div class="l-num" style="font-size:34px">$ {_num(r['precio'], 2)}</div></div></div>
<p class="l-nota" style="margin-top:14px;font-size:13px">Ejemplo con flete de 1.200 USD, seguro de 150 USD, 1.000 unidades, $1.750.000 de gastos locales y 30 % de margen. En la app cambias todos los valores.</p></div>""")

  # CADENA
  st.html("""<div class="fiq-land fiq-band fiq-band-dark" style="margin-top:72px"><div style="padding:72px 56px">
<h2 class="l-h2" style="max-width:760px">La misma cadena de costos que hoy armas en una hoja de cálculo.</h2>
<p style="margin-top:18px;font-size:18px;max-width:640px;color:#B9CCCB">Cada paso se calcula sobre el anterior, igual que en una liquidación aduanera. Sin fórmulas que se rompen ni celdas que alguien borró.</p>
<div class="fiq-cadena">
<div><div class="l-h3">1. CIF</div><p>FOB + flete + seguro, convertido a pesos con la TRM vigente.</p></div>
<div><div class="l-h3">2. Arancel</div><p>Porcentaje de la subpartida sobre el CIF en pesos.</p></div>
<div><div class="l-h3">3. IVA</div><p>Sobre la base gravable: CIF más arancel.</p></div>
<div><div class="l-h3">4. Frontera</div><p>Agenciamiento, bodegaje, transporte local e inspecciones.</p></div>
<div style="border-right:0"><div class="l-h3">5. Landed</div><p>Costo puesto en Cúcuta, costo por unidad y precio de venta con tu margen.</p></div>
</div></div></div>""")

  # FUNCIONES + PARA QUIÉN
  st.html("""<div class="fiq-land" style="padding:88px 0 40px">
<h2 class="l-h2" style="max-width:720px">Hecha para cotizar con respaldo, no para adivinar.</h2>
<div class="fiq-grid">
<div><h3 class="l-h3">TRM oficial, sin digitarla</h3><p>Se consulta cada hora en datos.gov.co y se muestra con su fecha de vigencia. Si la fuente no responde, la app te lo avisa en pantalla en lugar de usar un valor viejo en silencio.</p></div>
<div><h3 class="l-h3">Código de cotización único</h3><p>Cada cotización lleva un código tipo FIQ-20261017-B43FD1, generado con los datos de la operación. Dos cotizaciones con los mismos datos el mismo día tienen el mismo código.</p></div>
<div><h3 class="l-h3">PDF y CSV para enviar</h3><p>Reporte de cotización en PDF con TRM, origen de la TRM y desglose completo. Exporta también a CSV para llevar los números a tu contabilidad.</p></div>
<div><h3 class="l-h3">Aranceles con estado honesto</h3><p>Arancel e IVA salen de la Consulta de Arancel de la DIAN y cada cotización muestra la fuente y la fecha de consulta. Lo que aún no está verificado se marca como referencia. La subpartida de tu producto la defines tú o tu agente de aduanas.</p></div>
</div></div>
<div class="fiq-land" style="padding:16px 0 40px"><div class="fiq-quien">
<div><h3 class="l-h3">Pymes y comerciantes</h3><p>Decide el precio de venta antes de pagar la importación, no después.</p></div>
<div><h3 class="l-h3">Agencias aduaneras</h3><p>Entrega a tus clientes una cotización clara, con código y respaldo en PDF.</p></div>
<div><h3 class="l-h3">Agentes de carga</h3><p>Muestra el costo total de la operación en la frontera de Cúcuta en una sola vista.</p></div>
</div></div>
<div class="fiq-land" style="padding:40px 0 0"><h2 class="l-h2" style="max-width:860px">Planes diseñados para la dinámica comercial de Cúcuta y la frontera</h2>
<p style="margin-top:16px;font-size:18px;max-width:640px;color:#26474A">Elimina los errores de cálculo en tus importaciones. Sin contratos de permanencia.</p></div>
<div style="height:40px"></div>""")

  # PLANES
  p1, p2, p3 = st.columns(3, gap="medium")
  with p1:
    with st.container(key="plan-starter"):
      st.html("""<div class="fiq-land"><h3 class="l-h3" style="font-size:34px!important">Starter</h3><div class="l-num l-precio">$0 COP</div><div class="l-nota">siempre gratis</div>
<p style="margin-top:16px;color:#26474A">Ideal para comerciantes e importadores que realizan cotizaciones ocasionales.</p>
<ul style="margin:18px 0 0;padding-left:20px;color:#26474A;display:grid;gap:8px"><li>Calculadora de costos landed en tiempo real</li><li>Consulta automática de la TRM oficial</li><li>Selector de partidas arancelarias NANDINA y consulta en vivo en la DIAN de cualquier subpartida (arancel variable y acuerdos por país de origen)</li><li>Código de cotización y exportación a CSV</li><li>Enlace directo para pedir asesoría por WhatsApp</li></ul></div>""")
      with st.container(key="cta-starter"):
        st.page_link(pagina_calculadora, label="Probar la calculadora gratis")
  with p2:
    with st.container(key="plan-pro"):
      st.html("""<div class="fiq-land"><div style="display:inline-block;background:#0B2527;color:#F5B700;font-weight:700;font-size:13px;padding:5px 12px;border-radius:14px">Recomendado para importadores frecuentes</div>
<h3 class="l-h3" style="font-size:34px!important;margin-top:12px!important">Pro Fronterizo</h3><div class="l-num l-precio">$39.000 COP <small>/ mes</small></div><div style="font-size:14px">o $390.000 COP al año: ahorras 2 meses</div>
<p style="margin-top:16px">Para comerciantes, importadores frecuentes y consultores que necesitan cotizar rápido y de forma formal.</p>
<ul style="margin:18px 0 0;padding-left:20px;display:grid;gap:8px"><li>Todo lo del plan Starter, más:</li><li>Descarga ilimitada de cotizaciones en PDF para entregar a tus clientes</li><li>Conversor multimoneda: COP, USD, bolívares (VES) y USDT, con tasas referenciales</li><li>Cotización multimercancía: varias mercancías en un embarque, cada una con su arancel e IVA, y flete, seguro y gastos repartidos según su valor</li></ul></div>""")
      with st.container(key="cta-pro-m"):
        st.link_button("Suscribirme: $39.000 al mes", LINK_PRO_MENSUAL(), width="stretch")
      with st.container(key="cta-pro-a"):
        st.link_button("Pagar el año: $390.000", LINK_PRO_ANUAL(), width="stretch")
      st.html('<p class="fiq-land" style="font-size:13px">Pagas con tarjeta, PSE o Nequi. Te enviamos tu clave de licencia por WhatsApp o correo.</p>')
  with p3:
    with st.container(key="plan-agencia"):
      st.html("""<div class="fiq-land"><h3 class="l-h3" style="font-size:34px!important">Agencia / Corporativo</h3><div class="l-num l-precio">$149.000 COP <small>/ mes</small></div><div class="l-nota">&nbsp;</div>
<p style="margin-top:16px;color:#26474A">Diseñado para agencias de aduanas (SIA), depósitos y agentes de carga.</p>
<ul style="margin:18px 0 0;padding-left:20px;color:#26474A;display:grid;gap:8px"><li>Todo lo del plan Pro, más:</li><li>Soporte prioritario y capacitación de uso</li><li>Atención directa por WhatsApp para resolver dudas de tus operaciones</li></ul></div>""")
      with st.container(key="cta-agencia"):
        st.link_button("Hablar con un asesor", LINK_AGENCIA(), width="stretch")

  # LÍMITES + CTA FINAL + PIE
  st.html("""<div class="fiq-land" style="padding:72px 0"><h2 class="l-h2" style="font-size:40px!important">Lo que la app todavía no hace</h2>
<p style="margin-top:12px;max-width:720px;color:#26474A">Es una estimación de costos, no una liquidación oficial de la DIAN. No clasifica tu mercancía: la subpartida la defines tú o tu agente de aduanas. Las exportaciones a Venezuela aún no están disponibles. Confirma siempre con tu agente antes de cerrar una operación.</p></div>""")
  with st.container(key="band-final"):
    st.html("""<div class="fiq-land"><h2 class="l-h2" style="font-size:clamp(40px,3.6vw,56px)!important;max-width:640px">Conoce el costo real antes de que llegue el contenedor.</h2><div style="height:28px"></div></div>""")
    with st.container(key="cta-final"):
      st.page_link(pagina_calculadora, label="Abrir FronteraIQ Pro")
  st.html("""<div class="fiq-land l-nota" style="padding:28px 0;display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between"><div>FronteraIQ Pro · Cúcuta, Norte de Santander</div><div>Estimación de costos. No constituye liquidación oficial de la DIAN.</div></div>""")
