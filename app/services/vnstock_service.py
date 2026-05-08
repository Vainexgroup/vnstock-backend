"""
VNStock Service — Wrapper cho vnstock3 với:
  - In-memory cache (TTL)
  - Dual-source fallback (VCI → TCBS)
  - Mock data khi tất cả API lỗi (môi trường dev)
"""
import time
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════
# CACHE
# ════════════════════════════════════════════════
_cache: Dict[str, tuple] = {}

def _get(key: str, ttl: int) -> Optional[Any]:
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None

def _set(key: str, data: Any):
    _cache[key] = (data, time.time())

def cache_clear():
    _cache.clear()
    logger.info("Cache cleared")


# ════════════════════════════════════════════════
# LỊCH SỬ GIÁ
# ════════════════════════════════════════════════
def get_history(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1D",
) -> List[Dict]:
    """
    Lấy OHLCV lịch sử.
    interval: "1D" | "1W" | "1M" | "15" | "30" | "60" (phút)
    """
    today = datetime.today()
    if not end:
        end = today.strftime("%Y-%m-%d")
    if not start:
        days = {"1D": 365, "1W": 730, "1M": 1825}.get(interval, 365)
        start = (today - timedelta(days=days)).strftime("%Y-%m-%d")

    key = f"hist:{symbol}:{start}:{end}:{interval}"
    cached = _get(key, settings.CACHE_TTL_HISTORY)
    if cached is not None:
        logger.debug(f"Cache HIT: {key}")
        return cached

    # ── Thử vnstock3 VCI ───────────────────────────────────────
    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.quote.history(start=start, end=end, interval=interval)
        if df is not None and not df.empty:
            result = _normalize_history(df)
            _set(key, result)
            logger.info(f"vnstock3/VCI OK: {symbol} {len(result)} candles")
            return result
    except Exception as e:
        logger.warning(f"vnstock3/VCI thất bại {symbol}: {e}")

    # ── Thử vnstock3 TCBS ──────────────────────────────────────
    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="TCBS")
        df = stock.quote.history(start=start, end=end, interval=interval)
        if df is not None and not df.empty:
            result = _normalize_history(df)
            _set(key, result)
            logger.info(f"vnstock3/TCBS OK: {symbol} {len(result)} candles")
            return result
    except Exception as e:
        logger.warning(f"vnstock3/TCBS thất bại {symbol}: {e}")

    # ── Fallback vnstock (legacy) ──────────────────────────────
    try:
        from vnstock import stock_historical_data
        df = stock_historical_data(symbol=symbol, start_date=start, end_date=end)
        if df is not None and not df.empty:
            result = _normalize_history_legacy(df)
            _set(key, result)
            logger.info(f"vnstock/legacy OK: {symbol} {len(result)} candles")
            return result
    except Exception as e:
        logger.warning(f"vnstock/legacy thất bại {symbol}: {e}")

    # ── Mock data (development fallback) ──────────────────────
    logger.error(f"Tất cả nguồn thất bại cho {symbol} — dùng mock data")
    result = _mock_history(symbol, start, end)
    _set(key, result)
    return result


def _normalize_history(df) -> List[Dict]:
    """Chuẩn hóa DataFrame từ vnstock3"""
    import pandas as pd
    cols = {
        "time": "date", "open": "open", "high": "high",
        "low": "low", "close": "close", "volume": "volume"
    }
    df = df.rename(columns={k: v for k, v in cols.items() if k in df.columns})
    records = []
    for _, row in df.iterrows():
        date_val = row.get("date") or row.get("time") or row.name
        if hasattr(date_val, "strftime"):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val)[:10]
        records.append({
            "date":   date_str,
            "open":   _safe_float(row.get("open")),
            "high":   _safe_float(row.get("high")),
            "low":    _safe_float(row.get("low")),
            "close":  _safe_float(row.get("close")),
            "volume": _safe_int(row.get("volume")),
        })
    return records


