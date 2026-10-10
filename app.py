import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import random
import time
from datetime import datetime

st.set_page_config(page_title='ALPHA FUTURES V2.2 AGRESSIVO', layout='wide')
st.title('ALPHA FUTURES V2.2 - MODO AGRESSIVO')
st.caption('Score baixo = mais sinais - 15m scalp - 5x 10x 25x 50x')

MOEDAS_FIXAS=['BTCUSDT','ETHUSDT','ADAUSDT','BNBUSDT','PEPEUSDT','DOGEUSDT','LINKUSDT']
POOL=['SOLUSDT','XRPUSDT','SHIBUSDT','AVAXUSDT','DOTUSDT','MATICUSDT','LTCUSDT','TRXUSDT','UNIUSDT','FLOKIUSDT','BONKUSDT','WIFUSDT']
random.seed(42)
extras=random.sample(POOL,5)
LISTA=MOEDAS_FIXAS+extras
ALAV=[5,10,25,50]

def calc_rsi(s,p=14):
    d=s.diff()
    g=d.where(d>0,0).rolling(p).mean()
    l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l
    r=100-(100/(1+rs))
    return r

def calc_ema(s,p):
    return s.ewm(span=p,adjust=False).mean()

def calc_atr(df,p=14):
    hl=df['high']-df
