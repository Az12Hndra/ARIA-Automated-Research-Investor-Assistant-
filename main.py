import requests
import yfinance as yf
from colorama import Fore, Style, init
import random
import json
import datetime
import edge_tts
import asyncio
import os
import time

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

def format_market_cap(value):
    if value is None:
        return 'N/A'
    if value >= 1_000_000_000_000:
        return f'{value / 1_000_000_000_000:.2f}T'
    elif value >= 1_000_000_000:
        return f'{value / 1_000_000_000:.2f}B'
    elif value >= 1_000_000:
        return f'{value / 1_000_000:.2f}M'
    else:
        return f'{value:,.0f}'

def get_company_snapshot(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info

    # Calculation of PBV
    current_price = info.get('currentPrice', 0)
    book_value_per_share = info.get('bookValue', 0)

    if book_value_per_share and book_value_per_share > 1:
        pbv = current_price / book_value_per_share
    else:
        pbv = None

    data = {

        # Price & Market
        'Name': info.get('longName'),
        'Current Price': info.get('currentPrice'),
        'Today\'s Change': f'{info.get('regularMarketChangePercent', 0):.2f}%',
        'Market Cap': format_market_cap(info.get('marketCap')),
        '52-Week Low': info.get('fiftyTwoWeekLow'),
        '52-Week High': info.get('fiftyTwoWeekHigh'),
        'Volatility': info.get('beta'),

        # Fundamentals (Company)
        'Valuation': f'{info.get('trailingPE', 0):.2f}x',
        'Expected Valuation': f'{info.get('forwardPE', 0):.2f}x',
        'Asset Valuation (PBV)': f'{pbv:.2f}x' if pbv else 'N/A (unreliable data)',
        'Profitability (ROE)': f'{info.get('returnOnEquity', 0) * 100:.2f}%',
        'Profit Margin': f'{info.get('profitMargins', 0) * 100:.2f}%',
        'Total Debt': format_market_cap(info.get('totalDebt')),
        'Total Revenue': format_market_cap(info.get('totalRevenue')),

        # Analyst Opinion
        'Action Recommendation': info.get('recommendationKey'),
        'Price Target': info.get('targetMeanPrice'),
        'Number of Analyst Opinions': info.get('numberOfAnalystOpinions'),

        # Dividends
        'Dividend Yield': f'{info.get('dividendYield', 0):.2f}%',
        'Payout Ratio': f'{info.get('payoutRatio', 0) * 100:.2f}%'
    }

    print('Current Price: ', info.get('currentPrice'))
    print('Book Value per Share: ', info.get('bookValue'))
    return data

def print_banner():
    init()  # initialize colorama
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    taglines = [
        "Sentience Protocol v1.0 [ACTIVE]",
        "Intelligence Layer v1.0 [ARMED]",
        "Analysis Engine v1.0 [ONLINE]",
        "Reconnaissance Mode v1.0 [ARMED]"
    ]
    tagline = random.choice(taglines)
    
    print(Fore.CYAN + "=" * 72)
    print(Fore.CYAN + rf"""
  __  __          _____    _____ 
 |  \/  |   /\   |  __ \  / ____| {tagline}
 | \  / |  /  \  | |__) || (___   -------------------------------
 | |\/| | / /\ \ |  _  /  \___ \  System: IDX Top-Down Monitor
 | |  | |/ ____ \| | \ \  ____) | Operator: Sir Hendrawan
 |_|  |_/_/    \_\_|  \_\|_____/  """ + Fore.GREEN + f'Time: {now}')

    print(Fore.CYAN + """
   M A R K E T   A N A L Y S T  &   R E S E A R C H   S E N T I N E L""")
    print(Fore.CYAN + "=" * 72 + Style.RESET_ALL)
    print()

    # Boot sequence
    boot_checks = [
        ('Initializing M.A.R.S', 0.3),
        ('Connecting to FRED API', 0.5),
        ('Connecting to Jakarta Stock Exchange', 0.5),
        ('Loading News Pipeline', 0.4),
        ('Activating Voice Module', 0.3),
        ('All systems ready', 0.2),
    ]

    for message, delay in boot_checks:
        dots = '.' * (45 - len(message))
        print(Fore.YELLOW + f'   [BOOT] {message}{dots}', end='', flush=True)
        time.sleep(delay)
        print(Fore.GREEN + ' ONLINE' + Style.RESET_ALL)
    
    print()
    print(Fore.CYAN + '=' * 72 + Style.RESET_ALL)
    print()

def display_dashboard():
    pass

async def speak_async(text):
    tts = edge_tts.Communicate(text, voice='en-US-AvaNeural')
    await tts.save('speech.mp3')

def speak(text):
    asyncio.run(speak_async(text))
    os.system('start speech.mp3')

def greet():
    hour = datetime.datetime.now().hour
    date = datetime.datetime.now().strftime("%B %d, %Y")

    if hour < 12:
        greetings = [
            "Good morning sir, how is your condition today?",
            "Waking up early sir? Do you want me to run a full report for yesterday's news?",
            "Morning sir, did you get enough sleep last night?",
            "Morning sir, how's your sleep?",
            f"Morning, sir. M.A.R.S is now online. All systems are operational. Today is {date}. Here is your morning briefing.",
            "Good morning. I have pulled the latest global market data for your review. Macroeconomic conditions have shifted overnight. Shall I begin the briefing?",
            "Morning, sir. Brent crude and the Dollar Index have both moved since yesterday's close. I suggest we start with the macro overview. Ready when you are.",
            "Good morning, sir. I trust you slept well. Global markets have been active overnight. I have everything ready. Where would you like to begin?"
        ]
    elif hour < 18:
        greetings = [
            "Good afternoon, sir. Midday markets are in session. Shall I pull the latest price movements for your watchlist?",
            "Afternoon sir. How is your day going? Shall I prepare a sector update?",
            "Good afternoon. Markets are moving. Ready to run your analysis whenever you are."
        ]
    else:
        greetings = [
            "Good evening, sir. Markets are closing. Shall I prepare your end of day summary?",
            "Evening sir. Long day? Let me pull up the closing numbers for you.",
            "Good evening. The markets have closed. Shall I run a full end of day report?"
        ]

    greeting = random.choice(greetings)
    print(greeting)
    speak(greeting)

def main():
    pass

# ticker = yf.Ticker('BBCA.JK')
# print(dir(ticker))
# help(ticker.history)
# info = ticker.info
# print(list(info.keys()))

# print(get_company_snapshot('PGAS.JK'))

# print_banner()
