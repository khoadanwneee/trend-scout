# Trend Scout

Theo dõi repo GitHub đang hot (Frontend, Backend, Design/UI, UX, Data, Video, Viết bài, AI) và job IT fresher
tại Việt Nam. Có dashboard web và digest hằng ngày qua Telegram.

- `backend/`: FastAPI + SQLite + APScheduler (Python)
- `frontend/`: Next.js dashboard (lọc, tìm kiếm, trạng thái nguồn)
- Dữ liệu lưu ở `data/trend_scout.db`

## Chạy

```powershell
.\start.ps1          # mở backend :8000 và frontend :3000
```

Hoặc dùng CLI:

```powershell
cd backend
.\.venv\Scripts\python.exe cli.py scrape                 # cào tất cả nguồn
.\.venv\Scripts\python.exe cli.py scrape itviec          # cào một nguồn
.\.venv\Scripts\python.exe cli.py digest --dry-run       # xem digest, không gửi
```

Cấu hình: sao chép `.env.example` thành `.env` (đặt ở thư mục gốc dự án). Tất cả đều tùy chọn.

- `GITHUB_TOKEN`: nên có. Không token chỉ được 60 request/giờ và search chậm hơn.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: bắt buộc nếu muốn gửi digest thật. Thiếu thì digest chỉ in ra.
- Scheduler chạy mỗi ngày: cào lúc 08:00, gửi digest lúc 09:00 (đổi bằng `SCRAPE_HOUR`, `DIGEST_HOUR`).
  Cần để backend chạy liên tục.

## Deploy miễn phí (GitHub Actions + Vercel)

- `.github/workflows/daily.yml` chạy mỗi ngày 08:00 giờ VN: cào, gửi digest Telegram, xuất
  `frontend/public/data.json`, rồi commit lại repo (kèm `data/trend_scout.db` để nhớ mục nào đã gửi).
- Vercel (Root Directory = `frontend`) tự build lại mỗi khi có commit mới. Dashboard chỉ đọc `data.json`.
- Secrets cần thêm trong GitHub repo (Settings > Secrets and variables > Actions): `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_CHAT_ID`. Không cần `GITHUB_TOKEN`, workflow dùng token có sẵn.
- Chạy tay: tab Actions > daily-scrape-and-digest > Run workflow.
- Cập nhật dữ liệu local: `python cli.py scrape` rồi `python cli.py export`.

## Trạng thái các nguồn (kiểm tra thực tế ngày 2026-11-16, TopDev ngày 2026-11-17)

| Nguồn | Trạng thái | Ghi chú |
|---|---|---|
| github-categories | ok | GitHub Search API, theo topic từng lĩnh vực |
| github-trending | ok | Trending tuần (trang công khai) |
| itviec | ok | Trang `/viec-lam-it/fresher`, robots.txt cho phép |
| topcv | blocked | Cloudflare trả 403. Dừng, không lách |
| topdev | ok | Trang `/jobs/search` lọc nhóm IT + cấp Thực tập/Mới tốt nghiệp, đọc dữ liệu nhúng sẵn trong trang. TopDev giờ là trang tổng hợp (Saramin) nên rất ít tin IT (3 tin ngày 17/11). Chạy trên GitHub Actions; IP nhà đôi khi bị ngắt kết nối |
| vietnamworks | unsupported | HTML công khai chỉ có vài tin tài trợ; danh sách thật nằm ở API nội bộ |
| linkedin | disabled | robots.txt và điều khoản cấm cào |

Tab "Nguồn dữ liệu" trong dashboard luôn hiện trạng thái thật của lần chạy gần nhất.

## Quy tắc cào

User-Agent trung thực, đọc robots.txt, giới hạn tần suất (3 giây giữa các request), chỉ lấy tin công khai.
Nếu bị chặn (403, 429, challenge) thì dừng và báo `blocked`. Không có stealth, giả header hay lách captcha.

## Lưu ý

- Phân loại repo dựa trên topic GitHub nên có nhiễu (đặc biệt `video`, `writing`, `ux`).
- Trang web có nút "Cào dữ liệu mới" gọi `POST /api/refresh`, mất khoảng 2 phút nếu không có `GITHUB_TOKEN`.
- Hạn chế ITviec: mức lương thường bị ẩn khi chưa đăng nhập nên cột lương hay trống.
