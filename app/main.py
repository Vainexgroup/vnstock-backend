from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import anthropic
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    symbol: str


@app.get("/")
def root():
    return {"service": "VNStockAI API", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    symbol = request.symbol.upper()

    # ── 1. LẤY DỮ LIỆU VNSTOCK ─────────────────────────────────────
    real_stats = {}
    history = []
    real_info = f"Ma: {symbol}"

    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source='VCI')

        # Lich su gia 3 thang
        end_date   = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')

        try:
            price_df = stock.quote.history(start=start_date, end=end_date, interval='1D')
            if price_df is not None and not price_df.empty:
                price_df.columns = [c.lower() for c in price_df.columns]
                date_col  = next((c for c in ['time','date','tradingdate']  if c in price_df.columns), None)
                close_col = next((c for c in ['close','closeprice']         if c in price_df.columns), None)
                vol_col   = next((c for c in ['volume','totalvolume']       if c in price_df.columns), None)
                open_col  = next((c for c in ['open','openprice']           if c in price_df.columns), None)
                high_col  = next((c for c in ['high','highprice']           if c in price_df.columns), None)
                low_col   = next((c for c in ['low','lowprice']             if c in price_df.columns), None)

                if close_col:
                    for _, row in price_df.iterrows():
                        date_val = str(row[date_col])[:10] if date_col else ''
                        def safe_float(col):
                            try: return round(float(row[col]), 2) if col and row[col] else None
                            except: return None
                        history.append({
                            "date":   date_val,
                            "open":   safe_float(open_col),
                            "high":   safe_float(high_col),
                            "low":    safe_float(low_col),
                            "close":  safe_float(close_col),
                            "volume": int(row[vol_col]) if vol_col and row[vol_col] else None,
                        })
                    latest = history[-1]['close'] if history else 'N/A'
                    real_info += f", Gia: {latest}"
        except Exception as e:
            real_info += f" (lich su: {str(e)[:40]})"

        # Chi so tai chinh
        try:
            ratio_df = stock.finance.ratio(period='quarter', lang='vi', dropna=True)
            if ratio_df is not None and not ratio_df.empty:
                raw = {str(k): v for k, v in ratio_df.iloc[0].items()}

                def get_ratio(*keys):
                    for k in keys:
                        for rk, rv in raw.items():
                            if k.lower() in rk.lower():
                                try:
                                    v = float(rv)
                                    return round(v, 2) if v else None
                                except: pass
                    return None

                real_stats = {
                    "pe":  get_ratio("P/E","pe"),
                    "pb":  get_ratio("P/B","pb"),
                    "roe": get_ratio("ROE"),
                    "roa": get_ratio("ROA"),
                    "eps": get_ratio("EPS"),
                    "mc":  get_ratio("von hoa","marketCap","market_cap"),
                }
                real_stats = {k: v for k, v in real_stats.items() if v is not None}
                real_info += f", P/E:{real_stats.get('pe')}, ROE:{real_stats.get('roe')}%"
        except Exception as e:
            real_info += f" (tc:{str(e)[:30]})"

    except Exception as e:
        real_info += f" (vnstock:{str(e)[:50]})"

    # ── 2. GOI CLAUDE AI ────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    analysis_text = ""

    if api_key:
        system_prompt = (
            "Ban la chuyen gia phan tich chung khoan Viet Nam 15 nam kinh nghiem. "
            "Phan tich ngan gon, suc tich, co so lieu cu the. "
            "Dung bullet points voi emoji. Khoang 200 tu. "
            "Ket thuc bang: Khuyen nghi: MUA / GIU / BAN + Gia muc tieu + Stop loss. "
            "Viet bang tieng Viet."
        )
        models = ["claude-haiku-4-5-20251001", "claude-sonnet-4-20250514"]
        for model_name in models:
            try:
                client = anthropic.Anthropic(api_key=api_key)
                msg = client.messages.create(
                    model=model_name,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role":"user","content":f"Phan tich co phieu {symbol}: {real_info}"}]
                )
                analysis_text = msg.content[0].text
                break
            except Exception as e:
                analysis_text = f"Loi Claude: {str(e)[:100]}"
    else:
        analysis_text = "Chua cau hinh ANTHROPIC_API_KEY tren Railway Variables."

    # ── 3. TRA VE DAY DU ────────────────────────────────────────────
    return {
        "analysis":    analysis_text,
        "real_stats":  real_stats,
        "history":     history,
        "symbol":      symbol,
        "data_points": len(history),
    }
