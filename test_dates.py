import pandas as pd
from utils import TradingBot
from database import TradingDatabase

bot = TradingBot(TradingDatabase())

df_btc = bot.get_market_data('BTC-USD', 30)
df_sp500 = bot.get_market_data('^GSPC', 30)

print("BTC Dates:")
print(df_btc['date'].head(5))
print("SP500 Dates:")
print(df_sp500['date'].head(5))
