import yfinance as yf
t = yf.Ticker('AAPL')
print(t.info.get('longName'))
