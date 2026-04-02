import pprint
import pandas as pd
from database import TradingDatabase
from utils import TradingBot

db = TradingDatabase()
bot = TradingBot(db)

print("Fetching BTC data...")
df = bot.get_market_data("BTC-USD", 30)
print(f"BTC records: {len(df)}")

print("Calculating indicators...")
df = bot.calculate_indicators(df, 'BTC-USD')

print("Preparing for ML...")
df['target'] = 0
df_ml = df.dropna().copy()

print("Nulls per column:")
print(df.isnull().sum().to_string())

print(f"Rows left: {len(df_ml)}")
