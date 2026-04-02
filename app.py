import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Import custom modules
from database import TradingDatabase
from utils import TradingBot, create_price_chart, create_performance_chart, create_rsi_chart, create_atr_chart, create_fear_greed_gauge, get_fear_greed_emoji, get_fear_greed_color
from config import ConfigManager, init_session_state, get_available_symbols

# Initialize session state
init_session_state()

# Initialize database and config
db = TradingDatabase()
config = ConfigManager(db)
bot = TradingBot(db)

# Enhanced page configuration
st.set_page_config(
    page_title="Bot IA Trading - Professional Edition",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .signal-buy {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
    .signal-sell {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Page Header
st.markdown('<h1 class="main-header">🤖 Bot de Trading IA - Professional Edition</h1>', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #666; margin-bottom: 2rem;'>
    Sistema inteligente de trading con análisis técnico y machine learning
</div>
""", unsafe_allow_html=True)

# Navigation
page_options = ["Dashboard", "Análisis Técnico", "Historial de Operaciones", "Configuración"]
current_page_index = 0
if hasattr(st.session_state, 'page') and st.session_state.page in page_options:
    current_page_index = page_options.index(st.session_state.page)

page = st.sidebar.selectbox(
    "📍 Navegación",
    page_options,
    index=current_page_index
)
st.session_state.page = page

# Sidebar Configuration
st.sidebar.header("⚙️ Configuración del Bot")

# Symbol selection with enhanced options
available_symbols = get_available_symbols()
simbolo = st.sidebar.selectbox(
    "📊 Activo a analizar",
    available_symbols,
    index=available_symbols.index(config.get_setting('default_symbol')) if config.get_setting('default_symbol') in available_symbols else 0
)
st.session_state.current_symbol = simbolo

# Time period selection
dias_historial = st.sidebar.slider(
    "📅 Días de historial",
    min_value=7,
    max_value=90,
    value=int(config.get_setting('default_days')),
    step=7
)
st.session_state.current_days = dias_historial

# Risk level
risk_levels = [("low", "Bajo"), ("medium", "Medio"), ("high", "Alto")]
risk_level = st.sidebar.selectbox(
    "⚠️ Nivel de Riesgo",
    options=[level[1] for level in risk_levels],
    index=[level[0] for level in risk_levels].index(config.get_setting('risk_level'))
)

# Auto-save option
auto_save = st.sidebar.checkbox(
    "💾 Guardar datos automáticamente",
    value=config.get_setting('auto_save') == 'true'
)

# Refresh button
if st.sidebar.button("🔄 Actualizar Datos", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Load and process data
with st.spinner("🔄 Descargando datos y ejecutando análisis IA..."):
    df = bot.get_market_data(simbolo, dias_historial)
    
    if not df.empty:
        df = bot.calculate_indicators(df)
        model, predictions, df_ml, X_test, X_train, y_train, y_test = bot.train_model(df)
        capital_bot, capital_holding, stop_loss_data = bot.simulate_trading(df_ml, X_test, predictions)
        
        # Save data if auto-save is enabled
        if auto_save:
            bot.save_session_data(simbolo, df, capital_bot, capital_holding, predictions)
        
        st.session_state.last_update = datetime.now()
    else:
        st.error("No se pudieron obtener los datos del mercado. Por favor, intenta con otro símbolo.")
        st.stop()

# Dashboard Page
if page == "Dashboard":
    # Key Metrics with enhanced styling
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        current_price = float(df['close'].iloc[-1])
        price_change = float(df['close'].pct_change().iloc[-1] * 100) if len(df) > 1 else 0
        st.metric(
            label="💰 Precio Actual",
            value=f"${current_price:,.2f}",
            delta=f"{price_change:+.2f}%",
            delta_color="normal" if price_change >= 0 else "inverse"
        )
    
    with col2:
        bot_capital = float(capital_bot.iloc[-1]) if not capital_bot.empty else 1000
        bot_return = ((bot_capital - 1000) / 1000) * 100
        st.metric(
            label="🤖 Capital Bot IA",
            value=f"${bot_capital:,.2f}",
            delta=f"{bot_return:+.2f}%",
            delta_color="normal" if bot_return >= 0 else "inverse"
        )
    
    with col3:
        market_capital = float(capital_holding.iloc[-1]) if not capital_holding.empty else 1000
        market_return = ((market_capital - 1000) / 1000) * 100
        st.metric(
            label="📈 Capital Mercado",
            value=f"${market_capital:,.2f}",
            delta=f"{market_return:+.2f}%",
            delta_color="normal" if market_return >= 0 else "inverse"
        )
    
    with col4:
        current_signal = predictions[-1] if len(predictions) > 0 else 0
        signal_text = "🟢 COMPRAR" if current_signal == 1 else "🔴 VENDER"
        signal_class = "signal-buy" if current_signal == 1 else "signal-sell"
        st.markdown(f"<div class='{signal_class}'>{signal_text}</div>", unsafe_allow_html=True)
    
    with col5:
        # Fear & Greed Index
        fear_greed_value = int(df['fear_greed_index'].iloc[-1]) if 'fear_greed_index' in df.columns else 50
        fear_greed_text = get_fear_greed_emoji(fear_greed_value)
        fear_greed_color = get_fear_greed_color(fear_greed_value)
        st.markdown(f"<div style='background: linear-gradient(135deg, {fear_greed_color} 0%, #666 100%); color: white; padding: 1rem; border-radius: 8px; text-align: center; font-weight: bold;'>🧠 {fear_greed_text}</div>", unsafe_allow_html=True)
    
    st.divider()
    
    # Performance Chart
    st.subheader("📊 Comparativa de Estrategias")
    if not capital_bot.empty and not capital_holding.empty:
        dates = df_ml.loc[X_test.index, 'date']
        perf_fig = create_performance_chart(capital_bot, capital_holding, dates)
        st.plotly_chart(perf_fig, use_container_width=True)
    
    # Stop Loss Information
    if stop_loss_data and stop_loss_data.get('stop_loss') is not None:
        st.subheader("🛡️ Trailing Stop Loss Dinámico")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Stop Loss", f"${stop_loss_data['stop_loss']:,.2f}")
        
        with col2:
            st.metric("Take Profit", f"${stop_loss_data['take_profit']:,.2f}")
        
        with col3:
            st.metric("ATR Actual", f"{stop_loss_data['atr']:.4f}")
        
        with col4:
            st.metric("ATR %", f"{stop_loss_data['atr_percentage']:.2f}%")
    
    # Technical Indicators
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💹 Indicadores Técnicos")
        
        # RSI
        rsi_value = df['rsi_14'].iloc[-1] if 'rsi_14' in df.columns else 0
        st.metric("RSI (14)", f"{rsi_value:.2f}", delta=None)
        
        # Moving Averages
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            st.metric("SMA 20", f"${sma_20:,.2f}")
            st.metric("SMA 50", f"${sma_50:,.2f}")
        
        # Volatility
        if 'volatilidad' in df.columns:
            volatility = df['volatilidad'].iloc[-1]
            st.metric("Volatilidad", f"{volatility:.4f}")
        
        # ATR
        if 'atr' in df.columns:
            atr_value = df['atr'].iloc[-1]
            st.metric("ATR (14)", f"{atr_value:.4f}")
    
    with col2:
        st.subheader("📈 Estadísticas del Modelo")
        
        if len(predictions) > 0:
            accuracy = (predictions == y_test).mean() * 100
            win_rate = np.mean(predictions) * 100
            total_signals = len(predictions)
            buy_signals = np.sum(predictions)
            
            st.metric("Precisión del Modelo", f"{accuracy:.1f}%")
            st.metric("Tasa de Compra", f"{win_rate:.1f}%")
            st.metric("Señales Totales", total_signals)
            st.metric("Señales de Compra", buy_signals)
        
        # Model parameters if available
        if hasattr(bot, 'best_params') and bot.best_params:
            st.subheader("⚙️ Parámetros Optimizados")
            st.json(bot.best_params)
        
        # Fear & Greed Index
        if 'fear_greed_index' in df.columns:
            fear_greed_value = int(df['fear_greed_index'].iloc[-1])
            st.subheader("🧠 Fear & Greed Index")
            fear_greed_fig = create_fear_greed_gauge(fear_greed_value)
            st.plotly_chart(fear_greed_fig, use_container_width=True)

# Technical Analysis Page
elif page == "Análisis Técnico":
    st.subheader("📈 Análisis Técnico Avanzado")
    
    # Price Chart
    st.subheader("📊 Gráfico de Precios")
    price_fig = create_price_chart(df, capital_bot, capital_holding, simbolo)
    st.plotly_chart(price_fig, use_container_width=True)
    
    # RSI Chart
    st.subheader("📉 Indicador RSI")
    rsi_fig = create_rsi_chart(df)
    st.plotly_chart(rsi_fig, use_container_width=True)
    
    # ATR Chart
    st.subheader("📏 Indicador ATR")
    atr_fig = create_atr_chart(df)
    st.plotly_chart(atr_fig, use_container_width=True)
    
    # Fear & Greed Gauge
    st.subheader("🧠 Fear & Greed Index")
    if 'fear_greed_index' in df.columns:
        fear_greed_value = int(df['fear_greed_index'].iloc[-1])
        fear_greed_fig = create_fear_greed_gauge(fear_greed_value)
        st.plotly_chart(fear_greed_fig, use_container_width=True)
    
    # Technical Analysis Summary
    st.subheader("📋 Resumen de Análisis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**Tendencia:**")
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            current_price = df['close'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            
            if current_price > sma_20 > sma_50:
                st.success("🔥 Fuerte Alcista")
            elif current_price < sma_20 < sma_50:
                st.error("❄️ Fuerte Bajista")
            else:
                st.warning("⚖️ Lateral")
    
    with col2:
        st.markdown("**Momentum:**")
        rsi_value = df['rsi_14'].iloc[-1] if 'rsi_14' in df.columns else 50
        if rsi_value > 70:
            st.error("🔴 Sobrecompra")
        elif rsi_value < 30:
            st.success("🟢 Sobreventa")
        else:
            st.info("🟡 Neutral")
    
    with col3:
        st.markdown("**Volatilidad:**")
        if 'volatilidad' in df.columns:
            volatility = df['volatilidad'].iloc[-1]
            if volatility > df['volatilidad'].quantile(0.75):
                st.error("🌪️ Alta Volatilidad")
            elif volatility < df['volatilidad'].quantile(0.25):
                st.success("😌 Baja Volatilidad")
            else:
                st.info("⚖️ Volatilidad Normal")
    
    with col4:
        st.markdown("**Sentimiento Mercado:**")
        if 'fear_greed_index' in df.columns:
            fear_greed_value = int(df['fear_greed_index'].iloc[-1])
            fear_greed_emoji = get_fear_greed_emoji(fear_greed_value)
            st.markdown(f"{fear_greed_emoji}")

# History Page
elif page == "Historial de Operaciones":
    st.subheader("📜 Historial de Operaciones")
    
    # Get trading history
    trading_history = db.get_trading_history(simbolo, limit=50)
    
    if not trading_history.empty:
        # Display operations table
        st.dataframe(
            trading_history[['timestamp', 'operation_type', 'price', 'total_amount', 'status']],
            column_config={
                "timestamp": "Fecha",
                "operation_type": "Operación",
                "price": "Precio",
                "total_amount": "Monto Total",
                "status": "Estado"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Performance summary
        st.subheader("📊 Resumen de Rendimiento")
        performance_history = db.get_performance_history(simbolo, limit=20)
        
        if not performance_history.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_return = performance_history['total_return'].mean() * 100
                st.metric("Retorno Promedio", f"{avg_return:+.2f}%")
            
            with col2:
                total_sessions = len(performance_history)
                st.metric("Sesiones Totales", total_sessions)
            
            with col3:
                best_session = performance_history['total_return'].max() * 100
                st.metric("Mejor Sesión", f"{best_session:+.2f}%")
    
    else:
        st.info("No hay historial de operaciones disponible. Activa el guardado automático en la configuración.")

# Configuration Page
elif page == "Configuración":
    st.subheader("⚙️ Configuración del Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Configuración de Trading**")
        
        # Default symbol
        default_symbol = st.selectbox(
            "Símbolo por defecto",
            available_symbols,
            index=available_symbols.index(config.get_setting('default_symbol')) if config.get_setting('default_symbol') in available_symbols else 0
        )
        
        # Default days
        default_days = st.slider(
            "Días de análisis por defecto",
            min_value=7,
            max_value=90,
            value=int(config.get_setting('default_days')),
            step=7
        )
        
        # Risk level
        current_risk = config.get_setting('risk_level')
        risk_index = [level[0] for level in risk_levels].index(current_risk) if current_risk in [level[0] for level in risk_levels] else 1
        new_risk = st.selectbox(
            "Nivel de riesgo",
            options=[level[1] for level in risk_levels],
            index=risk_index
        )
        new_risk_value = [level[0] for level in risk_levels][[level[1] for level in risk_levels].index(new_risk)]
    
    with col2:
        st.markdown("**Configuración de Interfaz**")
        
        # Auto save
        new_auto_save = st.checkbox(
            "Guardar datos automáticamente",
            value=config.get_setting('auto_save') == 'true'
        )
        
        # Chart theme
        chart_themes = [("dark", "Oscuro"), ("light", "Claro"), ("plotly_dark", "Plotly Oscuro")]
        current_theme = config.get_setting('chart_theme')
        theme_index = [theme[0] for theme in chart_themes].index(current_theme) if current_theme in [theme[0] for theme in chart_themes] else 0
        new_theme = st.selectbox(
            "Tema de gráficos",
            options=[theme[1] for theme in chart_themes],
            index=theme_index
        )
        new_theme_value = [theme[0] for theme in chart_themes][[theme[1] for theme in chart_themes].index(new_theme)]
    
    # Save configuration button
    if st.button("💾 Guardar Configuración", type="primary"):
        config.set_setting('default_symbol', default_symbol)
        config.set_setting('default_days', str(default_days))
        config.set_setting('risk_level', new_risk_value)
        config.set_setting('auto_save', str(new_auto_save).lower())
        config.set_setting('chart_theme', new_theme_value)
        
        st.success("✅ Configuración guardada exitosamente!")
        st.rerun()
    
    st.divider()
    
    # Database management
    st.subheader("🗄️ Gestión de Base de Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Limpiar Datos Antiguos", type="secondary"):
            db.cleanup_old_data(days_to_keep=30)
            st.success("✅ Datos antiguos eliminados")
    
    with col2:
        if st.button("📊 Ver Estadísticas BD", type="secondary"):
            stats = db.get_portfolio_summary()
            st.json(stats)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.8em;'>
    Bot de Trading IA Professional Edition © 2024 | Desarrollado con Streamlit y Machine Learning
</div>
""", unsafe_allow_html=True)

# Last update info
if st.session_state.last_update:
    st.sidebar.markdown(f"**Última actualización:** {st.session_state.last_update.strftime('%H:%M:%S')}")
