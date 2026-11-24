# Spec 010 — Thử trình duyệt (UC03.1–03.2)

Người thử: … · Ngày: … · Kết quả/lỗi: …

Các ô dưới đây dành cho người dùng tự xác nhận. Kiểm thử Chrome tự động không thay thế bước này.
Chạy backend/frontend theo README, dùng tài khoản và dữ liệu thử; không nhập mật khẩu vào báo cáo.
Chuẩn bị hai Shop A/B, một Nhân viên và một Shipper; ghi mã YC/HTT của mỗi Shop.
Nên có một đơn mới tạo, một đơn đã phân công lấy và một đơn giao lại có đổi Shipper từ spec 009.

## Shop

- [ ] Đăng nhập Shop A, mở menu **Tra cứu vận đơn**. Chưa nhập thì có hướng dẫn, chưa có kết quả.
- [ ] Để trống rồi tra cứu: báo lỗi tại ô mã. Nhập đúng YC và HTT của A, thử chữ thường và khoảng trắng đầu/cuối: tìm thấy đúng đơn.
- [ ] Kết quả có trạng thái, người nhận, ngày tạo/cập nhật; **Xem chi tiết** mở trang Shop đúng đơn.
- [ ] Nhập một phần mã, mã không tồn tại và mã của B: đều không tìm thấy; không hiện thông tin đơn B.
- [ ] Tải lại URL `?code=…`, đi sang chi tiết rồi quay lại: mã và kết quả được khôi phục.
- [ ] Trong DevTools Network chuyển Offline rồi tra cứu: có lỗi, giữ mã. Chuyển Online và bấm **Thử lại**: tìm thấy đơn.
- [ ] Bấm **Lịch sử vận chuyển**: cuộn tới lịch sử, tiêu đề không bị thanh trên che. Đơn mới tạo hiện **Chưa phát sinh vận chuyển**.
- [ ] Đơn đã xử lý có tên người xử lý, thời gian và trạng thái; không hiện username/SĐT nội bộ. Có nhãn **Lần lấy N**, **Lần giao N**, **Đổi Shipper** đúng mốc. Đổi người giữ nguyên số lần giao.
- [ ] Chuyển **Cũ nhất trước** rồi **Mới nhất trước**, kiểm tra thời gian; nếu nhiều trang thì đổi thứ tự trở về trang 1 và sang trang tiếp được.

## Nhân viên và Shipper

- [ ] Nhân viên tra được đơn của cả A và B; kết quả có tên Shop, link chi tiết/lịch sử mở trang Nhân viên đúng đơn.
- [ ] Shipper không có menu tra cứu; nhập trực tiếp `/tracking` bị đưa về trang được phép. Chưa đăng nhập thì phải đăng nhập.

## Hiển thị

- [ ] Kiểm tra ở chiều rộng 1440 và 390 px: không tràn ngang; ô mã, nút, kết quả và lịch sử đọc/bấm được.
- [ ] Mở Console trong lúc thử: không có Vue warning hoặc lỗi trang. Ghi rõ URL/bước tái hiện nếu có lỗi.

Không đánh dấu đạt cho dữ liệu chưa chuẩn bị hoặc luồng chưa thử. Có thể ghi “chưa thử” kèm mục còn thiếu.
