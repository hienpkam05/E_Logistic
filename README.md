# HTT EXPRESS

Bộ khung hệ thống quản lý vận đơn trong Hà Nội, dùng Python/Django REST Framework, Vue 3 và PostgreSQL.

## Cấu trúc

```text
elogistic/
├── backend/
│   ├── manage.py
│   ├── .env.example
│   ├── config/                 # Settings, URL gốc, ASGI/WSGI
│   └── apps/
│       ├── core/               # Chức năng dùng chung, health endpoint
│       ├── accounts/           # Tài khoản, vai trò và phân quyền
│       ├── shipments/          # Yêu cầu gửi hàng, vận đơn và lịch sử
│       ├── dispatch/           # Nhiệm vụ lấy/giao/giao lại/hoàn
│       ├── tracking/           # Tra cứu, GPS và quyền xem vị trí
│       └── notifications/      # Thông báo trong hệ thống
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example
│   └── src/
│       ├── assets/styles/
│       ├── components/common/
│       ├── composables/
│       ├── layouts/
│       ├── router/
│       ├── services/           # Hàm gọi API (chưa triển khai)
│       ├── stores/             # Pinia stores (chưa triển khai)
│       ├── utils/
│       ├── views/
│       │   ├── auth/
│       │   ├── shop/
│       │   ├── staff/
│       │   ├── shipper/
│       │   ├── HomeView.vue
│       │   └── NotFoundView.vue
│       ├── App.vue
│       └── main.js
├── docs/
│   └── architecture.md
├── compose.yaml                # PostgreSQL cho môi trường local
├── requirements.txt            # Thư viện Python cho backend
└── README.md
```

Hai file Markdown yêu cầu và sáu ảnh luồng được giữ nguyên tại thư mục gốc.

## Chuẩn bị

- Python 3.12 hoặc 3.13.
- Node.js 22.12 trở lên cho bộ Vite 6 đã khai báo.
- PostgreSQL 17 cài sẵn, hoặc Docker Compose để chạy database local.

## Chạy database

Từ thư mục gốc:

```powershell
docker compose up -d db
```

Database mặc định: `htt_express`, user `htt_express`, password `htt_local_password`, cổng `5432`. Đây là cấu hình local; khi thay đổi phải đồng bộ với `backend/.env`.

## Chạy backend

Kích hoạt môi trường ảo bên ngoài dự án của bạn trước. Sau đó chạy từ thư mục gốc `elogistic`:

```powershell
python -m pip install -r requirements.txt
cd backend
Copy-Item .env.example .env
python manage.py check
python manage.py runserver
```

Kiểm tra: `http://127.0.0.1:8000/api/v1/health/`.
Endpoint này chỉ kiểm tra ứng dụng đang chạy, chưa kiểm tra kết nối database.

Chưa tạo model nghiệp vụ hoặc migration. Bước tiếp theo cần tạo custom User với ba vai trò, cấu hình `AUTH_USER_MODEL` và tạo migration **trước lần migrate đầu tiên**. Django admin đã được gắn URL nhưng chỉ sử dụng sau khi thiết lập tài khoản và migrate database.

## Chạy frontend

Mở terminal khác:

```powershell
cd frontend
npm.cmd install
Copy-Item .env.example .env
npm.cmd run dev
```

Mở `http://127.0.0.1:5173`. Trang khởi đầu hiển thị ba vai trò. Vue Router và Pinia đã được đăng ký; các màn hình nghiệp vụ chưa triển khai.

Vite chuyển tiếp đường dẫn `/api` đến Django tại `http://127.0.0.1:8000` trong môi trường phát triển. Production cần cấu hình reverse proxy riêng.

```powershell
npm.cmd run build
```

## Phạm vi hiện tại

- Cấu trúc module và cấu hình phát triển ban đầu.
- PostgreSQL local qua Docker Compose hoặc database cài sẵn.
- Django REST Framework mặc định yêu cầu đăng nhập cho các API được triển khai sau này; health endpoint công khai.
- Chưa có API nghiệp vụ, đăng nhập, phân quyền theo vai trò, dữ liệu mẫu hoặc tích hợp GPS.

Chi tiết ranh giới module và các điểm cần thống nhất: [docs/architecture.md](docs/architecture.md).

Tham khảo: [Django 5.2 LTS](https://docs.djangoproject.com/en/5.2/releases/5.2/), [Vite](https://vite.dev/guide/), [Vue](https://vuejs.org/guide/quick-start).
