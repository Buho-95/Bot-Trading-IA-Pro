import pandas as pd
import json
from database import TradingDatabase
from utils import TradingBot

db = TradingDatabase()
bot = TradingBot(db)

df = bot.get_market_data("BTC-USD", 30)
df = bot.calculate_indicators(df, 'BTC-USD')
df['target'] = 0

with open("nulls.json", "w") as f:
    json.dump(df.isnull().sum().to_dict(), f, indent=4)
