# Spec 005 — Kịch bản thử trên trình duyệt

Dùng cho bước 6.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**; đánh `[x]` khi đúng, ghi lỗi vào bảng tổng kết cuối file.

Phần khó tạo bằng tay đã có test tự động, không cần thử ở đây:
- hai Nhân viên bấm Duyệt **đúng cùng lúc**;
- mã vận đơn trùng;
- gọi API duyệt bằng tài khoản Shop.

Xem tasks.md Phase 3 (test 2 luồng thật).

## Chuẩn bị (một lần)

1. Docker Desktop + database: `docker compose --env-file backend/.env up -d db`
2. Backend: `cd backend` → `..\venv\Scripts\python manage.py runserver`
3. Frontend (terminal khác): `cd frontend` → `npm.cmd run dev`
4. Mật khẩu xem trong `backend/.demo-accounts.txt`.
5. Mở **2 cửa sổ** tại `http://127.0.0.1:5173`:
   - cửa sổ thường: `demo_shop` (gọi là **cửa sổ Shop**);
   - cửa sổ **ẩn danh**: `demo_nhanvien` (gọi là **cửa sổ NV**).

| Dữ liệu lúc bắt đầu (22/11/2026) | Giá trị |
|---|---|
| Vận đơn | Chưa có đơn nào; mã yêu cầu tiếp theo là `YC00000010` |
| Phường/xã | 5 phường demo `[Demo] …` (D1 spec 004) |

**Tạo dữ liệu thử (cửa sổ Shop):** menu "Tạo yêu cầu gửi hàng", tạo lần lượt **3 đơn**:

Các ô khác (phường lấy hàng, địa chỉ, mô tả hàng) điền tùy ý.

| Đơn | Người nhận | SĐT người nhận | Phường giao | COD |
|---|---|---|---|---|
| đơn 1 | Nguyễn Thị Lan | 0987654321 | [Demo] Phường B | 350000 |
| đơn 2 | Trần Văn Minh | 0912345678 | [Demo] Phường C | 0 |
| đơn 3 | Phạm Thu Hà | 0934567890 | [Demo] Xã D | 1250000 |

**Sau khi thử xong** (không bắt buộc), xóa đơn thử của `demo_shop`:

```powershell
cd backend
..\venv\Scripts\python manage.py shell -c "from apps.notifications.models import Notification; from apps.shipments.models import Shipment, ShipmentEvent; q = Shipment.objects.filter(shop__username='demo_shop'); ids = list(q.values_list('id', flat=True)); Notification.objects.filter(payload__shipment_id__in=ids).delete(); ShipmentEvent.objects.filter(shipment__in=q).delete(); print(q.delete())"
```

---

## A. Menu và trang chủ Nhân viên

- [ ] **A1**
  - Làm: cửa sổ NV, xem thanh bên.
  - Mong đợi: có "Quản lý vận đơn" (đứng đầu), "Quản lý tài khoản", "Quản lý Shipper".
- [ ] **A2**
  - Làm: bấm "Tổng quan".
  - Mong đợi:
    - Ô màu cam **"3 yêu cầu chờ duyệt"**, dòng nhỏ "Xử lý theo thứ tự đến (cũ nhất trước)".
    - Bấm vào ô → sang "Quản lý vận đơn".
- [ ] **A3**
  - Làm: cửa sổ Shop gõ `http://127.0.0.1:5173/staff/shipments`.
  - Mong đợi: bị đưa về trang Shop; thanh bên không có "Quản lý vận đơn".

## B. Danh sách (UC05.9)

- [ ] **B1**
  - Làm: cửa sổ NV, "Quản lý vận đơn".
  - Mong đợi:
    - Tab **"Chờ xác nhận"** đang chọn, dòng "Cũ nhất trước — xử lý theo thứ tự đến", góc phải "3 yêu cầu chờ duyệt".
    - Thứ tự đơn 1 → đơn 2 → đơn 3 (**cũ nhất ở trên**).
    - Cột Shop có "Shop Demo Hoàn Kiếm" và `demo_shop`; cột Mã có `YC…` + chữ nhỏ "mã yêu cầu".
- [ ] **B2**
  - Làm: bấm tab "Tất cả".
  - Mong đợi: thứ tự đảo lại (**mới nhất ở trên**); xuất hiện ô "Mọi trạng thái"; URL có `?tab=all`.
- [ ] **B3**
  - Làm: ô tìm gõ `0999000003` (SĐT của Shop) → Enter.
  - Mong đợi: ra cả 3 đơn (Nhân viên tìm được theo Shop). Thử gõ `Minh` → chỉ đơn 2.
