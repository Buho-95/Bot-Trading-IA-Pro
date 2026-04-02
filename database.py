import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class TradingDatabase:
    def __init__(self, db_path: str = "trading_bot.db"):
        """Initialize database with automatic migrations"""
        self.db_path = db_path
        self.initialize_database()
        self.run_migrations()
    
    def run_migrations(self):
        """Run database migrations to add new columns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if atr column exists in market_data
            cursor.execute("PRAGMA table_info(market_data)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add atr column if it doesn't exist
            if 'atr' not in columns:
                cursor.execute("ALTER TABLE market_data ADD COLUMN atr REAL")
                logger.info("✅ Added 'atr' column to market_data table")
            
            # Add fear_greed_index column if it doesn't exist
            if 'fear_greed_index' not in columns:
                cursor.execute("ALTER TABLE market_data ADD COLUMN fear_greed_index INTEGER")
                logger.info("✅ Added 'fear_greed_index' column to market_data table")
            
            # Check trading_operations table for new columns
            cursor.execute("PRAGMA table_info(trading_operations)")
            trading_columns = [row[1] for row in cursor.fetchall()]
            
            # Add atr_value column if it doesn't exist
            if 'atr_value' not in trading_columns:
                cursor.execute("ALTER TABLE trading_operations ADD COLUMN atr_value REAL")
                logger.info("✅ Added 'atr_value' column to trading_operations table")
            
            # Add fear_greed_index column if it doesn't exist
            if 'fear_greed_index' not in trading_columns:
                cursor.execute("ALTER TABLE trading_operations ADD COLUMN fear_greed_index INTEGER")
                logger.info("✅ Added 'fear_greed_index' column to trading_operations table")
            
            conn.commit()
            logger.info("🔄 Database migrations completed successfully")
    
    def initialize_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trading_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    operation_type TEXT NOT NULL, -- 'BUY' or 'SELL'
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    rsi_value REAL,
                    sma_20 REAL,
                    sma_50 REAL,
                    volatility REAL,
                    atr_value REAL,
                    fear_greed_index INTEGER,
                    prediction_confidence REAL,
                    strategy_used TEXT DEFAULT 'RandomForest',
                    status TEXT DEFAULT 'EXECUTED' -- 'EXECUTED', 'PENDING', 'FAILED'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    rsi_14 REAL,
                    sma_20 REAL,
                    sma_50 REAL,
                    volatility REAL,
                    return_rate REAL,
                    atr REAL,
                    fear_greed_index INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    initial_capital REAL NOT NULL,
                    current_capital REAL NOT NULL,
                    total_return REAL NOT NULL,
                    win_rate REAL,
                    total_trades INTEGER,
                    profitable_trades INTEGER,
                    strategy_parameters TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_name TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_trading_operation(self, operation_data: Dict) -> int:
        """Save a trading operation to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO trading_operations 
                (symbol, operation_type, price, quantity, total_amount, rsi_value, 
                 sma_20, sma_50, volatility, atr_value, fear_greed_index, prediction_confidence, strategy_used, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                operation_data['symbol'],
                operation_data['operation_type'],
                operation_data['price'],
                operation_data['quantity'],
                operation_data['total_amount'],
                operation_data.get('rsi_value'),
                operation_data.get('sma_20'),
                operation_data.get('sma_50'),
                operation_data.get('volatility'),
                operation_data.get('atr_value'),
                operation_data.get('fear_greed_index'),
                operation_data.get('prediction_confidence'),
                operation_data.get('strategy_used', 'RandomForest'),
                operation_data.get('status', 'EXECUTED')
            ))
            conn.commit()
            return cursor.lastrowid
    
    def save_market_data(self, market_data: List[Dict]) -> None:
        """Save market data to database"""
        with sqlite3.connect(self.db_path) as conn:
            for data in market_data:
                conn.execute("""
                    INSERT OR REPLACE INTO market_data 
                    (symbol, open_price, high_price, low_price, close_price, volume, 
                     rsi_14, sma_20, sma_50, volatility, return_rate, atr, fear_greed_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['symbol'],
                    data['open_price'],
                    data['high_price'],
                    data['low_price'],
                    data['close_price'],
                    data['volume'],
                    data.get('rsi_14'),
                    data.get('sma_20'),
                    data.get('sma_50'),
                    data.get('volatility'),
                    data.get('return_rate'),
                    data.get('atr'),
                    data.get('fear_greed_index')
                ))
            conn.commit()
    
    def save_bot_performance(self, performance_data: Dict) -> int:
        """Save bot performance metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO bot_performance 
                (symbol, initial_capital, current_capital, total_return, win_rate, 
                 total_trades, profitable_trades, strategy_parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                performance_data['symbol'],
                performance_data['initial_capital'],
                performance_data['current_capital'],
                performance_data['total_return'],
                performance_data.get('win_rate'),
                performance_data.get('total_trades', 0),
                performance_data.get('profitable_trades', 0),
                performance_data.get('strategy_parameters', '{}')
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_trading_history(self, symbol: Optional[str] = None, limit: int = 100) -> pd.DataFrame:
        """Get trading operations history"""
        query = "SELECT * FROM trading_operations"
        params = []
        
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_performance_history(self, symbol: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
        """Get bot performance history"""
        query = "SELECT * FROM bot_performance"
        params = []
        
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Total operations by type
            ops_df = pd.read_sql_query("""
                SELECT operation_type, COUNT(*) as count, SUM(total_amount) as total_volume
                FROM trading_operations 
                WHERE status = 'EXECUTED'
                GROUP BY operation_type
            """, conn)
            
            # Performance metrics
            perf_df = pd.read_sql_query("""
                SELECT symbol, AVG(total_return) as avg_return, 
                       COUNT(*) as sessions, MAX(current_capital) as max_capital
                FROM bot_performance
                GROUP BY symbol
            """, conn)
            
            return {
                'operations_summary': ops_df.to_dict('records'),
                'performance_summary': perf_df.to_dict('records'),
                'total_sessions': len(perf_df)
            }
    
    def save_user_setting(self, setting_name: str, setting_value: str) -> None:
        """Save user setting"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_settings (setting_name, setting_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (setting_name, setting_value))
            conn.commit()
    
    def get_user_setting(self, setting_name: str, default_value: str = None) -> Optional[str]:
        """Get user setting"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT setting_value FROM user_settings WHERE setting_name = ?",
                (setting_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else default_value
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old data to manage database size"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM market_data 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days_to_keep))
            
            conn.execute("""
                DELETE FROM trading_operations 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days_to_keep * 2))  # Keep operations longer
            
            conn.commit()
