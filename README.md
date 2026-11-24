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
python manage.py seed_demo --output .demo-accounts.txt --wards                  # kèm 5 phường/xã DEMO (giả)
```

Danh mục phường/xã Hà Nội: nạp từ CSV chính thức (cột `code,name`, UTF-8) — phường demo tự ngừng dùng:

```powershell
python manage.py load_wards ..\docs\data\hanoi_wards.csv --dry-run   # xem trước
python manage.py load_wards ..\docs\data\hanoi_wards.csv
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

Đã xong [spec 004 — Yêu cầu gửi hàng của Shop](specs/004-yeu-cau-gui-hang/spec.md) (chờ thử trình duyệt):

- Shop tạo yêu cầu gửi hàng (người gửi điền sẵn từ hồ sơ, sửa được trên từng đơn), nhận mã yêu cầu `YC…`; mã vận đơn cấp khi Nhân viên duyệt (spec 005).
- Danh sách đơn của mình: lọc trạng thái, tìm theo mã/người nhận/SĐT, bộ lọc nằm trên URL.
- Sửa/hủy khi còn Chờ xác nhận; chống ghi đè khi hai nơi cùng sửa (`409`); lịch sử ghi trước/sau, lý do hủy; không xóa bản ghi.
- Phường/xã Hà Nội lấy từ bảng `Ward`: **hiện là dữ liệu demo** (`seed_demo --wards`). Nạp danh sách chính thức: `python manage.py load_wards <file.csv>` (cột `code,name`, UTF-8; có `--dry-run`).

Đã xong [spec 005 — Duyệt và quản lý vận đơn](specs/005-duyet-van-don/spec.md) (chờ thử trình duyệt):

- Nhân viên xem vận đơn **toàn hệ thống**: tab Chờ xác nhận (cũ nhất trước) / Tất cả, lọc trạng thái, khoảng ngày, tìm theo mã, người nhận hoặc Shop.
- **Duyệt** (có hộp xác nhận) sinh mã vận đơn `HTT` + ngày + 5 ký tự, chuyển Chờ lấy hàng; **từ chối** bắt buộc lý do. Shop nhận thông báo có nút "Xem vận đơn", thấy lý do từ chối ở chi tiết.
- Chống xử lý trên dữ liệu cũ (Shop vừa sửa/hủy → 409 + tải bản mới); bấm lại / hai người cùng duyệt vẫn chỉ một mã.
- Trang chủ Nhân viên có ô "N yêu cầu chờ duyệt".

Đã xong [spec 006 — Lấy hàng và nhập điểm tập kết](specs/006-lay-hang-diem-tap-ket/spec.md) (chờ thử trình duyệt):

- Nhân viên **phân công Shipper lấy hàng** (danh sách Shipper đang hoạt động, ít việc trước, kèm số nhiệm vụ đang mở); mỗi đơn tối đa một nhiệm vụ đang mở (chặn cả ở database).
- **Shipper** (giao diện cho điện thoại): xem nhiệm vụ của mình — chỉ thông tin để đi lấy, không thấy người nhận/COD; "Đã lấy hàng" hoặc "Lấy hàng thất bại" (lý do theo danh mục).
- Nhân viên **xác nhận tiếp nhận tại điểm tập kết** (ghi người giao/nhận, sai lệch); lấy thất bại thì **lấy lại** hoặc **kết thúc** có lý do.
- Theo dõi người giữ hàng (Shop → Shipper → Điểm tập kết); thông báo đúng người; khóa Shipper còn nhiệm vụ → đánh dấu + báo Nhân viên.

Đã xong [spec 007 — Giao hàng, COD, giao lại](specs/007-giao-hang-cod/spec.md) (chờ thử trình duyệt) — **đạt cột mốc demo "giao thành công"**:

- Nhân viên **phân công giao** đơn đã nhập điểm tập kết (xác nhận Shipper đã nhận hàng); phân công không tăng số lần giao.
- **Shipper** xem nhiệm vụ giao (người nhận, địa chỉ, COD, lần N/3), **giao thành công** phải tự gõ số tiền đã thu đúng bằng COD (lệch thì báo thiếu/thừa bao nhiêu, không lưu gì), hoặc **giao thất bại** có lý do.
- Nhân viên **giao lại** (tối đa 3 lần giao, giao lại chỉ bằng Shipper đang giữ hàng) hoặc **chuyển hoàn** (hoàn sớm được; đủ 3 lần thì chỉ còn hoàn).
- Shop thấy đơn **Đã giao** kèm thời gian và **COD đã thu**; mọi bước có thông báo đúng người. Bấm lại không cộng tiền, không tăng lần.

Đã xong [spec 008 — Hoàn hàng](specs/008-hoan-hang/spec.md) (chờ thử trình duyệt):

- Nhân viên **phân công hoàn** cho Shipper đang giữ hàng; Shipper thấy nhiệm vụ hoàn (điểm tập kết, lý do hoàn — không người nhận / COD) và bấm **"Đã đưa hàng về điểm tập kết"**.
- Nhân viên **tiếp nhận hàng hoàn** (ghi sai lệch nếu có; tiếp nhận được cả khi Shipper chưa báo) → **Chờ Shop đến lấy**, Shop nhận thông báo kèm địa chỉ điểm tập kết.
- Nhân viên **xác nhận Shop đã nhận** (tên người nhận + đã kiểm tra người nhận thuộc Shop) → **Đã hoàn về Shop**.
- Màn Nhân viên gộp tab theo giai đoạn (Chờ xác nhận · Lấy hàng · Giao hàng · Hoàn hàng · Tất cả) kèm chip trạng thái.
- Điểm tập kết cấu hình trong `backend/.env`: `HUB_NAME`, `HUB_ADDRESS`, `HUB_PHONE` (xem `backend/.env.example`).

