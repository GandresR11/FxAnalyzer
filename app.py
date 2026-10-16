import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página
st.set_page_config(
    page_title="Forex Price Action Analyzer (1H + 5M)", layout="wide"
)

st.title(
    "📈 Analizador Avanzado de Price Action (Zonas 1H + Confirmación 5M)"
)
st.markdown(
    """
Esta aplicación combina dos temporalidades para tu operativa:
* **Gráfico 1H (Zonas Macro):** Identificación visual de soportes y resistencias estructurales.
* **Gráfico 5M (Gatillo Micro):** Detalle de la acción del precio para buscar la confirmación de entrada.
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

# Pestañas principales de navegación
tab1, tab2, tab3 = st.tabs(
    [
        "📊 Gráficos Multi-Temporalidad (1H y 5M)",
        "🔍 Análisis y Confluencia",
        "💡 Plan de Entrada y Riesgo",
    ]
)

with tab1:
    st.subheader(f"Estructura para {ticker_symbol}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Precio Actual", f"{precio_actual:.5f}")
    col2.metric(
        "Resistencia 1H cercana",
        (
            f"{zonas_resistencia[0]:.5f}"
            if len(zonas_resistencia) > 0
            else "N/A"
        ),
    )
    col3.metric(
        "Soporte 1H cercano",
        f"{zonas_soporte[0]:.5f}" if len(zonas_soporte) > 0 else "N/A",
    )

    st.markdown("---")

    # Layout en dos columnas para ver ambos gráficos lado a lado (o apilados si prefieres)
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### ⏱️ Temporalidad 1H (Zonas Macro)")
        df_1h_plot = data_1h.tail(120)  # Últimas 120 velas de 1 hora
        fig_1h = go.Figure(
            data=[
                go.Candlestick(
                    x=df_1h_plot.index,
                    open=df_1h_plot["Open"],
                    high=df_1h_plot["High"],
                    low=df_1h_plot["Low"],
                    close=df_1h_plot["Close"],
                    name="1H Candles",
                )
            ]
        )

        # Pintar las zonas de 1H en su propio gráfico para ver de dónde salen
        for r in zonas_resistencia:
            fig_1h.add_hline(
                y=r,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Res: {r:.5f}",
                annotation_position="top right",
            )
        for s in zonas_soporte:
            fig_1h.add_hline(
                y=s,
                line_dash="dash",
                line_color="green",
                annotation_text=f"Sop: {s:.5f}",
                annotation_position="bottom right",
            )

        fig_1h.update_layout(
            title="Estructura de 1H (Origen de Zonas)",
            xaxis_title="Fecha / Hora",
            yaxis_title="Precio",
            height=500,
            template="plotly_dark",
        )
        st.plotly_chart(fig_1h, use_container_width=True)

    with col_g2:
        st.markdown("### ⏱️ Temporalidad 5M (Gatillo de Entrada)")
        df_5m_plot = data_5m.tail(150)  # Últimas 150 velas de 5 minutos
        fig_5m = go.Figure(
            data=[
                go.Candlestick(
                    x=df_5m_plot.index,
                    open=df_5m_plot["Open"],
                    high=df_5m_plot["High"],
                    low=df_5m_plot["Low"],
                    close=df_5m_plot["Close"],
                    name="5M Candles",
                )
            ]
        )

        # Repetir las líneas de 1H sobre el gráfico de 5M para ver la interacción en tiempo real
        for r in zonas_resistencia:
            fig_5m.add_hline(
                y=r,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Res 1H",
                annotation_position="top right",
            )
        for s in zonas_soporte:
            fig_5m.add_hline(
                y=s,
                line_dash="dash",
                line_color="green",
                annotation_text=f"Sop 1H",
                annotation_position="bottom right",
            )

        fig_5m.update_layout(
            title="Acción del Precio en 5M (Confirmación)",
            xaxis_title="Fecha / Hora",
            yaxis_title="Precio",
            height=500,
            template="plotly_dark",
        )
        st.plotly_chart(fig_5m, use_container_width=True)

with tab2:
    st.subheader("📋 Confluencia entre 1H y 5M")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### ⏱️ Zonas Identificadas en 1H")
        st.write(
            "Los niveles se calculan analizando los máximos y mínimos de pivote recientes en la temporalidad de 1 hora:"
        )
        if len(zonas_resistencia) > 0:
            st.success(
                f"🔴 Resistencias 1H: {[round(x, 5) for x in zonas_resistencia]}"
            )
        if len(zonas_soporte) > 0:
            st.success(
                f"🟢 Soportes 1H: {[round(x, 5) for x in zonas_soporte]}"
            )

    with col_b:
        st.markdown("### ⏱️ Lectura de Acción del Precio en 5M")
        ultimas_velas = data_5m.tail(3)
        cierre_ult = ultimas_velas["Close"].iloc[-1]
        apertura_ult = ultimas_velas["Open"].iloc[-1]

        if cierre_ult > apertura_ult:
            st.info(
                "ℹ️ **Estado 5M:** Vela actual alcista. Espere acercamiento y rechazo en los soportes de 1H marcados en verde."
            )
        else:
            st.info(
                "ℹ️ **Estado 5M:** Vela actual bajista. Espere acercamiento y rechazo en las resistencias de 1H marcadas en rojo."
            )

with tab3:
    st.subheader("🎯 Plan de Operación y Control de Riesgo")
    st.markdown(
        """
    1. **Ubicación (1H):** Valida en el gráfico de 1H por qué la zona fue trazada (confluencia de máximos/mínimos anteriores).
    2. **Gatillo (5M):** Observa cómo reacciona el precio en el gráfico de 5M al tocar esa línea institucional. Busca velas de rechazo o ruptura de estructura interna.
    3. **Gestión de Riesgo:**
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
            "🚨 **ALERTA DE RIESGO:** Máximo 3 operaciones abiertas simultáneamente."
        )
    elif ops_perdidas_hoy >= 4:
        st.error(
            "🚨 **STOP TRADING:** Límite diario de 4 operaciones perdedoras alcanzado. Detén la operativa."
        )
    else:
        st.success(
            "✅ **Estado de Riesgo Aceptable:** Operando dentro de los parámetros permitidos."
        )
