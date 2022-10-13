# Databricks notebook source
# MAGIC %md
# MAGIC ####Install packages
# MAGIC * psaw (A minimalist wrapper for searching public reddit comments/submissions via the pushshift.io API)
# MAGIC * alpaca_trade_api (library for the Alpaca trade API)
# MAGIC * bs4 (Beautiful Soup to scrape information from web pages)
# MAGIC * nltk (Natural Language Toolkit)

# COMMAND ----------

# MAGIC %pip install psaw
# MAGIC %pip install alpaca_trade_api
# MAGIC %pip install bs4
# MAGIC %pip install nltk

# COMMAND ----------

# MAGIC %md
# MAGIC ####Import packages

# COMMAND ----------

from psaw import PushshiftAPI
from datetime import timedelta
import datetime
from datetime import datetime
from dateutil import tz
from time import mktime
import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
import re
import nltk
from nltk.corpus import stopwords
from collections import Counter  
from pyspark.sql import *
spark.conf.set("spark.sql.execution.arrow.enabled", "true")

# COMMAND ----------

# MAGIC %md
# MAGIC Find cleaning word pattern (stopwords and english common words)

# COMMAND ----------

nltk.download('stopwords')

common_words_df = spark.read.text('/FileStore/tables/common_words.txt')
common_words_list = ([data[0].upper() for data in common_words_df.select('value').collect()])

stop_word = stopwords.words('english')
stop_word_list = [x.upper() for x in stop_word]

all_remove_words = common_words_list + stop_word_list

pattern = re.compile(r'\b(' + r'|'.join(all_remove_words) + r')\b\s*')

print(pattern)

# COMMAND ----------

# MAGIC %md
# MAGIC ####Alpaca trade api
# MAGIC * Connect Alpaca using key and secret (alpaca developer account)
# MAGIC * Get stock tickers

# COMMAND ----------

API_URL = 'https://api.alpaca.markets'
API_KEY = dbutils.secrets.get(scope="socialAnalyticScope", key="alpacakey")
API_SECRET = dbutils.secrets.get(scope="socialAnalyticScope", key="alpacasecret")

api = tradeapi.REST(API_KEY, API_SECRET, base_url=API_URL)
assets = api.list_assets()

rows = []

for asset in assets:
  rows.append([asset.name, asset.symbol, asset.exchange])

stockDesc = pd.DataFrame(rows, columns=["Name", "Symbol", "Exchange"])
symList = set(stockDesc['Symbol'])

# COMMAND ----------

today = (datetime.utcnow() - timedelta(1)).date()
oldPostDate = (datetime.utcnow() - timedelta(0)) 
print(oldPostDate)

# COMMAND ----------

# MAGIC %md
# MAGIC ####Extract and parse submissions
# MAGIC * Find submission - url, author, title, subreddit and date
# MAGIC * Apply stopwords pattern to clean 
# MAGIC * Create dataframe of ticker (Symbol), post count (Count) and post date (RunDate)

# COMMAND ----------

start = datetime(today.year, today.month, today.day, tzinfo=tz.tzutc())
start_time = int(start.timestamp())

# COMMAND ----------

api = PushshiftAPI()

start = datetime(today.year, today.month, today.day, tzinfo=tz.tzutc())
start_time = int(start.timestamp())

runDate = start.strftime('%Y-%m-%d')

submissions = api.search_submissions(after=start_time,subreddit='wallstreetbets',filter=['url','author','title','subreddit'])

allStock = []
countSubmission = 0

column_names = ["Symbol", "Count", "RunDate"]
finalStock_df = pd.DataFrame(columns = column_names)
stockCount_df = pd.DataFrame(columns = column_names)

for submission in submissions:
  newPostDate = datetime.fromtimestamp(submission.created_utc).date()
  words = submission.title 
  cleanWords = pattern.sub('', words)
  onlyCapsWords = re.findall('([A-Z]+(?:(?!\s?[A-Z][a-z])\s?[A-Z])+)', cleanWords)
  onlyCapsWords = [x.split() for x in onlyCapsWords]
  onlyCapsWords = sum(onlyCapsWords,[])
  allStock = allStock + onlyCapsWords
  countSubmission = countSubmission + 1
  
  if (newPostDate != oldPostDate) and (countSubmission > 1):
    stockOcc = dict(Counter(allStock))
    dictfilt = lambda x, y: dict([ (i,x[i]) for i in x if i in set(y) ])
    stockOcc = dictfilt(stockOcc, symList)
    actualPostDate = newPostDate + timedelta(days=1)
    
    stockCount_df = pd.DataFrame(stockOcc.items(), columns=['Symbol', 'Count'])
    stockCount_df['RunDate'] = actualPostDate
    frames = [finalStock_df, stockCount_df]
    finalStock_df = pd.concat(frames)
    
    stockOcc = {}
    stockCount_df = pd.DataFrame(columns = column_names)
    allStock = []
    
  oldPostDate = newPostDate

