import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import random
import time
from datetime import datetime

st.set_page_config(page_title='ALPHA FUTURES V2.1 SEM TG', layout='wide')
st.title('ALPHA FUTURES V2.1 - ALERTA NA TELA + SOM')
st.caption('Sem Telegram - Alerta visual + sonoro + historico')

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

def get_funding(symbol):
    try:
        url='https://fapi.binance.com/fapi/v1/premiumIndex?symbol='+symbol
        r=requests.get(url,timeout=5).json()
        f=float(r['lastFundingRate'])*100
        return f
    except:
        return 0.0

def gera_sinal(df,symbol):
    if df is None or len(df)<50:
        return 'SEM DADOS',0,{}
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
    if last['EMA9']>last['EMA21'] and prev['EMA9']<=prev['EMA21']:
        score=score+25
        motivos.append('EMA 9x21 alta')
    elif last['EMA9']>last['EMA21']:
        score=score+10
    if last['EMA9']<last['EMA21'] and prev['EMA9']>=prev['EMA21']:
        score=score-25
        motivos.append('EMA 9x21 baixa')
    elif last['EMA9']<last['EMA21']:
        score=score-10
    rsi=last['RSI']
    if rsi<30:
        score=score+20
        motivos.append('RSI '+str(int(rsi))+' fundo')
    elif rsi>70:
        score=score-20
        motivos.append('RSI '+str(int(rsi))+' topo')
    if last['MACD']>last['MACD_SIG'] and prev['MACD']<=prev['MACD_SIG']:
        score=score+20
        motivos.append('MACD alta')
    elif last['MACD']<last['MACD_SIG'] and prev['MACD']>=prev['MACD_SIG']:
        score=score-20
        motivos.append('MACD baixa')
    if last['vol']>last['VOL_MA']*1.5:
        score=score+15
        motivos.append('Baleia')
    funding=get_funding(symbol)
    if funding<-0.05:
        score=score+15
        motivos.append('Fund neg '+str(round(funding,4))+'%')
    if funding>0.1:
        score=score-10
    if last['close']>last['EMA50']:
        score=score+10
    else:
        score=score-10
    if score>=75:
        sinal='LONG FORTE'
    elif score>=45:
        sinal='LONG FRACO'
    elif score<=-75:
        sinal='SHORT FORTE'
    elif score<=-45:
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
    st.header('CONFIG V2.1 SEM TG')
    tf_sel=st.selectbox('Tempo', ['15m','4h','1d'], index=1)
    lev_sel=st.selectbox('Alavancagem', ALAV, index=1)
    min_score=st.slider('Score minimo alerta', 50, 90, 75)
    auto_refresh=st.checkbox('Auto-refresh 60s', True)
    som=st.checkbox('Ativar som alerta', True)
    st.divider()
    st.write('Moedas: '+', '.join(LISTA))
    if st.button('Limpar historico'):
        st.session_state['historico']=[]

if 'historico' not in st.session_state:
    st.session_state['historico']=[]

st.subheader('SCANNER V2.1 - '+tf_sel.upper()+' - '+str(lev_sel)+'x')
resultados=[]
for sym in LISTA:
    df=get_futures_candle(sym, tf_sel, 100)
    sinal,score,info=gera_sinal(df,sym)
    resultados.append({'symbol':sym,'sinal':sinal,'score':score,'info':info,'df':df})

resultados=sorted(resultados, key=lambda x: abs(x['score']), reverse=True)

# ALERTA VISUAL + HISTORICO
alertas_agora=[]
for r in resultados:
    if abs(r['score'])>=min_score and 'FORTE' in r['sinal']:
        alertas_agora.append(r)
        # salva no historico
        ja_tem=False
        for h in st.session_state['historico']:
            if h['symbol']==r['symbol'] and h['sinal']==r['sinal']:
                ja_tem=True
        if not ja_tem:
            novo={}
            novo['hora']=datetime.now().strftime('%H:%M:%S')
            novo['symbol']=r['symbol']
            novo['sinal']=r['sinal']
            novo['score']=r['score']
            novo['price']=r['info'].get('price',0)
            st.session_state['historico'].append(novo)

if alertas_agora:
    st.balloons()
    for a in alertas_agora:
        if 'LONG' in a['sinal']:
            st.success('ALERTA: '+a['symbol']+' '+a['sinal']+' Score '+str(a['score'])+' - ENTRADA AGORA')
        else:
            st.error('ALERTA: '+a['symbol']+' '+a['sinal']+' Score '+str(a['score'])+' - ENTRADA AGORA')
    if som:
        st.components.v1.html('<audio autoplay><source src="https://www.soundjay.com/buttons/beep-07a.wav" type="audio/wav"></audio>', height=0)
else:
    st.info('Nenhum sinal FORTE agora. Monitorando...')

cols=st.columns(3)
idx=0
for res in resultados:
    sym=res['symbol']
    sinal=res['sinal']
    score=res['score']
    info=res['info']
    col=cols[idx%3]
    with col:
        price=info.get('price',0)
        atr=info.get('atr', price*0.01)
        funding=info.get('funding',0)
        rsi=info.get('rsi',50)
        if 'FORTE' in sinal:
            if 'LONG' in sinal:
                st.success(sym+' '+sinal+' '+str(score))
            else:
                st.error(sym+' '+sinal+' '+str(score))
        elif 'FRACO' in sinal:
            st.info(sym+' '+sinal+' '+str(score))
        else:
            st.write(sym+' HOLD '+str(score))
        st.write('Preco:'+str(round(price,4))+' RSI:'+str(int(rsi))+' Fund:'+str(round(funding,4))+'%')
        if 'LONG' in sinal:
            entry=price
            stop=entry-atr*1.5
            take1=entry+atr*1.5
            take2=entry+atr*3
            liq=entry*(1-0.9/float(lev_sel))
            st.write('Stop:'+str(round(stop,4))+' T1:'+str(round(take1,4))+' Liq:'+str(round(liq,4)))
        elif 'SHORT' in sinal:
            entry=price
            stop=entry+atr*1.5
            take1=entry-atr*1.5
            liq=entry*(1+0.9/float(lev_sel))
            st.write('Stop:'+str(round(stop,4))+' T1:'+str(round(take1,4))+' Liq:'+str(round(liq,4)))
        motivos=info.get('motivos',[])
        if motivos:
            st.caption(' | '.join(motivos[:2]))
    idx=idx+1

st.divider()
st.subheader('Historico de sinais de hoje')
if st.session_state['historico']:
    df_hist=pd.DataFrame(st.session_state['historico'])
    st.dataframe(df_hist, use_container_width=True)
    csv=df_hist.to_csv(index=False)
    st.download_button('Baixar historico CSV', csv, 'sinais_futures.csv', 'text/csv')
else:
    st.write('Nenhum sinal forte ainda hoje')

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

if auto_refresh:
    time.sleep(60)
    st.rerun()

st.success('V2.1 SEM TELEGRAM OK - Alerta na tela + historico')
