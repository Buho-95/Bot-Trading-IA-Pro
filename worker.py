#!/usr/bin/env python3
"""
Trading Bot Worker - Autonomous Permanent Mode
Runs in background every 5 minutes to execute trading decisions
"""

import schedule
import time
import logging
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from database import TradingDatabase
from utils import TradingBot
from config import ConfigManager
from notifications import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingWorker:
    def __init__(self):
        """Initialize the autonomous trading worker"""
        self.db = TradingDatabase()
        self.config = ConfigManager(self.db)
        self.bot = TradingBot(self.db)
        self.telegram = TelegramNotifier()
        self.last_training_time = None
        self.is_running = True
        
        # Default symbols to monitor
        self.symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
        
        logger.info("🤖 Trading Worker initialized in Autonomous Permanent Mode")
    
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly Criterion for optimal position sizing
        Formula: f* = (p * b - q) / b
        Where: p = win probability, b = win/loss ratio, q = loss probability
        """
        if avg_loss == 0 or win_rate == 0:
            return 0.01  # Minimum 1% if no data
        
        win_probability = win_rate / 100
        loss_probability = 1 - win_probability
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 1
        
        kelly_fraction = (win_probability * win_loss_ratio - loss_probability) / win_loss_ratio
        
        # Conservative approach: use 25% of Kelly to reduce volatility
        kelly_fraction *= 0.25
        
        # Ensure fraction is between 1% and 25%
        kelly_fraction = max(0.01, min(kelly_fraction, 0.25))
        
        return kelly_fraction
    
    def execute_trading_cycle(self):
        """Execute one complete trading cycle for all symbols"""
        logger.info("🔄 Starting trading cycle...")
        
        try:
            for symbol in self.symbols:
                self.process_symbol(symbol)
            
            # Send summary notification
            self.send_daily_summary()
            
        except Exception as e:
            logger.error(f"❌ Error in trading cycle: {str(e)}")
            self.telegram.send_error_notification(f"Trading cycle error: {str(e)}")
    
    def process_symbol(self, symbol: str):
        """Process trading for a single symbol"""
        try:
            logger.info(f"📊 Processing {symbol}...")
            
            # Get market data
            days = int(self.config.get_setting('default_days', '7'))
            df = self.bot.get_market_data(symbol, days)
            
            if df.empty:
                logger.warning(f"⚠️ No data available for {symbol}")
                return
            
            # Calculate indicators
            df = self.bot.calculate_indicators(df)
            
            # Train model (if needed)
            model, predictions, df_ml, X_test, X_train, y_train, y_test = self.bot.train_model(df, symbol)

            import gc
            gc.collect()

            if model is None:
                logger.warning(f"⚠️ Model not trained for {symbol}. Sending basic fallback notification.")
                # Basic notification even if training fails
                current_price = float(df['close'].iloc[-1]) if not df.empty else 0.0
                decision = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'signal': 'ESPERAR (Modelo No Disponible)',
                    'price': current_price,
                    'confidence': 0.0,
                    'kelly_fraction': 0.01,
                    'suggested_investment': 100,
                    'stop_loss': current_price * 0.98,
                    'take_profit': current_price * 1.02,
                    'atr': float(df['atr'].iloc[-1]) if 'atr' in df.columns and not df.empty else 0.0,
                    'fear_greed_index': int(df['fear_greed_index'].iloc[-1]) if 'fear_greed_index' in df.columns and not df.empty else 50,
                    'model_accuracy': 0.0,
                    'strategy': 'Basic Indicators (Fallback)'
                }
                self.save_trading_decision(decision)
                self.telegram.send_trading_signal(decision)
                return
            
            # Simulate trading
            capital_bot, capital_holding, stop_loss_data = self.bot.simulate_trading(df_ml, X_test, predictions)
            
            # Get current signal
            current_signal = predictions[-1] if len(predictions) > 0 else 0
            current_price = float(df['close'].iloc[-1])
            
            # Calculate performance metrics
            if len(predictions) > 0:
                accuracy = (predictions == y_test).mean() * 100
                win_rate = np.mean(predictions) * 100
                
                # Calculate returns for Kelly criterion
                returns = df_ml.loc[X_test.index, 'retorno'].shift(-1).fillna(0)
                winning_returns = returns[predictions == 1]
                losing_returns = returns[predictions == 0]
                
                avg_win = winning_returns.mean() if not winning_returns.empty else 0.01
                avg_loss = abs(losing_returns.mean()) if not losing_returns.empty else 0.01
                
                # Calculate Kelly fraction
                kelly_fraction = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
                suggested_investment = 10000 * kelly_fraction  # Assuming $10,000 portfolio
                
                # Create trading decision
                decision = {
                    'timestamp': datetime.now(),
                    'symbol': symbol,
                    'signal': 'BUY' if current_signal == 1 else 'SELL',
                    'price': current_price,
                    'confidence': float(accuracy / 100),
                    'kelly_fraction': kelly_fraction,
                    'suggested_investment': suggested_investment,
                    'stop_loss': stop_loss_data.get('stop_loss'),
                    'take_profit': stop_loss_data.get('take_profit'),
                    'atr': stop_loss_data.get('atr'),
                    'fear_greed_index': int(df['fear_greed_index'].iloc[-1]) if 'fear_greed_index' in df.columns else 50,
                    'model_accuracy': accuracy,
                    'strategy': 'RandomForest + RandomizedSearchCV (Optimizado)'
                }
                
                # Save decision to database
                self.save_trading_decision(decision)
                
                # Send notification if significant signal
                if current_signal == 1 or accuracy > 70:
                    self.telegram.send_trading_signal(decision)
                
                logger.info(f"✅ {symbol}: {decision['signal']} at ${current_price:.2f} | "
                          f"Accuracy: {accuracy:.1f}% | Kelly: {kelly_fraction:.2%} | "
                          f"Suggested: ${suggested_investment:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {symbol}: {str(e)}")
    
    def save_trading_decision(self, decision: dict):
        """Save trading decision to database"""
        try:
            operation_data = {
                'symbol': decision['symbol'],
                'operation_type': decision['signal'],
                'price': decision['price'],
                'quantity': decision.get('kelly_fraction', 0.01),  # Use Kelly fraction as quantity
                'total_amount': decision['suggested_investment'],
                'rsi_value': None,  # Will be populated if available
                'sma_20': None,
                'sma_50': None,
                'volatility': None,
                'atr_value': decision.get('atr'),
                'fear_greed_index': decision.get('fear_greed_index'),
                'prediction_confidence': decision['confidence'],
                'strategy_used': decision['strategy'],
                'status': 'EXECUTED'
            }
            
            self.db.save_trading_operation(operation_data)
            logger.info(f"💾 Decision saved for {decision['symbol']}")
            
        except Exception as e:
            logger.error(f"❌ Error saving decision: {str(e)}")
    
    def check_and_retrain_model(self):
        """Check if model needs retraining (every 24 hours)"""
        now = datetime.now()
        
        if self.last_training_time is None or (now - self.last_training_time) >= timedelta(hours=24):
            logger.info("🔄 Starting scheduled model retraining...")
            
            try:
                # Retrain for each symbol with latest data
                for symbol in self.symbols:
                    self.retrain_symbol_model(symbol)
                
                self.last_training_time = now
                logger.info("✅ Model retraining completed")
                self.telegram.send_notification("🤖 Model retraining completed successfully")
                
            except Exception as e:
                logger.error(f"❌ Error in model retraining: {str(e)}")
                self.telegram.send_error_notification(f"Model retraining failed: {str(e)}")
    
    def retrain_symbol_model(self, symbol: str):
        """Retrain model for a specific symbol with latest data"""
        try:
            # Get extended data for retraining
            days = 30  # Use last 30 days for retraining
            df = self.bot.get_market_data(symbol, days)
            
            if not df.empty:
                df = self.bot.calculate_indicators(df)
                model, predictions, df_ml, X_test, X_train, y_train, y_test = self.bot.train_model(df)
                
                # Save retraining metrics
                accuracy = (predictions == y_test).mean() * 100
                
                performance_data = {
                    'symbol': symbol,
                    'initial_capital': 10000,
                    'current_capital': 10000,  # Will be updated with real performance
                    'total_return': 0.0,
                    'win_rate': accuracy,
                    'total_trades': len(predictions),
                    'profitable_trades': int(np.sum(predictions)),
                    'strategy_parameters': json.dumps(self.bot.best_params) if self.bot.best_params else '{}'
                }
                
                self.db.save_bot_performance(performance_data)
                logger.info(f"🔄 {symbol} model retrained | Accuracy: {accuracy:.1f}%")
        
        except Exception as e:
            logger.error(f"❌ Error retraining {symbol}: {str(e)}")
    
    def send_daily_summary(self):
        """Send daily performance summary via Telegram"""
        try:
            # Get portfolio summary
            summary = self.db.get_portfolio_summary()
            
            # Get today's performance
            today = datetime.now().date()
            today_performance = self.db.get_performance_history(limit=10)
            
            if not today_performance.empty:
                latest_performance = today_performance.iloc[0]
                
                message = f"""
