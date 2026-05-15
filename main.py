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
import pygame

watchlist = [
    'ADMR.JK', 'ADRO.JK', 'BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'BRMS.JK', 
    'CDIA.JK', 'CUAN.JK', 'CYBR.JK', 'ENRG.JK', 'MBMA.JK', 'MDKA.JK', 
    'MEDC.JK', 'NCKL.JK', 'PGEO.JK', 'RMKE.JK', 'SUPA.JK', 'TPIA.JK'
]

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

    if 'observations' not in data:
        print(f'FRED ERROR for {series_id}: {data}')
        return [{'value': 'N/A'}]

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

    if data['status'] != 'ok':
        print('Failed to fetch news.')
        return []
    
    return data['articles']

def detect_sector(user_input):
    user_input = user_input.lower()

    sector_map = {
        'oil and gas': ['oil', 'gas', 'energy', 'petroleum', 'crude', 'brent', 'pgas', 'medc', 'enrg'],
        'banking': ['bank', 'banking', 'finance', 'financial', 'interest rate', 'loans'],
        'technology': ['tech', 'technology', 'digital', 'ai', 'startup', 'software', 'graphics card', 'robot'],
        'mining': ['mining', 'nickel', 'coal', 'mineral', 'tambang', 'nckl', 'mdka'],
        'consumer': ['consumer', 'retail', 'fmcg', 'goods', 'food']
    }

    for sector, keywords in sector_map.items():
        for keyword in keywords:
            if keyword in user_input:
                return sector
    
    return 'oil and gas' # My default

def get_stock_prices(watchlist):
    results = {}
    for ticker in watchlist:
        stock_data = yf.Ticker(ticker)

        try:
            current_price = stock_data.fast_info['lastPrice']
            prev_close = stock_data.fast_info['previousClose']

            percent_change = ((current_price - prev_close) / prev_close) * 100

            results[ticker] = {
                'price': current_price,
                'change': percent_change
            }
        except KeyError:
            results[ticker] = {'price': 0.0, 'change': 0.0}
    
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
        ('Initializing MARS', 0.3),
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

def display_dashboard(indo_macro, global_macro, stocks, news):

    # Macro Economics Section (Top-Level)
    print(Fore.CYAN + '=== [ GLOBAL & DOMESTIC MACRO ] ===' + Style.RESET_ALL)
    print(f'USD/IDR         : Rp {indo_macro['idr_usd']:.0f}')
    print(f'JCI (IHSG)      : {indo_macro['ihsg']:.0f}')
    print(f'Brent Crude     : ${global_macro['brent_price']:.2f}')
    print(f'US Fed Rate     : {global_macro['fed_rate']}%')
    print(f'US Inflation    : {global_macro['yoy_inflation']}%')
    print(f'DXY             : {global_macro['dxy']:.2f}')

    # Watchlist Section (Sector-Level)
    print(Fore.CYAN + '\n=== [ ACTIVE WISHLIST ] ===' + Style.RESET_ALL)
    for ticker, data in stocks.items():
        price = data['price']
        change = data['change']

        if change > 0:
            color = Fore.GREEN
            arrow = '▲'
        elif change < 0:
            color = Fore.RED
            arrow = '▼'
        else:
            color = Fore.YELLOW
            arrow = '-'

        ticker_clean = ticker.replace('.JK', '')
        print(color + f'[{ticker_clean:<5}] : Rp {price:>7,.0f} | {arrow} {change:>+6.2f}%' + Style.RESET_ALL)

    # Lates Intel Section (Micro-Level)
    print(Fore.CYAN + '\n=== [ SECTOR INTELLIGENCE ] ===' + Style.RESET_ALL)
    for articles in news:
        print(Fore.YELLOW + f'📰 {articles['title']}' + Style.RESET_ALL)
        print(f'    Source: {articles['source']['name']}')
        print(f'    URL: {articles['url']}\n')
    
    print(Fore.GREEN + '[SYSTEM] Scan Complete. Awaiting orders, Operator.' + Style.RESET_ALL)
    speak('Scan complete. Awaiting your orders, sir.')
    
async def speak_async(text):
    tts = edge_tts.Communicate(text, voice='en-US-AvaNeural')
    await tts.save('speech.mp3')

def speak(text):
    asyncio.run(speak_async(text))
    
    pygame.mixer.init()
    pygame.mixer.music.load('speech.mp3')
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.quit()

def greet():
    hour = datetime.datetime.now().hour
    date = datetime.datetime.now().strftime("%B %d, %Y")

    if hour < 12:
        greetings = [
            "Good morning sir, how is your condition today?",
            "Waking up early sir?",
            "Morning sir, did you get enough sleep last night?",
            "Morning sir, how's your sleep?",
            f"Morning, sir. MARS is now online. All systems are operational. Today is {date}.",
            "Good morning. I have pulled the latest global market data for your review. Macroeconomic conditions have shifted overnight.",
            "Morning, sir. Brent crude and the Dollar Index have both moved since yesterday's close. I suggest we start with the macro overview. Ready when you are.",
            "Good morning, sir. I trust you slept well. Global markets have been active overnight. I have everything ready."
        ]
    elif hour < 18:
        greetings = [
            "Good afternoon, sir. Midday markets are in session.",
            "Afternoon sir. How is your day going?",
            "Good afternoon. Markets are moving. Ready to run your analysis whenever you are."
        ]
    else:
        greetings = [
            "Good evening, sir. Markets are closing.",
            "Evening sir. Long day?",
            "Good evening. The markets have closed, sir."
        ]

    greeting = random.choice(greetings)
    print(Fore.CYAN + greeting + Style.RESET_ALL)
    speak(greeting)

    print(Fore.CYAN + '\nWhat sector shall I scan for intelligence today, sir?' + Style.RESET_ALL)
    raw_input = input(Fore.YELLOW + '>> ' + Style.RESET_ALL)
    sector = detect_sector(raw_input)
    print(Fore.CYAN + f'Understood. Scanning \'{sector}\' intelligence...' + Style.RESET_ALL)

    return sector

def main():
    print_banner()
    target_sector = greet()
    
    print(Fore.YELLOW + f'\nFetching macro, market, and \'{target_sector}\' intelligence...' + Style.RESET_ALL)

    indo_data = get_indonesia_macro()
    global_data = get_global_macro()
    stock_data = get_stock_prices(watchlist)
    news_data = get_news(target_sector)

    display_dashboard(indo_data, global_data, stock_data, news_data)

if __name__ == '__main__':
    main()
