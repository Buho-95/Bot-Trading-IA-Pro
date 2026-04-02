"""
Correlation Analysis Module
Provides visualization and analysis of multi-asset correlations
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from utils import obtener_datos_multiactivo
import yfinance as yf

def create_correlation_heatmap(corr_matrix: pd.DataFrame, title: str = "Matriz de Correlación") -> go.Figure:
    """Create correlation heatmap"""
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=np.around(corr_matrix.values, decimals=2),
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Activos",
        yaxis_title="Activos",
        width=700,
        height=600
    )
    
    return fig

def _get_close_column(df: pd.DataFrame) -> str:
    """Find the close price column name regardless of prefix"""
    if 'close' in df.columns:
        return 'close'
    close_cols = [col for col in df.columns if col.endswith('_close')]
    return close_cols[0] if close_cols else None

def create_price_comparison_chart(data_dict: dict, title: str = "Comparación de Precios") -> go.Figure:
    """Create price comparison chart"""
    fig = go.Figure()
    
    for symbol, df in data_dict.items():
        close_col = _get_close_column(df)
        if not df.empty and close_col:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df[close_col],
                mode='lines',
                name=symbol,
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Precio (USD)",
        hovermode='x unified',
        legend=dict(x=0, y=1),
        width=900,
        height=500
    )
    
    return fig


def create_return_scatter_plot(data_dict: dict, title: str = "Análisis de Retornos") -> go.Figure:
    """Create return scatter plot for correlation analysis"""
    returns_data = []
    
    for symbol, df in data_dict.items():
        close_col = _get_close_column(df)
        if not df.empty and close_col:
            returns = df[close_col].pct_change().dropna()
            returns_data.extend([{
                'Symbol': symbol,
                'Returns': returns.iloc[i] if i < len(returns) else 0,
                'Index': i
            } for i in range(min(len(returns), 100))])  # Limit to 100 points
    
    if returns_data:
        returns_df = pd.DataFrame(returns_data)
        
        # Create separate traces for each symbol
        fig = go.Figure()
        
        for symbol in returns_df['Symbol'].unique():
            symbol_data = returns_df[returns_df['Symbol'] == symbol]
            fig.add_trace(go.Scatter(
                x=symbol_data['Index'],
                y=symbol_data['Returns'],
                mode='markers',
                name=symbol,
                marker=dict(size=6)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Índice de Tiempo",
            yaxis_title="Retornos (%)",
            hovermode='closest',
            width=800,
            height=500
        )
        
        return fig
    
    return go.Figure()

def calculate_correlation_metrics(data_dict: dict) -> dict:
    """Calculate correlation metrics between assets"""
    # Extract close prices for correlation
    close_prices = {}
    
    for symbol, df in data_dict.items():
        close_col = _get_close_column(df)
        if not df.empty and close_col:
            close_prices[symbol] = df[close_col]
    
    if len(close_prices) < 2:
        return {}
    
    # Create DataFrame with all close prices
    prices_df = pd.DataFrame(close_prices)
    
    # Calculate correlation matrix
    corr_matrix = prices_df.corr()
    
    # Calculate additional metrics
    metrics = {
        'correlation_matrix': corr_matrix,
        'avg_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.shape)[1:]].mean(),
        'max_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.shape)[1:]].max(),
        'min_correlation': corr_matrix.values[np.triu_indices_from(corr_matrix.shape)[1:]].min(),
        'volatility_comparison': {},
        'return_comparison': {}
    }
    
    # Calculate volatility and returns for each asset
    for symbol in close_prices.keys():
        if symbol in data_dict and not data_dict[symbol].empty:
            df = data_dict[symbol]
            close_col = _get_close_column(df)
            if close_col:
                returns = df[close_col].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized volatility
                
                metrics['volatility_comparison'][symbol] = volatility
                metrics['return_comparison'][symbol] = {
                    'mean_return': returns.mean() * 252,  # Annualized return
                    'total_return': (df[close_col].iloc[-1] / df[close_col].iloc[0] - 1) * 100
                }
    
    return metrics

def show_correlation_analysis():
    """Display correlation analysis in Streamlit"""
    st.header("📊 Análisis de Correlación Multi-Activo")
    
    # Asset selection
    available_assets = ["BTC-USD", "ETH-USD", "^GSPC"]
    selected_assets = st.multiselect(
        "📈 Selecciona Activos para Análisis",
        available_assets,
        default=["BTC-USD", "ETH-USD", "^GSPC"]
    )
    
    if len(selected_assets) < 2:
        st.warning("⚠️ Selecciona al menos 2 activos para análisis de correlación")
        return
    
    # Time period
    days = st.slider("📅 Período de Análisis (días)", 7, 90, 30)
    
    # Download data
    with st.spinner(f"🔄 Descargando datos para {len(selected_assets)} activos..."):
        data_dict = obtener_datos_multiactivo(selected_assets, days)
    
    if not data_dict:
        st.error("❌ No se pudieron descargar los datos")
        return
    
    # Calculate metrics
    metrics = calculate_correlation_metrics(data_dict)
    
    if not metrics:
        st.error("❌ Error calculando métricas de correlación")
        return
    
    # Display correlation heatmap
    st.subheader("🔥 Matriz de Correlación")
    fig_heatmap = create_correlation_heatmap(
        metrics['correlation_matrix'],
        f"Correlación de Activos - {days} días"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Display correlation metrics
    st.subheader("📈 Métricas de Correlación")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Correlación Promedio",
            f"{metrics['avg_correlation']:.3f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Correlación Máxima",
            f"{metrics['max_correlation']:.3f}",
            delta=None
        )
    
    with col3:
        st.metric(
            "Correlación Mínima",
            f"{metrics['min_correlation']:.3f}",
            delta=None
        )
    
    # Display price comparison
    st.subheader("📊 Comparación de Precios")
    fig_prices = create_price_comparison_chart(data_dict, f"Comparación de Precios - {days} días")
    st.plotly_chart(fig_prices, use_container_width=True)
    
    # Display return analysis
    st.subheader("📈 Análisis de Retornos")
    fig_returns = create_return_scatter_plot(data_dict, f"Análisis de Retornos - {days} días")
    st.plotly_chart(fig_returns, use_container_width=True)
    
    # Display detailed metrics
    st.subheader("📋 Métricas Detalladas por Activo")
    
    for symbol in selected_assets:
        if symbol in metrics['return_comparison']:
            with st.expander(f"📊 {symbol}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Retorno Total (%)",
                        f"{metrics['return_comparison'][symbol]['total_return']:.2f}",
                        delta=None
                    )
                    st.metric(
                        "Retorno Anualizado (%)",
                        f"{metrics['return_comparison'][symbol]['mean_return']:.2f}",
                        delta=None
                    )
                    st.metric(
                        "Volatilidad Anualizada",
                        f"{metrics['volatility_comparison'][symbol]:.3f}",
                        delta=None
                    )
                
                with col2:
                    # Create mini correlation info
                    symbol_correlations = []
                    for other_symbol in selected_assets:
                        if other_symbol != symbol and other_symbol in metrics['correlation_matrix'].index:
                            corr_val = metrics['correlation_matrix'].loc[symbol, other_symbol]
                            symbol_correlations.append(f"{other_symbol}: {corr_val:.3f}")
                    
                    if symbol_correlations:
                        st.write("**Correlaciones con otros activos:**")
                        for corr in symbol_correlations:
                            st.write(f"• {corr}")

if __name__ == "__main__":
    show_correlation_analysis()
