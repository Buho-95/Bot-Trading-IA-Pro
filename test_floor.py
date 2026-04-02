import pandas as pd
from utils import TradingBot
from database import TradingDatabase

bot = TradingBot(TradingDatabase())
df_sp500 = bot.get_market_data('^GSPC', 30)
df_sp500['date'] = pd.to_datetime(df_sp500['date']).dt.tz_localize(None).dt.floor('h')
print(df_sp500['date'].head(5))