def _normalize_history_legacy(df) -> List[Dict]:
    """Chuẩn hóa DataFrame từ vnstock legacy"""
    records = []
    for _, row in df.iterrows():
        date_val = row.get("tradingDate") or row.get("date")
        if hasattr(date_val, "strftime"):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val)[:10]
        records.append({
            "date":   date_str,
            "open":   _safe_float(row.get("open")),
            "high":   _safe_float(row.get("high")),
            "low":    _safe_float(row.get("low")),
            "close":  _safe_float(row.get("close")),
            "volume": _safe_int(row.get("volume")),
        })
    return records


# ════════════════════════════════════════════════
# GIÁ REAL-TIME / INTRADAY
# ════════════════════════════════════════════════
def get_realtime_price(symbol: str) -> Dict:
    """Giá realtime + KLGD phiên hiện tại"""
    key = f"rt:{symbol}"
    cached = _get(key, settings.CACHE_TTL_PRICE)
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.quote.intraday(symbol=symbol, page_size=1, investor_condition=None)
        if df is not None and not df.empty:
            row = df.iloc[-1]
            result = {
                "symbol": symbol,
                "price":  _safe_float(row.get("price", 0)),
                "volume": _safe_int(row.get("volume", 0)),
                "time":   str(row.get("time", "")),
                "source": "VCI/intraday",
            }
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"Intraday thất bại {symbol}: {e}")

    # Fallback: dùng close ngày hôm nay
    today = datetime.today().strftime("%Y-%m-%d")
    hist = get_history(symbol, today, today, "1D")
    if hist:
        last = hist[-1]
        result = {
            "symbol": symbol,
            "price":  last["close"],
            "volume": last["volume"],
            "time":   today,
            "source": "history/eod",
        }
        _set(key, result)
        return result

    return {"symbol": symbol, "price": None, "error": "Không lấy được giá"}


def get_intraday_ticks(symbol: str, page_size: int = 100) -> List[Dict]:
    """Tick data trong phiên hôm nay"""
    key = f"ticks:{symbol}:{page_size}"
    cached = _get(key, 30)  # Cache 30s vì dữ liệu thay đổi liên tục
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.quote.intraday(symbol=symbol, page_size=page_size, investor_condition=None)
        if df is not None and not df.empty:
            records = []
            for _, row in df.iterrows():
                records.append({
                    "time":   str(row.get("time", "")),
                    "price":  _safe_float(row.get("price", 0)),
                    "volume": _safe_int(row.get("volume", 0)),
                    "type":   str(row.get("match_type", "")),
                })
            _set(key, records)
            return records
    except Exception as e:
        logger.warning(f"Ticks thất bại {symbol}: {e}")
    return []


# ════════════════════════════════════════════════
# THÔNG TIN CÔNG TY
# ════════════════════════════════════════════════
def get_company_info(symbol: str) -> Dict:
    """Tổng quan công ty"""
    key = f"info:{symbol}"
    cached = _get(key, settings.CACHE_TTL_INFO)
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        overview = stock.company.overview()
        if overview is not None and not overview.empty:
            result = overview.iloc[0].to_dict()
            result["symbol"] = symbol
            result = {k: _json_safe(v) for k, v in result.items()}
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"Company overview thất bại {symbol}: {e}")
    return {"symbol": symbol, "error": "Không lấy được thông tin công ty"}


def get_financials(symbol: str, report_type: str = "IncomeStatement", period: str = "quarterly") -> List[Dict]:
    """
    Báo cáo tài chính.
    report_type: "IncomeStatement" | "BalanceSheet" | "CashFlow"
    period: "quarterly" | "yearly"
    """
    key = f"fin:{symbol}:{report_type}:{period}"
    cached = _get(key, settings.CACHE_TTL_INFO)
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        if report_type == "IncomeStatement":
            df = stock.finance.income_statement(period=period, lang="vi")
        elif report_type == "BalanceSheet":
            df = stock.finance.balance_sheet(period=period, lang="vi")
        else:
            df = stock.finance.cash_flow(period=period, lang="vi")

        if df is not None and not df.empty:
            result = [{k: _json_safe(v) for k, v in row.items()} for _, row in df.iterrows()]
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"Financials thất bại {symbol}: {e}")
    return []


