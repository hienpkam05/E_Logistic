# Spec 009 — Kịch bản người dùng thử trình duyệt

Đối chiếu [spec.md](spec.md), [API](api.md), [kết quả tự động](acceptance.md).
**Chưa có kết quả người dùng tự thử.** Chỉ đánh `[x]` bên dưới sau khi chính người thử làm và thấy đúng.
Các bài kiểm thử tự động đã đạt được ghi riêng, không thay cho chữ ký nghiệm thu của người dùng.

## Chuẩn bị

1. Chạy PostgreSQL, Django và Vite theo README; mở `http://127.0.0.1:5173`.
2. Dùng các phiên trình duyệt tách biệt cho **Nhân viên**, **Shop**, **Shipper A**, **Shipper B**.
   Có thể dùng tài khoản demo hiện có; mật khẩu lấy từ file demo trên máy, không chép vào tài liệu này.
3. Cần hai Shipper hoạt động; nếu mới có một người, Nhân viên vào Quản lý Shipper tạo B.
   B đăng nhập và đổi mật khẩu tạm trước khi thử. Tạo thêm C nếu thử thay người dự kiến khi B bị khóa.
4. Có phường/xã hoạt động và thông tin điểm tập kết trong meta. Ghi lại mã vận đơn của các đơn thử.
5. Thử cả desktop 1440px và mobile 390px (DevTools). Trước khi thao tác, kiểm tra đúng mã đơn và người giữ hàng.

Tạo đơn chuẩn: Shop tạo yêu cầu → NV duyệt → phân công lấy A.
Muốn tới bước giao: A báo đã lấy → NV xác nhận tiếp nhận tại điểm tập kết → phân công giao A,
tích xác nhận A đã nhận hàng thực tế. Mỗi kịch bản dùng đơn mới hoặc ghi rõ bước nối tiếp.

## A. Đổi người trước khi lấy hàng

- [ ] **A1 — Mở hộp đổi.** Làm: NV mở đơn đang phân công lấy A, bấm **Đổi Shipper**.
  Mong đợi: nêu A, số kiện và thay ngay do chưa nhận hàng; danh sách không có A; chưa chọn người/lý do thì không xác nhận.
- [ ] **A2 — Đổi sang B.** Làm: chọn B, nhập lý do, xác nhận một lần.
  Mong đợi: đơn vẫn Đã phân công lấy; nhiệm vụ cũ Đã thay thế → B, nhiệm vụ mới của B; lịch sử có người đổi và lý do.
- [ ] **A3 — Quyền hai người.** Làm: A tải lại nhiệm vụ cũ, B mở danh sách và nhiệm vụ mới.
  Mong đợi: A chỉ xem, không nút lấy/thất bại, không SĐT liên hệ; B có đúng đơn và bấm **Đã lấy hàng** được.
- [ ] **A4 — Thông báo.** Làm: kiểm thông báo A, B và Shop.
  Mong đợi: A được báo thay thế, B nhận nhiệm vụ; Shop không có thông báo đổi người nội bộ.

## B. Đổi người khi đang giữ hàng giao

- [ ] **B1 — Bắt đầu chờ.** Làm: trên đơn đang giao bởi A, NV chọn đổi sang B và nhập lý do.
  Mong đợi: đơn vẫn Đang giao; nhiệm vụ A Chờ bàn giao đổi Shipper, B chỉ là dự kiến; nơi giữ hàng vẫn A;
  số lần đã giao không đổi. A nhận thông báo đưa hàng về có địa chỉ điểm tập kết, B chưa nhận nhiệm vụ.
- [ ] **B2 — Shipper cũ.** Làm: A tải lại trang nhiệm vụ trên điện thoại.
  Mong đợi: dải cảnh báo, thẻ điểm tập kết + nút gọi, kiện hàng; không thẻ giao người nhận/COD,
  không nút giao thành công/thất bại; chỉ **Đã đưa hàng về điểm tập kết**.
- [ ] **B3 — Chưa cấp quyền.** Làm: B tải lại danh sách đang làm.
  Mong đợi: chưa thấy nhiệm vụ dự kiến. Thử mở link nhiệm vụ A sẽ không tìm thấy (API 404).
- [ ] **B4 — Báo đưa về.** Làm: A bấm nút báo đưa về và xác nhận đã giao tận tay điểm tập kết.
  Mong đợi: hiện thời điểm báo + chờ NV; nút báo biến mất. NV nhận thông báo; chưa có nhiệm vụ mới cho B.
- [ ] **B5 — Nhận thực tế.** Làm: NV bấm **Xác nhận nhận hàng bàn giao**.
  Mong đợi: nêu A, B, số kiện; chưa tích đã nhận đủ/người mới đã nhận thì nút xác nhận bị khóa.
  Nếu A chưa báo, hiện cảnh báo nhưng NV vẫn được xác nhận sau khi thực tế nhận hàng.
- [ ] **B6 — Hoàn tất đổi.** Làm: sau khi kiểm đủ hàng và giao B, tích xác nhận, ghi chú tùy chọn, gửi.
  Mong đợi: nhiệm vụ A Đã thay thế → B; B có nhiệm vụ giao **cùng lần giao**, người giữ là B,
  số lần đã giao không đổi; A không ghi kết quả/COD được. Thông báo A giữ lý do đổi người, không lấy ghi chú nhận hàng làm lý do.

## C. Người dự kiến, sai lệch và tài khoản bị khóa

- [ ] **C1 — Ghi sai lệch.** Làm: trên đơn chờ bàn giao, NV bấm **Ghi sai lệch bàn giao**, nhập tình trạng thiếu/sai kiện.
  Mong đợi: lý do bắt buộc; lưu lịch sử, giữ chờ; B chưa được giao nhiệm vụ, chưa đổi người giữ.
