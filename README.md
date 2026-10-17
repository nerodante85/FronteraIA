# 🚢 FronteraIQ Pro

**Inteligencia aduanera y cálculo de Costo Landed para la frontera de Cúcuta.**

FronteraIQ es una aplicación web que calcula en segundos el costo real de una importación puesto en destino (*Costo Landed*): valor CIF, tributos DIAN, gastos logísticos locales, costo unitario y precio de venta sugerido. Reemplaza las hojas de cálculo manuales por una herramienta interactiva, pensada para pymes, comerciantes, agencias de aduanas y agentes de carga que operan en Cúcuta.

---

## Tabla de contenido

- [Funcionalidades](#funcionalidades)
- [Planes: Gratuito y Pro](#planes-gratuito-y-pro)
- [Cómo se calcula](#cómo-se-calcula)
- [Stack tecnológico](#stack-tecnológico)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Configuración](#configuración)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Limitaciones y descargo de responsabilidad](#limitaciones-y-descargo-de-responsabilidad)
- [Hoja de ruta](#hoja-de-ruta)

---

## Funcionalidades

- **Base de partidas NANDINA** precargada (confecciones, calzado, celulares, portátiles, arroz, autopartes, medicamentos) con arancel e IVA sugeridos, más una opción *Personalizado* para cualquier otra partida.
- **TRM automática** consultada al servicio de datos abiertos de Colombia (`datos.gov.co`) con caché de una hora. Si la consulta falla, se usa un valor de respaldo de 4.000 COP/USD. La TRM puede ajustarse manualmente.
- **Liquidación completa** de CIF (FOB + flete + seguro), arancel, IVA y gastos logísticos de frontera: agenciamiento SIA, bodegaje, transporte local y otros gastos.
- **Indicadores clave**: costo total landed, costo unitario, impuestos DIAN y precio de venta sugerido según el margen deseado.
- **Visualización**: gráfico de distribución de costos (CIF, tributos y gastos locales) y tabla de desglose de la liquidación.
- **Exportación** a CSV, y a PDF de cotización en el plan Pro.
- **Contacto directo por WhatsApp** con un mensaje prellenado con los datos de la operación.

## Planes: Gratuito y Pro

| Capacidad | Gratuito | Pro |
|---|:---:|:---:|
| Cálculo de Costo Landed y precio sugerido | ✅ | ✅ |
| Base NANDINA y TRM oficial | ✅ | ✅ |
| Gráfico y tabla de liquidación | ✅ | ✅ |
| Exportar a CSV | ✅ | ✅ |
| Contacto por WhatsApp | ✅ | ✅ |
| Cotización en PDF | — | ✅ |
| Equivalencia multimoneda fronteriza (USDT y bolívares) | — | ✅ |

> El plan Pro se activa en la barra lateral con una clave de licencia. En la versión actual es un mecanismo de demostración (ver [Limitaciones](#limitaciones-y-descargo-de-responsabilidad)).

## Cómo se calcula

```
CIF            = FOB + Flete + Seguro                     (USD)
CIF (COP)      = CIF × TRM
Arancel        = CIF (COP) × % arancel
Base IVA       = CIF (COP) + Arancel
IVA            = Base IVA × % IVA
Tributos DIAN  = Arancel + IVA
Gastos locales = Agenciamiento + Bodegaje + Transporte + Otros
Costo Landed   = CIF (COP) + Tributos DIAN + Gastos locales
Costo unitario = Costo Landed ÷ Unidades
Precio sugerido = Costo unitario ÷ (1 − % margen)
```

El precio sugerido aplica el margen sobre el precio de venta (no un recargo sobre el costo): con un margen del 30 %, el costo representa el 70 % del precio.

## Stack tecnológico

| Componente | Uso |
|---|---|
| [Streamlit](https://streamlit.io/) | Interfaz web y servidor de la aplicación |
| [pandas](https://pandas.pydata.org/) | Tablas y exportación a CSV |
| [Plotly](https://plotly.com/python/) | Gráfico de distribución de costos |
| [requests](https://requests.readthedocs.io/) | Consulta de la TRM a `datos.gov.co` |
| [fpdf2](https://py-pdf.github.io/fpdf2/) | Generación del PDF de cotización |

## Instalación y ejecución

**Requisitos:** Python 3.11 o superior.

```bash
# 1. Clonar el repositorio
git clone https://github.com/nerodante85/FronteraIA.git
cd FronteraIA

# 2. (Opcional) Crear un entorno virtual
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
streamlit run app.py
```

La aplicación queda disponible en `http://localhost:8501`.

El repositorio incluye una configuración de **Dev Container** (`.devcontainer/`) para abrirlo directamente en GitHub Codespaces o VS Code con todo el entorno listo.

## Configuración

**Licencia Pro.** La clave no está en el código. Se define con el nombre `PRO_LICENSE_KEY`, en `.streamlit/secrets.toml` (local, ya ignorado por Git) o en los *Secrets* del despliegue, o como variable de entorno:

```toml
# .streamlit/secrets.toml
PRO_LICENSE_KEY = "una-clave-larga-y-unica"
```

Mientras no esté definida, el plan Pro no se puede activar.

**Valores en el código** (`app.py`):

| Parámetro | Ubicación | Descripción |
|---|---|---|
| `TELEFONO_WHATSAPP` | Inicio del archivo | Número de contacto con prefijo de país (por ejemplo `57...`) |
| `DATABASE_NANDINA` | Sección *Base de datos NANDINA* | Partidas, aranceles e IVA predefinidos; se pueden agregar nuevas entradas |
| `PARTIDAS_VALIDADAS` | Después de la tabla NANDINA | Partidas ya validadas por un agente de aduanas, con fuente y vigencia (ver `docs/validacion-nandina.csv`) |
| `TRM_RESPALDO` | Sección *Consulta TRM* | TRM usada, con advertencia visible, si la consulta a `datos.gov.co` falla |

## Pruebas

La suite usa `pytest` y el arnés de pruebas de Streamlit; no hace llamadas de red (la TRM se simula).

```bash
pip install -r requirements-dev.txt
pytest -q
```

Cubre la cadena de cálculo, la consulta de la TRM (éxito, falla, caché y forma de la consulta), la licencia Pro, la generación del PDF con texto especial y los avisos de la tabla NANDINA. Se ejecuta automáticamente en GitHub Actions (Python 3.11 y 3.13) en cada *push* y *pull request*.

## Estructura del repositorio

```
.
├── app.py                  # Aplicación completa (interfaz, cálculos, PDF)
├── requirements.txt        # Dependencias fijadas
├── requirements-dev.txt    # Dependencias + pytest
├── pytest.ini
├── tests/                  # Pruebas automáticas
├── docs/                   # Roadmap de IA y hoja de validación NANDINA
├── .github/workflows/      # Integración continua
├── .devcontainer/          # Entorno de desarrollo para Codespaces / VS Code
└── README.md
```

## Limitaciones y descargo de responsabilidad

- **Las cifras son estimaciones.** La herramienta proyecta costos para apoyar la toma de decisiones y **no constituye una liquidación oficial de la DIAN**. Los aranceles e IVA de la base NANDINA son valores de referencia: deben verificarse contra la normativa y el arancel vigentes antes de cualquier operación.
- **Alcance actual:** la versión actual calcula **importaciones a Colombia**. El cálculo de exportaciones hacia Venezuela aún no está implementado.
- **Licencia Pro básica:** hay una única clave compartida, validada dentro de la app. Sirve para demos y pilotos; para uso comercial se recomienda un sistema de licencias por usuario en servidor.
- Las tasas COP/VES y COP/USDT del plan Pro son valores editables por el usuario, no cotizaciones en tiempo real.

## Hoja de ruta

- [ ] Módulo de exportaciones a Venezuela
- [ ] Ampliar la base de partidas NANDINA y mantener aranceles actualizados
- [ ] Licenciamiento y autenticación de usuarios en servidor
- [ ] Historial de cotizaciones guardadas
- [ ] Tasas fronterizas (VES y USDT) en tiempo real
- [x] Pruebas automatizadas y CI
- [ ] Validar la tabla NANDINA con un agente de aduanas (`docs/validacion-nandina.csv`)
