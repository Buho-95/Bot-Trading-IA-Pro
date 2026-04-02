import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import plotly.graph_objects as go
import plotly.express as px
import requests
from database import TradingDatabase
from notifications import TelegramNotifier

@st.cache_data(ttl=300)  # Cache for 5 minutes
def obtener_datos_multiactivo(symbols: List[str], dias: int) -> Dict[str, pd.DataFrame]:
    """
    Download data for multiple assets and align them for correlation analysis
    
    Args:
        symbols: List of symbols to download
        dias: Number of days of historical data
    
    Returns:
        Dictionary with symbol as key and DataFrame as value
    """
    data_dict = {}
    
    for symbol in symbols:
        try:
            # Download data for each symbol
            df = yf.download(tickers=symbol, period=f"{dias}d", interval="1h", progress=False)
            df = df.reset_index()

            # Flatten columns if Yahoo sends them in MultiIndex format
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Convert all columns to lowercase to avoid errors
            df.columns = [col.lower() for col in df.columns]

            # Ensure the date column name
            if 'datetime' in df.columns:
                df.rename(columns={'datetime': 'date'}, inplace=True)

            # Add symbol prefix to columns to avoid conflicts
            if not df.empty:
                prefix = symbol.replace('-', '_').replace('^', '').lower()
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df.rename(columns={col: f'{prefix}_{col}'}, inplace=True)
                
                data_dict[symbol] = df
                st.success(f"✅ Datos descargados para {symbol}: {len(df)} registros")
            else:
                st.warning(f"⚠️ No hay datos disponibles para {symbol}")
                
        except Exception as e:
            st.error(f"❌ Error descargando datos para {symbol}: {str(e)}")
            continue
    
    return data_dict

@st.cache_resource(ttl=3600, show_spinner=False)
def _cached_train_model(X_train: pd.DataFrame, y_train: pd.Series, param_grid: dict) -> Tuple[object, dict]:
    """Train the model with caching, using RandomizedSearchCV and a 30s timeout fallback"""
    import concurrent.futures
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import RandomizedSearchCV
    
    rf = RandomForestClassifier(random_state=42, n_jobs=None)
    
    search = RandomizedSearchCV(
        estimator=rf,
        param_distributions=param_grid,
        n_iter=5,
        cv=3,
        n_jobs=None,
        scoring='accuracy',
        random_state=42,
        verbose=0
    )
    
    def _do_train():
        search.fit(X_train, y_train)
        return search.best_estimator_, search.best_params_
        
    try:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_do_train)
        best_model, best_params = future.result(timeout=30)
        executor.shutdown(wait=False)
        return best_model, best_params
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False)
        st.warning("⏱️ El entrenamiento optimizado superó los 30 segundos. Usando parámetros por defecto para no bloquear la app.")
        default_rf = RandomForestClassifier(random_state=42, n_jobs=None)
        default_rf.fit(X_train, y_train)
        return default_rf, "Parámetros Por Defecto (Timeout Previsto)"
    except Exception as e:
        if 'executor' in locals():
            executor.shutdown(wait=False)
        st.error(f"❌ Error durante el entrenamiento: {e}")
        default_rf = RandomForestClassifier(random_state=42, n_jobs=None)
        default_rf.fit(X_train, y_train)
        return default_rf, f"Parámetros Por Defecto (Recuperado de Error)"