def get_ratios(symbol: str) -> Dict:
    """Chỉ số tài chính: P/E, P/B, ROE, ROA, EPS..."""
    key = f"ratio:{symbol}"
    cached = _get(key, settings.CACHE_TTL_INFO)
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.finance.ratio(period="quarterly", lang="vi", dropna=True)
        if df is not None and not df.empty:
            latest = df.iloc[0]
            result = {k: _json_safe(v) for k, v in latest.items()}
            result["symbol"] = symbol
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"Ratios thất bại {symbol}: {e}")
    return {"symbol": symbol}


# ════════════════════════════════════════════════
# THỊ TRƯỜNG
# ════════════════════════════════════════════════
def get_market_indices() -> Dict:
    """VN-Index, HNX-Index, UPCOM-Index"""
    key = "market:indices"
    cached = _get(key, settings.CACHE_TTL_MARKET)
    if cached is not None:
        return cached

    result = {}
    index_map = {
        "vnindex":  "VNINDEX",
        "hnxindex": "HNX-INDEX",
        "upcom":    "UPCOM-INDEX",
    }

    today = datetime.today()
    start = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    for key_name, sym in index_map.items():
        try:
            hist = get_history(sym, start, end, "1D")
            if len(hist) >= 2:
                latest = hist[-1]
                prev = hist[-2]
                chg = latest["close"] - prev["close"]
                pct = chg / prev["close"] * 100 if prev["close"] else 0
                result[key_name] = {
                    "symbol": sym,
                    "value": round(latest["close"], 2),
                    "change": round(chg, 2),
                    "pct_change": round(pct, 2),
                    "open": latest["open"],
                    "high": latest["high"],
                    "low": latest["low"],
                    "volume": latest["volume"],
                    "date": latest["date"],
                }
            elif len(hist) == 1:
                result[key_name] = {"symbol": sym, "value": hist[0]["close"], "date": hist[0]["date"]}
        except Exception as e:
            logger.warning(f"Index {sym}: {e}")

    if not result:
        # Mock fallback
        result = {
            "vnindex":  {"symbol": "VNINDEX", "value": 1287.45, "change": 12.3, "pct_change": 0.96},
            "hnxindex": {"symbol": "HNX-INDEX", "value": 224.18, "change": -1.2, "pct_change": -0.53},
            "upcom":    {"symbol": "UPCOM-INDEX", "value": 91.34, "change": 0.3, "pct_change": 0.33},
        }

    _set("market:indices", result)
    return result


def get_top_movers(exchange: str = "HOSE", top: int = 10) -> Dict:
    """Top tăng/giảm mạnh nhất theo sàn"""
    key = f"movers:{exchange}:{top}"
    cached = _get(key, 120)
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        vn = Vnstock()
        # Lấy danh sách cổ phiếu sàn
        listing = vn.stock(symbol="ACB", source="VCI").listing.symbols_by_exchange()
        if listing is not None and not listing.empty:
            exch_stocks = listing[listing["exchange"].str.upper() == exchange.upper()]
            symbols = exch_stocks["symbol"].tolist()[:50]  # Giới hạn 50 để tránh quá tải

            # Lấy giá hôm nay
            today = datetime.today().strftime("%Y-%m-%d")
            yesterday = (datetime.today() - timedelta(days=3)).strftime("%Y-%m-%d")

            gainers, losers = [], []
            for sym in symbols[:20]:  # Sample 20 stocks
                try:
                    hist = get_history(sym, yesterday, today, "1D")
                    if len(hist) >= 2:
                        latest, prev = hist[-1], hist[-2]
                        pct = (latest["close"] - prev["close"]) / prev["close"] * 100
                        item = {
                            "symbol": sym, "price": latest["close"],
                            "change_pct": round(pct, 2),
                            "volume": latest["volume"],
                        }
                        if pct > 0:
                            gainers.append(item)
                        else:
                            losers.append(item)
                except Exception:
                    pass

            gainers.sort(key=lambda x: x["change_pct"], reverse=True)
            losers.sort(key=lambda x: x["change_pct"])
            result = {
                "exchange": exchange,
                "gainers": gainers[:top],
                "losers": losers[:top],
            }
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"Top movers thất bại: {e}")
    return {"exchange": exchange, "gainers": [], "losers": []}