- [ ] **B4**
  - Làm: xóa ô tìm; chọn "Từ ngày" = ngày mai.
  - Mong đợi:
    - Khung "Không có kết quả phù hợp với bộ lọc." + "Bỏ lọc".
    - Ô "Đến ngày" không chọn được ngày trước "Từ ngày".
- [ ] **B5**
  - Làm: bấm "Bỏ lọc".
  - Mong đợi: về đủ 3 đơn, vẫn ở tab "Tất cả".
- [ ] **B6**
  - Làm: gõ thẳng URL `http://127.0.0.1:5173/staff/shipments?tab=all&from=2026-12-31&to=2026-01-01`.
  - Mong đợi: báo lỗi "Dữ liệu chưa hợp lệ." kèm nút "Tải lại" và "Bỏ lọc" (Đến ngày trước Từ ngày).
- [ ] **B7**
  - Làm: ở tab "Tất cả" chọn trạng thái "Chờ xác nhận", rồi **F5**.
  - Mong đợi: tải lại vẫn giữ tab và bộ lọc.

## C. Chi tiết (UC05.7)

- [ ] **C1**
  - Làm: tab "Chờ xác nhận" → bấm mã đơn 1.
  - Mong đợi:
    - Tiêu đề `YC…` + nhãn "Chờ xác nhận"; dòng mã ghi "Chưa có mã vận đơn (cấp khi duyệt)" và tên Shop.
    - Các thẻ: **Shop gửi hàng**, Người gửi, Người nhận, Kiện hàng, Thu hộ, **Điều phối**.
    - Lịch sử bên phải có "Tạo yêu cầu gửi hàng".
- [ ] **C2**
  - Làm: xem thẻ "Điều phối".
  - Mong đợi: "Đang giữ hàng: Shop", "Shipper phụ trách: **Chưa phát sinh**", "Số lần giao: 0", "Kết quả giao: **Chưa phát sinh**".
- [ ] **C3**
  - Làm: tìm nút sửa nội dung / đổi trạng thái.
  - Mong đợi: **không có**, chỉ có "Từ chối" và "Duyệt" (UC05.7 BR1).
- [ ] **C4**
  - Làm: gõ URL `/staff/shipments/999999`.
  - Mong đợi: "Không tìm thấy vận đơn".

## D. Duyệt (UC05.6)

- [ ] **D1**
  - Làm: ở đơn 1 bấm "Duyệt".
  - Mong đợi:
    - Hộp "Duyệt yêu cầu gửi hàng?" nêu mã yêu cầu, Shop, người nhận + phường, COD "350.000 ₫".
    - Có câu "…không hoàn tác được.", nút "Để sau" và "Duyệt".
- [ ] **D2**
  - Làm: bấm "Để sau".
  - Mong đợi: hộp đóng, đơn vẫn "Chờ xác nhận".
- [ ] **D3**
  - Làm:
    1. Cửa sổ NV: chuột phải mã đơn 1 ở danh sách → mở thêm ở **tab thứ hai** (để dùng ở D7, đừng bấm gì ở tab đó).
    2. Ở tab đầu: "Duyệt" → bấm "Duyệt" trong hộp.
  - Mong đợi:
    - Thông báo xanh "Đã duyệt. Mã vận đơn HTT…; Shop đã được thông báo." (ghi lại, gọi là **mã A**).
    - Tiêu đề đổi thành mã A, nhãn "Chờ lấy hàng"; **hết** nút Duyệt/Từ chối.
    - Lịch sử thêm "Duyệt yêu cầu": "Chờ xác nhận → Chờ lấy hàng", "Mã vận đơn: (trống) → mã A".
- [ ] **D4**
  - Làm: kiểm tra mã A.
  - Mong đợi: dạng `HTT` + 6 số ngày duyệt (vd `261122`) + 5 ký tự in hoa/số, **không** có I, O, 0, 1 ở 5 ký tự cuối.
- [ ] **D5**
  - Làm: cửa sổ Shop: bấm chuông → màn Thông báo.
  - Mong đợi:
    - Thông báo mới "Yêu cầu YC… đã được duyệt", nội dung "Mã vận đơn mã A. Đơn đang chờ lấy hàng."
    - Có liên kết **"Xem vận đơn →"**; bấm vào mở đúng đơn 1, tiêu đề là mã A.
