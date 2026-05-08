"""
Market Router — Chỉ số thị trường, top tăng/giảm, tổng quan phiên
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

from app.services import vnstock_service as vs

router = APIRouter()


@router.get(
    "/indices",
    summary="Chỉ số thị trường",
    description="VN-Index, HNX-Index, UPCOM-Index: giá trị, thay đổi điểm và % thay đổi."
)
def market_indices():
    return vs.get_market_indices()


@router.get(
    "/top-movers",
    summary="Top tăng/giảm mạnh",
    description="Danh sách cổ phiếu tăng mạnh nhất và giảm mạnh nhất trong phiên."
)
def top_movers(
    exchange: str = Query("HOSE", description="HOSE | HNX | UPCOM"),
    top: int = Query(10, ge=3, le=30, description="Số lượng cổ phiếu mỗi nhóm"),
):
    return vs.get_top_movers(exchange=exchange, top=top)


@router.get(
    "/overview",
    summary="Tổng quan phiên giao dịch",
    description="Thống kê toàn thị trường: số mã tăng/giảm/đứng, tổng KLGD, GTGD."
)
def market_overview():
    indices = vs.get_market_indices()
    return {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "session": "open" if 9 <= datetime.now().hour < 15 else "closed",
        "indices": indices,
        "generated_at": datetime.now().isoformat(),
    }


@router.post(
    "/cache/clear",
    summary="Xóa cache",
    description="Xóa toàn bộ cache trong bộ nhớ để buộc tải lại dữ liệu mới."
)
def clear_cache():
    vs.cache_clear()
    return {"message": "Cache đã được xóa", "timestamp": datetime.now().isoformat()}
