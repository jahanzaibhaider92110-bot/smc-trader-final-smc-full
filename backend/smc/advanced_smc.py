import pandas as pd
def detect_order_blocks(df, lookback=40):
    obs = []
    for i in range(2, min(len(df), lookback)):
        cur = df.iloc[-i]
        body = abs(cur['close'] - cur['open'])
        rng = cur['high'] - cur['low'] if cur['high']!=cur['low'] else 1e-9
        if body > 0.6 * rng and body > 0.0015 * cur['close']:
            if cur['close'] < cur['open']:
                obs.append({'type':'bearish','high':float(cur['high']),'low':float(cur['low']),'index':len(df)-i-1})
            else:
                obs.append({'type':'bullish','high':float(cur['high']),'low':float(cur['low']),'index':len(df)-i-1})
    return obs
def detect_fvg(df):
    fvg = []
    for i in range(2, len(df)):
        a = df.iloc[i-2]
        c = df.iloc[i]
        if c['low'] > a['high']:
            fvg.append({'type':'bullish','from':float(a['high']),'to':float(c['low']),'index':i})
        if c['high'] < a['low']:
            fvg.append({'type':'bearish','from':float(c['high']),'to':float(a['low']),'index':i})
    return fvg
def detect_bos(df):
    # simple BOS: last close breaks previous swing high/low
    if len(df) < 6:
        return None
    highs = df['high'].rolling(3).max().shift(1)
    lows = df['low'].rolling(3).min().shift(1)
    last = df.iloc[-1]
    prev_high = highs.iloc[-1]
    prev_low = lows.iloc[-1]
    if pd.isna(prev_high) or pd.isna(prev_low):
        return None
    if last['close'] > prev_high:
        return {'type':'bullish_bos','price':float(last['close'])}
    if last['close'] < prev_low:
        return {'type':'bearish_bos','price':float(last['close'])}
    return None
def evaluate_smc(df):
    signals = []
    obs = detect_order_blocks(df)
    fvg = detect_fvg(df)
    bos = detect_bos(df)
    last = df.iloc[-1]
    # Prioritize BOS with OB/FVG confluence
    if bos and obs:
        for ob in obs:
            if ob['type']=='bullish' and last['low']>=ob['low'] and last['low']<=ob['high']:
                entry = float(last['close'])
                sl = ob['low'] - 0.5*(ob['high']-ob['low'])
                tp1 = entry + (entry - sl)
                tp2 = entry + (entry - sl)*2
                tp3 = entry + (entry - sl)*3
                signals.append({'symbol':df.attrs.get('symbol','BTC/USDT'),'timeframe':df.attrs.get('timeframe','1m'),'side':'buy','entry':entry,'stop_loss':sl,'take_profits':[tp1,tp2,tp3],'rr':round((tp2-entry)/(entry-sl) if entry-sl!=0 else 0,2),'confidence':0.68,'reason':'bullish_ob_with_bos','ob':ob,'fvg':fvg})
            if ob['type']=='bearish' and last['high']<=ob['high'] and last['high']>=ob['low']:
                entry = float(last['close'])
                sl = ob['high'] + 0.5*(ob['high']-ob['low'])
                tp1 = entry - (sl-entry)
                tp2 = entry - (sl-entry)*2
                tp3 = entry - (sl-entry)*3
                signals.append({'symbol':df.attrs.get('symbol','BTC/USDT'),'timeframe':df.attrs.get('timeframe','1m'),'side':'sell','entry':entry,'stop_loss':sl,'take_profits':[tp1,tp2,tp3],'rr':round((entry-tp2)/(sl-entry) if sl-entry!=0 else 0,2),'confidence':0.68,'reason':'bearish_ob_with_bos','ob':ob,'fvg':fvg})
    # fallback: if OBS exist without BOS, weaker signals near OB
    elif obs:
        for ob in obs:
            last = df.iloc[-1]
            if ob['type']=='bullish' and last['low']>=ob['low'] and last['low']<=ob['high']:
                entry = float(last['close']); sl = ob['low'] - 0.5*(ob['high']-ob['low'])
                tp1 = entry + (entry-sl); tp2 = entry + (entry-sl)*2; tp3 = entry + (entry-sl)*3
                signals.append({'symbol':df.attrs.get('symbol','BTC/USDT'),'timeframe':df.attrs.get('timeframe','1m'),'side':'buy','entry':entry,'stop_loss':sl,'take_profits':[tp1,tp2,tp3],'rr':round((tp2-entry)/(entry-sl) if entry-sl!=0 else 0,2),'confidence':0.53,'reason':'bullish_ob','ob':ob,'fvg':fvg})
            if ob['type']=='bearish' and last['high']<=ob['high'] and last['high']>=ob['low']:
                entry = float(last['close']); sl = ob['high'] + 0.5*(ob['high']-ob['low'])
                tp1 = entry - (sl-entry); tp2 = entry - (sl-entry)*2; tp3 = entry - (sl-entry)*3
                signals.append({'symbol':df.attrs.get('symbol','BTC/USDT'),'timeframe':df.attrs.get('timeframe','1m'),'side':'sell','entry':entry,'stop_loss':sl,'take_profits':[tp1,tp2,tp3],'rr':round((entry-tp2)/(sl-entry) if sl-entry!=0 else 0,2),'confidence':0.53,'reason':'bearish_ob','ob':ob,'fvg':fvg})
    return signals