def get_all_symbols(exchange: Optional[str] = None) -> List[Dict]:
    """Danh sách tất cả cổ phiếu"""
    key = f"symbols:{exchange or 'all'}"
    cached = _get(key, 3600)  # Cache 1 giờ
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        vn = Vnstock()
        df = vn.stock(symbol="ACB", source="VCI").listing.all_symbols()
        if df is not None and not df.empty:
            if exchange:
                df = df[df["exchange"].str.upper() == exchange.upper()]
            result = [{k: _json_safe(v) for k, v in row.items()} for _, row in df.iterrows()]
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"All symbols thất bại: {e}")
    return []


def screener(
    exchange: Optional[str] = None,
    sector: Optional[str] = None,
    min_roe: Optional[float] = None,
    max_pe: Optional[float] = None,
    max_pb: Optional[float] = None,
    min_volume: Optional[int] = None,
    min_mc: Optional[float] = None,
) -> List[Dict]:
    """Lọc cổ phiếu theo tiêu chí tài chính"""
    key = f"screener:{exchange}:{sector}:{min_roe}:{max_pe}:{max_pb}:{min_volume}:{min_mc}"
    cached = _get(key, 300)
    if cached is not None:
        return cached

    try:
        from vnstock3 import Vnstock
        vn = Vnstock()
        df = vn.stock(symbol="ACB", source="VCI").listing.symbols_by_industries()
        if df is not None and not df.empty:
            if exchange:
                df = df[df.get("exchange", "").str.upper() == exchange.upper()]
            if sector:
                mask = df.apply(
                    lambda r: sector.lower() in str(r.get("icbName3", "")).lower()
                              or sector.lower() in str(r.get("icbName2", "")).lower(),
                    axis=1
                )
                df = df[mask]
            result = [{k: _json_safe(v) for k, v in row.items()} for _, row in df.iterrows()]
            _set(key, result)
            return result
    except Exception as e:
        logger.warning(f"Screener thất bại: {e}")
    return []


# ════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════
def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def _json_safe(v):
    """Chuyển về type JSON-serializable"""
    import pandas as pd
    import numpy as np
    if pd.isna(v) if hasattr(pd, 'isna') else False:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    return v

def _mock_history(symbol: str, start: str, end: str) -> List[Dict]:
    """Mock OHLCV khi tất cả API thất bại (chỉ dùng trong dev)"""
    PRICES = {
        "VCB": 87500, "BID": 47800, "CTG": 37200, "TCB": 52300, "ACB": 24800,
        "VNM": 71200, "HPG": 26500, "FPT": 138000, "MWG": 64300, "GAS": 78500,
        "VIC": 42300, "VHM": 38700, "DGC": 72800, "PNJ": 82500, "MSN": 68400,
        "VNINDEX": 128745, "HNX-INDEX": 22418,
    }
    base = PRICES.get(symbol.upper(), 50000)
    start_dt = datetime.strptime(start[:10], "%Y-%m-%d")
    end_dt = datetime.strptime(end[:10], "%Y-%m-%d")
    p = base * 0.85
    records = []
    d = start_dt
    while d <= end_dt:
        if d.weekday() < 5:
            p = p * (1 + random.gauss(0.0003, 0.015))
            p = max(p, base * 0.5)
            c = round(p)
            records.append({
                "date":   d.strftime("%Y-%m-%d"),
                "open":   round(c * random.uniform(0.985, 1.01)),
                "high":   round(c * random.uniform(1.005, 1.025)),
                "low":    round(c * random.uniform(0.975, 0.995)),
                "close":  c,
                "volume": random.randint(500_000, 15_000_000),
            })
        d += timedelta(days=1)
    return records
