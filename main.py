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
import google.generativeai as genai
import re

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

def is_relevant(article, query_keywords):
    title = (article.get('title') or '').lower()
    description = (article.get('description') or '').lower()
    content = (article.get('content') or '').lower()
    combined = title + ' ' + description + ' ' + content

    # Filter out podcasts and non-articles
    junk_keywords = ['podcast', 'sounds.bbc', 'radio', 'test match', 'playlist']
    if any(junk in combined for junk in junk_keywords):
        return False

    keywords = [k.strip() for k in query_keywords.lower().split(' or ')]
    return any(keyword in combined for keyword in keywords)

def get_news(sector):
    api_key = '64d7af736a51472191fe471584124310'
    trusted_sources = 'bloomberg,reuters,financial-times,the-wall-street-journal,cnbc,bbc-news,the-economist'
    
    sector_keywords = {
        'oil and gas': 'oil OR gas OR crude OR OPEC OR Brent OR energy OR petroleum',
        'banking': 'banking OR interest rate OR loans OR financial',
        'technology': 'technology OR tech OR digital OR AI OR startup',
        'mining': 'mining OR nickel OR coal OR mineral OR tambang',
        'consumer': 'consumer goods OR retail OR FMCG OR purchasing power'
    }
    query = sector_keywords.get(sector.lower(), sector)

    url = f'https://newsapi.org/v2/everything?q={query}&sources={trusted_sources}&apiKey={api_key}'
    response = requests.get(url)
    data = response.json()

    if data['status'] != 'ok':
        print('Failed to fetch news.')
        return []

    articles = data['articles']
    relevant_articles = [a for a in articles if is_relevant(a, query)]

    print(f"Total articles fetched: {len(articles)}")
    print(f"Relevant articles after filter: {len(relevant_articles)}")
    return relevant_articles

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

def display_dashboard(indo_macro, global_macro, stocks, news, alerts, ai_report):

    # Macro Economics Section (Top-Level)
    print(Fore.CYAN + '\n=== [ GLOBAL & DOMESTIC MACRO ] ===' + Style.RESET_ALL)
    print(f'USD/IDR         : Rp {indo_macro['idr_usd']:.0f}')
    print(f'JCI (IHSG)      : {indo_macro['ihsg']:.0f}')
    print(f'Brent Crude     : ${global_macro['brent_price']:.2f}')
    print(f'US Fed Rate     : {global_macro['fed_rate']}%')
    print(f'US Inflation    : {global_macro['yoy_inflation']}%')
    print(f'DXY             : {global_macro['dxy']:.2f}')

    # Watchlist Section (Sector-Level)
    print(Fore.CYAN + '\n=== [ ACTIVE WATCHLIST ] ===' + Style.RESET_ALL)
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
    
    # Alert Section
    print(Fore.CYAN + '\n=== [ ALERT SYSTEM ] ===' + Style.RESET_ALL)
    if not alerts:
        print(Fore.GREEN + '✅ All positions within threshold. No alerts.' + Style.RESET_ALL)
    else:
        for alert_type, ticker, message in alerts:
            if alert_type == 'DANGER':
                print(Fore.RED + f'🚨 DANGER | {message}' + Style.RESET_ALL)
                speak(message)
            elif alert_type == 'OPPORTUNITY':
                print(Fore.YELLOW + f'⚡ SIGNAL | {message}' + Style.RESET_ALL)
                speak(message)

    # Lates Intel Section (Micro-Level)
    print(Fore.CYAN + '\n=== [ SECTOR INTELLIGENCE ] ===' + Style.RESET_ALL)
    for articles in news:
        print(Fore.YELLOW + f'📰 {articles['title']}' + Style.RESET_ALL)
        print(f'    Source: {articles['source']['name']}')
        print(f'    URL: {articles['url']}\n')
    
    # AI Section
    print(Fore.CYAN + "\n=== [ M.A.R.S AI ANALYSIS ] ===" + Style.RESET_ALL)
    print(Fore.WHITE + ai_report + Style.RESET_ALL)
    speak(clean_for_speech(ai_report))
    
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

