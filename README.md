# HTT EXPRESS

Hệ thống quản lý vận đơn trong Hà Nội, dùng Python/Django REST Framework, Vue 3 và PostgreSQL.

## Cấu trúc

```text
elogistic/
├── backend/
│   ├── manage.py
│   ├── .env.example            # Biến môi trường Django + Docker Compose
│   ├── config/                 # Settings, URL gốc, ASGI/WSGI
│   └── apps/
│       ├── core/               # Lỗi API, phân trang, chuyển trạng thái, /meta/choices/, health
│       ├── accounts/           # User tùy biến, ba vai trò, HasRole
│       ├── shipments/          # Yêu cầu gửi hàng, vận đơn, lịch sử (enum + bảng trạng thái đã có)
│       ├── dispatch/           # Nhiệm vụ lấy/giao/hoàn (enum + bảng trạng thái đã có)
│       ├── tracking/           # Tra cứu, GPS và quyền xem vị trí
│       └── notifications/      # Thông báo nội bộ (model + notify())
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example
│   └── src/
│       ├── assets/styles/
│       ├── components/common/  # StatusBadge
│       ├── composables/
│       ├── layouts/
│       ├── router/
│       ├── services/           # http.js (API client duy nhất), metaService.js
│       ├── stores/             # meta.js (enum từ backend)
│       ├── utils/              # format.js, statusTones.js
│       ├── views/{auth,shop,staff,shipper}/
│       ├── App.vue
│       └── main.js
├── docs/                       # Đặc tả 42 UC (.docx + .md), phân quyền, checklist, kiến trúc, ảnh luồng
├── specs/                      # Spec theo phần việc: spec.md, tasks.md, models.md, api.md
├── compose.yaml                # PostgreSQL cho môi trường local
├── requirements.txt            # Thư viện Python cho backend
└── README.md
```

Tài liệu nghiệp vụ: [docs/](docs/). Lộ trình và quy ước spec: [specs/README.md](specs/README.md).

## Chuẩn bị

- Python 3.14 (đã kiểm tra với 3.14.2; 3.12/3.13 dự kiến cũng chạy được với Django 5.2).
- Node.js 22.12 trở lên cho bộ Vite 6 đã khai báo.
- Docker Desktop (PostgreSQL 17 qua Compose), hoặc PostgreSQL cài sẵn.

## Chạy database

Từ thư mục gốc:

```powershell
Copy-Item backend/.env.example backend/.env   # lần đầu; đặt DJANGO_SECRET_KEY mới (lệnh tạo key có trong file)
docker compose --env-file backend/.env up -d db
```

Compose đọc tên database, user, mật khẩu và cổng từ `backend/.env`, cùng file Django dùng, nên chỉ cần sửa một chỗ. Mặc định: database/user `htt_express`, password `htt_local_password`, cổng `5432`. Nếu máy đã có PostgreSQL khác chiếm cổng 5432, đặt `POSTGRES_PORT=5433` trong `backend/.env`.

Mỗi lần khởi động lại máy: mở Docker Desktop rồi chạy lại lệnh `docker compose ...` ở trên.

## Chạy backend

Kích hoạt môi trường ảo (`venv\Scripts\activate`), rồi từ thư mục gốc `elogistic`:

```powershell
python -m pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py createsuperuser     # hỏi username, họ tên, số điện thoại (10 số, bắt đầu bằng 0), mật khẩu
python manage.py runserver
```

Tài khoản demo cho máy local (chỉ chạy khi `DJANGO_DEBUG=True`): 1 superuser, 1 tài khoản mỗi vai trò, `demo_mktam` (đang dùng mật khẩu tạm) và `demo_khoa` (bị khóa). Mật khẩu ngẫu nhiên ghi vào file (đã có trong `.gitignore`); chạy lại vẫn giữ mật khẩu cũ trong file:

```powershell
python manage.py seed_demo --output .demo-accounts.txt                          # tạo tài khoản còn thiếu
python manage.py seed_demo --reset --output .demo-accounts.txt                  # đặt lại mật khẩu + trạng thái demo
python manage.py seed_demo --output .demo-accounts.txt --notifications          # kèm 31 thông báo mẫu
```

Kịch bản thử trên trình duyệt: [specs/002-xac-thuc/manual-test.md](specs/002-xac-thuc/manual-test.md).

