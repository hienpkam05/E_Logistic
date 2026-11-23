# Spec 006 — Kịch bản thử trên trình duyệt

Dùng cho bước 6.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**; đánh `[x]` khi đúng, ghi lỗi vào bảng tổng kết cuối file.

Phần khó tạo bằng tay đã có test tự động, không cần thử ở đây:
- hai Nhân viên phân công cùng lúc;
- Shipper bấm "Đã lấy hàng" và "Thất bại" cùng lúc;
- khóa Shipper đúng lúc đang phân công.

Xem tasks.md Phase 2–3.

## Chuẩn bị (một lần)

1. Docker Desktop + database: `docker compose --env-file backend/.env up -d db`
2. Backend: `cd backend` → `..\venv\Scripts\python manage.py runserver`
3. Frontend (terminal khác): `cd frontend` → `npm.cmd run dev`
4. Mật khẩu xem trong `backend/.demo-accounts.txt`.
5. Mở **3 phiên tách biệt** tại `http://127.0.0.1:5173`:

| Phiên | Cách mở | Tài khoản |
|---|---|---|
| **Shop** | cửa sổ thường | `demo_shop` |
| **NV** | cửa sổ ẩn danh | `demo_nhanvien` |
| **Shipper** | trình duyệt khác (Edge / Firefox), **thu nhỏ cửa sổ cỡ điện thoại** hoặc bật chế độ điện thoại (F12 → biểu tượng điện thoại) | `demo_shipper` |

| Dữ liệu lúc bắt đầu (22/11/2026) | Giá trị |
|---|---|
| Vận đơn | Chưa có; mã yêu cầu tiếp theo `YC00000010` |
| Shipper | `demo_shipper` (hoạt động), `demo_khoa` (bị khóa) |

**Tạo dữ liệu thử:**
1. Phiên Shop tạo **3 yêu cầu** (người nhận tùy ý): **đơn 1**, **đơn 2**, **đơn 3**.
2. Phiên NV → "Quản lý vận đơn" → tab "Chờ xác nhận" → **duyệt cả 3**.
3. Ghi lại mã vận đơn `HTT…` của từng đơn.

**Sau khi thử xong:**
- Mở khóa lại `demo_shipper` (nhóm H khóa tài khoản này): NV → Quản lý Shipper → `demo_shipper` → Mở khóa.
- Xóa dữ liệu thử (không bắt buộc):

```powershell
cd backend
..\venv\Scripts\python manage.py shell -c "from apps.dispatch.models import Handover, Task, TaskResult; from apps.notifications.models import Notification; from apps.shipments.models import Shipment, ShipmentEvent; q = Shipment.objects.filter(shop__username='demo_shop'); ids = list(q.values_list('id', flat=True)); Notification.objects.filter(payload__shipment_id__in=ids).delete(); ShipmentEvent.objects.filter(shipment__in=q).delete(); Handover.objects.filter(shipment__in=q).delete(); TaskResult.objects.filter(task__shipment__in=q).delete(); Task.objects.filter(shipment__in=q).delete(); print(q.delete())"
```

---

## A. Menu và trang chủ

- [ ] **A1**
  - Làm: phiên Shipper, xem thanh bên (điện thoại: bấm ☰).
  - Mong đợi: có "Tổng quan" và **"Nhiệm vụ lấy hàng"**.
- [ ] **A2**
  - Làm: "Tổng quan" của Shipper.
  - Mong đợi: ô **"0 nhiệm vụ lấy hàng đang làm"**, dòng "Chưa có nhiệm vụ mới".
- [ ] **A3**
  - Làm: phiên NV → "Quản lý vận đơn".
  - Mong đợi: 5 tab **Chờ xác nhận · Chờ lấy hàng · Lấy hàng thất bại · Đã lấy hàng · Tất cả**.

## B. Phân công lấy hàng (UC06.5)

- [ ] **B1**
  - Làm: tab "Chờ lấy hàng".
  - Mong đợi: 3 đơn, **cũ nhất ở trên**, dòng "Cũ nhất trước — xử lý theo thứ tự đến".
- [ ] **B2**
  - Làm: mở đơn 1.
  - Mong đợi:
    - Chỉ có nút **"Phân công lấy hàng"**.
    - Thẻ "Điều phối": "Shipper phụ trách: Chưa phát sinh", "Nhiệm vụ: Chưa phát sinh".
- [ ] **B3**
  - Làm: bấm "Phân công lấy hàng".
  - Mong đợi:
    - Hộp nêu địa chỉ lấy + số kiện.
    - Danh sách có **Shipper Demo — "Đang rảnh"**, **không** có `demo_khoa` (bị khóa).
    - Nút "Phân công" bị khóa khi chưa chọn ai.