- [ ] **C2 — Đổi dự kiến.** Làm: bấm Đổi Shipper khi còn chờ; đổi B sang C và nhập lý do.
  Mong đợi: chọn sẵn B khi mở, không có A trong danh sách; sau gửi, dự kiến là C, chưa tạo nhiệm vụ mới.
  Không có thao tác hủy đổi để trao lại quyền giao/COD cho A.
- [ ] **C3 — Người mới bị khóa.** Làm: để B là dự kiến; ở tab khác NV khóa B rồi quay lại xác nhận bàn giao.
  Mong đợi: 409, báo chọn người khác và tải bản mới; không báo thành công, không bàn giao/nhiệm vụ/tiền ghi nửa chừng.
  Chọn C hoạt động rồi xác nhận lại mới được phân công.
- [ ] **C4 — Người cũ bị khóa.** Làm: khóa A khi còn chờ, ghi nhận tiếp nhận thực tế từ A bằng tài khoản NV.
  Mong đợi: A mất phiên và không báo được; NV vẫn xác nhận được sau khi kiểm đủ hàng, người mới hợp lệ nhận nhiệm vụ.

## D. Khóa Shipper và nhận hàng về khi không còn nhiệm vụ mở

- [ ] **D1 — Hộp khóa.** Làm: mở Khóa tài khoản của Shipper đang có nhiệm vụ lấy/giao/hoàn mở.
  Mong đợi: có số nhiệm vụ, mã đơn (link), loại, trạng thái và cảnh báo cần xử lý; không tải được thì có Thử lại,
  không cho khóa khi chưa xem được danh sách. Tài khoản không phải Shipper không gọi/tải khối này.
- [ ] **D2 — Đổi lấy khi A khóa.** Làm: sau khóa A còn nhiệm vụ lấy, NV đổi sang B.
  Mong đợi: nhiệm vụ cũ đóng, mới không `needs_attention`; cảnh báo khóa trên nhiệm vụ mở hết.
- [ ] **D3 — Nhận về để giao lại.** Làm: A giao thất bại → NV quyết định giao lại; khóa A nếu cần;
  NV nhận thực tế kiện hàng rồi bấm **Nhận hàng về điểm tập kết**, nhập ghi chú tùy chọn.
  Mong đợi: hàng ở điểm tập kết, trạng thái vẫn Chờ giao lại, hết cảnh báo người giữ bị khóa;
  phân công giao lại B được, lần giao tiếp theo đúng số; không gửi thông báo riêng cho nhận về.
- [ ] **D4 — Nhận về để hoàn.** Làm: với đơn Chờ xử lý hoàn, không nhiệm vụ mở, hàng ở A,
  NV nhận về điểm tập kết rồi **Tiếp nhận hàng hoàn**.
  Mong đợi: vào Chờ Shop đến lấy, không tạo chuyến hoàn thừa. Nếu nhiệm vụ hoàn đã đang mở thì dùng Tiếp nhận hàng hoàn,
  không có Đổi Shipper; vẫn xử lý được khi A bị khóa/chưa báo đưa về.

## E. Ba lần giao, dữ liệu cũ và kết thúc

- [ ] **E1 — Không đặt lại lượt.** Làm: giao thất bại lần 1, NV cho giao lại; đổi người khi đang giao lần 2 hoặc 3,
  thực hiện bàn giao đúng B1–B6 rồi tiếp tục giao thất bại.
  Mong đợi: nhiệm vụ thay thế giữ số lần của nhiệm vụ cũ; đổi người không tăng/đặt lại số lần đã giao;
  sau thất bại thứ 3 chỉ còn Chuyển hoàn, không có Giao lại hoặc lần 4.
- [ ] **E2 — Dữ liệu vừa đổi.** Làm: hai tab NV mở cùng một đơn; tab đầu thay người dự kiến, tab sau gửi lựa chọn khác
  trên dữ liệu cũ. Mong đợi: tab sau báo xung đột, đóng hộp và tải bản mới; không ghi đè thao tác tab đầu.
- [ ] **E3 — Đơn kết thúc.** Làm: xem đơn Đã giao/Đã hoàn về Shop, nhiệm vụ thất bại hoặc nhiệm vụ hoàn đang mở.
  Mong đợi: không có Đổi Shipper cho các trường hợp không hợp lệ; lịch sử cũ còn nguyên.
- [ ] **E4 — Mobile và lỗi.** Làm: thử hộp đổi/nhận/khóa ở 390px, thử mất mạng khi mở danh sách Shipper/nhiệm vụ mở.
  Mong đợi: đọc/bấm được, không tràn ngang, giữ dữ liệu nhập khi lỗi để thử lại, không báo thành công giả.

## Bằng chứng tự động và tổng kết người dùng

Đã kiểm tự động: quyền chéo và trạng thái, gửi lại, transaction rollback, COD/lượt giao, khóa tài khoản khi báo,
hai NV xác nhận, hai thiết bị báo, hai thứ tự giao thành công/đổi người; 3 smoke API trọn luồng.
Chrome headless đã bấm A/B và luồng ba lần giao trên database test; ảnh desktop/mobile tại artifacts.
Các kiểm tra đó không dùng dữ liệu hoặc mật khẩu demo thật của người dùng.

| Nhóm | Người dùng tự thử | Lỗi / mã đơn / ghi chú |
|---|---|---|
| A — Đổi lấy | Chưa thử | |
| B — Đổi giao + bàn giao | Chưa thử | |
| C — Sai lệch, dự kiến, khóa | Chưa thử | |
| D — Nhiệm vụ mở, nhận về | Chưa thử | |
| E — Giới hạn lượt, xung đột, mobile | Chưa thử | |

Người thử: … · Ngày: … · Kết luận: …