📊 **Daily Trading Summary** - {today.strftime('%Y-%m-%d')}

🤖 **Bot Performance:**
• Total Return: {latest_performance.get('total_return', 0):.2%}
• Win Rate: {latest_performance.get('win_rate', 0):.1%}
• Total Trades: {latest_performance.get('total_trades', 0)}
• Current Capital: ${latest_performance.get('current_capital', 0):,.2f}

📈 **Portfolio Summary:**
• Total Sessions: {summary.get('total_sessions', 0)}
• Active Symbols: {len(self.symbols)}

⏰ Next retraining: {(datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')}
                """
                
                self.telegram.send_notification(message)
                logger.info("📧 Daily summary sent")
        
        except Exception as e:
            logger.error(f"❌ Error sending daily summary: {str(e)}")
    
    def run(self):
        """Main worker loop"""
        logger.info("🚀 Starting Trading Worker - Autonomous Permanent Mode")
        self.telegram.send_notification("🤖 Trading Bot started in Autonomous Permanent Mode")
        
        # Schedule tasks
        schedule.every(5).minutes.do(self.execute_trading_cycle)
        schedule.every(24).hours.do(self.check_and_retrain_model)
        schedule.every().day.at("08:00").do(self.send_daily_summary)
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("⏹️ Trading Worker stopped by user")
            self.telegram.send_notification("⏹️ Trading Bot stopped")
        
        except Exception as e:
            logger.error(f"❌ Fatal error in worker: {str(e)}")
            self.telegram.send_error_notification(f"Fatal worker error: {str(e)}")
    
    def stop(self):
        """Stop the worker gracefully"""
        self.is_running = False
        logger.info("🛑 Trading Worker stopping...")

def main():
    """Main entry point"""
    worker = TradingWorker()
    
    try:
        worker.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        worker.stop()

if __name__ == "__main__":
    main()
