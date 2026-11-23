# Spec 004 — Kịch bản thử trên trình duyệt

Dùng cho bước 6.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**; đánh `[x]` khi đúng, ghi lỗi vào bảng tổng kết cuối file.

Phần khó tạo bằng tay đã có test tự động, không cần thử ở đây:
- hai thao tác cùng lúc (test 2 luồng);
- Shop A mở đơn của Shop B (`404`);
- gửi `shop`/`status` giả lên API.

Xem tasks.md Phase 2–3.

## Chuẩn bị (một lần)

1. Docker Desktop + database: `docker compose --env-file backend/.env up -d db`
2. Backend: `cd backend` → `..\venv\Scripts\python manage.py runserver`
3. Frontend (terminal khác): `cd frontend` → `npm.cmd run dev`
4. Mật khẩu xem trong `backend/.demo-accounts.txt`.
5. Mở `http://127.0.0.1:5173`. Nhóm D cần thêm **một tab thứ hai** cùng tài khoản.

| Dữ liệu (21/11/2026) | Giá trị |
|---|---|
| Người thử | `demo_shop`: "Shop Demo Hoàn Kiếm", SĐT `0999000003`, địa chỉ "1 Tràng Tiền, Hoàn Kiếm, Hà Nội" |
| Phường/xã demo | `[Demo] Phường A`, `[Demo] Phường B`, `[Demo] Phường C`, `[Demo] Xã D`, `[Demo] Xã E`. Đây là dữ liệu giả, chưa có danh sách thật (D1). |
| Vận đơn | Chưa có đơn nào |
| Tài khoản khác | `demo_nhanvien` (Nhân viên), `demo_shipper` (Shipper) — dùng ở nhóm G |

Mã yêu cầu bắt đầu từ `YC00000010` (các id đã dùng khi smoke test và chụp giao diện không quay lại). Kịch bản ghi **"đơn 1", "đơn 2"** thay vì mã cụ thể.

**Sau khi thử xong** (không bắt buộc), xóa các đơn thử của `demo_shop`. App không có nút xóa — đúng nghiệp vụ, bản ghi phải giữ lại. Lệnh xóa:

```powershell
cd backend
..\venv\Scripts\python manage.py shell -c "from apps.shipments.models import Shipment, ShipmentEvent; q = Shipment.objects.filter(shop__username='demo_shop'); ShipmentEvent.objects.filter(shipment__in=q).delete(); print(q.delete())"
```

---

## A. Menu và trang chủ Shop

- [ ] **A1**
  - Làm: đăng nhập `demo_shop`.
  - Mong đợi: thanh bên trái có "Tổng quan", "Vận đơn của tôi", "Tạo yêu cầu gửi hàng".
- [ ] **A2**
  - Làm: bấm "Vận đơn của tôi".
  - Mong đợi:
    - URL `/shop/shipments`, tiêu đề "Vận đơn của tôi".
    - Khung "Bạn chưa có yêu cầu gửi hàng nào." có nút "Tạo yêu cầu đầu tiên".

## B. Tạo yêu cầu (UC05.2)

- [ ] **B1**
  - Làm: bấm "Tạo yêu cầu đầu tiên".
  - Mong đợi:
    - Form có 4 nhóm: Người gửi, Người nhận, Kiện hàng, Thu hộ (COD).
    - Nhóm Người gửi **điền sẵn** "Shop Demo Hoàn Kiếm", `0999000003`, "1 Tràng Tiền, Hoàn Kiếm, Hà Nội".
    - Số kiện = 1, COD = 0 (dưới ô ghi "Không thu hộ").
- [ ] **B2**
  - Làm: bấm "Gửi yêu cầu" ngay, chưa điền thêm gì.
  - Mong đợi:
    - Lỗi đỏ dưới các ô còn trống: phường lấy hàng, người nhận, SĐT, phường giao, địa chỉ giao, mô tả hàng.
    - Vẫn ở trang tạo.
- [ ] **B3**
  - Làm: ô lọc phường lấy hàng gõ `phuong a` (không dấu).
  - Mong đợi: danh sách chỉ còn "[Demo] Phường A". Chọn nó.
- [ ] **B4**
  - Làm: điền
    - Người nhận "Trần Thị B", SĐT `12345`;
    - Phường giao "[Demo] Phường B", địa chỉ "5 Láng Hạ";
    - Mô tả "Áo len", Số kiện `0`, COD `-1000`.
  - Bấm "Gửi yêu cầu".
  - Mong đợi: lỗi dưới SĐT người nhận ("10 chữ số, bắt đầu bằng 0"), Số kiện và COD.
