#Like = tweet.favorite
#Retweet = tweet.retweet

from operator import index
import tweepy
import requests 
from bs4 import BeautifulSoup 
from datetime import datetime
import pytz
from operator import index
import pandas as pd

auth = tweepy.OAuth1UserHandler(
   "***************", "************************************",
   "**********************************", "******************************************************"
)

api = tweepy.API(auth, wait_on_rate_limit=False)


#This portion handles getting all the information and webscraping to format up to date information on the stock market


#info for all 3 indexes/active movers
SP500url = 'https://www.cnbc.com/quotes/.SPX'
NASDAQurl = 'https://www.cnbc.com/quotes/.IXIC'
DOWurl = 'https://www.cnbc.com/quotes/.DJI'

#Formatting and accessing elements via website HTML for indexes
SPresponse = requests.get(SP500url)
soup = BeautifulSoup(SPresponse.text, 'html.parser')

NASDAQresponse = requests.get(NASDAQurl)
soup2 = BeautifulSoup(NASDAQresponse.text, 'html.parser')

DOWresponse = requests.get(DOWurl)
soup3 = BeautifulSoup(DOWresponse.text, 'html.parser')

"""
This portion handles timing. It indicates market open at 6:30 to trigger morning updates. It also checks if the market
is open to run our big mover methods
"""
#Checks the current time in local timezone
current_time = datetime.now()
local_date = datetime.strftime(current_time, '%b %d, %Y')

#Gets the current time in eastern time and if it is a weekend or not 
eastern_time = datetime.strftime(current_time.astimezone(pytz.timezone('US/Eastern')), '%I:%M %p')
day_of_week = datetime.strftime(current_time.astimezone(pytz.timezone('US/Eastern')), '%A')
dt_east = int(datetime.strftime(current_time.astimezone(pytz.timezone('US/Eastern')), '%H%M'))

#Determines if the market is open
market_open = 930 <= dt_east <= 1600 and (day_of_week != "Saturday" or day_of_week != "Sunday")

#Getting up to date info on index's 
for x in SP500url:
    SP500_price = soup.find('span', {"class":"QuoteStrip-lastPrice"}).getText()
    try:
        SP500_change = soup.find('span', {"class":"QuoteStrip-changeDown"}).getText()
    except:
        SP500_change = soup.find('span', {"class":"QuoteStrip-changeUp"}).getText()
    break

for y in NASDAQurl:
    Nasdaq_price = soup2.find('span', {"class":"QuoteStrip-lastPrice"}).getText()
    try:
        Nasdaq_change = soup2.find('span', {"class":"QuoteStrip-changeDown"}).getText()
    except:
        Nasdaq_change = soup2.find('span', {"class":"QuoteStrip-changeUp"}).getText()
    break

for z in DOWurl:
    Dow_price = soup3.find('span', {"class":"QuoteStrip-lastPrice"}).getText()
    try:
        Dow_change = soup3.find('span', {"class":"QuoteStrip-changeDown"}).getText()
    except:
        Dow_change = soup3.find('span', {"class":"QuoteStrip-changeUp"}).getText()
    break


#This portion handles checking for big market movers while the market is open

#Get the active movers table from the website
active_list = pd.read_html('https://www.tradingview.com/markets/stocks-usa/market-movers-active/')
#Website gives it to us as a single element list. This converts it to a multi-element data frame that we can manipulate
df = active_list[0].reset_index()

#Get ride of all the columns that we do not need
df.pop('Sector')
df.pop('Vol 1D')
df.pop('Volume * Price 1D')
df.pop('Market cap')
df.pop('P/E(TTM)')
df.pop('EPS(TTM)')
df.pop('Employees')
col = df.head()
df['Price'] = df['Price'].apply(lambda x: str(x).replace("USD",""))
df['Chg 1D'] = df['Chg 1D'].apply(lambda x: str(x).replace("USD",""))

#Convert Chg % column into type float so we can compare for any big changes
cols = ['Chg % 1D']
for col in cols:
    df[col] = df[col].map(lambda x: str(x).lstrip('%').rstrip('%'))
    df[col] = df[col].map(lambda x: str(x).lstrip('−').rstrip('−'))
    df[col] = df['Chg % 1D'].astype(str).astype(float)
#this is now a seperate dataframe with the % change as a float


#Checking each of the tweets from the account on this day 
# Collecting tweets
count = 100 # Set the number of tweets to retrieve
tweets = tweepy.Cursor(api.search_tweets,
                               q="from:daily_fantasy",
                               lang="es",
                               tweet_mode='extended',
                               until = local_date # format YYYY-MM-DD in datetime. Not string. Twitter only extract tweets before that date
                               ).items(count)

morning_tweet = 'The S&P500 is currently at: ' + (SP500_price) + " " + (SP500_change) + '\n' + 'NASDAQ is currently at: $' + (Nasdaq_price) + ' ' + (Nasdaq_change) + '\n' + 'The DOW is currently at: $' + (Dow_price) + ' ' + (Dow_change)

if 930 == dt_east:
    api.update_status(morning_tweet)

while market_open is False:
    for i, row in df.iterrows():
        if row['Chg % 1D'] > 7:
            ticker_name   = row['Ticker']
            price_chg = row['Chg 1D']
            percent_chg = row['Chg % 1D']
            new_price = row['Price']
            analyst_rating = row['Technical Rating 1D']
            if ticker_name in tweets:
                continue
            else:    
                active_movers = ('ALERT! ' + ticker_name + ' has moved ' + str(percent_chg) + '% ($' + price_chg + '). It is now at $' + new_price + ' analyst rating: ' + analyst_rating)
                try:
                    tweet = api.update_status(active_movers)
                except:
                    continue

