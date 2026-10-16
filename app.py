import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# Configuración de la página
st.set_page_config(
    page_title="Forex SMC & Price Action Analyzer", layout="wide"
)

st.title(
    "📈 Analizador SMC & Price Action (OB + FVG en 1H + Confirmación en 5M)"
)
st.markdown(
    """
Esta herramienta detecta automáticamente zonas institucionales en **1H** (Order Blocks y Fair Value Gaps impulsados por rompimientos de estructura BOS) y las proyecta para buscar la confirmación en **5M**.
"""
)

# Sidebar
st.sidebar.header("⚙️ Configuración")
ticker_symbol = st.sidebar.selectbox(
    "Par de Divisas", ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"], index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Control de Riesgo")
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


with st.spinner("Cargando datos de mercado..."):
    try:
        data_1h, data_5m = cargar_datos(ticker_symbol)
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()


def detectar_zonas_smc_1h(df, df_5m_ref):
    """Detecta Fair Value Gaps (FVG) y Order Blocks (OB) basados en estructura de 1H."""
    df = df.copy()
    fvg_list = []
    ob_list = []

    # Calcular rangos y cuerpos
    df["Body"] = abs(df["Close"] - df["Open"])
    df["Range"] = df["High"] - df["Low"]
    avg_range = df["Range"].mean()

    # Recorrer el DataFrame de 1H buscando patrones institucionales (últimas 100 velas)
    for i in range(2, len(df) - 1):
        # 1. Detección de Fair Value Gaps (FVG)
        # Impulso alcista: El Low de la vela i es mayor que el High de la vela i-2
        if df["Low"].iloc[i] > df["High"].iloc[i - 2]:
            fvg_list.append(
                {
                    "tipo": "FVG Alcista",
                    "zona_inferior": df["High"].iloc[i - 2],
                    "zona_superior": df["Low"].iloc[i],
                    "tiempo": df.index[i],
                }
            )
        # Impulso bajista: El High de la vela i es menor que el Low de la vela i-2
        elif df["High"].iloc[i] < df["Low"].iloc[i - 2]:
            fvg_list.append(
                {
                    "tipo": "FVG Bajista",
                    "zona_inferior": df["High"].iloc[i],
                    "zona_superior": df["Low"].iloc[i - 2],
                    "tiempo": df.index[i],
                }
            )

        # 2. Detección de Order Blocks (OB)
        # Impulso alcista fuerte (vela grande tras una bajista)
        if (
            df["Close"].iloc[i] > df["Open"].iloc[i]
            and df["Range"].iloc[i] > avg_range * 1.2
            and df["Close"].iloc[i - 1] < df["Open"].iloc[i - 1]
        ):
            ob_list.append(
                {
                    "tipo": "OB Alcista",
                    "zona_inferior": df["Low"].iloc[i - 1],
                    "zona_superior": df["High"].iloc[i - 1],
                    "tiempo": df.index[i - 1],
                }
            )
        # Impulso bajista fuerte (vela grande tras una alcista)
        elif (
            df["Close"].iloc[i] < df["Open"].iloc[i]
            and df["Range"].iloc[i] > avg_range * 1.2
            and df["Close"].iloc[i - 1] > df["Open"].iloc[i - 1]
        ):
            ob_list.append(
                {
                    "tipo": "OB Bajista",
                    "zona_inferior": df["Low"].iloc[i - 1],
                    "zona_superior": df["High"].iloc[i - 1],
                    "tiempo": df.index[i - 1],
                }
            )

    precio_actual = df_5m_ref["Close"].iloc[-1]

    # Filtrar zonas recientes y cercanas al precio actual (últimos elementos de las listas)
    valid_fvgs = [
        f
        for f in fvg_list[-15:]
        if abs(f["zona_inferior"] - precio_actual) / precio_actual < 0.02
    ]
    valid_obs = [
        o
        for o in ob_list[-15:]
        if abs(o["zona_inferior"] - precio_actual) / precio_actual < 0.02
    ]

    return valid_fvgs, valid_obs, precio_actual


fvgs, obs, precio_actual = detectar_zonas_smc_1h(data_1h, data_5m)