- [ ] **B5**
  - Làm: sửa lại SĐT `0987654321`, Số kiện `2`, COD `350000`.
  - Mong đợi: dưới ô COD hiện "350.000 ₫".
  - Bấm "Gửi yêu cầu".
  - Mong đợi:
    - Sang trang chi tiết, tiêu đề là mã `YC…` (**đơn 1**), nhãn "Chờ xác nhận".
    - Có thông báo xanh "Đã gửi yêu cầu…".
    - Dòng mã ghi "Mã vận đơn được cấp khi Nhân viên duyệt".
- [ ] **B6**
  - Làm: menu "Tạo yêu cầu gửi hàng". Đổi tên người gửi thành "Kho Cầu Giấy", điền người nhận "Lê Văn C", `0911222333`, "[Demo] Xã D", "Thôn 3", mô tả "Sách", COD 0.
  - Bấm "Gửi yêu cầu" (**đơn 2**).
  - Mong đợi:
    - Tạo được; chi tiết nhóm Người gửi là "Kho Cầu Giấy".
    - Hồ sơ Shop **không đổi**: mở "Hồ sơ" vẫn là "Shop Demo Hoàn Kiếm".
- [ ] **B7**
  - Làm: menu "Tạo yêu cầu gửi hàng", gõ vài ô rồi bấm "Hủy".
  - Mong đợi: về danh sách, **không** có đơn mới (vẫn 2 đơn).

## C. Danh sách — lọc, tìm (UC05.3)

- [ ] **C1**
  - Làm: "Vận đơn của tôi".
  - Mong đợi:
    - 2 dòng, đơn 2 ở trên (mới nhất).
    - Cột Mã có `YC…` + chữ nhỏ "mã yêu cầu"; cột Giao đến là tên phường.
    - Thu hộ: đơn 1 "350.000 ₫", đơn 2 "—". Trạng thái "Chờ xác nhận".
- [ ] **C2**
  - Làm: gõ `Lê Văn` → Tìm.
  - Mong đợi: chỉ đơn 2; URL có `?q=…`.
- [ ] **C3**
  - Làm: gõ số đuôi mã của đơn 1 (vd `05`) → Tìm.
  - Mong đợi: tìm ra đơn 1.
- [ ] **C4**
  - Làm: xóa ô tìm → Tìm, rồi chọn trạng thái "Đã hủy".
  - Mong đợi: khung "Không có vận đơn phù hợp với bộ lọc." + nút "Bỏ lọc".
  - Bấm "Bỏ lọc" → về đủ 2 đơn, URL sạch.
- [ ] **C5**
  - Làm: chọn lọc "Chờ xác nhận", rồi **F5**.
  - Mong đợi: sau khi tải lại vẫn giữ lọc (URL `?status=PENDING_APPROVAL`).
- [ ] **C6**
  - Làm: thử dán vào ô tìm một chuỗi rất dài.
  - Mong đợi: ô không nhận quá 100 ký tự (giới hạn lấy từ backend).

## D. Chi tiết và sửa (UC05.4, UC05.1)

- [ ] **D1**
  - Làm: bấm mã đơn 1.
  - Mong đợi:
    - 4 thẻ: Người gửi, Người nhận, Kiện hàng (Khối lượng "Không ghi"), Thu hộ (COD "350.000 ₫", Ghi chú "Không có").
    - Nút "Sửa yêu cầu" và "Hủy yêu cầu".
    - Lịch sử 1 mốc "Tạo yêu cầu gửi hàng", người làm "Shop Demo Hoàn Kiếm".
- [ ] **D2**
  - Làm: "Sửa yêu cầu" → đổi COD `400000`, Phường giao "[Demo] Phường C", Ghi chú "Gọi trước" → "Lưu thay đổi".
  - Mong đợi:
    - Về chế độ xem, thông báo "Đã lưu thay đổi yêu cầu.", thông tin mới.
    - Lịch sử thêm mốc "Sửa yêu cầu" liệt kê:
      - COD: 350.000 ₫ → 400.000 ₫;
      - Phường/xã giao hàng: [Demo] Phường B → [Demo] Phường C;
      - Ghi chú: (trống) → Gọi trước.
- [ ] **D3**
  - Làm: "Sửa yêu cầu" → "Hủy" (nút cuối form).
  - Mong đợi: về chế độ xem, không lưu gì, lịch sử không thêm mốc.
- [ ] **D4** *(2 tab — người khác vừa sửa)*
  - Làm:
    1. Mở đơn 1 ở **tab 2** (cùng tài khoản).
    2. Tab 1 bấm "Sửa yêu cầu".
    3. Tab 2 bấm "Sửa yêu cầu" → đổi ghi chú "Tab 2" → Lưu.
    4. Quay lại tab 1, đổi ghi chú "Tab 1" → Lưu.
  - Mong đợi:
    - Tab 1 hiện cảnh báo vàng "Yêu cầu vừa được thay đổi. Vui lòng tải lại." + nút "Tải bản mới nhất".
    - **Không** ghi đè bản của tab 2.
