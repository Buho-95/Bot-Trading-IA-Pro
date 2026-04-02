#!/usr/bin/env python3
"""
Database Migration Script
Handles automatic migration of database schema for new indicators
"""

import sqlite3
import logging
import shutil
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_database(db_path: str = "trading_bot.db"):
    """
    Migrate database to add new columns for ATR and Fear & Greed Index
    """
    if not Path(db_path).exists():
        logger.info(f"Database {db_path} does not exist. No migration needed.")
        return
    
    logger.info(f"🔄 Starting database migration for {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check existing columns in market_data table
            cursor.execute("PRAGMA table_info(market_data)")
            market_data_columns = [row[1] for row in cursor.fetchall()]
            logger.info(f"Current market_data columns: {market_data_columns}")
            
            # Add atr column to market_data if missing
            if 'atr' not in market_data_columns:
                cursor.execute("ALTER TABLE market_data ADD COLUMN atr REAL")
                logger.info("✅ Added 'atr' column to market_data table")
            else:
                logger.info("ℹ️ 'atr' column already exists in market_data table")
            
            # Add fear_greed_index column to market_data if missing
            if 'fear_greed_index' not in market_data_columns:
                cursor.execute("ALTER TABLE market_data ADD COLUMN fear_greed_index INTEGER")
                logger.info("✅ Added 'fear_greed_index' column to market_data table")
            else:
                logger.info("ℹ️ 'fear_greed_index' column already exists in market_data table")
            
            # Check existing columns in trading_operations table
            cursor.execute("PRAGMA table_info(trading_operations)")
            trading_ops_columns = [row[1] for row in cursor.fetchall()]
            logger.info(f"Current trading_operations columns: {trading_ops_columns}")
            
            # Add atr_value column to trading_operations if missing
            if 'atr_value' not in trading_ops_columns:
                cursor.execute("ALTER TABLE trading_operations ADD COLUMN atr_value REAL")
                logger.info("✅ Added 'atr_value' column to trading_operations table")
            else:
                logger.info("ℹ️ 'atr_value' column already exists in trading_operations table")
            
            # Add fear_greed_index column to trading_operations if missing
            if 'fear_greed_index' not in trading_ops_columns:
                cursor.execute("ALTER TABLE trading_operations ADD COLUMN fear_greed_index INTEGER")
                logger.info("✅ Added 'fear_greed_index' column to trading_operations table")
            else:
                logger.info("ℹ️ 'fear_greed_index' column already exists in trading_operations table")
            
            # Verify migration
            cursor.execute("PRAGMA table_info(market_data)")
            updated_market_columns = [row[1] for row in cursor.fetchall()]
            
            cursor.execute("PRAGMA table_info(trading_operations)")
            updated_trading_columns = [row[1] for row in cursor.fetchall()]
            
            logger.info(f"✅ Migration completed successfully!")
            logger.info(f"📊 Updated market_data columns: {updated_market_columns}")
            logger.info(f"💼 Updated trading_operations columns: {updated_trading_columns}")
            
            conn.commit()
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise

def backup_database(db_path: str = "trading_bot.db"):
    """
    Create a backup of the database before migration
    """
    if not Path(db_path).exists():
        logger.info(f"Database {db_path} does not exist. No backup needed.")
        return
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"❌ Backup failed: {str(e)}")
        raise

def verify_migration(db_path: str = "trading_bot.db"):
    """
    Verify that migration was successful
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check market_data table
        cursor.execute("PRAGMA table_info(market_data)")
        market_columns = [row[1] for row in cursor.fetchall()]
        
        # Check trading_operations table
        cursor.execute("PRAGMA table_info(trading_operations)")
        trading_columns = [row[1] for row in cursor.fetchall()]
        
        required_market_columns = ['atr', 'fear_greed_index']
        required_trading_columns = ['atr_value', 'fear_greed_index']
        
        market_ok = all(col in market_columns for col in required_market_columns)
        trading_ok = all(col in trading_columns for col in required_trading_columns)
        
        if market_ok and trading_ok:
            logger.info("✅ Migration verification successful!")
            return True
        else:
            missing_market = [col for col in required_market_columns if col not in market_columns]
            missing_trading = [col for col in required_trading_columns if col not in trading_columns]
            logger.error(f"❌ Migration verification failed!")
            logger.error(f"Missing market_data columns: {missing_market}")
            logger.error(f"Missing trading_operations columns: {missing_trading}")
            return False

def main():
    """Main migration function"""
    from datetime import datetime
    
    print("🚀 Trading Bot Database Migration")
    print("=" * 40)
    
    db_path = "trading_bot.db"
    
    # Create backup
    print("\n📦 Creating backup...")
    try:
        backup_database(db_path)
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return
    
    # Run migration
    print("\n🔄 Running migration...")
    try:
        migrate_database(db_path)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return
    
    # Verify migration
    print("\n🔍 Verifying migration...")
    if verify_migration(db_path):
        print("\n🎉 Migration completed successfully!")
        print("✅ Your trading bot database is now ready for the new indicators")
        print("📊 New features available:")
        print("   • ATR (Average True Range) for dynamic stop loss")
        print("   • Fear & Greed Index for market sentiment")
        print("   • Enhanced position sizing with Kelly Criterion")
    else:
        print("\n❌ Migration verification failed!")
        print("Please check the logs and try again.")

if __name__ == "__main__":
    main()