finalStock_df.head()

# COMMAND ----------

stockCountDesc = pd.merge(finalStock_df, stockDesc, on='Symbol',how='left')
stockCountDesc['RunDate'] =  pd.to_datetime(stockCountDesc['RunDate'], format='%Y-%m-%d')

# COMMAND ----------

# MAGIC %md
# MAGIC ####Append data to table (Azure SQL)
# MAGIC * Establish connection using JDBC protocol 
# MAGIC * Write (append) incremental data
# MAGIC * Run query against the table 

# COMMAND ----------

jdbcHostname = "socialanalyticserver.database.windows.net"
jdbcPort = "1433"
jdbcDatabase = "socialanalyticsdb"

dbuser = dbutils.secrets.get(scope="socialAnalyticScope", key="dbusername")
dbpass = dbutils.secrets.get(scope="socialAnalyticScope", key="dbpassword")

connectionProperties = {"user" : dbuser, "password" : dbpass}

jdbcUrl = "jdbc:sqlserver://{0}:{1};database={2}".format(jdbcHostname, jdbcPort, jdbcDatabase)

# COMMAND ----------

df = spark.createDataFrame(stockCountDesc)
redditData = DataFrameWriter(df)
redditData.jdbc(url=jdbcUrl, table="redditPostCount", mode ="append", properties = connectionProperties)

# COMMAND ----------

redditSql = spark.read.jdbc(url=jdbcUrl, table='redditPostCount', properties=connectionProperties)
redditSql_df = redditSql.select("*").toPandas()
redditSql_df.head()

# COMMAND ----------

# MAGIC %md
# MAGIC #### Stock sentiment analysis 
# MAGIC * Use finviz.com news feed
# MAGIC * Use Vader lexicon and SentimentIntensityAnalyzer for sentiment analysis 

# COMMAND ----------

from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import os
import pandas as pd
import matplotlib.pyplot as plt
%matplotlib inline
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from urllib.error import HTTPError

finwiz_url = 'https://finviz.com/quote.ashx?t='
nltk.downloader.download('vader_lexicon')

# COMMAND ----------

import urllib.request
from urllib.error import HTTPError

stockListSql = list(redditSql_df['Symbol'].unique())

news_tables = {}
tickers = stockListSql

for ticker in tickers:
    url = finwiz_url + ticker
    req = Request(url=url,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}) 
    try:
      response = urlopen(req)
    except urllib.error.HTTPError as err:
      continue
      
    html = BeautifulSoup(response)
    news_table = html.find(id='news-table')
    news_tables[ticker] = news_table

# COMMAND ----------

news_tables_clean = {k: v for k, v in news_tables.items() if v}

# COMMAND ----------

parsed_news = []

for file_name, news_table in news_tables_clean.items():
    for x in news_table.findAll('tr'):
      try:
        text = x.a.get_text() 
        date_scrape = x.td.text.split()
      except:
        continue 

      if len(date_scrape) == 1:
          time = date_scrape[0] 
      else:
          date = date_scrape[0]
          time = date_scrape[1]
          
      ticker = file_name.split('_')[0]

      parsed_news.append([ticker, date, time, text])

# COMMAND ----------

# Initiate the sentiment intensity analyzer
vader = SentimentIntensityAnalyzer()

# Set column names
columns = ['ticker', 'newsdate', 'time', 'headline']

# Convert the parsed_news list into a DataFrame called 'parsed_and_scored_news'
parsed_and_scored_news = pd.DataFrame(parsed_news, columns=columns)
#parsed_and_scored_news 

# Iterate through the headlines and get the polarity scores using vader
scores = parsed_and_scored_news['headline'].apply(vader.polarity_scores).tolist()

# Convert the 'scores' list of dicts into a DataFrame
scores_df = pd.DataFrame(scores)

# Join the DataFrames of the news and the list of dicts
parsed_and_scored_news = parsed_and_scored_news.join(scores_df['compound'], rsuffix='_right')

# # Convert the date column from string to datetime
parsed_and_scored_news['newsdate'] = pd.to_datetime(parsed_and_scored_news.newsdate) 

# # Group scores by date
parsed_news_group = parsed_and_scored_news.groupby(['ticker', 'newsdate'])['compound'].mean().reset_index()

# COMMAND ----------

# MAGIC %md
# MAGIC Load data to Azure SQL table 

# COMMAND ----------

df = spark.createDataFrame(parsed_news_group)
newsData = DataFrameWriter(df)
newsData.jdbc(url=jdbcUrl, table="sentimentStock", mode ="overwrite", properties = connectionProperties)

# COMMAND ----------

stockSentiment = spark.read.jdbc(url=jdbcUrl, table='sentimentStock', properties=connectionProperties)
stockSentiment_df = stockSentiment.select("*").toPandas()
stockSentiment_df.head()

# COMMAND ----------