- [ ] **D5**
  - Làm: tab 1 bấm "Tải bản mới nhất".
  - Mong đợi:
    - Cảnh báo biến mất, form vẫn mở với ghi chú "Tab 2".
    - Sửa thành "Tab 1" → Lưu được.
- [ ] **D6**
  - Làm: gõ URL `/shop/shipments/999999`.
  - Mong đợi: "Không tìm thấy vận đơn" — giống hệt khi mở đơn của Shop khác.

## E. Hủy yêu cầu (UC05.5)

- [ ] **E1**
  - Làm: mở đơn 2 → "Hủy yêu cầu".
  - Mong đợi:
    - Hộp "Hủy yêu cầu gửi hàng?" nêu mã đơn, nói bản ghi vẫn được giữ.
    - Có ô lý do (không bắt buộc), nút "Hủy yêu cầu" (đỏ) và "Không hủy".
- [ ] **E2**
  - Làm: bấm "Không hủy".
  - Mong đợi: hộp đóng, đơn vẫn "Chờ xác nhận".
- [ ] **E3**
  - Làm: mở lại hộp, lý do "Khách đổi ý" → "Hủy yêu cầu".
  - Mong đợi:
    - Nhãn "Đã hủy", thông báo "Đã hủy yêu cầu.".
    - **Mất** cả nút Sửa lẫn Hủy.
    - Lịch sử có mốc "Hủy yêu cầu": "Chờ xác nhận → Đã hủy", "Lý do: Khách đổi ý".
- [ ] **E4**
  - Làm: về danh sách, lọc "Đã hủy".
  - Mong đợi: đơn 2 vẫn còn (không bị xóa).

## F. Đơn vừa được duyệt — Shop hết sửa/hủy (UC05.1 E1, UC05.5 E1)

*(Cập nhật sau spec 005: duyệt bằng màn hình thật, không còn lệnh giả lập.)* Cần **cửa sổ ẩn danh** đăng nhập `demo_nhanvien` → menu "Quản lý vận đơn".

- [ ] **F1**
  - Làm:
    1. Cửa sổ Shop: mở đơn 1, bấm "Sửa yêu cầu" (để form mở).
    2. Cửa sổ Nhân viên: tab "Chờ xác nhận" → mở đơn 1 → "Duyệt" → xác nhận "Duyệt".
    3. Cửa sổ Shop: ở form, đổi ghi chú → Lưu.
  - Mong đợi: cảnh báo vàng "Yêu cầu không còn ở trạng thái Chờ xác nhận nên không sửa được." + "Tải bản mới nhất".
- [ ] **F2**
  - Làm: bấm "Tải bản mới nhất".
  - Mong đợi:
    - Form đóng; tiêu đề đổi thành mã vận đơn `HTT…` (ghi lại, gọi là **mã A**), nhãn "Chờ lấy hàng".
    - Không còn nút Sửa/Hủy; dữ liệu giữ nguyên bản trước.
    - Lịch sử có mốc "Duyệt yêu cầu" với "Mã vận đơn: (trống) → mã A".
- [ ] **F3**
  - Làm: danh sách.
  - Mong đợi: đơn 1 hiện **mã A**, **không** còn chữ "mã yêu cầu".
- [ ] **F4** *(tùy chọn — hủy đúng lúc vừa duyệt)*
  - Làm: tạo **đơn 3** → mở chi tiết → "Hủy yêu cầu" (để hộp mở) → cửa sổ Nhân viên duyệt đơn 3 → quay lại bấm "Hủy yêu cầu" trong hộp.
  - Mong đợi:
    - Trong hộp báo "…không hủy được.", nút "Hủy yêu cầu" bị **khóa**.
    - Trang phía sau đã đổi sang mã vận đơn của đơn 3, "Chờ lấy hàng". Bấm "Không hủy" để đóng.

## G. Phân quyền màn hình

- [ ] **G1**
  - Làm: đăng xuất, đăng nhập `demo_nhanvien`, gõ `/shop/shipments`.
  - Mong đợi: bị đưa về trang Nhân viên; thanh bên không có "Vận đơn của tôi".
- [ ] **G2**
  - Làm: tương tự với `demo_shipper`.
  - Mong đợi: bị đưa về trang Shipper.
- [ ] **G3**
  - Làm: đăng xuất, gõ `/shop/shipments/new`.
  - Mong đợi: về trang đăng nhập. Đăng nhập `demo_shop` → quay lại đúng trang tạo yêu cầu.

---

## Tổng kết

| Nhóm | Số bước | Đạt | Lỗi (ghi bước + mô tả) |
|---|---|---|---|
| A. Menu | 2 | | |
| B. Tạo | 7 | | |
| C. Danh sách | 6 | | |
| D. Chi tiết, sửa | 6 | | |
| E. Hủy | 4 | | |
| F. Đã duyệt | 4 | | |
| G. Phân quyền | 3 | | |
| **Tổng** | **32** | | |