class TradingBot:
    def __init__(self, db: TradingDatabase):
        self.db = db
        self.model = None
        self.best_params = None
        # Enhanced features for multi-asset analysis
        self.features = [
            'open', 'high', 'low', 'close', 'volume', 
            'rsi_14', 'sma_20', 'sma_50', 'volatilidad', 'retorno', 
            'atr', 'fear_greed_index',
            # New technical indicators
            'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_position',
            'obv', 'obv_sma',
            # Multi-asset correlation features
            'eth_close', 'sp500_close', 'eth_return', 'sp500_return'
        ]
        self.telegram = TelegramNotifier()
    
    def calculate_macd(self, df: pd.DataFrame, price_col: str = 'close') -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            df: DataFrame with price data
            price_col: Name of the price column
        
        Returns:
            DataFrame with MACD values added
        """
        if df.empty or price_col not in df.columns:
            return df
        
        # Calculate MACD using standard parameters
        exp1 = df[price_col].ewm(span=12, adjust=False).mean()
        exp2 = df[price_col].ewm(span=26, adjust=False).mean()
        
        df[f'{price_col}_macd'] = exp1 - exp2
        df[f'{price_col}_macd_signal'] = df[f'{price_col}_macd'].ewm(span=9, adjust=False).mean()
        df[f'{price_col}_macd_histogram'] = df[f'{price_col}_macd'] - df[f'{price_col}_macd_signal']
        
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, price_col: str = 'close', period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with price data
            price_col: Name of the price column
            period: Period for moving average
            std_dev: Standard deviation multiplier
        
        Returns:
            DataFrame with Bollinger Bands added
        """
        if df.empty or price_col not in df.columns:
            return df
        
        # Calculate middle band (SMA)
        df[f'{price_col}_bb_middle'] = df[price_col].rolling(window=period).mean()
        
        # Calculate standard deviation
        std = df[price_col].rolling(window=period).std()
        
        # Calculate upper and lower bands
        df[f'{price_col}_bb_upper'] = df[f'{price_col}_bb_middle'] + (std * std_dev)
        df[f'{price_col}_bb_lower'] = df[f'{price_col}_bb_middle'] - (std * std_dev)
        
        # Calculate bandwidth and position
        df[f'{price_col}_bb_width'] = df[f'{price_col}_bb_upper'] - df[f'{price_col}_bb_lower']
        df[f'{price_col}_bb_position'] = (df[price_col] - df[f'{price_col}_bb_lower']) / df[f'{price_col}_bb_width']
        
        return df
    
    def calculate_obv(self, df: pd.DataFrame, price_col: str = 'close', volume_col: str = 'volume') -> pd.DataFrame:
        """
        Calculate On-Balance Volume (OBV)
        
        Args:
            df: DataFrame with price and volume data
            price_col: Name of the price column
            volume_col: Name of the volume column
        
        Returns:
            DataFrame with OBV added
        """
        if df.empty or price_col not in df.columns or volume_col not in df.columns:
            return df
        
        # Calculate OBV
        obv = [0]
        for i in range(1, len(df)):
            if df[price_col].iloc[i] > df[price_col].iloc[i-1]:
                obv.append(obv[-1] + df[volume_col].iloc[i])
            elif df[price_col].iloc[i] < df[price_col].iloc[i-1]:
                obv.append(obv[-1] - df[volume_col].iloc[i])
            else:
                obv.append(obv[-1])
        
        df[f'{price_col}_obv'] = obv
        df[f'{price_col}_obv_sma'] = pd.Series(obv).rolling(window=10).mean()
        
        return df
    
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> Dict[str, float]:
        """
        Calculate Kelly Criterion for optimal position sizing
        Formula: f* = (p * b - q) / b
        Where: p = win probability, b = win/loss ratio, q = loss probability
        
        Returns dictionary with Kelly calculations and position sizing recommendations
        """
        if avg_loss == 0 or win_rate == 0:
            return {
                'kelly_fraction': 0.01,  # Minimum 1% if no data
                'conservative_fraction': 0.01,
                'aggressive_fraction': 0.01,
                'recommended_position_size': 100.0,
                'risk_level': 'Minimum'
            }
        
        win_probability = win_rate / 100
        loss_probability = 1 - win_probability
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 1
        
        # Calculate Kelly fraction
        kelly_fraction = (win_probability * win_loss_ratio - loss_probability) / win_loss_ratio
        
        # Apply different safety multipliers
        conservative_fraction = kelly_fraction * 0.25  # 25% of Kelly
        moderate_fraction = kelly_fraction * 0.50      # 50% of Kelly  
        aggressive_fraction = kelly_fraction * 0.75   # 75% of Kelly
        
        # Ensure fractions are reasonable
        kelly_fraction = max(0.01, min(kelly_fraction, 0.50))    # Max 50%
        conservative_fraction = max(0.01, min(conservative_fraction, 0.25))  # Max 25%
        moderate_fraction = max(0.01, min(moderate_fraction, 0.35))          # Max 35%
        aggressive_fraction = max(0.01, min(aggressive_fraction, 0.45))       # Max 45%
        
        # Determine risk level based on win rate
        if win_rate >= 70:
            risk_level = 'Low Risk - High Confidence'
        elif win_rate >= 60:
            risk_level = 'Moderate Risk - Good Confidence'
        elif win_rate >= 50:
            risk_level = 'High Risk - Low Confidence'
        else:
            risk_level = 'Very High Risk - Poor Performance'
        
        # Calculate recommended position size for $10,000 portfolio
        portfolio_size = 10000.0
        recommended_position_size = portfolio_size * conservative_fraction
        
        return {
            'kelly_fraction': kelly_fraction,
            'conservative_fraction': conservative_fraction,
            'moderate_fraction': moderate_fraction,
            'aggressive_fraction': aggressive_fraction,
            'recommended_position_size': recommended_position_size,
            'portfolio_size': portfolio_size,
            'risk_level': risk_level,
            'win_probability': win_probability,
            'win_loss_ratio': win_loss_ratio,
            'expected_value': (win_probability * avg_win) - (loss_probability * avg_loss)
        }
    
    def get_fear_greed_index(self) -> int:
        """Get Fear & Greed Index from Alternative.me API"""
        try:
            response = requests.get('https://api.alternative.me/fng/', timeout=10)
            response.raise_for_status()
            data = response.json()
            return int(data['data'][0]['value'])
        except Exception as e:
            st.warning(f"No se pudo obtener Fear & Greed Index: {str(e)}")
            return 50  # Neutral value as fallback
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_market_data(_self, symbol: str, days: int) -> pd.DataFrame:
        """Download and process market data from Yahoo Finance"""
        try:
            df = yf.download(tickers=symbol, period=f"{days}d", interval="1h", progress=False)
            df = df.reset_index()

            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Standardize column names
            df.columns = [col.lower() for col in df.columns]

            # Ensure date column
            if 'datetime' in df.columns:
                df.rename(columns={'datetime': 'date'}, inplace=True)

            return df
        except Exception as e:
            st.error(f"Error downloading data: {str(e)}")
            return pd.DataFrame()
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR) for dynamic stop loss"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def calculate_trailing_stop_loss(self, df: pd.DataFrame, predictions: np.ndarray, atr_multiplier: float = 2.0) -> Dict:
        """Calculate dynamic trailing stop loss using ATR"""
        if len(df) < 20 or len(predictions) == 0:
            return {'stop_loss': None, 'take_profit': None, 'atr': None}
        
        atr = self.calculate_atr(df)
        current_price = df['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        # Dynamic stop loss based on ATR and prediction
        if predictions[-1] == 1:  # BUY signal
            stop_loss = current_price - (current_atr * atr_multiplier)
            take_profit = current_price + (current_atr * atr_multiplier * 2)
        else:  # SELL signal
            stop_loss = current_price + (current_atr * atr_multiplier)
            take_profit = current_price - (current_atr * atr_multiplier * 2)
        
        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'atr': current_atr,
            'atr_percentage': (current_atr / current_price) * 100
        }
    
    
    def calculate_indicators(self, df: pd.DataFrame, symbol: str = 'BTC-USD') -> pd.DataFrame:
        """
        Calculate technical indicators including ATR, MACD, Bollinger Bands, OBV and Fear & Greed
        Enhanced for multi-asset correlation analysis
        """
        if df.empty:
            return df
        
        # Standard indicators
        df = self.calculate_standard_indicators(df)
        
        # New technical indicators
        df = self.calculate_macd(df, 'close')
        df = self.calculate_bollinger_bands(df, 'close')
        df = self.calculate_obv(df, 'close', 'volume')
        
        # Add correlation features if multi-asset
        if symbol == 'BTC-USD':
            # Try to get ETH and S&P 500 data for correlation
            try:
                # Download ETH data
                eth_df = self.get_market_data('ETH-USD', 7)
                if not eth_df.empty:
                    eth_df = eth_df.copy()
                    eth_df['eth_return'] = eth_df['close'].pct_change()
                    
                    # Align by date
                    eth_df = eth_df[['date', 'close', 'eth_return']].rename(columns={'close': 'eth_close'})
                    df = pd.merge(df, eth_df, on='date', how='left')
                    df['eth_close'] = df['eth_close'].ffill()
                    df['eth_return'] = df['eth_return'].ffill()
                
                # Download S&P 500 data
                sp500_df = self.get_market_data('^GSPC', 7)
                if not sp500_df.empty:
                    sp500_df = sp500_df.copy()
                    sp500_df['sp500_return'] = sp500_df['close'].pct_change()
                    
                    # Align by date
                    sp500_df = sp500_df[['date', 'close', 'sp500_return']].rename(columns={'close': 'sp500_close'})
                    df = pd.merge(df, sp500_df, on='date', how='left')
                    df['sp500_close'] = df['sp500_close'].ffill()
                    df['sp500_return'] = df['sp500_return'].ffill()
                    
            except Exception as e:
                st.warning(f"⚠️ Error obteniendo datos de correlación: {str(e)}")
        
        return df
    
    def calculate_standard_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate standard technical indicators"""
        # RSI calculation
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        ema_gain = gain.ewm(com=13, adjust=False).mean()
        ema_loss = loss.ewm(com=13, adjust=False).mean()
        df['rsi_14'] = 100 - (100 / (1 + (ema_gain / ema_loss)))
        
        # Moving averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Volatility and returns
        df['volatilidad'] = df['close'].rolling(window=20).std()
        df['retorno'] = df['close'].pct_change()
        
        # ATR calculation
        df['atr'] = self.calculate_atr(df)
        
        # Fear & Greed Index (same value for all rows in current session)
        fear_greed = self.get_fear_greed_index()
        df['fear_greed_index'] = fear_greed
        
        return df
    
    def simulate_trading(self, df_ml: pd.DataFrame, X_test: pd.DataFrame, predictions: np.ndarray) -> Tuple[pd.Series, pd.Series, Dict]:
        """Simulate trading strategy with trailing stop loss"""
        # Calculate returns
        retornos_reales = df_ml.loc[X_test.index, 'retorno'].shift(-1).fillna(0)
        
        # Apply trailing stop loss logic
        stop_loss_data = self.calculate_trailing_stop_loss(df_ml, predictions)
        adjusted_returns = self.apply_trailing_stop_logic(retornos_reales, predictions, stop_loss_data)
        
        retornos_bot = predictions * adjusted_returns
        
        # Calculate capital evolution
        initial_capital = 1000
        capital_bot = initial_capital * (1 + retornos_bot).cumprod()
        capital_holding = initial_capital * (1 + retornos_reales).cumprod()
        
        return capital_bot, capital_holding, stop_loss_data



    def train_model(self, df: pd.DataFrame, symbol: str = 'BTC-USD') -> Tuple[object, np.ndarray, pd.DataFrame]:
        """Train Random Forest model with RandomizedSearchCV optimization (cached) for enhanced features"""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, classification_report
        
        # Prepare target variable
        df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
        df_ml = df.dropna().copy()
        
        # Filter features based on availability
        available_features = [feat for feat in self.features if feat in df_ml.columns]
        
        if not available_features:
            st.error("❌ No hay suficientes características para entrenar el modelo")
            return None, None, None, None, None, None, None
        
        # Split data
        X = df_ml[available_features]
        y = df_ml['target']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
        
        # Enhanced parameter grid for multi-asset analysis
        param_grid = {
            'n_estimators': [100, 200],  # Reduced max trees for speed
            'max_depth': [10, 15, None],  
            'min_samples_split': [2, 5],
            'min_samples_leaf': [1, 2],
            'max_features': ['sqrt', 'log2'], 
            'bootstrap': [True, False],  
            'class_weight': ['balanced', None]  
        }
        
        with st.spinner('🔍 Optimizando parámetros del modelo (con caché)...'):
            # Call our cached, optimized, timeout-safe training routine
            self.model, self.best_params = _cached_train_model(X_train, y_train, param_grid)
            
            # Make predictions
            predictions = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, predictions)
            
            # Store results in session state
            st.session_state.model_accuracy = accuracy
            st.session_state.best_params = self.best_params
            st.session_state.features_used = available_features
            
            st.success(f"✅ Modelo optimizado con {accuracy:.2%} de precisión usando {len(available_features)} características")
            
            # Feature importance analysis
            if hasattr(self.model, 'feature_importances_'):
                feature_importance = pd.DataFrame({
                    'feature': available_features,
                    'importance': self.model.feature_importances_
                }).sort_values('importance', ascending=False)
                
                st.subheader("🎯 Importancia de Características")
                st.dataframe(feature_importance, use_container_width=True)
            
            # Send Telegram notification for model retraining
            if self.telegram.enabled:
                retraining_data = {
                    'symbol': symbol,
                    'accuracy': accuracy,
                    'best_params': self.best_params,
                    'duration': 'Unknown',
                    'data_points': len(X_train),
                    'cv_score': accuracy,
                    'previous_accuracy': st.session_state.get('previous_accuracy', 0),
                    'improvement': accuracy - st.session_state.get('previous_accuracy', 0),
                    'features_count': len(available_features)
                }
                self.telegram.send_model_retraining_notification(retraining_data)
        
        return self.model, predictions, df_ml, X_test, X_train, y_train, y_test
    

    def apply_trailing_stop_logic(self, returns: pd.Series, predictions: np.ndarray, stop_data: Dict) -> pd.Series:
        """Apply trailing stop loss logic to returns"""
        adjusted_returns = returns.copy()
        
        if stop_data['stop_loss'] is not None:
            stop_loss_pct = stop_data['atr_percentage'] * 2  # 2x ATR as stop loss
            
            for i in range(1, len(adjusted_returns)):
                if predictions[i] == 1:  # BUY signal
                    # Apply stop loss for negative returns beyond threshold
                    if adjusted_returns.iloc[i] < -stop_loss_pct / 100:
                        adjusted_returns.iloc[i] = -stop_loss_pct / 100  # Cap the loss
                else:  # SELL signal
                    # Apply stop loss for positive returns beyond threshold
                    if adjusted_returns.iloc[i] > stop_loss_pct / 100:
                        adjusted_returns.iloc[i] = stop_loss_pct / 100  # Cap the gain
        
        return adjusted_returns
    
    def generate_trading_signals(self, df: pd.DataFrame, predictions: np.ndarray) -> List[Dict]:
        """Generate trading signals based on predictions"""
        signals = []
        current_price = df['close'].iloc[-1]
        
        for i, pred in enumerate(predictions[-5:]):  # Last 5 predictions
            signal_type = "BUY" if pred == 1 else "SELL"
            signal_data = {
                'timestamp': datetime.now() - timedelta(hours=len(predictions)-i),
                'symbol': st.session_state.get('current_symbol', 'BTC-USD'),
                'operation_type': signal_type,
                'price': current_price,
                'quantity': 1.0,  # Default quantity
                'total_amount': current_price,
                'rsi_value': df['rsi_14'].iloc[-1] if not df.empty else None,
                'sma_20': df['sma_20'].iloc[-1] if not df.empty else None,
                'sma_50': df['sma_50'].iloc[-1] if not df.empty else None,
                'volatility': df['volatilidad'].iloc[-1] if not df.empty else None,
                'atr_value': df['atr'].iloc[-1] if 'atr' in df.columns and not df.empty else None,
                'fear_greed_index': df['fear_greed_index'].iloc[-1] if 'fear_greed_index' in df.columns and not df.empty else None,
                'prediction_confidence': 0.85,  # Default confidence
                'strategy_used': 'RandomForest + RandomizedSearchCV (Optimizado)'
            }
            
            # Send Telegram notification for new signal
            if self.telegram.enabled and i == len(predictions[-5:]) - 1:  # Only for latest signal
                # Convert signal_data to expected format for send_trading_signal
                trading_decision = {
                    'signal': signal_type,
                    'symbol': st.session_state.get('current_symbol', 'BTC-USD'),
                    'price': current_price,
                    'confidence': 0.85,
                    'kelly_fraction': 0.25,  # Default conservative Kelly
                    'suggested_investment': current_price * 0.25,
                    'risk_level': 'Medium',
                    'stop_loss': current_price * 0.98,  # 2% stop loss
                    'take_profit': current_price * 1.04,  # 4% take profit
                    'atr': df['atr'].iloc[-1] if 'atr' in df.columns and not df.empty else 0,
                    'fear_greed_index': df['fear_greed_index'].iloc[-1] if 'fear_greed_index' in df.columns and not df.empty else 50,
                    'model_accuracy': st.session_state.get('model_accuracy', 0.85),
                    'timestamp': datetime.now()
                }
                self.telegram.send_trading_signal(trading_decision)
            
            signals.append(signal_data)
        
        return signals
    
    def save_session_data(self, symbol: str, df: pd.DataFrame, capital_bot: pd.Series, 
                         capital_holding: pd.Series, predictions: np.ndarray):
        """Save session data to database"""
        try:
            # Save market data
            market_data_list = []
            for _, row in df.tail(10).iterrows():  # Save last 10 records
                market_data_list.append({
                    'symbol': symbol,
                    'open_price': row['open'],
                    'high_price': row['high'],
                    'low_price': row['low'],
                    'close_price': row['close'],
                    'volume': row['volume'],
                    'rsi_14': row.get('rsi_14'),
                    'sma_20': row.get('sma_20'),
                    'sma_50': row.get('sma_50'),
                    'volatility': row.get('volatilidad'),
                    'atr_value': row.get('atr'),
                    'fear_greed_index': row.get('fear_greed_index'),
                    'return_rate': row.get('retorno')
                })
            
            self.db.save_market_data(market_data_list)
            
            # Save performance data
            if not capital_bot.empty:
                performance_data = {
                    'symbol': symbol,
                    'initial_capital': 1000,
                    'current_capital': float(capital_bot.iloc[-1]),
                    'total_return': float((capital_bot.iloc[-1] - 1000) / 1000),
                    'win_rate': float(np.mean(predictions)) if len(predictions) > 0 else 0,
                    'total_trades': len(predictions),
                    'profitable_trades': int(np.sum(predictions)),
                    'strategy_parameters': '{"model": "RandomForest", "features": "technical_indicators"}'
                }
                self.db.save_bot_performance(performance_data)
            
            # Save trading signals
            signals = self.generate_trading_signals(df, predictions)
            for signal in signals:
                self.db.save_trading_operation(signal)
                
        except Exception as e:
            st.error(f"Error saving session data: {str(e)}")

def create_price_chart(df: pd.DataFrame, capital_bot: pd.Series, capital_holding: pd.Series, 
                      symbol: str) -> go.Figure:
    """Create interactive price chart with plotly"""
    fig = go.Figure()
    
    # Add price data
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['close'],
        mode='lines',
        name=f'{symbol} Price',
        line=dict(color='lightblue', width=2)
    ))
    
    # Add moving averages
    if 'sma_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['sma_20'],
            mode='lines',
            name='SMA 20',
            line=dict(color='orange', width=1, dash='dash')
        ))
    
    if 'sma_50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['sma_50'],
            mode='lines',
            name='SMA 50',
            line=dict(color='purple', width=1, dash='dash')
        ))
    
    fig.update_layout(
        title=f'{symbol} Price Chart',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig

def create_performance_chart(capital_bot: pd.Series, capital_holding: pd.Series, 
                           dates: pd.Series) -> go.Figure:
    """Create performance comparison chart"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=capital_holding,
        mode='lines',
        name='Market (Hold)',
        line=dict(color='gray', width=2, dash='dash')
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=capital_bot,
        mode='lines',
        name='Bot IA',
        line=dict(color='#00ff41', width=3)
    ))
    
    fig.update_layout(
        title='Strategy Performance Comparison',
        xaxis_title='Date',
        yaxis_title='Capital (USD)',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig

def create_rsi_chart(df: pd.DataFrame) -> go.Figure:
    """Create RSI indicator chart"""
    if 'rsi_14' not in df.columns:
        return go.Figure()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['rsi_14'],
        mode='lines',
        name='RSI (14)',
        line=dict(color='yellow', width=2)
    ))
    
    # Add overbought/oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    
    fig.update_layout(
        title='RSI Indicator',
        xaxis_title='Date',
        yaxis_title='RSI Value',
        template='plotly_dark',
        height=300,
        showlegend=True,
        yaxis=dict(range=[0, 100])
    )
    
    return fig

