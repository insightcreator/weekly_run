
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_tickers_from_csv(url):
    df = pd.read_csv(url)
    return df['Symbol'].str.strip() + '.NS'

urls=["ind_niftylargemidcap250list.csv"]
# Fetch unique tickers
tickers = set()
for u in urls:
    tickers.update(get_tickers_from_csv(u))
tickers = list(tickers)
print(f"Fetched {len(tickers)} unique tickers")
# Collect weekly data
for t in enumerate(tickers):
    try:
        df = yf.download(t[1], period="8d", interval="1d", progress=False,auto_adjust=True)
        if len(df) >= 6:  # at least 5 trading days + today
            df["wa_move"]=df['Close']*df['Volume']
            df["lead_wa_move"]=df["wa_move"].shift(7)
            df["lead_close"]=df['Close'].shift(7)
            df["stock"] =[col[1].split(".")[0] for col in df.columns][0]
            col=[col[0] for col in df.columns]
            df.columns=col
            df.reset_index(inplace=True)
            df["pct_chg_volume"] = (((df["Close"]-df["lead_close"])*df['Volume']*.0001) / df["lead_close"] )
            df["pct_chg"] = (((df["Close"]-df["lead_close"])*100) / df["lead_close"] )
            df["abs_chg"] = (df['Close']-df["lead_close"])
            df2=df.iloc[-1:,:]
            
        if t[0]==0:
            Complete_List=df2
        else:
           Complete_List=pd.concat([Complete_List, df2], ignore_index=True,)
    except Exception as e:
        print("Error", t, e)

top_abs   = Complete_List.nlargest(10, 'abs_chg')
top_abs['Selection']="Top Absolute Change"
bot_abs   = Complete_List.nsmallest(10, 'abs_chg')
bot_abs['Selection']="Bottom Absolute Change"
top_pct   = Complete_List.nlargest(10, 'pct_chg')
top_pct['Selection']="Top Percentage Change"
bot_pct   = Complete_List.nsmallest(10, 'pct_chg')
bot_pct['Selection']="Bottom Percentage Change"
top_pct_volume   = Complete_List.nlargest(10, 'pct_chg_volume')
top_pct_volume['Selection']="Top Percentage Change with Volume"
bot_pct_volume   = Complete_List.nsmallest(10, 'pct_chg_volume')
bot_pct_volume['Selection']="Bottom Percentage Change with Volume"

Interested_stocks=pd.concat([top_abs,bot_abs,top_pct,bot_pct,bot_pct_volume,top_pct_volume],ignore_index=True)

'''Fetching News data'''

def get_top_headlines(ticker, days=15, max_articles=5):
    """
    Fetch top news articles for a given ticker from Google News RSS.
    """
    base_url = f"https://news.google.com/rss/search?q={ticker}+stock"
    response = requests.get(base_url)
    
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")

    headlines = []
    cutoff_date = Interested_stocks['Date'][0] - timedelta(days=days)

    for item in items[:max_articles]:
        title = item.title.text
        link = item.link.text
        pub_date = datetime.strptime(item.pubDate.text, '%a, %d %b %Y %H:%M:%S %Z')

        if pub_date >= cutoff_date:
            headlines.append(item.title.text)
        return headlines
   
tickers2 = [j for j in Interested_stocks["stock"]]

# Collect data into a list of dicts
news_data = []
for ticker in tickers2:
    headlines = get_top_headlines(ticker, max_articles=10)
    # Format as bullet points
    bullet_points = "\n• " + "\n• ".join(headlines) if headlines else "No news found"
    news_data.append({"Ticker": ticker, "News": bullet_points})

# Convert to DataFrame
df = pd.DataFrame(news_data)
df_final=Interested_stocks.merge(df,left_on="stock", right_on='Ticker', how='left')

#file exported
df_final.to_excel(f"./Output/stocks_{Interested_stocks['Date'][0].strftime('%Y%m%d')}.xlsx", index=False)
