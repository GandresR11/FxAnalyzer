import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página
st.set_page_config(
    page_title="Forex Price Action Analyzer (1H + 5M)", layout="wide"
)

st.title("📈 Analizador de Price Action (1H Zonas + 5M Confirmación)")
st.markdown(
    """
Esta aplicación analiza gráficos de Forex combinando múltiples temporalidades:
* **Temporalidad 1H:** Identificación de zonas institucionales clave (Soportes/Resistencias).
* **Temporalidad 5M:** Búsqueda de gatillos de entrada y confirmaciones de precio.
"""
)

# Sidebar de configuración
st.sidebar.header("⚙️ Parámetros de Configuración")
ticker_symbol = st.sidebar.selectbox(
    "Par de Divisas (Yahoo Finance)",
    [
        "EURUSD=X",
        "GBPUSD=X",
        "USDJPY=X",
        "AUDUSD=X",
        "USDCAD=X",
        "EURGBP=X",
    ],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Reglas de Gestión de Riesgo")
st.sidebar.info(
    "• Máximo 3 operaciones abiertas simultáneamente.\n• Hasta 4 operaciones perdedoras permitidas por día."
)


@st.cache_data(ttl=300)
def cargar_datos(ticker):
    df_1h = yf.download(
        ticker, period="30d", interval="60m", progress=False
    )
    df_5m = yf.download(ticker, period="5d", interval="5m", progress=False)

    if isinstance(df_1h.columns, pd.MultiIndex):
        df_1h.columns = df_1h.columns.get_level_values(0)
    if isinstance(df_5m.columns, pd.MultiIndex):
        df_5m.columns = df_5m.columns.get_level_values(0)

    return df_1h, df_5m


with st.spinner(f"Cargando y procesando datos para {ticker_symbol}..."):
    try:
        data_1h, data_5m = cargar_datos(ticker_symbol)
    except Exception as e:
        st.error(f"Error al descargar los datos: {e}")
        st.stop()


def identificar_zonas_1h(df, df_5m_ref):
    df = df.copy()
    window = 10
    df["Resistencia_1H"] = df["High"].rolling(window=window, center=True).max()
    df["Soporte_1H"] = df["Low"].rolling(window=window, center=True).min()

    resistencias = df["Resistencia_1H"].dropna().unique()
    soportes = df["Soporte_1H"].dropna().unique()

    precio_actual = df_5m_ref["Close"].iloc[-1]

    zonas_res = sorted(
        [r for r in resistencias if r >= precio_actual * 0.995], reverse=False
    )[:3]
    zonas_sop = sorted(
        [s for s in soportes if s <= precio_actual * 1.005], reverse=True
    )[:3]

    return zonas_res, zonas_sop, precio_actual


zonas_resistencia, zonas_soporte, precio_actual = identificar_zonas_1h(
    data_1h, data_5m
)

tab1, tab2, tab3 = st.tabs(
    ["📊 Gráfico y Niveles Operativos", "🔍 Análisis 1H vs 5M", "💡 Plan de Entrada"]
)

with tab1:
    st.subheader(f"Estructura de Mercado para {ticker_symbol}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Precio Actual", f"{precio_actual:.5f}")
    col2.metric(
        "Zona 1H Resistencia más cercana",
        (
            f"{zonas_resistencia[0]:.5f}"
            if len(zonas_resistencia) > 0
            else "N/A"
        ),
    )
    col3.metric(
        "Zona 1H Soporte más cercano",
        f"{zonas_soporte[0]:.5f}" if len(zonas_soporte) > 0 else "N/A",
    )

    df_plot = data_5m.tail(150)
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df_plot.index,
                open=df_plot["Open"],
                high=df_plot["High"],
                low=df_plot["Low"],
                close=df_plot["Close"],
                name="Precio 5M",
            )
        ]
    )

    for r in zonas_resistencia:
        fig.add_hline(
            y=r,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Resistencia 1H: {r:.5f}",
            annotation_position="top right",
        )
    for s in zonas_soporte:
        fig.add_hline(
            y=s,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Soporte 1H: {s:.5f}",
            annotation_position="bottom right",
        )

    fig.update_layout(
        title="Gráfico de 5 Minutos con Zonas Clave de 1H",
        xaxis_title="Fecha / Hora",
        yaxis_title="Precio",
        height=600,
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📋 Estado de Confluencia Temporal")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### ⏱️ Temporalidad 1H (Zonas Macro)")
        if len(zonas_resistencia) > 0:
            st.success(
                f"✅ Zonas de Resistencia identificadas: {[round(x, 5) for x in zonas_resistencia]}"
            )
        else:
            st.warning("⚠️ No se detectaron resistencias claras cercanas.")

        if len(zonas_soporte) > 0:
            st.success(
                f"✅ Zonas de Soporte identificadas: {[round(x, 5) for x in zonas_soporte]}"
            )
        else:
            st.warning("⚠️ No se detectaron soportes claros cercanos.")

    with col_b:
        st.markdown("### ⏱️ Temporalidad 5M (Gatillo de Entrada)")
        ultimas_velas = data_5m.tail(3)
        cierre_ult = ultimas_velas["Close"].iloc[-1]
        apertura_ult = ultimas_velas["Open"].iloc[-1]

        if cierre_ult > apertura_ult:
            st.info(
                "ℹ️ **Estado 5M:** Vela actual alcista. Monitorear rechazos en soporte 1H."
            )
        else:
            st.info(
                "ℹ️ **Estado 5M:** Vela actual bajista. Monitorear reacciones en resistencia 1H."
            )

        st.markdown(
            "**Criterio de Confirmación:**\n1. Llegada del precio a zona 1H.\n2. Patrón de rechazo o giro en 5M.\n3. Confirmación de aceleración a favor."
        )

with tab3:
    st.subheader("🎯 Plan de Operación y Reglas de Entrada")
    st.markdown(
        """
    1. **Ubicación (1H):** El precio interactúa exactamente con una línea de soporte o resistencia.
    2. **Gatillo (5M):** Esperar patrón de rechazo o ruptura de estructura en 5 minutos.
    3. **Gestión de Riesgo:** Máximo 3 operaciones simultáneas y hasta 4 perdedoras por día.
    """
    )

    st.markdown("---")
    st.markdown("### 🛠️ Panel de Control de Sesión")
    op_abiertas = st.number_input(
        "Operaciones abiertas actualmente:",
        min_value=0,
        max_value=10,
        value=1,
        step=1,
    )
    ops_perdidas_hoy = st.number_input(
        "Operaciones perdedoras hoy:", min_value=0, max_value=10, value=0, step=1
    )

    if op_abiertas > 3:
        st.error(
            "🚨 **ALERTA DE RIESGO:** Has superado el límite de 3 operaciones abiertas al mismo tiempo."
        )
    elif ops_perdidas_hoy >= 4:
        st.error(
            "🚨 **STOP TRADING:** Has alcanzado el límite de 4 operaciones perdedoras en el día. Descansa."
        )
    else:
        st.success(
            "✅ **Estado de Riesgo Aceptable:** Operativa bajo control de reglas."
        )