- [ ] **B4**
  - Làm: chọn Shipper Demo → "Phân công".
  - Mong đợi:
    - Thông báo xanh "Đã phân công cho Shipper Demo…"; nhãn "Đã phân công lấy hàng".
    - Thẻ Điều phối: Shipper phụ trách = Shipper Demo + SĐT; nhiệm vụ "Lấy hàng — Đang thực hiện".
    - Lịch sử: "Phân công lấy hàng" với "**Shipper: (trống) → Shipper Demo**".
- [ ] **B5**
  - Làm: mở đơn 2 → "Phân công lấy hàng".
  - Mong đợi: Shipper Demo hiện **"1 nhiệm vụ đang mở"**. Chọn → Phân công.
- [ ] **B6**
  - Làm: phiên Shipper → chuông thông báo.
  - Mong đợi: 2 thông báo "Nhiệm vụ lấy hàng mới: HTT…". Bấm **"Xem vận đơn →"** mở đúng **nhiệm vụ** của đơn đó.

## C. Shipper xem nhiệm vụ (UC04.1)

- [ ] **C1**
  - Làm: "Nhiệm vụ lấy hàng".
  - Mong đợi:
    - Tab "Đang làm", 2 thẻ.
    - Mỗi thẻ: mã vận đơn, "Đang thực hiện", tên Shop, **địa chỉ lấy**, số kiện, giờ phân công.
- [ ] **C2**
  - Làm: bấm thẻ đơn 1.
  - Mong đợi:
    - "Lấy hàng tại" (Shop, địa chỉ, người gửi + SĐT, nút **Gọi**), "Kiện hàng" (mô tả, số kiện, khối lượng, ghi chú).
    - **Không** thấy người nhận, địa chỉ giao, tiền thu hộ (D3).
- [ ] **C3**
  - Làm: xem đáy màn hình (cỡ điện thoại).
  - Mong đợi: thanh dính đáy có 2 nút to "Lấy hàng thất bại" và "Đã lấy hàng".
- [ ] **C4**
  - Làm: "Tổng quan" của Shipper.
  - Mong đợi: ô ghi **"2 nhiệm vụ lấy hàng đang làm"** (màu cam).

## D. Lấy hàng thành công (UC04.2)

- [ ] **D1**
  - Làm: Shipper mở đơn 1 → "Đã lấy hàng".
  - Mong đợi: hộp "Xác nhận đã lấy hàng?" nêu mã, Shop, số kiện, hàng; nút **"Tôi đã nhận đủ hàng"**.
- [ ] **D2**
  - Làm: bấm "Tôi đã nhận đủ hàng".
  - Mong đợi:
    - Thông báo "Đã ghi nhận lấy hàng. Hãy mang hàng về điểm tập kết…"; nhãn "Hoàn tất".
    - Dòng "Đã lấy hàng lúc …"; **hết** nút thao tác.
- [ ] **D3**
  - Làm: phiên Shop → chuông.
  - Mong đợi: "Vận đơn HTT… đã được lấy — Shipper Shipper Demo đã nhận hàng…". Chi tiết đơn ở phía Shop: "Đã lấy hàng".
- [ ] **D4**
  - Làm: phiên NV → tab "Đã lấy hàng".
  - Mong đợi: có đơn 1. Mở ra: "Đang giữ hàng: **Shipper · Shipper Demo**", nút "Xác nhận tiếp nhận".

## E. Nhập điểm tập kết (UC04.10)

- [ ] **E1**
  - Làm: "Xác nhận tiếp nhận".
  - Mong đợi: hộp nêu mã vận đơn, **Shipper giao = Shipper Demo**, số kiện + mô tả; có ô "Ghi chú sai lệch (không bắt buộc)".
- [ ] **E2**
  - Làm: ghi "  Hộp hơi móp  " → "Xác nhận tiếp nhận".
  - Mong đợi:
    - Nhãn "Đã nhập điểm tập kết", "Đang giữ hàng: **Điểm tập kết**".
    - Lịch sử: "Người giữ hàng: Shipper Demo → Điểm tập kết", "Ghi chú sai lệch: (trống) → Hộp hơi móp" (đã cắt khoảng trắng).
- [ ] **E3**
  - Làm: thử bấm lại (tải lại trang).
  - Mong đợi: không còn nút "Xác nhận tiếp nhận" (đã tiếp nhận).

## F. Lấy hàng thất bại (UC04.3)

- [ ] **F1**
  - Làm: Shipper mở đơn 2 → "Lấy hàng thất bại".
  - Mong đợi: hộp có ô "Lý do *" (6 lựa chọn) và "Ghi chú"; nút "Ghi nhận thất bại" bị khóa.
- [ ] **F2**
  - Làm: chọn lý do **"Khác"**.
  - Mong đợi: nhãn đổi thành "Ghi chú (bắt buộc với lý do Khác)"; nút vẫn khóa tới khi ghi chú.
- [ ] **F3**
  - Làm: đổi sang "Shop vắng mặt / không liên lạc được", ghi chú "Gọi 3 lần" → "Ghi nhận thất bại".
  - Mong đợi: nhãn "Thất bại", dòng "Lấy thất bại: Shop vắng mặt… — Gọi 3 lần (…)"; hết nút.
