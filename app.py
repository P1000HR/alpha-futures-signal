import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import random
import time
from datetime import datetime

st.set_page_config(page_title='ALPHA FUTURES V2.3 TURBO', layout='wide')
st.title('ALPHA FUTURES V2.3 - TURBO AGRESSIVO')
st.caption('Carrega em 5s - cache 60s - nao trava mais')

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
    hl=df['high']-df['low']
    hc=abs(df['high']-df['close'].shift())
    lc=abs(df['low']-df['close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calc_macd(s):
    ema12=calc_ema(s,12)
    ema26=calc_ema(s,26)
    macd=ema12-ema26
    signal=calc_ema(macd,9)
    return macd,signal

@st.cache_data(ttl=60)
def get_futures_candle(symbol,interval,limit=50):
    try:
        url='https://fapi.binance.com/fapi/v1/klines?symbol='+symbol+'&interval='+interval+'&limit='+str(limit)
        r=requests.get(url,timeout=5).json()
        if not isinstance(r,list) or len(r)==0:
            return None
        cols=['time','open','high','low','close','vol','ct','qav','trades','tbav','tqav','ign']
        df=pd.DataFrame(r,columns=cols)
        for c in ['open','high','low','close','vol']:
            df[c]=df[c].astype(float)
        df['time']=pd.to_datetime(df['time'],unit='ms')
        return df
    except:
        return None

@st.cache_data(ttl=120)
def get_funding(symbol):
    try:
        url='https://fapi.binance.com/fapi/v1/premiumIndex?symbol='+symbol
        r=requests.get(url,timeout=3).json()
        f=float(r['lastFundingRate'])*100
        return f
    except:
        return 0.0

def gera_sinal_agressivo(df,symbol):
    if df is None or len(df)<30:
        return 'SEM DADOS',0,{'price':0,'rsi':50,'motivos':['API Binance lenta'],'atr':0,'funding':0}
    close=df['close']
    df['EMA9']=calc_ema(close,9)
    df['EMA21']=calc_ema(close,21)
    df['EMA50']=calc_ema(close,50)
    df['RSI']=calc_rsi(close,14)
    df['ATR']=calc_atr(df,14)
    macd,sig=calc_macd(close)
    df['MACD']=macd
    df['MACD_SIG']=sig
    df['VOL_MA']=df['vol'].rolling(20).mean()
    last=df.iloc[-1]
    prev=df.iloc[-2]
    score=0
    motivos=[]
    if last['EMA9']>last['EMA21']:
        score=score+20
        motivos.append('EMA9>21')
        if prev['EMA9']<=prev['EMA21']:
            score=score+15
            motivos.append('CRUZOU ALTA')
    else:
        score=score-20
        motivos.append('EMA9<21')
        if prev['EMA9']>=prev['EMA21']:
            score=score-15
            motivos.append('CRUZOU BAIXA')
    rsi=last['RSI']
    if rsi<35:
        score=score+20
        motivos.append('RSI '+str(int(rsi))+' fundo')
    elif rsi<45:
        score=score+10
        motivos.append('RSI baixo '+str(int(rsi)))
    elif rsi>65:
        score=score-20
        motivos.append('RSI topo '+str(int(rsi)))
    elif rsi>55:
        score=score-10
        motivos.append('RSI alto '+str(int(rsi)))
    else:
        motivos.append('RSI neutro '+str(int(rsi)))
    if last['MACD']>last['MACD_SIG']:
        score=score+15
        motivos.append('MACD alta')
    else:
        score=score-15
        motivos.append('MACD baixa')
    if last['vol']>last['VOL_MA']*1.2:
        score=score+10
        motivos.append('Vol alta')
    funding=get_funding(symbol)
    if funding<-0.02:
        score=score+10
        motivos.append('Fund neg')
    if last['close']>last['EMA50']:
        score=score+10
        motivos.append('>EMA50')
    else:
        score=score-10
        motivos.append('<EMA50')
    if score>=55:
        sinal='LONG FORTE'
    elif score>=25:
        sinal='LONG FRACO'
    elif score<=-55:
        sinal='SHORT FORTE'
    elif score<=-25:
        sinal='SHORT FRACO'
    else:
        sinal='HOLD'
    info={}
    info['rsi']=rsi
    info['motivos']=motivos
    info['price']=last['close']
    info['atr']=last['ATR']
    info['funding']=funding
    return sinal,score,info

with st.sidebar:
    st.header('V2.3 TURBO')
    tf_sel=st.selectbox('Tempo', ['15m','4h','1d'], index=0)
    lev_sel=st.selectbox('Alavancagem', ALAV, index=0)
    min_score=st.slider('Score minimo', 0, 60, 20)
    auto_refresh=st.checkbox('Auto 60s', True)
    st.write('Moedas: '+', '.join(LISTA))
    if st.button('Limpar cache'):
        st.cache_data.clear()

st.subheader('Buscando 12 moedas Binance Futures...')

progress=st.progress(0)
status=st.empty()

resultados=[]
for i,sym in enumerate(LISTA):
    status.text('Buscando '+sym
