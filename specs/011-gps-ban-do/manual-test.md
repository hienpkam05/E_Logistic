# Spec 011 — Thử tay GPS và chỉ đường

Người thử: … · Ngày: … · Thiết bị/trình duyệt: … · Kết quả/lỗi: …

Các ô dưới dành cho người dùng xác nhận, không đánh dấu thay bằng browser tự động.
Chạy backend/frontend theo README; review/apply migration tracking theo quy trình DB local trước khi thử.
Dùng dữ liệu thử gồm Shop A/B, Nhân viên, Shipper cũ/mới và nhiệm vụ lấy/giao/hoàn.

## Chuẩn bị vị trí

Dùng localhost trên máy tính hoặc HTTPS trên điện thoại; HTTP địa chỉ LAN không phải cấu hình GPS đã kiểm chứng.
Có thể giả lập vị trí bằng Sensors/Location override của Chrome DevTools hoặc dùng GPS thiết bị.
Mở hai phiên trình duyệt riêng để giữ đăng nhập Shipper và Shop/Nhân viên.

| Làm | Mong đợi | Người dùng xác nhận |
|---|---|---|
| Mở nhiệm vụ lấy, chưa bấm bật | Có giải thích người được xem/thời hạn lưu, địa chỉ và Chỉ đường; chưa gửi vị trí | [ ] |
| Bấm bật, cho phép vị trí | Hiện trạng thái chờ/đang chia sẻ, thời điểm điểm đã gửi; Shop/NV đúng đơn thấy vị trí/thời điểm/sai số | [ ] |
| Từ chối/thu hồi quyền vị trí | Dừng thu thập, báo chưa cấp quyền; địa chỉ/Chỉ đường và thao tác lấy/giao/hoàn vẫn dùng được | [ ] |
| Bấm Tắt, rời trang hoặc đăng xuất | Dừng gửi; mở lại trang không tự bật | [ ] |
| Mất tín hiệu hoặc chuyển Offline, sau đó kết nối lại | Báo chưa cập nhật được; không đổi timestamp cũ thành điểm mới, chỉ gửi mẫu GPS mới phù hợp | [ ] |
| Xem Shop/NV khi chưa có điểm hoặc điểm cũ | Hiện chưa có vị trí hoặc cảnh báo vị trí cũ; không vẽ điểm/tuyến giả | [ ] |
| Dùng Shop B mở đơn A, hoặc Shipper mở URL chi tiết Shop | Bị chặn theo quyền, không lộ GPS | [ ] |
| Hoàn tất nhiệm vụ bằng thao tác nghiệp vụ | Shipper dừng GPS; Shop/NV tự dừng và bỏ điểm khi lần polling kế tiếp nhận task đóng | [ ] |
| NV đổi Shipper đang giữ hàng; người cũ đang bật GPS | Sau health check, điểm đến người cũ về hub, không còn ghi giao/COD; chờ bàn giao vẫn được gửi GPS | [ ] |
| NV xác nhận bàn giao | Task cũ dừng; Shop/NV bỏ GPS cũ, task mới chưa có điểm cho tới khi người mới bật | [ ] |
| Chỉ đường ở lấy/giao/hoàn/chờ bàn giao | Google Maps mở tab mới với địa chỉ lấy/giao/hub tương ứng; tab gốc giữ địa chỉ nếu Maps ngoài không tải được | [ ] |
| Nền bản đồ lỗi | Còn tọa độ/thời điểm/attribution, có nút tải lại; lỗi tile không chặn ghi kết quả nhiệm vụ | [ ] |
| Thử 1440/390, cuộn trang để dùng các nút | Không tràn ngang; bật/tắt GPS, chỉ đường và thanh thao tác nhiệm vụ dùng được | [ ] |
| Mở Console trong các luồng trên | Không Vue warning/lỗi trang; ghi URL và bước tái hiện nếu lỗi | [ ] |

Nhịp gửi/đọc mặc định 15 giây; điểm cũ hơn 5 phút được đánh cũ. Trình duyệt không bảo đảm theo dõi nền khi tắt màn hình.
App chỉ kiểm được URL chỉ đường, không xác nhận kết quả định tuyến của dịch vụ Maps ngoài.
Lệnh purge cần lịch chạy riêng theo README; không dùng command xóa dữ liệu trên DB thực chỉ để thử giao diện.
