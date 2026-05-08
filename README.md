# 🇻🇳 VNStockAI — Python FastAPI Backend

API server cho ứng dụng phân tích chứng khoán Việt Nam, tích hợp **vnstock3** để lấy dữ liệu HOSE/HNX/UPCOM.

---

## 📁 Cấu trúc project

```
vnstock-backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Cấu hình từ env variables
│   ├── routers/
│   │   ├── stocks.py        # /api/stocks/* endpoints
│   │   └── market.py        # /api/market/* endpoints
│   └── services/
│       └── vnstock_service.py  # Wrapper vnstock3 + cache + fallback
├── requirements.txt
├── Procfile                 # Render deploy
├── railway.toml             # Railway deploy
├── render.yaml              # Render blueprint
├── .env.example
└── README.md
```

---

## ⚡ Chạy local (5 phút)

### 1. Clone & cài đặt

```bash
# Clone hoặc giải nén project
cd vnstock-backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows

# Cài dependencies
pip install -r requirements.txt
```

### 2. Cấu hình .env

```bash
cp .env.example .env
# Mở .env và chỉnh sửa nếu cần (mặc định là ổn để dev)
```

### 3. Chạy server

```bash
# Development (auto-reload)
python -m app.main

# Hoặc dùng uvicorn trực tiếp
uvicorn app.main:app --reload --port 8000
```

### 4. Kiểm tra

```
API docs:   http://localhost:8000/docs
Health:     http://localhost:8000/health
VN-Index:   http://localhost:8000/api/market/indices
VCB history: http://localhost:8000/api/stocks/VCB/history
```

---

## 📡 API Endpoints

### Cổ phiếu

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/stocks` | Danh sách cổ phiếu niêm yết |
| GET | `/api/stocks/screener` | Lọc cổ phiếu theo tiêu chí |
| GET | `/api/stocks/{symbol}/history` | Lịch sử OHLCV |
| GET | `/api/stocks/{symbol}/price` | Giá realtime |
| GET | `/api/stocks/{symbol}/intraday` | Tick data trong phiên |
| GET | `/api/stocks/{symbol}/info` | Thông tin công ty |
| GET | `/api/stocks/{symbol}/ratios` | P/E, P/B, ROE, ROA... |
| GET | `/api/stocks/{symbol}/financials` | Báo cáo tài chính |

### Thị trường

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/market/indices` | VN-Index, HNX-Index, UPCOM |
| GET | `/api/market/top-movers` | Top tăng/giảm mạnh nhất |
| GET | `/api/market/overview` | Tổng quan phiên giao dịch |
| POST | `/api/market/cache/clear` | Xóa cache |

### Ví dụ query parameters

```bash
# Lịch sử 3 tháng, nến ngày
GET /api/stocks/VCB/history?start=2026-02-01&end=2026-05-06

# Lịch sử 1 năm, nến tuần
GET /api/stocks/HPG/history?interval=1W

# Screener: ngân hàng, ROE > 15%, P/E < 12
GET /api/stocks/screener?sector=Ngân hàng&min_roe=15&max_pe=12&exchange=HOSE

# Top 10 tăng mạnh sàn HOSE
GET /api/market/top-movers?exchange=HOSE&top=10
```

---

## 🚀 Deploy lên Cloud (miễn phí)

### Option A — Railway (khuyến nghị)

1. Tạo tài khoản tại [railway.app](https://railway.app)
2. Tạo project mới → **Deploy from GitHub**
3. Kết nối repo GitHub chứa project này
4. Railway tự detect `railway.toml` và deploy
5. Vào **Settings → Networking → Generate Domain** để lấy URL public

```bash
# Hoặc dùng Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

### Option B — Render

1. Tạo tài khoản tại [render.com](https://render.com)
2. **New → Web Service → Connect GitHub repo**
3. Render tự đọc `render.yaml`
4. Hoặc điền thủ công:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Region:** Singapore

> ⚠️ **Lưu ý Render Free tier:** Server sleep sau 15 phút idle → request đầu tiên chậm ~30s.
> Dùng [UptimeRobot](https://uptimerobot.com) ping mỗi 10 phút để giữ server awake.

### Sau khi deploy — cập nhật frontend

Trong file `vnstock-ai.html`, thay `BASE_API`:

```javascript
// Thêm vào đầu <script> trong vnstock-ai.html
const BASE_API = "https://your-api.railway.app";  // URL từ Railway/Render

// Sau đó gọi API thật thay vì mock data:
async function loadStockHistory(sym, period) {
    const end = new Date().toISOString().slice(0,10);
    const start = new Date(Date.now() - period * 86400000).toISOString().slice(0,10);
    const res = await fetch(`${BASE_API}/api/stocks/${sym}/history?start=${start}&end=${end}`);
    const json = await res.json();
    return json.data;  // Array of {date, open, high, low, close, volume}
}
```

---

## 🔧 Nguồn dữ liệu

Backend hỗ trợ **3 tầng fallback**:

```
vnstock3 (VCI)  →  vnstock3 (TCBS)  →  vnstock legacy  →  Mock data
```

| Nguồn | Dữ liệu | Độ trễ |
|-------|---------|--------|
| VCI | Real-time, OHLCV, Intraday | ~1-2s |
| TCBS | Real-time, OHLCV, Tài chính | ~2-3s |
| vnstock legacy | EOD, lịch sử | ~3-5s |
| Mock | Giả lập (dev only) | 0ms |

---

## 🗄️ Cache

In-memory cache với TTL tự động:

| Loại dữ liệu | TTL | Lý do |
|---|---|---|
| Giá realtime | 60s | Cần tươi mới |
| Intraday ticks | 30s | Realtime nhất |
| Lịch sử giá | 5 phút | Ít thay đổi |
| Thông tin công ty | 1 giờ | Rất ít thay đổi |
| Chỉ số thị trường | 60s | Cần tươi mới |

Xóa cache thủ công: `POST /api/market/cache/clear`

---

## 🐛 Troubleshooting

**vnstock3 không cài được:**
```bash
pip install --upgrade pip
pip install vnstock3 --no-cache-dir
```

**ModuleNotFoundError: No module named 'app':**
```bash
# Chạy từ thư mục gốc (chứa folder app/)
python -m app.main
# Không phải:
# cd app && python main.py  ← SAI
```

**Port đã dùng:**
```bash
PORT=8001 python -m app.main
```

**CORS error từ frontend:**
```bash
# Thêm domain frontend vào .env
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 📝 License

MIT — Sử dụng tự do cho dự án cá nhân và thương mại.
