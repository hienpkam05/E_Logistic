# Spec 007 — Kịch bản thử trên trình duyệt

Dùng cho bước 6.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**. Đánh `[x]` khi đúng, ghi lỗi vào bảng tổng kết cuối file.

Phần khó tạo bằng tay đã có test tự động, không cần thử ở đây (xem tasks.md Phase 2–3):
- hai Nhân viên phân công giao cùng lúc;
- Shipper bấm "Giao thành công" và "Giao thất bại" cùng lúc, hoặc bấm 3 lần liền;
- giao lại và hoàn cùng lúc;
- giao lại bằng **Shipper khác** khi hàng đang ở Shipper cũ — demo chỉ có 1 Shipper hoạt động, và màn hình cũng không cho chọn người khác.

## Chuẩn bị (một lần)

1. Docker Desktop + database: `docker compose --env-file backend/.env up -d db`
2. Backend: `cd backend` → `..\venv\Scripts\python manage.py runserver`
3. Frontend (terminal khác): `cd frontend` → `npm.cmd run dev`
4. Mật khẩu xem trong `backend/.demo-accounts.txt`.
5. Mở **3 phiên tách biệt** tại `http://127.0.0.1:5173` (như spec 006):

| Phiên | Cách mở | Tài khoản |
|---|---|---|
| **Shop** | cửa sổ thường | `demo_shop` |
| **NV** | cửa sổ ẩn danh | `demo_nhanvien` |
| **Shipper** | trình duyệt khác, **cỡ điện thoại** (F12 → biểu tượng điện thoại) | `demo_shipper` |

`demo_shipper` phải **đang hoạt động**. Nếu vừa thử spec 006 nhóm H mà chưa mở khóa: NV → Quản lý Shipper → `demo_shipper` → Mở khóa.

**Tạo dữ liệu thử — đưa 4 đơn tới "Đã nhập điểm tập kết":**

| Đơn | Người nhận (gợi ý) | COD |
|---|---|---|
| **Đơn 1** | Nguyễn Thị Lan | 350.000 |
| **Đơn 2** | Trần Văn Minh | 0 (không thu hộ) |
| **Đơn 3** | Phạm Thu Hà | 200.000 |
| **Đơn 4** | Lê Quang Huy | 150.000 |

1. Phiên Shop tạo 4 yêu cầu theo bảng trên.
2. Phiên NV duyệt cả 4, rồi phân công lấy cho `demo_shipper`.
3. Phiên Shipper: mỗi đơn bấm "Đã lấy hàng".
4. Phiên NV: tab "Đã lấy hàng" → mỗi đơn bấm "Xác nhận tiếp nhận".
5. Ghi lại mã `HTT…` của từng đơn.