def create_atr_chart(df: pd.DataFrame) -> go.Figure:
    """Create ATR indicator chart"""
    if 'atr' not in df.columns:
        return go.Figure()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['atr'],
        mode='lines',
        name='ATR (14)',
        line=dict(color='cyan', width=2)
    ))
    
    fig.update_layout(
        title='Average True Range (ATR)',
        xaxis_title='Date',
        yaxis_title='ATR Value',
        template='plotly_dark',
        height=300,
        showlegend=True
    )
    
    return fig

def create_fear_greed_gauge(fear_greed_value: int) -> go.Figure:
    """Create Fear & Greed Index gauge chart"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = fear_greed_value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Fear & Greed Index"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightcoral"},
                {'range': [25, 45], 'color': "lightyellow"},
                {'range': [45, 55], 'color': "lightgreen"},
                {'range': [55, 75], 'color': "lightyellow"},
                {'range': [75, 100], 'color': "lightcoral"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        template='plotly_dark',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def get_fear_greed_emoji(value: int) -> str:
    """Get emoji for Fear & Greed Index"""
    if value <= 25:
        return "😱 Extreme Fear"
    elif value <= 45:
        return "😟 Fear"
    elif value <= 55:
        return "😐 Neutral"
    elif value <= 75:
        return "😊 Greed"
    else:
        return "🤪 Extreme Greed"

def get_fear_greed_color(value: int) -> str:
    """Get color for Fear & Greed Index"""
    if value <= 25:
        return "red"
    elif value <= 45:
        return "orange"
    elif value <= 55:
        return "green"
    elif value <= 75:
        return "orange"
    else:
        return "red"

def format_currency(value: float) -> str:
    """Format currency values"""
    return f"${value:,.2f}"

def format_percentage(value: float) -> str:
    """Format percentage values"""
    return f"{value:.2f}%"

def get_signal_emoji(signal: int) -> str:
    """Get emoji for trading signal"""
    return "🟢 COMPRAR" if signal == 1 else "🔴 VENDER / ESPERAR"

def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol"""
    valid_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "AAPL", "GOOGL", "MSFT"]
    return symbol in valid_symbols

def handle_errors(func):
    """Decorator for error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            return None
    return wrapper