# Interfaz en Pestañas
tab1, tab2, tab3 = st.tabs(
    [
        "📊 Gráficos SMC (1H Zonas + 5M Gatillo)",
        "🔍 Auditoría de Zonas (OB & FVG)",
        "💡 Plan y Gestión de Riesgo",
    ]
)

with tab1:
    st.subheader(f"Estructura Institucional para {ticker_symbol}")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ⏱️ Zonas 1H (Order Blocks & FVGs)")
        df_1h_plot = data_1h.tail(100)
        fig_1h = go.Figure(
            data=[
                go.Candlestick(
                    x=df_1h_plot.index,
                    open=df_1h_plot["Open"],
                    high=df_1h_plot["High"],
                    low=df_1h_plot["Low"],
                    close=df_1h_plot["Close"],
                    name="1H",
                )
            ]
        )

        # Dibujar Order Blocks en el gráfico de 1H
        for ob in obs:
            color_ob = "blue" if "Alcista" in ob["tipo"] else "orange"
            fig_1h.add_shape(
                type="rect",
                x0=ob["tiempo"],
                x1=df_1h_plot.index[-1],
                y0=ob["zona_inferior"],
                y1=ob["zona_superior"],
                line=dict(color=color_ob, width=1),
                fillcolor=color_ob,
                opacity=0.3,
            )

        fig_1h.update_layout(
            title="Zonas de Order Blocks (1H)",
            xaxis_title="Fecha",
            yaxis_title="Precio",
            height=500,
            template="plotly_dark",
        )
        st.plotly_chart(fig_1h, use_container_width=True)

    with col2:
        st.markdown("### ⏱️ Seguimiento y Gatillo en 5M")
        df_5m_plot = data_5m.tail(150)
        fig_5m = go.Figure(
            data=[
                go.Candlestick(
                    x=df_5m_plot.index,
                    open=df_5m_plot["Open"],
                    high=df_5m_plot["High"],
                    low=df_5m_plot["Low"],
                    close=df_5m_plot["Close"],
                    name="5M",
                )
            ]
        )

        # Proyectar Order Blocks en 5M para buscar confirmación de giro o quiebre interno
        for ob in obs:
            color_ob = "blue" if "Alcista" in ob["tipo"] else "orange"
            fig_5m.add_hline(
                y=ob["zona_superior"],
                line_dash="dot",
                line_color=color_ob,
                annotation_text=ob["tipo"],
            )

        fig_5m.update_layout(
            title="Reacción del Precio en 5M",
            xaxis_title="Fecha",
            yaxis_title="Precio",
            height=500,
            template="plotly_dark",
        )
        st.plotly_chart(fig_5m, use_container_width=True)

with tab2:
    st.subheader("📋 Detalle de Zonas Institucionales Detectadas")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 🟦 Order Blocks (OB) Activos en 1H")
        if obs:
            for o in obs:
                st.info(
                    f"• **{o['tipo']}** | Rango: {o['zona_inferior']:.5f} - {o['zona_superior']:.5f}"
                )
        else:
            st.warning("No se detectaron Order Blocks cercanos al precio actual.")

    with col_b:
        st.markdown("### 🟩 Fair Value Gaps (FVG) Activos en 1H")
        if fvgs:
            for f in fvgs:
                st.success(
                    f"• **{f['tipo']}** | Zona: {f['zona_inferior']:.5f} - {f['zona_superior']:.5f}"
                )
        else:
            st.warning("No se detectaron FVGs cercanos al precio actual.")

with tab3:
    st.subheader("🎯 Panel de Gestión de Riesgo y Sesión")
    op_abiertas = st.number_input(
        "Operaciones abiertas actualmente:", 0, 10, 1, 1
    )
    ops_perdidas_hoy = st.number_input(
        "Operaciones perdedoras hoy:", 0, 10, 0, 1
    )

    if op_abiertas > 3:
        st.error(
            "🚨 **ALERTA DE RIESGO:** Máximo 3 operaciones abiertas simultáneamente."
        )
    elif ops_perdidas_hoy >= 4:
        st.error(
            "🚨 **STOP TRADING:** Límite diario de 4 operaciones perdedoras alcanzado. Cierra pantallas."
        )
    else:
        st.success(
            "✅ **Riesgo Controlado:** Puedes operar bajo supervisión de tus reglas."
        )