**Sau khi thử xong:**
- Mở khóa `demo_shipper` nếu còn khóa (nhóm H khóa tài khoản này).
- Xóa dữ liệu thử nếu muốn: dùng lệnh ở cuối [manual-test spec 006](../006-lay-hang-diem-tap-ket/manual-test.md#chuẩn-bị-một-lần).

---

## A. Menu và trang chủ

- [ ] **A1**
  - Làm: phiên Shipper, xem thanh bên (điện thoại: bấm ☰).
  - Mong đợi: mục **"Nhiệm vụ"** (không còn chữ "Nhiệm vụ lấy hàng").
- [ ] **A2**
  - Làm: "Tổng quan" của Shipper.
  - Mong đợi:
    - Có 2 ô: **"0 nhiệm vụ giao hàng đang làm"** và **"0 nhiệm vụ lấy hàng đang làm"**.
    - Mục "Sắp có" **không còn** "Nhiệm vụ giao hàng, ghi nhận COD".
- [ ] **A3**
  - Làm: phiên NV → "Quản lý vận đơn".
  - Mong đợi: 8 tab: Chờ xác nhận · Chờ lấy hàng · Lấy hàng thất bại · Đã lấy hàng · **Đã nhập điểm tập kết · Chờ giao lại · Giao hàng thất bại** · Tất cả.

## B. Phân công giao hàng (UC06.6)

- [ ] **B1**
  - Làm: tab "Đã nhập điểm tập kết".
  - Mong đợi: 4 đơn, cũ nhất ở trên.
- [ ] **B2**
  - Làm: mở đơn 1.
  - Mong đợi:
    - Chỉ có nút **"Phân công giao hàng"**.
    - Điều phối: "Đang giữ hàng: Điểm tập kết", "Số lần giao: **0/3**".
- [ ] **B3**
  - Làm: bấm "Phân công giao hàng".
  - Mong đợi:
    - Hộp nêu Giao đến (người nhận, địa chỉ), Thu hộ 350.000 ₫, **Lần giao 1/3**.
    - Có danh sách Shipper và ô **"Shipper đã nhận hàng tại điểm tập kết"**.
- [ ] **B4**
  - Làm: chọn `demo_shipper` nhưng **chưa tích** ô bàn giao.
  - Mong đợi: nút "Phân công giao" **mờ, không bấm được** (D6).
- [ ] **B5**
  - Làm: tích ô → "Phân công giao".
  - Mong đợi:
    - Báo "Đã phân công giao lần 1 cho …".
    - Trạng thái **Đang giao hàng**.
    - Điều phối: giữ hàng "Shipper · …", Số lần giao **vẫn 0/3** (phân công không tăng số lần).
    - Lịch sử: "Phân công giao hàng" với người giữ hàng Điểm tập kết → Shipper, Lần giao → 1.
- [ ] **B6**
  - Làm: phiên Shop → chuông thông báo.
  - Mong đợi: **"Vận đơn HTT… đang được giao"**, nội dung "Shipper … đang giao lần 1/3".

## C. Shipper xem nhiệm vụ giao (UC04.4)

- [ ] **C1**
  - Làm: phiên Shipper → chuông.
  - Mong đợi: "Nhiệm vụ giao hàng mới: HTT…"; bấm "Xem" mở thẳng nhiệm vụ.
- [ ] **C2**
  - Làm: "Nhiệm vụ" → bấm chip **"Giao hàng"**.
  - Mong đợi:
    - URL có `?type=DELIVERY`.
    - Thẻ ghi "GIAO HÀNG · LẦN 1/3", người nhận, địa chỉ giao, **COD 350.000 ₫**.
- [ ] **C3**
  - Làm: mở nhiệm vụ.
  - Mong đợi:
    - Thẻ "Giao đến": tên, địa chỉ, SĐT người nhận + nút **"Gọi người nhận"**.
    - Thẻ "Thu hộ (COD)": **350.000 ₫** chữ to.
    - **Không** có "Lấy hàng tại", SĐT người gửi (D3).
    - Thẻ Kiện hàng có "Hàng của Shop".
- [ ] **C4**
  - Làm: chip "Tất cả" rồi "Lấy hàng".
  - Mong đợi: "Tất cả" có cả nhiệm vụ giao lẫn lấy; "Lấy hàng" chỉ còn tab Đang làm trống ("Chưa có nhiệm vụ lấy hàng.").

## D. Giao thành công + COD (UC04.5, UC04.7)

- [ ] **D1**
  - Làm: nhiệm vụ đơn 1 → **"Giao thành công"**.
  - Mong đợi:
    - Hộp nêu mã, người nhận; ô "COD phải thu 350.000 ₫".
    - Ô "Số tiền đã thu" **để trống** (không điền sẵn — D5).
    - Nút "Người nhận đã nhận hàng" mờ.
- [ ] **D2**
  - Làm: gõ `330000`.
  - Mong đợi:
    - Ô hiện `330.000`.
    - Dòng đỏ **"Thiếu 20.000 ₫ — chưa thu đủ thì ghi giao thất bại…"**; nút vẫn mờ.
- [ ] **D3**
  - Làm: sửa thành `370000`.
  - Mong đợi: **"Thừa 20.000 ₫ so với COD phải thu."**; nút vẫn mờ.
- [ ] **D4**
  - Làm: sửa thành `350000` → "Người nhận đã nhận hàng".
  - Mong đợi:
    - "Khớp COD phải thu." rồi báo **đã giao thành công**.
    - Kết quả ghi "Đã giao lúc … · đã thu COD 350.000 ₫".
    - **Mất nút "Gọi người nhận"** và số điện thoại (nhiệm vụ đã đóng — BR2).
- [ ] **D5**
  - Làm: phiên Shop mở đơn 1.
  - Mong đợi:
    - Trạng thái **Đã giao hàng**.
    - Thẻ **"Kết quả giao"**: Giao lúc, Lần giao 1, **COD đã thu 350.000 ₫**.
    - Không thấy thẻ Điều phối / nhiệm vụ.
    - Thông báo "Vận đơn … đã giao thành công", nội dung "Đã thu COD 350.000 ₫".
- [ ] **D6**
  - Làm: NV phân công giao **đơn 2** (không COD); Shipper mở nhiệm vụ → "Giao thành công".
  - Mong đợi:
    - Thẻ "Thu hộ" ghi "Không thu hộ".
    - Hộp ghi **"Đơn không thu COD"**, không có ô nhập, nút bấm được ngay.
    - Xong: Shop nhận "đã giao thành công", **không** nêu tiền.

## E. Giao thất bại (UC04.6)

- [ ] **E1**
  - Làm: NV phân công giao **đơn 3**. Shipper mở nhiệm vụ → "Giao thành công" → bấm **"Chưa thu đủ? Ghi giao thất bại"**.
  - Mong đợi:
    - Chuyển sang hộp "Giao hàng thất bại", **lý do chọn sẵn "Người nhận chưa đủ tiền COD"**.
    - Dòng "Lần giao 1/3. Hàng vẫn do bạn giữ; bạn không tự quyết định hoàn."
- [ ] **E2**
  - Làm: đổi lý do thành **"Khác"**, để trống ghi chú.
  - Mong đợi:
    - Danh sách lý do là của **giao hàng** (không liên hệ được, hẹn lại, từ chối, chưa đủ COD, sai địa chỉ, Khác).
    - Nút "Ghi nhận thất bại" mờ.
- [ ] **E3**
  - Làm: chọn **"Không liên hệ được người nhận"** → "Ghi nhận thất bại".
  - Mong đợi:
    - Báo "…Hàng vẫn do bạn giữ — Nhân viên sẽ quyết định giao lại hay hoàn."
    - Kết quả "Giao thất bại: Không liên hệ được người nhận".
- [ ] **E4**
  - Làm: phiên NV → chuông; tab "Giao hàng thất bại" → mở đơn 3.
  - Mong đợi:
    - Thông báo "Giao hàng thất bại: HTT… (lần 1/3)" (Shop cũng nhận).
    - Ô đỏ "Giao lần 1/3 thất bại: Không liên hệ được người nhận".
    - Nút **"Chuyển hoàn"** và **"Giao lại"**.
    - Điều phối: giữ hàng "Shipper · …", **Số lần giao 1/3**, nhiệm vụ "Giao hàng · lần 1 — Thất bại", lý do.

## F. Giao lại / hoàn (UC04.12)

- [ ] **F1**
  - Làm: đơn 3 → "Giao lại", để trống lý do.
  - Mong đợi: hộp nêu "đã giao 1/3 lần… phân công lần 2"; nút "Giao lại" mờ.
- [ ] **F2**
  - Làm: nhập "Khách hẹn sau 17h" → "Giao lại".
  - Mong đợi:
    - Trạng thái **Chờ giao lại**; còn đúng nút "Phân công giao hàng".
    - Shop nhận **"Vận đơn … sẽ được giao lại"** kèm lý do.
- [ ] **F3**
  - Làm: bấm "Phân công giao hàng".
  - Mong đợi:
    - Tiêu đề **"Phân công giao lại"**, Lần giao **2/3**.
    - Chỉ có **một** Shipper (người đang giữ hàng), chọn sẵn, **không có ô tìm**, có dòng giải thích đổi Shipper (D7).
    - Ô tích ghi "Shipper đang giữ hàng và sẵn sàng giao lại".
- [ ] **F4**
  - Làm: tích → "Phân công giao".
  - Mong đợi: "Đã phân công giao lần 2…"; Shipper thấy thẻ "GIAO HÀNG · LẦN 2/3".
- [ ] **F5**
  - Làm: NV phân công giao **đơn 4**; Shipper ghi thất bại lý do **"Người nhận từ chối nhận"**; NV mở đơn 4 → **"Chuyển hoàn"**.
  - Mong đợi: hộp đỏ "Chuyển hoàn về Shop?", nêu "đã giao 1/3 lần… không giao tiếp nữa"; lý do bắt buộc.
- [ ] **F6**
  - Làm: nhập "Khách từ chối nhận" → "Chuyển hoàn".
  - Mong đợi:
    - Trạng thái **Chờ xử lý hoàn** (hoàn sớm ở lần 1 được — A1.2).
    - Shop nhận **"Vận đơn … chuyển hoàn về Shop"**.
    - Không có nút phân công giao.

## G. Giới hạn 3 lần (D8)

- [ ] **G1**
  - Làm: đơn 3 (đang giao lần 2): Shipper ghi thất bại → NV "Giao lại" → phân công lần 3.
  - Mong đợi: thẻ của Shipper "LẦN 3/3".
- [ ] **G2**
  - Làm: Shipper ghi thất bại lần 3; NV mở đơn 3.
  - Mong đợi:
    - Ô đỏ "Giao lần 3/3 thất bại: … — **đã đủ 3 lần nên chỉ được chuyển hoàn**".
    - Chỉ còn nút **"Chuyển hoàn"**, không có "Giao lại".
    - Điều phối: Số lần giao **3/3**, 3 nhiệm vụ giao lần 1, 2, 3 + nhiệm vụ lấy.
- [ ] **G3**
  - Làm: xem lịch sử đơn 3.
  - Mong đợi: đủ các mốc phân công / thất bại / giao lại, mỗi lần thất bại có "Số lần đã giao: N−1 → N" và lý do.
- [ ] **G4**
  - Làm: "Chuyển hoàn" với lý do bất kỳ.
  - Mong đợi: trạng thái Chờ xử lý hoàn.

## H. Shipper đang giữ hàng bị khóa (D7)

Cần một đơn **Chờ giao lại** mà hàng ở `demo_shipper`. Tạo thêm **đơn 5** theo phần Chuẩn bị: phân công giao → Shipper thất bại → NV "Giao lại".

- [ ] **H1**
  - Làm: NV → Quản lý Shipper → `demo_shipper` → Khóa (lý do bất kỳ).
  - Mong đợi: khóa được (đơn 5 không còn nhiệm vụ mở nên không có cảnh báo "nhiệm vụ đang mở").
- [ ] **H2**
  - Làm: NV mở đơn 5.
  - Mong đợi: thẻ Điều phối có cảnh báo **"Shipper đang giữ hàng đã bị khóa tài khoản — chưa phân công giao được…"**.
- [ ] **H3**
  - Làm: bấm "Phân công giao hàng".
  - Mong đợi: hộp có cảnh báo vàng, **không có** danh sách Shipper / ô tích, nút "Phân công giao" mờ.
- [ ] **H4**
  - Làm: mở khóa `demo_shipper`, tải lại đơn 5.
  - Mong đợi: hết cảnh báo; phân công giao lại được như F3–F4.

## I. Phân quyền và hiển thị khác

- [ ] **I1**
  - Làm: phiên Shipper gõ `/staff/shipments`.
  - Mong đợi: bị đưa về trang Shipper.
- [ ] **I2**
  - Làm: phiên Shop mở đơn đang giao / giao thất bại.
  - Mong đợi: thấy trạng thái + lịch sử; **không** thấy Shipper phụ trách, nhiệm vụ, cảnh báo khóa; không có nút thao tác.
- [ ] **I3**
  - Làm: phiên Shipper mở lại nhiệm vụ **lấy hàng** đã xong (spec 006).
  - Mong đợi: còn tên người gửi, **không còn SĐT và nút "Gọi"** (D3 áp dụng cả nhiệm vụ lấy).
- [ ] **I4**
  - Làm: thu nhỏ phiên Shipper còn ~390px, mở nhiệm vụ giao đang làm.
  - Mong đợi: hai nút "Giao thất bại" / "Giao thành công" dính đáy màn hình, dễ bấm; hộp COD vừa màn hình.

---

## Tổng kết

| Nhóm | Số bước | Đạt | Lỗi (ghi bước + mô tả) |
|---|---|---|---|
| A. Menu, trang chủ | 3 | | |
| B. Phân công giao | 6 | | |
| C. Shipper xem nhiệm vụ giao | 4 | | |
| D. Giao thành công + COD | 6 | | |
| E. Giao thất bại | 4 | | |
| F. Giao lại / hoàn | 6 | | |
| G. Giới hạn 3 lần | 4 | | |
| H. Shipper giữ hàng bị khóa | 4 | | |
| I. Phân quyền, hiển thị | 4 | | |
| **Tổng** | **41** | | |
