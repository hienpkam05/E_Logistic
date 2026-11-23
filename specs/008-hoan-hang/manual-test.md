# Spec 008 — Kịch bản thử trên trình duyệt

Dùng cho bước 6.3 ở [tasks.md](tasks.md). Mỗi bước ghi **Làm** và **Mong đợi**. Đánh `[x]` khi đúng, ghi lỗi vào bảng tổng kết cuối file.

Phần khó tạo bằng tay đã có test tự động, không cần thử ở đây (xem tasks.md Phase 2–3):
- hai Nhân viên cùng tiếp nhận / cùng xác nhận Shop nhận;
- Shipper báo bàn giao đúng lúc Nhân viên tiếp nhận;
- hàng đã ở điểm tập kết khi Chờ xử lý hoàn (tiếp nhận thẳng, không chuyến hoàn) — chỉ xảy ra sau đổi Shipper (spec 009);
- phân công hoàn cho Shipper khác người đang giữ — demo chỉ có 1 Shipper hoạt động, màn hình cũng không cho chọn.

## Chuẩn bị (một lần)

1. Docker + database, backend `runserver`, frontend `npm.cmd run dev` — như [spec 007](../007-giao-hang-cod/manual-test.md#chuẩn-bị-một-lần).
2. Mật khẩu trong `backend/.demo-accounts.txt`. 3 phiên tách biệt tại `http://127.0.0.1:5173`: **Shop** (`demo_shop`), **NV** (`demo_nhanvien`, ẩn danh), **Shipper** (`demo_shipper`, trình duyệt khác, **cỡ điện thoại**).
3. `demo_shipper` phải đang hoạt động.
4. **Điểm tập kết:** nếu `backend/.env` chưa có `HUB_NAME`, `HUB_ADDRESS`, `HUB_PHONE` thì hệ thống dùng giá trị demo — "Điểm tập kết HTT EXPRESS (demo)", "Số 1 Phố Demo, Phường Demo, Hà Nội", `0900 000 000`. Muốn đổi: thêm 3 biến vào `.env` rồi khởi động lại backend.

**Tạo dữ liệu — cần 3 đơn ở "Chờ xử lý hoàn":**

Nếu vừa thử spec 007 thì đã có sẵn: **đơn 4** (bước F6) và **đơn 3** (bước G4) — dùng làm **đơn A** và **đơn B**; tạo thêm **đơn C** như dưới. Nếu không, tạo cả 3:

1. Phiên Shop tạo yêu cầu → NV duyệt → phân công lấy cho `demo_shipper` → Shipper "Đã lấy hàng" → NV "Xác nhận tiếp nhận".
2. NV "Phân công giao hàng" (tích "Shipper đã nhận hàng") → Shipper "Giao thất bại" (lý do bất kỳ).
3. NV mở đơn → **"Chuyển hoàn"** với lý do: đơn A "Khách từ chối nhận", đơn B "Sai địa chỉ", đơn C "Khách hủy đơn".
4. Ghi lại mã `HTT…` của đơn A, B, C.

**Sau khi thử xong:** mở khóa `demo_shipper` nếu còn khóa (nhóm H khóa tài khoản này).

---

## A. Menu, trang chủ, tab

- [ ] **A1**
  - Làm: phiên Shipper → "Tổng quan".
  - Mong đợi: 3 ô **giao hàng · lấy hàng · hoàn hàng** đang làm; mục "Sắp có" chỉ còn "Chia sẻ vị trí khi làm nhiệm vụ".
- [ ] **A2**
  - Làm: Shipper → "Nhiệm vụ".
  - Mong đợi: chip **Tất cả · Lấy hàng · Giao hàng · Hoàn hàng**.
- [ ] **A3**
  - Làm: phiên NV → "Quản lý vận đơn".
  - Mong đợi:
    - 5 tab **Chờ xác nhận · Lấy hàng · Giao hàng · Hoàn hàng · Tất cả** (gộp theo giai đoạn — D10).
    - Bấm "Giao hàng": chip Tất cả · Đã nhập điểm tập kết · Chờ giao lại · Giao hàng thất bại. Bấm một chip → danh sách chỉ còn trạng thái đó, URL có `&status=…`.

## B. Phân công hoàn (UC06.7)

- [ ] **B1**
  - Làm: tab **"Hoàn hàng"**.
  - Mong đợi: chip Tất cả · Chờ xử lý hoàn · Đang hoàn · Chờ Shop đến lấy; thấy đơn A, B, C, cũ nhất ở trên.
- [ ] **B2**
  - Làm: mở đơn A.
  - Mong đợi: chỉ có nút **"Phân công hoàn hàng"**; Điều phối "Đang giữ hàng: Shipper · …".
- [ ] **B3**
  - Làm: bấm "Phân công hoàn hàng".
  - Mong đợi:
    - Hộp nêu kiện hàng, "Đưa về: <tên điểm tập kết>", dòng "Lý do hoàn xem ở mục Lịch sử".
    - Chỉ **một** Shipper (người đang giữ), chọn sẵn, không có ô tìm, có giải thích đổi Shipper.
    - **Không** có ô "đã nhận hàng" (người đó đang giữ sẵn — D3).
- [ ] **B4**
  - Làm: "Phân công hoàn".
  - Mong đợi: báo "Đã phân công hoàn cho …"; trạng thái **Đang hoàn**; nút đổi thành "Ghi sai lệch" + "Tiếp nhận hàng hoàn".
- [ ] **B5**
  - Làm: phiên Shipper → chuông; phiên Shop → chuông.
  - Mong đợi:
    - Shipper: **"Nhiệm vụ hoàn hàng mới: HTT…"**, nội dung "Đưa hàng về <tên>: <địa chỉ>."; bấm Xem mở thẳng nhiệm vụ.
    - Shop: **không** có thông báo mới cho bước phân công hoàn (D9).

## C. Shipper xem nhiệm vụ hoàn (UC04.8)

- [ ] **C1**
  - Làm: Shipper → "Nhiệm vụ" → chip **"Hoàn hàng"**.
  - Mong đợi: thẻ ghi "HOÀN HÀNG", mã đơn A, tên Shop, **"Về <tên điểm tập kết>"**, số kiện.
- [ ] **C2**
  - Làm: mở nhiệm vụ.
  - Mong đợi:
    - Thẻ **"Đưa hàng về"**: tên, địa chỉ, SĐT điểm tập kết + nút "Gọi điểm tập kết".
    - **"Lý do hoàn: Khách từ chối nhận"**.
    - Thẻ Kiện hàng có "Hàng của Shop".
- [ ] **C3**
  - Làm: xem kỹ trang.
  - Mong đợi: **không** có người nhận, địa chỉ giao, COD, SĐT người gửi (D8).
- [ ] **C4**
  - Làm: xem thanh nút dưới đáy.
  - Mong đợi: đúng **một** nút **"Đã đưa hàng về điểm tập kết"** — không có nút tiếp nhận (UC04.9 BR1).

## D. Shipper báo đã đưa hàng về (UC04.9 bước 1–3)

- [ ] **D1**
  - Làm: bấm "Đã đưa hàng về điểm tập kết".
  - Mong đợi: hộp nêu mã, Shop, số kiện, dòng "Chỉ bấm khi đã giao hàng tận tay cho Nhân viên tại điểm tập kết…".
- [ ] **D2**
  - Làm: "Tôi đã giao hàng cho điểm tập kết".
  - Mong đợi:
    - Báo "Đã báo đưa hàng về. Nhân viên điểm tập kết sẽ kiểm tra…".
    - Dòng xanh **"Đã báo đưa hàng về lúc … — chờ Nhân viên điểm tập kết xác nhận tiếp nhận."**
    - **Hết nút**; nhiệm vụ vẫn "Đang thực hiện" (A1).
- [ ] **D3**
  - Làm: quay lại danh sách hoàn.
  - Mong đợi: thẻ đơn A có nhãn **"Đã báo đưa về — chờ xác nhận"**.
- [ ] **D4**
  - Làm: phiên NV → chuông.
  - Mong đợi: **"Shipper … đã đưa hàng hoàn HTT… về điểm tập kết"**, nội dung "Kiểm tra mã đơn, số kiện, tình trạng hàng rồi xác nhận tiếp nhận."

## E. Nhân viên tiếp nhận hàng hoàn (UC04.9 bước 4–7)

- [ ] **E1**
  - Làm: NV mở đơn A (tải lại trang).
  - Mong đợi: Điều phối, nhiệm vụ "Hoàn hàng": dòng **"Shipper đã báo đưa hàng về lúc …"**.
- [ ] **E2**
  - Làm: "Tiếp nhận hàng hoàn".
  - Mong đợi: hộp nêu mã, Shipper giao, kiện hàng; **không** có cảnh báo vàng (Shipper đã báo).
- [ ] **E3**
  - Làm: ghi chú "Hộp móp nhẹ" → "Xác nhận tiếp nhận".
  - Mong đợi:
    - Báo "Đã tiếp nhận hàng hoàn. Đơn chờ Shop đến lấy…".
    - Trạng thái **Chờ Shop đến lấy**; Điều phối "Đang giữ hàng: Điểm tập kết"; nhiệm vụ hoàn "Hoàn tất".
    - Lịch sử "Tiếp nhận hàng hoàn": người giữ hàng Shipper → Điểm tập kết, ghi chú sai lệch "Hộp móp nhẹ".
    - Nút còn lại: **"Xác nhận Shop đã nhận"**.
- [ ] **E4**
  - Làm: phiên Shop → chuông.
  - Mong đợi: **"Hàng hoàn HTT… đã về điểm tập kết"**, nội dung "Mời Shop đến nhận tại <tên>: <địa chỉ> (SĐT <số>)."
- [ ] **E5**
  - Làm: phiên Shipper mở lại nhiệm vụ đơn A.
  - Mong đợi: "Hoàn tất"; dòng "Điểm tập kết đã tiếp nhận lúc …"; không còn dòng "chờ Nhân viên…".

## F. Tiếp nhận khi Shipper chưa báo + ghi sai lệch (D5, UC04.9 E1)

- [ ] **F1**
  - Làm: NV phân công hoàn **đơn B**. Phiên Shipper **mở sẵn** nhiệm vụ đơn B nhưng **không bấm gì**.
  - Mong đợi: Shipper thấy nút "Đã đưa hàng về điểm tập kết".
- [ ] **F2**
  - Làm: NV mở đơn B → "Tiếp nhận hàng hoàn".
  - Mong đợi: cảnh báo vàng **"Shipper chưa báo đã đưa hàng về. Chỉ xác nhận khi đã nhận kiện hàng thực tế."**
- [ ] **F3**
  - Làm: bấm **"Có sai lệch, chưa nhận?"**.
  - Mong đợi: chuyển sang hộp đỏ **"Ghi sai lệch hàng hoàn"** — "Đơn vẫn Đang hoàn, CHƯA tiếp nhận…"; nút "Ghi sai lệch" mờ khi chưa nhập.
- [ ] **F4**
  - Làm: nhập "Thiếu 1 kiện" → "Ghi sai lệch".
  - Mong đợi:
    - Báo "Đã ghi sai lệch vào lịch sử. Đơn vẫn chờ tiếp nhận."; trạng thái **vẫn Đang hoàn**.
    - Lịch sử có mốc "Ghi sai lệch hàng hoàn" — Lý do: Thiếu 1 kiện.
    - (Cũng ghi được bằng nút "Ghi sai lệch" trên đầu trang.)
- [ ] **F5**
  - Làm: NV "Tiếp nhận hàng hoàn" → "Xác nhận tiếp nhận" (vẫn có cảnh báo vàng). Sau đó ở phiên Shipper (trang đơn B **mở từ trước**) bấm "Đã đưa hàng về điểm tập kết" → xác nhận.
  - Mong đợi:
    - NV: tiếp nhận được dù Shipper chưa báo → Chờ Shop đến lấy.
    - Shipper: báo vàng **"Nhiệm vụ đã kết thúc hoặc đã chuyển cho người khác…"**, trang tải lại, nhiệm vụ "Hoàn tất", không còn nút.

## G. Xác nhận Shop nhận hàng hoàn (UC04.11)

- [ ] **G1**
  - Làm: phiên Shop mở đơn A.
  - Mong đợi: trạng thái Chờ Shop đến lấy; thẻ **"Đến nhận hàng hoàn tại"** — tên, địa chỉ, SĐT điểm tập kết + nút gọi; dòng "Khi đến nhận, Nhân viên sẽ kiểm tra người nhận…". **Không** có nút tự xác nhận (BR1).
- [ ] **G2**
  - Làm: NV mở đơn A → "Xác nhận Shop đã nhận".
  - Mong đợi:
    - Hộp nêu mã, Shop + SĐT, kiện hàng.
    - Ô **"Tên người nhận"** điền sẵn tên Shop, gợi ý "sửa nếu người đến nhận là người được Shop ủy quyền".
    - Ô tích **"Đã kiểm tra người nhận thuộc Shop hoặc được Shop ủy quyền"** — chưa tích thì nút "Xác nhận đã bàn giao" mờ.
- [ ] **G3**
  - Làm: tích ô, rồi xóa trắng tên.
  - Mong đợi: nút lại mờ (tên bắt buộc).
- [ ] **G4**
  - Làm: nhập "Chị Hoa (ủy quyền)" → "Xác nhận đã bàn giao".
  - Mong đợi:
    - Báo "Đã xác nhận Shop nhận lại hàng. Luồng hoàn kết thúc…".
    - Trạng thái **Đã hoàn về Shop**; không còn nút thao tác.
    - Thẻ **"Kết quả hoàn"**: Nhận lại lúc …, Người nhận "Chị Hoa (ủy quyền)".
- [ ] **G5**
  - Làm: phiên Shop tải lại đơn A + chuông.
  - Mong đợi: thẻ "Kết quả hoàn" giống G4, không còn thẻ "Đến nhận…"; thông báo **"Shop đã nhận lại hàng hoàn HTT…"**, nội dung "Người nhận: Chị Hoa (ủy quyền)."

## H. Shipper giữ hàng bị khóa

- [ ] **H1**
  - Làm: NV → Quản lý Shipper → `demo_shipper` → Khóa (đơn C đang Chờ xử lý hoàn, hàng ở Shipper này).
  - Mong đợi: khóa được.
- [ ] **H2**
  - Làm: NV mở đơn C.
  - Mong đợi: Điều phối cảnh báo **"Shipper đang giữ hàng đã bị khóa tài khoản…"**.
- [ ] **H3**
  - Làm: "Phân công hoàn hàng".
  - Mong đợi: hộp có cảnh báo vàng, **không** có danh sách Shipper, nút "Phân công hoàn" mờ. Mở khóa `demo_shipper` → tải lại → phân công hoàn được như B3–B4.

## I. Phân quyền

- [ ] **I1**
  - Làm: phiên Shop xem đơn đang hoàn.
  - Mong đợi: thấy trạng thái + lịch sử; **không** thấy Shipper phụ trách / nhiệm vụ / nút thao tác.
- [ ] **I2**
  - Làm: phiên Shipper gõ `/staff/shipments`.
  - Mong đợi: bị đưa về trang Shipper.
- [ ] **I3**
  - Làm: phiên NV mở tab "Hoàn hàng" với URL lạ `?tab=return&status=DELIVERED`.
  - Mong đợi: bỏ qua trạng thái lạ, hiện cả giai đoạn Hoàn hàng (chip "Tất cả" được chọn).

---

## Tổng kết

| Nhóm | Số bước | Đạt | Lỗi (ghi bước + mô tả) |
|---|---|---|---|
| A. Menu, trang chủ, tab | 3 | | |
| B. Phân công hoàn | 5 | | |
| C. Shipper xem nhiệm vụ hoàn | 4 | | |
| D. Shipper báo đã đưa về | 4 | | |
| E. NV tiếp nhận | 5 | | |
| F. Chưa báo + sai lệch | 5 | | |
| G. Shop nhận hàng hoàn | 5 | | |
| H. Shipper giữ hàng bị khóa | 3 | | |
| I. Phân quyền | 3 | | |
| **Tổng** | **37** | | |