- [ ] **D6** *(duyệt trên dữ liệu cũ — UC05.6 E1)*
  - Làm:
    1. Cửa sổ NV mở đơn 2 (đừng bấm gì).
    2. Cửa sổ Shop mở đơn 2 → "Sửa yêu cầu" → đổi COD thành `200000` → Lưu.
    3. Cửa sổ NV bấm "Duyệt" → "Duyệt".
  - Mong đợi:
    - Hộp đóng, cảnh báo vàng "Yêu cầu vừa được Shop thay đổi. Vui lòng tải lại để kiểm tra trước khi xử lý. Đã tải bản mới nhất bên dưới."
    - Thẻ Thu hộ đã hiện "200.000 ₫"; nút Duyệt vẫn còn (xem lại xong mới duyệt). **Chưa** duyệt đơn 2 ở bước này.
- [ ] **D7** *(duyệt lại trên màn hình cũ — BR1, BR2)*
  - Làm: sang **tab thứ hai** mở ở D3 (vẫn còn nút "Duyệt" vì tải trước khi duyệt) → "Duyệt" → "Duyệt".
  - Mong đợi:
    - Thông báo "Đã duyệt. Mã vận đơn **mã A**…": **cùng mã A**, không sinh mã mới.
    - Lịch sử đơn 1 vẫn chỉ **một** mốc "Duyệt yêu cầu"; cửa sổ Shop chỉ có **một** thông báo duyệt cho đơn 1.

## E. Từ chối (UC05.8)

- [ ] **E1**
  - Làm: cửa sổ NV mở đơn 2 → "Từ chối".
  - Mong đợi:
    - Hộp "Từ chối yêu cầu gửi hàng?" có ô "Lý do từ chối *".
    - Nút "Từ chối" **bị khóa** khi ô trống.
- [ ] **E2**
  - Làm: gõ toàn dấu cách.
  - Mong đợi: nút "Từ chối" vẫn khóa.
- [ ] **E3**
  - Làm: bấm "Không từ chối".
  - Mong đợi: hộp đóng, đơn 2 vẫn "Chờ xác nhận" (A1).
- [ ] **E4**
  - Làm: mở lại hộp, gõ "  Địa chỉ chưa có số nhà  " → "Từ chối".
  - Mong đợi:
    - Thông báo xanh "Đã từ chối yêu cầu…"; nhãn "Bị từ chối".
    - Khung đỏ "Lý do từ chối: Địa chỉ chưa có số nhà" (đã cắt khoảng trắng); **không** có mã vận đơn.
- [ ] **E5**
  - Làm: cửa sổ Shop mở đơn 2.
  - Mong đợi: khung đỏ "Yêu cầu bị từ chối. Lý do: Địa chỉ chưa có số nhà"; không còn nút Sửa/Hủy.
- [ ] **E6**
  - Làm: cửa sổ Shop, màn Thông báo.
  - Mong đợi: "Yêu cầu YC… bị từ chối", nội dung "Lý do: Địa chỉ chưa có số nhà", có "Xem vận đơn →".

## F. Shop hủy đúng lúc Nhân viên đang duyệt (UC05.6 E1)

- [ ] **F1**
  - Làm:
    1. Cửa sổ NV mở đơn 3 → "Duyệt" (để hộp mở, **chưa** bấm).
    2. Cửa sổ Shop mở đơn 3 → "Hủy yêu cầu" → "Hủy yêu cầu".
    3. Cửa sổ NV bấm "Duyệt" trong hộp.
  - Mong đợi:
    - Hộp đóng, cảnh báo vàng "Yêu cầu đang ở trạng thái Đã hủy nên không duyệt được. …".
    - Đơn 3 hiện "Đã hủy", hết nút; **không** có mã vận đơn.
- [ ] **F2**
  - Làm: "Tổng quan" của Nhân viên.
  - Mong đợi: ô ghi **"0 yêu cầu chờ duyệt"**, "Đã xử lý hết", không còn màu cam.

## G. Phân quyền

- [ ] **G1**
  - Làm: đăng nhập `demo_shipper` (cửa sổ ẩn danh mới), gõ `/staff/shipments`.
  - Mong đợi: bị đưa về trang Shipper.
- [ ] **G2**
  - Làm: cửa sổ Shop gõ `/staff/shipments/` + id của đơn 1 (xem trên URL chi tiết Shop).
  - Mong đợi: bị đưa về trang Shop, không xem được màn Nhân viên.

---

## Tổng kết

| Nhóm | Số bước | Đạt | Lỗi (ghi bước + mô tả) |
|---|---|---|---|
| A. Menu, trang chủ | 3 | | |
| B. Danh sách | 7 | | |
| C. Chi tiết | 4 | | |
| D. Duyệt | 7 | | |
| E. Từ chối | 6 | | |
| F. Hủy chồng duyệt | 2 | | |
| G. Phân quyền | 2 | | |
| **Tổng** | **31** | | |
