import requests
import yfinance as yf
import pyttsx3
from colorama import Fore, Style, init
import random
import json
import datetime

def get_indonesia_macro():
    idr_usd = yf.Ticker('USDIDR=X')
    ihsg = yf.Ticker('^JKSE')

    idr_usd_price = idr_usd.fast_info['lastPrice']
    ihsg_price = ihsg.fast_info['lastPrice']

    return {
        'idr_usd': idr_usd_price,
        'ihsg': ihsg_price
    }

def get_global_macro():
    api_key = 'e8254e772e7954d761364ad64309a4cc'

    fed = get_fred_data('FEDFUNDS', api_key)
    fed_rate = fed[0]['value']

    cpi_data = get_fred_data('CPIAUCSL', api_key, limit=13)
    raw_cpi = cpi_data[0]['value']
    last_year_cpi = cpi_data[12]['value']
    yoy_inflation = ((float(raw_cpi) - float(last_year_cpi)) / float(last_year_cpi)) * 100
    
    t10 = get_fred_data('T10YIE', api_key)
    inflation_expectation = t10[0]['value']

    us_GDP = get_fred_data('A191RL1Q225SBEA', api_key)

    brent = yf.Ticker('BZ=F')
    brent_price = brent.fast_info ['lastPrice']

    dxy = yf.Ticker('DX-Y.NYB')
    dxy_price = dxy.fast_info['lastPrice']

    return {
        'fed_rate': fed_rate,
        'raw_cpi': raw_cpi,
        'yoy_inflation': round(yoy_inflation, 2),
        'inflation_expectation': inflation_expectation,
        'us_gdp': us_GDP[0]['value'],
        'brent_price': brent_price,
        'dxy': dxy_price
    }

def get_fred_data(series_id, api_key, limit=1):
    url = f'https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&sort_order=desc&limit={limit}&file_type=json'
    response = requests.get(url)
    data = response.json()

    print(json.dumps(data, indent=4))
    return data['observations']

def get_news(sector):
    api_key = '64d7af736a51472191fe471584124310'
    
    sector_keywords = {
        'oil and gas': 'oil OR gas OR crude OR OPEC OR Brent OR energy OR petroleum',
        'banking': 'banking OR interest rate OR loans OR financial',
        'technology': 'technology OR tech OR digital OR AI OR startup',
        'mining': 'mining OR nickel OR coal OR mineral OR tambang',
        'consumer': 'consumer goods OR retail OR FMCG OR purchasing power'
    }
    query = sector_keywords.get(sector.lower(), sector)

    url = f'https://newsapi.org/v2/everything?q={query}&apiKey={api_key}'
    response = requests.get(url)
    data = response.json()

    # print(json.dumps(data, indent=4))

    if data['status'] != 'ok':
        print('Failed to fetch news.')
        return []
    
    return data['articles']

def get_stock_prices(watchlist):
    results = {}
    for ticker in watchlist:
        stock_data = yf.Ticker(ticker)
        current_price = stock_data.fast_info['lastPrice']
        results[ticker] = current_price
    
    return results

def get_company_snapshot(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info

    data = {
        'Name': info.get('longName')
    }

def display_dashboard():
    articles = get_news('oil and gas')
    for article in articles:
        print(f'📰 {article['title']}')
        print(f'   Source: {article['source']['name']}')
        print(f'   Published: {article['publishedAt']}')
        print(f'   URL: {article['url']}')

def speak(text):
    pass

def greet():
    pass

def main():
    pass

ticker = yf.Ticker('BBCA.JK')
# print(dir(ticker))
# help(ticker.history)
info = ticker.info
print(list(info.keys()))