- Kiểm tra ứng dụng chạy: `http://127.0.0.1:8000/api/v1/health/` (không kiểm tra database).
- Danh mục trạng thái/vai trò cho frontend: `http://127.0.0.1:8000/api/v1/meta/choices/`.
- Django admin (công cụ kỹ thuật): `http://127.0.0.1:8000/admin/`.

Chạy test (trên PostgreSQL, cần database đang chạy):

```powershell
python manage.py test apps
```

Biến môi trường backend: xem [backend/.env.example](backend/.env.example) (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `POSTGRES_*`).

## Chạy frontend

Mở terminal khác:

```powershell
cd frontend
npm.cmd install
Copy-Item .env.example .env
npm.cmd run dev
```

Mở `http://127.0.0.1:5173`. Khi khởi động, app tải danh mục trạng thái từ `/api/v1/meta/choices/`; nếu backend chưa chạy sẽ hiện thanh báo lỗi kèm nút "Thử lại".

Vite chuyển tiếp đường dẫn `/api` đến địa chỉ trong `VITE_PROXY_TARGET` (`frontend/.env`, mặc định `http://127.0.0.1:8000`) khi chạy `npm run dev`, **giữ nguyên header `Host`** (`changeOrigin: false`) để kiểm tra CSRF của Django không chặn đăng nhập. Production cần reverse proxy riêng, cũng phải giữ `Host` (nginx: `proxy_set_header Host $host`).

Mở ứng dụng bằng đúng địa chỉ `http://127.0.0.1:5173` (Vite chỉ lắng nghe trên 127.0.0.1).

```powershell
npm.cmd run test    # Vitest (jsdom), không cần backend
npm.cmd run build
```

## Phạm vi hiện tại

Đã xong [spec 001 — Nền tảng](specs/001-nen-tang/spec.md):

- User tùy biến với ba vai trò `SHOP`, `ADMIN`, `SHIPPER`; permission `HasRole`.
- Định dạng lỗi API thống nhất `{"error": {code, message, fields}}`, phân trang chuẩn.
- Enum và bảng chuyển trạng thái vận đơn/nhiệm vụ, khớp checklist mục 4.
- Thông báo nội bộ (`notify()`), endpoint enum `/api/v1/meta/choices/`.
- Frontend: API client, store enum, formatter, `StatusBadge`.

Đã xong [spec 002 — Xác thực, hồ sơ, thông báo](specs/002-xac-thuc/spec.md) (chờ thử trình duyệt):

- Đăng nhập/đăng xuất bằng session + CSRF, phiên 8 giờ, giới hạn 10 lần đăng nhập/phút/IP.
- Hồ sơ cá nhân, đổi mật khẩu, luồng mật khẩu tạm (backend chặn mọi API cho tới khi đổi).
- Thông báo nội bộ: danh sách, lọc chưa đọc, đánh dấu đã đọc, số chưa đọc cập nhật 60 giây.
- Giao diện: layout sau đăng nhập, trang chủ tạm 3 vai trò, phân quyền route theo vai trò.

Đã xong [spec 003 — Quản lý tài khoản và Shipper](specs/003-quan-ly-tai-khoan/spec.md) (chờ thử trình duyệt):

- Nhân viên/Admin xem, lọc, tìm, tạo, sửa tài khoản cả 3 vai trò; "Quản lý Shipper" là cùng màn hình lọc sẵn Shipper.
- Mật khẩu tạm do hệ thống sinh, chỉ hiện một lần; đặt lại mật khẩu sau khi xác minh danh tính.
- Khóa/mở khóa: phiên cũ mất ngay và không sống lại khi mở khóa; không khóa được Admin hoạt động cuối cùng.
- Lịch sử thao tác chỉ thêm, ghi người thực hiện, không chứa mật khẩu. Không có xóa tài khoản.

Chưa có: các chức năng nghiệp vụ vận đơn/điều phối (spec 004–011).

Chi tiết ranh giới module: [docs/architecture.md](docs/architecture.md).

Tham khảo: [Django 5.2 LTS](https://docs.djangoproject.com/en/5.2/releases/5.2/), [Vite](https://vite.dev/guide/), [Vue](https://vuejs.org/guide/quick-start).