- [ ] **F4**
  - Làm: phiên NV và phiên Shop → chuông.
  - Mong đợi: **cả hai** có "Lấy hàng thất bại: HTT…" kèm lý do.
- [ ] **F5**
  - Làm: phiên NV → tab "Lấy hàng thất bại" → mở đơn 2.
  - Mong đợi:
    - Nút "Kết thúc" và "Lấy lại".
    - Thẻ Điều phối: nhiệm vụ "Thất bại", "Lý do: Shop vắng mặt… — Gọi 3 lần"; "Đang giữ hàng: Shop".

## G. Xử lý lấy hàng thất bại (UC04.13)

- [ ] **G1**
  - Làm: "Lấy lại".
  - Mong đợi: hộp nói đơn quay về Chờ lấy hàng, lịch sử được giữ; nút khóa tới khi nhập lý do.
- [ ] **G2**
  - Làm: lý do "Shop hẹn chiều" → "Lấy lại".
  - Mong đợi: "Chờ lấy hàng"; nút **"Phân công lấy hàng"** hiện lại ngay. Phiên Shop nhận "Vận đơn … sẽ được lấy lại".
- [ ] **G3**
  - Làm: phân công lại cho Shipper Demo.
  - Mong đợi: thẻ Điều phối có **2 nhiệm vụ** (mới "Đang thực hiện", cũ "Thất bại").
- [ ] **G4**
  - Làm: phiên Shipper → tab "Đã xong" → mở nhiệm vụ cũ của đơn 2.
  - Mong đợi: chỉ xem, **không** có nút (nhiệm vụ cũ đã đóng).
- [ ] **G5**
  - Làm: Shipper mở nhiệm vụ mới của đơn 2 → "Lấy hàng thất bại" → "Shop không muốn gửi nữa" → ghi nhận.
  - Mong đợi: ghi nhận thành công.
- [ ] **G6**
  - Làm: phiên NV mở đơn 2 → "Kết thúc".
  - Mong đợi: hộp đỏ nói "không hoàn tác được"; nhập lý do "Shop không gửi nữa" → "Kết thúc".
- [ ] **G7**
  - Làm: xem đơn 2.
  - Mong đợi:
    - Nhãn "Kết thúc do không lấy được hàng", **hết** nút; mã vận đơn vẫn giữ.
    - Phiên Shop nhận thông báo kèm lý do.

## H. Khóa Shipper khi còn nhiệm vụ (D9)

- [ ] **H1**
  - Làm: phiên NV phân công **đơn 3** cho Shipper Demo.
  - Mong đợi: thành công.
- [ ] **H2**
  - Làm: NV → "Quản lý Shipper" → `demo_shipper` → "Khóa tài khoản" → xác nhận.
  - Mong đợi: khóa thành công.
- [ ] **H3**
  - Làm: NV → chuông.
  - Mong đợi: "**Shipper Shipper Demo bị khóa khi còn 1 nhiệm vụ đang mở** — Cần đổi Shipper…".
- [ ] **H4**
  - Làm: mở đơn 3.
  - Mong đợi:
    - Thẻ Điều phối có cảnh báo vàng "Shipper phụ trách đã bị khóa tài khoản khi nhiệm vụ còn mở — cần đổi Shipper".
    - Nhiệm vụ **vẫn còn** (không tự đóng).
- [ ] **H5**
  - Làm: phiên Shipper tải lại trang.
  - Mong đợi: bị đưa về trang đăng nhập (đã bị khóa).
- [ ] **H6**
  - Làm: NV mở khóa lại `demo_shipper` (để dùng tiếp).
  - Mong đợi: mở khóa được. Cảnh báo ở đơn 3 **vẫn còn** — việc đổi Shipper / gỡ cảnh báo thuộc spec 009.

## I. Phân quyền

- [ ] **I1**
  - Làm: phiên Shipper (đăng nhập lại) gõ `/staff/shipments`.
  - Mong đợi: bị đưa về trang Shipper.
- [ ] **I2**
  - Làm: phiên Shipper gõ `/shipper/tasks/999999`.
  - Mong đợi: "Không tìm thấy nhiệm vụ".
- [ ] **I3**
  - Làm: phiên Shop gõ `/shipper/tasks`.
  - Mong đợi: bị đưa về trang Shop.

---

## Tổng kết

| Nhóm | Số bước | Đạt | Lỗi (ghi bước + mô tả) |
|---|---|---|---|
| A. Menu, trang chủ | 3 | | |
| B. Phân công | 6 | | |
| C. Shipper xem nhiệm vụ | 4 | | |
| D. Lấy thành công | 4 | | |
| E. Nhập điểm tập kết | 3 | | |
| F. Lấy thất bại | 5 | | |
| G. Lấy lại / kết thúc | 7 | | |
| H. Khóa Shipper | 6 | | |
| I. Phân quyền | 3 | | |
| **Tổng** | **41** | | |