def clean_for_speech(text):
    # remove ** bold markers
    text = re.sub(r'\*\*', '', text)
    # remove * italic markers
    text = re.sub(r'\*', '', text)
    # remove # headers
    text = re.sub(r'#+\s', '', text)
    # remove numbered list dots
    text = re.sub(r'\d+\.\s', '', text)
    return text

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

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config):
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def check_alerts(stocks, config):
    thresholds = config['alert_thresholds']
    alerts = []

    for ticker, data in stocks.items():
        if ticker in thresholds:
            price = data['price']
            min_price = thresholds[ticker]['min']
            max_price = thresholds[ticker]['max']

            if price < min_price:
                message = f'Warning. {ticker} is below support at Rp {price:,.0f}. Support level is Rp {min_price:,.0f}'
                alerts.append(('DANGER', ticker, message))
            elif price > max_price:
                message = f'Alert. {ticker} has broken resistance at Rp {price:,.0f}. Resistance level is Rp {max_price:,.0f}'
                alerts.append(('OPPORTUNITY', ticker, message))
    
    return alerts

def init_gemini(config):
    genai.configure(api_key=config['gemini_api_key'])
    model = genai.GenerativeModel('gemini-2.5-flash')
    return model

def analyze_with_ai(model, global_macro, indo_macro, stocks, sector):
    context = f"""
    You are MARS, an advanced financial analyst AI assistant.
    Analyze the following real-time market data using strict top-down analysis framework.
    Be concise, data-driven, and professional. Speak directly to the operator.

    === GLOBAL MACRO ===
    Fed Rate: {global_macro['fed_rate']}%
    US Inflation (YoY): {global_macro['yoy_inflation']}%
    10Y Inflation Expectation: {global_macro['inflation_expectation']}%
    US GDP Growth : {global_macro['us_gdp']}%
    Brent Crude: ${global_macro['brent_price']:.2f}
    DXY: {global_macro['dxy']:.2f}

    === INDONESIA MACRO ===
    USD/IDR: Rp {indo_macro['idr_usd']:,.0f}
    IHSD: {indo_macro['ihsg']:,.0f}

    === WATCHLIST ({sector.upper()}) SECTOR ===
    {chr(10).join([f'{ticker}: Rp {data['price']:,.0f} ({data['change']:+.2f}%)' for ticker, data in stocks.items()])}

    Based on this data, provide:
    1. Global macro assessment (2-3 sentences)
    2. Indonesia macro impact (2-3 sentences)
    3. Sector outlook for {sector} (2-3 sentences)
    4. Top 2 stocks to watch and why (based on price movement)
    5. One key risk to monitor today

    Keep the entire response under 200 words. Be direct and actionable.
    """

    try:
        response = model.generate_content(context)
        return response.text
    except Exception as e:
        if 'ResourceExhausted' in str(e):
            print(Fore.YELLOW + "Rate limit hit. Waiting 60 seconds..." + Style.RESET_ALL)
            time.sleep(60)
            response = model.generate_content(context)
            return response.text
        else:
            return "AI analysis unavailable at this time."

def interactive_model(model, global_macro, indo_macro, stocks, config):
    pass

def main():
    config = load_config()
    watchlist = config['watchlist']
    model = init_gemini(config)

    print_banner()
    target_sector = greet()
    
    print(Fore.YELLOW + f'\nFetching macro, market, and \'{target_sector}\' intelligence...' + Style.RESET_ALL)

    indo_data = get_indonesia_macro()
    global_data = get_global_macro()
    stock_data = get_stock_prices(watchlist)
    news_data = get_news(target_sector)
    alerts = check_alerts(stock_data, config)

    # AI analysis
    print(Fore.YELLOW + '\nRunning AI top-down analysis...' + Style.RESET_ALL)
    ai_report = analyze_with_ai(model, global_data, indo_data, stock_data, target_sector)

    display_dashboard(indo_data, global_data, stock_data, news_data, alerts, ai_report)

if __name__ == '__main__':
    main()