Đã triển khai [spec 009 — Đổi Shipper](specs/009-doi-shipper/spec.md), nghiệm thu chức năng tự động đạt:

- Đổi nhiệm vụ lấy ngay; khi đang giữ hàng giao, người mới chỉ là dự kiến cho tới khi Nhân viên xác nhận bàn giao thực tế.
- Người cũ chỉ báo đưa hàng về; người mới nhận nhiệm vụ cùng lần giao. Đổi người không đặt lại số lần giao hay ghi COD.
- Ghi sai lệch giữ chờ; nhận hàng về điểm tập kết khi không còn nhiệm vụ mở để giao lại/tiếp nhận hoàn.
- Hộp khóa Shipper hiện nhiệm vụ mở và link vận đơn; xử lý được trường hợp người cũ/người dự kiến bị khóa.
- Kiểm chứng: 531 test backend xuôi và đảo thứ tự, 326 Vitest, 3 kịch bản Chrome với API/PostgreSQL test DB thật.

**Còn chờ:** người dùng tự thử [manual-test.md](specs/009-doi-shipper/manual-test.md); audit dev còn 7 mục
(2 critical), audit production 0. Báo cáo và các giới hạn build tại [acceptance.md](specs/009-doi-shipper/acceptance.md).
Spec 009 chưa được đánh dấu nghiệm thu toàn bộ.

Đã triển khai [spec 010 — Tra cứu và lịch sử](specs/010-tra-cuu-lich-su/spec.md):

- Shop/Nhân viên tra đúng mã YC/HTT tại `/tracking`, có link chi tiết/lịch sử và thử lại khi lỗi mạng.
- Shop chỉ thấy đơn mình; Shipper không có quyền tra cứu. Lịch sử phân biệt lần lấy, lần giao và đổi Shipper, có đổi thứ tự.
- Nghiệm thu kỹ thuật: 550 test backend xuôi/ngược, 337 Vitest, build và Chrome với API/PostgreSQL test DB thật.
- Còn chờ người dùng thử [manual-test.md](specs/010-tra-cuu-lich-su/manual-test.md); audit dev còn 7 mục (2 critical),
  production 0. Kết quả/giới hạn: [acceptance.md](specs/010-tra-cuu-lich-su/acceptance.md).

[Spec 011 — GPS](specs/011-gps-ban-do/spec.md) đã triển khai backend Phase 1–2: model LocationPing,
API gửi vị trí kiểm nhiệm vụ/nhịp gửi và API xem điểm mới nhất cho Shop/Nhân viên đúng quyền.
Nhiệm vụ đóng hoặc đã thay người không trả GPS cũ. Migration mới chưa áp dụng vào database đang dùng.

Lệnh `python backend/manage.py purge_location_pings` giữ mặc định 30 ngày theo thời điểm máy chủ nhận,
chỉ xóa GPS quá hạn. Sau khi migrate DB local, người vận hành cần lên lịch chạy lệnh hằng ngày
(ví dụ Task Scheduler trên Windows); chưa có lịch tự động được cài. Override `--days N` phải là số nguyên dương.
Chi tiết: [models.md](specs/011-gps-ban-do/models.md).

Phase 4 đã gắn chia sẻ GPS vào nhiệm vụ Shipper và bản đồ live vào chi tiết đơn Shop/Nhân viên.
Shipper chủ động bật sau giải thích; từ chối quyền vẫn có địa chỉ và chỉ đường. Nhiệm vụ chờ bàn giao đổi người
dẫn về điểm tập kết; khi đóng/thay người, khối GPS dừng và không tái dùng điểm cũ cho task mới.
Nút Chỉ đường mở Google Maps bằng địa chỉ, không có tuyến nhúng hoặc gọi dịch vụ định tuyến phía máy chủ.
Kiểm chứng: 384 Vitest, build và Chrome/session/CSRF/API/PostgreSQL test DB thật; 10 ảnh 1440/390.
GPS và tile giả lập trong browser test, không dùng vị trí thiết bị/tài khoản thực.
Nền mặc định OSM; đổi provider qua `VITE_MAP_TILE_URL` và `VITE_MAP_TILE_ATTRIBUTION` trong `frontend/.env`
(xem `.env.example`). Attribution luôn hiện, không tải hàng loạt/offline tile. Nguồn OSM là dịch vụ best-effort;
provider riêng cần attribution phù hợp. [Bằng chứng Phase 4](specs/011-gps-ban-do/artifacts/phase4/README.md),
[audit Phase 3](specs/011-gps-ban-do/artifacts/phase3/README.md).
Tiếp theo: nghiệm thu Phase 5 và người dùng [tự thử](specs/011-gps-ban-do/manual-test.md).

Chi tiết ranh giới module: [docs/architecture.md](docs/architecture.md).

Giao diện: thanh bên + thanh trên, font Be Vietnam Pro, icon Lucide, bảng tự thành thẻ trên điện thoại. Khuôn màn hình, biến màu, thành phần dùng chung: [docs/design-system.md](docs/design-system.md).

Tham khảo: [Django 5.2 LTS](https://docs.djangoproject.com/en/5.2/releases/5.2/), [Vite](https://vite.dev/guide/), [Vue](https://vuejs.org/guide/quick-start).
