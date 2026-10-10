import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import random

st.set_page_config(page_title='ALPHA FUTURES GOD', layout='wide')
st.title('ALPHA FUTURES GOD - SINAIS BINANCE')
st.caption('V1 Scanner 15m 4h 1D - 5x 10x 25x 50x')

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

def calc_macd(s):
    ema12=calc_ema(s,12)
    ema26=calc_ema(s,26)
    macd=ema12-ema26
    signal=calc_ema(macd,9)
    return macd,signal

def get_futures_candle(symbol,interval,limit=100):
    try:
        url='https://fapi.binance.com/fapi/v1/klines?symbol='+symbol+'&interval='+interval+'&limit='+str(limit)
        r=requests.get(url,timeout=8).json()
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

def gera_sinal(df):
    if df is None or len(df)<50:
        return 'SEM DADOS',0,{}
    close=df['close']
    df['EMA9']=calc_ema(close,9)
    df['EMA21']=calc_ema(close,21)
    df['EMA50']=calc_ema(close,50)
    df['RSI']=calc_rsi(close,14)
    macd,sig=calc_macd(close)
    df['MACD']=macd
    df['MACD_SIG']=sig
    df['VOL_MA']=df['vol'].rolling(20).mean()
    last=df.iloc[-1]
    prev=df.iloc[-2]
    score=0
    motivos=[]
    if last['EMA9']>last['EMA21'] and prev['EMA9']<=prev['EMA21']:
        score=score+25
        motivos.append('EMA 9 cruzou 21 alta')
    elif last['EMA9']>last['EMA21']:
        score=score+10
        motivos.append('EMA 9 acima 21')
    if last['EMA9']<last['EMA21'] and prev['EMA9']>=prev['EMA21']:
        score=score-25
        motivos.append('EMA 9 cruzou 21 baixa')
    elif last['EMA9']<last['EMA21']:
        score=score-10
        motivos.append('EMA 9 abaixo 21')
    rsi=last['RSI']
    if rsi<30:
        score=score+20
        motivos.append('RSI sobrevendido '+str(int(rsi)))
    elif rsi>70:
        score=score-20
        motivos.append('RSI sobrecomprado '+str(int(rsi)))
    if last['MACD']>last['MACD_SIG'] and prev['MACD']<=prev['MACD_SIG']:
        score=score+20
        motivos.append('MACD cruzou alta')
    elif last['MACD']<last['MACD_SIG'] and prev['MACD']>=prev['MACD_SIG']:
        score=score-20
        motivos.append('MACD cruzou baixa')
    if last['vol']>last['VOL_MA']*1.5:
        score=score+15
        motivos.append('Volume baleia')
    if last['close']>last['EMA50']:
        score=score+10
        motivos.append('Acima EMA50')
    else:
        score=score-10
        motivos.append('Abaixo EMA50')
    if score>=70:
        sinal='LONG FORTE'
    elif score>=40:
        sinal='LONG FRACO'
    elif score<=-70:
        sinal='SHORT FORTE'
    elif score<=-40:
        sinal='SHORT FRACO'
    else:
        sinal='HOLD'
    info={}
    info['rsi']=rsi
    info['motivos']=motivos
    info['price']=last['close']
    return sinal,score,info

with st.sidebar:
    st.header('CONFIG FUTURES')
    tf_sel=st.selectbox('Tempo', ['15m','4h','1d'], index=1)
    lev_sel=st.selectbox('Alavancagem', ALAV, index=1)
    st.write('Moedas: '+', '.join(LISTA))
    min_score=st.slider('Score minimo', 40, 90, 50)

st.subheader('SCANNER FUTURES - '+tf_sel.upper()+' - Alav '+str(lev_sel)+'x')
resultados=[]
for sym in LISTA:
    df=get_futures_candle(sym, tf_sel, 100)
    sinal,score,info=gera_sinal(df)
    resultados.append({'symbol':sym,'sinal':sinal,'score':score,'info':info,'df':df})

resultados=sorted(resultados, key=lambda x: abs(x['score']), reverse=True)
cols=st.columns(3)
idx=0
for res in resultados:
    sym=res['symbol']
    sinal=res['sinal']
    score=res['score']
    info=res['info']
    df=res['df']
    col=cols[idx%3]
    with col:
        if 'FORTE' in sinal:
            if 'LONG' in sinal:
                st.success(sym+' '+sinal+' '+str(score))
            else:
                st.error(sym+' '+sinal+' '+str(score))
        elif 'FRACO' in sinal:
            st.info(sym+' '+sinal+' '+str(score))
        else:
            st.write(sym+' HOLD '+str(score))
        if df is not None and len(df)>0:
            price=info.get('price',0)
            rsi=info.get('rsi',50)
            st.write('Preco: $'+str(round(price,4))+' RSI:'+str(int(rsi)))
            if 'LONG' in sinal:
                entry=price
                stop=entry*0.985
                take1=entry*1.015
                take2=entry*1.03
                liq=entry*(1-0.9/float(lev_sel))
                st.write('Entrada:'+str(round(entry,4))+' Stop:'+str(round(stop,4)))
                st.write('Take1:'+str(round(take1,4))+' Take2:'+str(round(take2,4)))
                st.write('Liq:'+str(round(liq,4))+' '+str(lev_sel)+'x')
            elif 'SHORT' in sinal:
                entry=price
                stop=entry*1.015
                take1=entry*0.985
                liq=entry*(1+0.9/float(lev_sel))
                st.write('Entrada:'+str(round(entry,4))+' Stop:'+str(round(stop,4)))
                st.write('Take1:'+str(round(take1,4))+' Liq:'+str(round(liq,4)))
    idx=idx+1

st.divider()
st.subheader('TOP SINAIS Score acima de '+str(min_score))
fortes=[]
for r in resultados:
    if abs(r['score'])>=min_score and 'HOLD' not in r['sinal']:
        fortes.append(r)

if fortes:
    for f in fortes:
        sym=f['symbol']
        sinal=f['sinal']
        score=f['score']
        price=f['info'].get('price',0)
        linha=sym+' | '+sinal+' | Score:'+str(score)+' | Preco:'+str(round(price,4))
        st.code(linha)
else:
    st.write('Nenhum sinal forte agora.')

if resultados:
    top=resultados[0]
    df_top=top['df']
    if df_top is not None:
        st.subheader('Grafico TOP - '+top['symbol']+' '+top['sinal'])
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=df_top['time'], open=df_top['open'], high=df_top['high'], low=df_top['low'], close=df_top['close']))
        if 'EMA9' in df_top.columns:
            fig.add_trace(go.Scatter(x=df_top['time'], y=df_top['EMA9'], name='EMA9'))
            fig.add_trace(go.Scatter(x=df_top['time'], y=df_top['EMA21'], name='EMA21'))
        fig.update_layout(height=500, template='plotly_dark', xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

st.success('ALPHA FUTURES V1 OK')