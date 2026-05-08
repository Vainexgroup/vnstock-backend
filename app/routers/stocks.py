"""
Stocks Router — Tất cả endpoints liên quan đến cổ phiếu cụ thể
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Literal
from datetime import datetime, timedelta

from app.services import vnstock_service as vs

router = APIRouter()


# ── Danh sách cổ phiếu ────────────────────────────────────────────
@router.get(
    "",
    summary="Danh sách cổ phiếu",
    description="Trả về danh sách cổ phiếu niêm yết, có thể lọc theo sàn."
)
def list_stocks(
    exchange: Optional[str] = Query(None, description="HOSE | HNX | UPCOM"),
):
    data = vs.get_all_symbols(exchange)
    return {"count": len(data), "data": data}


# ── Screener ──────────────────────────────────────────────────────
@router.get(
    "/screener",
    summary="Bộ lọc cổ phiếu",
    description="Lọc cổ phiếu theo các tiêu chí cơ bản."
)
def screener(
    exchange: Optional[str] = Query(None, description="HOSE | HNX"),
    sector: Optional[str] = Query(None, description="Tên ngành (tiếng Việt hoặc tiếng Anh)"),
    min_roe: Optional[float] = Query(None, description="ROE tối thiểu (%)"),
    max_pe: Optional[float] = Query(None, description="P/E tối đa"),
    max_pb: Optional[float] = Query(None, description="P/B tối đa"),
    min_volume: Optional[int] = Query(None, description="KLGD tối thiểu"),
    min_mc: Optional[float] = Query(None, description="Vốn hóa tối thiểu (tỷ VND)"),
):
    data = vs.screener(
        exchange=exchange,
        sector=sector,
        min_roe=min_roe,
        max_pe=max_pe,
        max_pb=max_pb,
        min_volume=min_volume,
        min_mc=min_mc,
    )
    return {"count": len(data), "filters_applied": {
        "exchange": exchange, "sector": sector,
        "min_roe": min_roe, "max_pe": max_pe, "max_pb": max_pb,
    }, "data": data}


# ── Lịch sử giá ───────────────────────────────────────────────────
@router.get(
    "/{symbol}/history",
    summary="Lịch sử OHLCV",
    description="""
Lấy dữ liệu nến (open/high/low/close/volume) theo symbol và khoảng thời gian.

**Ví dụ:**
- `/api/stocks/VCB/history?start=2024-01-01&end=2025-01-01`
- `/api/stocks/HPG/history?interval=1W` (nến tuần)
- `/api/stocks/FPT/history?interval=1M` (nến tháng)
    """
)
def stock_history(
    symbol: str,
    start: Optional[str] = Query(None, description="YYYY-MM-DD, mặc định 1 năm trước"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD, mặc định hôm nay"),
    interval: Literal["1D", "1W", "1M", "15", "30", "60"] = Query("1D", description="Khung thời gian"),
):
    symbol = symbol.upper()
    data = vs.get_history(symbol, start, end, interval)
    if not data:
        raise HTTPException(status_code=404, detail=f"Không có dữ liệu cho {symbol}")
    return {
        "symbol": symbol,
        "interval": interval,
        "count": len(data),
        "from": data[0]["date"] if data else None,
        "to":   data[-1]["date"] if data else None,
        "data": data,
    }


# ── Giá realtime ──────────────────────────────────────────────────
@router.get(
    "/{symbol}/price",
    summary="Giá realtime",
    description="Lấy giá mới nhất và KLGD tổng phiên."
)
def stock_price(symbol: str):
    result = vs.get_realtime_price(symbol.upper())
    if result.get("price") is None:
        raise HTTPException(status_code=503, detail=result.get("error", "Không lấy được giá"))
    return result


# ── Intraday ticks ────────────────────────────────────────────────
@router.get(
    "/{symbol}/intraday",
    summary="Tick data trong phiên",
    description="Lấy dữ liệu khớp lệnh trong phiên giao dịch hôm nay."
)
def stock_intraday(
    symbol: str,
    page_size: int = Query(100, ge=10, le=1000),
):
    data = vs.get_intraday_ticks(symbol.upper(), page_size)
    return {"symbol": symbol.upper(), "count": len(data), "data": data}


# ── Thông tin công ty ─────────────────────────────────────────────
@router.get(
    "/{symbol}/info",
    summary="Thông tin công ty",
    description="Tổng quan công ty: tên, ngành, sàn niêm yết, vốn điều lệ..."
)
def stock_info(symbol: str):
    result = vs.get_company_info(symbol.upper())
    return result


# ── Chỉ số tài chính ──────────────────────────────────────────────
@router.get(
    "/{symbol}/ratios",
    summary="Chỉ số định giá",
    description="P/E, P/B, EPS, ROE, ROA, Debt/Equity và các chỉ số tài chính khác."
)
def stock_ratios(symbol: str):
    return vs.get_ratios(symbol.upper())


# ── Báo cáo tài chính ─────────────────────────────────────────────
@router.get(
    "/{symbol}/financials",
    summary="Báo cáo tài chính",
    description="Kết quả kinh doanh, bảng cân đối kế toán, lưu chuyển tiền tệ."
)
def stock_financials(
    symbol: str,
    report_type: Literal["IncomeStatement", "BalanceSheet", "CashFlow"] = Query(
        "IncomeStatement",
        description="Loại báo cáo tài chính"
    ),
    period: Literal["quarterly", "yearly"] = Query("quarterly", description="Chu kỳ báo cáo"),
):
    data = vs.get_financials(symbol.upper(), report_type, period)
    return {
        "symbol": symbol.upper(),
        "report_type": report_type,
        "period": period,
        "count": len(data),
        "data": data,
    }
