# ĐẶC TẢ USE CASE HỆ THỐNG HTT EXPRESS

> Bản Markdown xuất tự động từ `HTT_EXPRESS_Dac_ta_42_Use_Case.docx` để đọc và tra cứu khi code. File .docx là bản gốc; khi .docx thay đổi, xuất lại file này thay vì sửa tay.

*Quản lý vận đơn và giao nhận tại Hà Nội*

Ngày lập 20/11/2026 · Phiên bản 1.0

Tài liệu mô tả 42 use case thuộc sáu nhóm chức năng, làm căn cứ thống nhất nghiệp vụ trong báo cáo và triển khai phần mềm. Mỗi use case trình bày mục đích, đường dẫn thao tác, tác nhân, các luồng xử lý, điều kiện trước và sau cùng quy tắc nghiệp vụ.

## 1 Phạm vi và quy ước

Hệ thống gồm ba tác nhân: Shop, Nhân viên/Admin và Shipper. Nhân viên/Admin được gọi ngắn là Nhân viên trong các luồng. Hệ thống là thành phần xử lý tự động, không phải tác nhân bên ngoài. Người nhận tham gia nhận hàng và trả COD ngoài thực tế, chưa có tài khoản hoặc màn hình riêng.

Luồng chính: Shop gửi yêu cầu, Nhân viên duyệt và phân công lấy; Shipper nhận hàng tại Shop rồi đưa về điểm tập kết; Nhân viên xác nhận tiếp nhận trước khi phân công giao. Hàng hoàn về điểm tập kết để Shop đến lấy. Điểm tập kết chỉ ghi nhận bàn giao, không bao gồm quản lý kho hoặc tồn kho.

Tối đa ba lần giao thực tế cho mỗi vận đơn. Sau lần thất bại thứ ba, Nhân viên phải quyết định hoàn. COD chỉ ghi nhận phải thu và thực thu, không triển khai nộp tiền, đối soát hoặc thanh toán lại cho Shop. Đơn COD phải thu đủ mới được xác nhận giao thành công.

Khôi phục tài khoản phải xác minh danh tính trước khi đặt mật khẩu mới. Nhân viên hỗ trợ khôi phục và tạo tài khoản Shop qua chức năng quản lý tài khoản là phương án quản lý được đề xuất; không mặc định tích hợp OTP, email, SMS hoặc tự đăng ký.

Đường dẫn thể hiện vị trí chức năng theo nghiệp vụ, không phải URL kỹ thuật. Luồng thay thế A mô tả nhánh xử lý hợp lệ; luồng ngoại lệ E mô tả lỗi hoặc điều kiện không đạt. Khi nhánh không lưu thành công, dữ liệu nghiệp vụ đã lưu phải được giữ nguyên.

## 2 Quy tắc xử lý áp dụng chung

- Mọi thao tác được bảo vệ phải kiểm tra phiên, trạng thái tài khoản, vai trò và quyền trên bản ghi. Shop chỉ xử lý dữ liệu của mình; Shipper chỉ thực hiện nhiệm vụ còn hiệu lực được giao.
- Phiên hết hạn hoặc tài khoản bị khóa: dừng thao tác, không lưu thay đổi và yêu cầu đăng nhập lại hoặc liên hệ Nhân viên. Quy tắc này áp dụng cho toàn bộ use case cần đăng nhập.
- Mất kết nối hoặc lỗi lưu: thông báo chưa hoàn tất, không hiển thị thành công khi chưa có xác nhận. Khi gửi lại, kiểm tra kết quả đã lưu để tránh tạo trùng; không yêu cầu người dùng làm lại thao tác bàn giao hoặc thu tiền thực tế chỉ vì giao diện chưa nhận phản hồi.
- Mọi cập nhật trạng thái phải đi cùng lịch sử gồm người thực hiện, thời điểm, trạng thái trước/sau và lý do nếu có. Không cho sửa/xóa sự kiện đã ghi; trạng thái nhiệm vụ được tách với trạng thái vận đơn.
- Thông báo sử dụng kênh nội bộ trong hệ thống. Nếu thông báo chưa hiển thị, trạng thái đã lưu vẫn là căn cứ xử lý; không lặp lại cập nhật nghiệp vụ để gửi lại thông báo.

## 3 Danh mục use case

| Mã | Tên chức năng | Tác nhân |
|---|---|---|
| UC01.1 | Đăng nhập hệ thống | Shop, Nhân viên, Shipper |
| UC01.2 | Đăng xuất hệ thống | Shop, Nhân viên, Shipper |
| UC01.3 | Quên mật khẩu | Shop, Nhân viên, Shipper |
| UC02.1 | Xem thông tin tài khoản | Shop, Nhân viên, Shipper |
| UC02.2 | Cập nhật thông tin cá nhân | Shop, Nhân viên, Shipper |
| UC02.3 | Đổi mật khẩu | Shop, Nhân viên, Shipper |
| UC02.4 | Quản lý tài khoản người dùng | Nhân viên |
| UC03.1 | Tra cứu vận đơn | Shop, Nhân viên |
| UC03.2 | Xem lịch sử vận chuyển | Shop, Nhân viên |
| UC03.3 | Theo dõi vị trí Shipper | Shop, Nhân viên |
| UC03.4 | Xem bản đồ và tuyến đường | Shipper |
| UC03.5 | Chia sẻ vị trí GPS khi thực hiện nhiệm vụ | Shipper |
| UC04.1 | Xem nhiệm vụ lấy hàng | Shipper |
| UC04.2 | Xác nhận lấy hàng thành công | Shipper |
| UC04.3 | Cập nhật lấy hàng thất bại | Shipper |
| UC04.4 | Xem nhiệm vụ giao hàng | Shipper |
| UC04.5 | Xác nhận giao hàng thành công | Shipper |
| UC04.6 | Cập nhật giao hàng thất bại | Shipper |
| UC04.7 | Ghi nhận tiền COD đã thu | Shipper |
| UC04.8 | Xem nhiệm vụ hoàn hàng | Shipper |
| UC04.9 | Bàn giao hàng hoàn | Shipper |
| UC04.10 | Xác nhận nhập điểm tập kết | Nhân viên |
| UC04.11 | Xác nhận Shop nhận hàng hoàn | Nhân viên |
| UC04.12 | Quyết định giao lại hoặc hoàn hàng | Nhân viên |
| UC04.13 | Xử lý lấy hàng thất bại | Nhân viên |
| UC05.1 | Chỉnh sửa yêu cầu gửi hàng | Shop |
| UC05.2 | Tạo yêu cầu gửi hàng | Shop |
| UC05.3 | Xem danh sách vận đơn của Shop | Shop |
| UC05.4 | Xem chi tiết vận đơn của Shop | Shop |
| UC05.5 | Hủy yêu cầu gửi hàng | Shop |
| UC05.6 | Xác nhận vận đơn | Nhân viên |
| UC05.7 | Xem chi tiết vận đơn của Nhân viên | Nhân viên |
| UC05.8 | Từ chối vận đơn | Nhân viên |
| UC05.9 | Xem danh sách vận đơn của Nhân viên | Nhân viên |
| UC06.1 | Xem danh sách Shipper | Nhân viên |
| UC06.2 | Thêm Shipper | Nhân viên |
| UC06.3 | Cập nhật thông tin Shipper | Nhân viên |
| UC06.4 | Khóa hoặc mở khóa tài khoản Shipper | Nhân viên |
| UC06.5 | Phân công Shipper lấy hàng | Nhân viên |
| UC06.6 | Phân công Shipper giao hàng | Nhân viên |
| UC06.7 | Phân công Shipper hoàn hàng | Nhân viên |
| UC06.8 | Đổi Shipper hoặc phân công lại | Nhân viên |

UC04.10 đến UC04.13 và UC06.8 là các chức năng bổ sung trong phạm vi giao nhận đã chốt.

## 4 Đăng nhập hệ thống

### UC01.1 Đăng nhập hệ thống

**Mô tả:** Cho phép người dùng truy cập hệ thống bằng tài khoản được cấp và sử dụng chức năng đúng vai trò.

**Đường dẫn:** HTT Express >> Đăng nhập

**Tác nhân:** Shop, Nhân viên/Admin, Shipper

**Luồng cơ bản**

1. Người dùng mở màn hình Đăng nhập.
2. Hệ thống hiển thị các trường tên đăng nhập và mật khẩu.
3. Người dùng nhập thông tin và chọn Đăng nhập.
4. Hệ thống kiểm tra dữ liệu bắt buộc, đối chiếu thông tin xác thực và trạng thái tài khoản.
5. Hệ thống tạo phiên làm việc và xác định vai trò của người dùng.
6. Hệ thống chuyển đến trang chức năng tương ứng với vai trò.

**Luồng thay thế**

- **A1 – Đã có phiên hợp lệ**
  - *Điều kiện: Đã có phiên hợp lệ.*
  - A1.1. Người dùng mở lại hệ thống.
  - A1.2. Hệ thống kiểm tra phiên và chuyển đến trang theo vai trò, không tạo phiên nghiệp vụ trùng.

**Luồng ngoại lệ**

- **E1 – Thông tin sai hoặc tài khoản bị khóa**
  - *Điều kiện: Thông tin sai hoặc tài khoản bị khóa.*
  - E1.1. Hệ thống từ chối đăng nhập và thông báo phù hợp, không tiết lộ tài khoản có tồn tại hay không.
  - E1.2. Người dùng kiểm tra thông tin hoặc liên hệ hỗ trợ.

**Điều kiện trước:** Người dùng đã mở hệ thống và có tài khoản đang hoạt động.

**Điều kiện sau:** Thành công: có phiên hợp lệ và vào đúng trang theo quyền. Thất bại: không tạo phiên mới.

**Business Rules**

- BR1. Không lưu hoặc hiển thị mật khẩu dạng rõ.
- BR2. Vai trò được xác định từ tài khoản trên hệ thống, không lấy theo lựa chọn tùy ý của người dùng.

### UC01.2 Đăng xuất hệ thống

**Mô tả:** Kết thúc phiên làm việc để ngăn việc tiếp tục truy cập bằng phiên vừa đăng xuất.

**Đường dẫn:** HTT Express >> Tài khoản >> Đăng xuất

**Tác nhân:** Shop, Nhân viên/Admin, Shipper

**Luồng cơ bản**

1. Người dùng chọn Đăng xuất.
2. Hệ thống tiếp nhận yêu cầu kết thúc phiên hiện tại.
3. Hệ thống vô hiệu hóa phiên ở phía máy chủ và xóa thông tin phiên trên giao diện.
4. Hệ thống dừng gửi dữ liệu GPS từ phiên vừa kết thúc nếu đang chia sẻ.
5. Hệ thống chuyển về màn hình Đăng nhập.

**Luồng thay thế**

- **A1 – Phiên đã hết hạn trước khi đăng xuất**
  - *Điều kiện: Phiên đã hết hạn trước khi đăng xuất.*
  - A1.1. Hệ thống xóa thông tin phiên còn trên giao diện.
  - A1.2. Hệ thống chuyển về Đăng nhập và yêu cầu đăng nhập lại khi cần.

**Luồng ngoại lệ**

- **E1 – Mất kết nối khi gửi yêu cầu đăng xuất**
  - *Điều kiện: Mất kết nối khi gửi yêu cầu đăng xuất.*
  - E1.1. Hệ thống báo chưa xác nhận được việc kết thúc phiên trên máy chủ.
  - E1.2. Giao diện xóa thông tin phiên cục bộ.
  - E1.3. Người dùng thực hiện lại việc kết thúc phiên khi có kết nối.

**Điều kiện trước:** Người dùng đang có phiên đăng nhập.

**Điều kiện sau:** Thành công: phiên không còn hiệu lực. Nếu chưa xác nhận từ máy chủ: không thông báo rằng phiên đã bị vô hiệu hóa hoàn toàn.

**Business Rules**

- BR1. Đăng xuất không hủy nhiệm vụ Shipper đang mở.
- BR2. Thông tin phiên đã vô hiệu hóa không được dùng lại để gọi chức năng có quyền.

### UC01.3 Quên mật khẩu

**Mô tả:** Cho phép người dùng yêu cầu khôi phục quyền truy cập khi quên mật khẩu, sau bước xác minh danh tính.

**Đường dẫn:** HTT Express >> Đăng nhập >> Quên mật khẩu

**Tác nhân:** Shop, Nhân viên/Admin, Shipper

**Luồng cơ bản**

1. Người dùng chọn Quên mật khẩu.
2. Hệ thống hiển thị hướng dẫn cung cấp thông tin tài khoản và thực hiện xác minh.
3. Người dùng cung cấp thông tin theo quy trình khôi phục đang áp dụng.
4. Bên có thẩm quyền kiểm tra danh tính và xác nhận yêu cầu hợp lệ.
5. Sau khi xác minh thành công, hệ thống cho phép đặt mật khẩu mới bằng quyền khôi phục hợp lệ.
6. Người dùng nhập và xác nhận mật khẩu mới.
7. Hệ thống kiểm tra, lưu mật khẩu đã băm, vô hiệu hóa quyền khôi phục đã dùng và thông báo kết quả.
8. Người dùng quay lại Đăng nhập để truy cập bằng mật khẩu mới.

**Luồng thay thế**

- **A1 – Áp dụng phương án Nhân viên hỗ trợ sau xác minh**
  - *Điều kiện: Áp dụng phương án Nhân viên hỗ trợ sau xác minh.*
  - A1.1. Người dùng liên hệ Nhân viên theo hướng dẫn.
  - A1.2. Nhân viên kiểm tra danh tính và hỗ trợ khôi phục theo quyền được cấp.
  - A1.3. Người dùng hoàn tất việc thiết lập mật khẩu mới theo quy trình hỗ trợ.

**Luồng ngoại lệ**

- **E1 – Chưa xác minh được danh tính hoặc quyền khôi phục không hợp lệ**
  - *Điều kiện: Chưa xác minh được danh tính hoặc quyền khôi phục không hợp lệ.*
  - E1.1. Hệ thống không cho đặt lại mật khẩu.
  - E1.2. Người dùng bổ sung thông tin hoặc liên hệ bên có thẩm quyền.

**Điều kiện trước:** Tài khoản đã tồn tại; người dùng chưa thể đăng nhập vì quên mật khẩu.

**Điều kiện sau:** Thành công: mật khẩu mới được lưu và người dùng có thể đăng nhập lại. Thất bại: mật khẩu hiện tại không thay đổi.

**Business Rules**

- BR1. Khôi phục tài khoản phải có bước xác minh; không mặc định tích hợp OTP, email hoặc SMS.
- BR2. Không cho đặt lại chỉ dựa vào tên đăng nhập; phương án Nhân viên hỗ trợ phải tuân thủ quy trình xác minh được áp dụng.
- BR3. Tài khoản Admin cuối cùng cần bên có thẩm quyền hỗ trợ, không mở quyền đặt lại không xác minh.

## 5 Quản lý tài khoản

### UC02.1 Xem thông tin tài khoản

**Mô tả:** Cho phép người dùng xem thông tin hồ sơ thuộc tài khoản đang đăng nhập.

**Đường dẫn:** HTT Express >> Tài khoản >> Thông tin cá nhân

**Tác nhân:** Shop, Nhân viên/Admin, Shipper

**Luồng cơ bản**

1. Người dùng mở Thông tin cá nhân.
2. Hệ thống xác định tài khoản từ phiên đăng nhập.
3. Hệ thống lấy họ tên, thông tin liên hệ và các thông tin hồ sơ được phép hiển thị.
4. Hệ thống hiển thị hồ sơ và các thao tác được cấp quyền.
5. Người dùng xem thông tin hoặc chuyển sang cập nhật hồ sơ.

**Luồng thay thế**

- **A1 – Một số thông tin hồ sơ chưa được khai báo**
  - *Điều kiện: Một số thông tin hồ sơ chưa được khai báo.*
  - A1.1. Hệ thống hiển thị Chưa cập nhật ở trường tương ứng.
  - A1.2. Người dùng có thể mở Cập nhật thông tin cá nhân.

**Luồng ngoại lệ**

- **E1 – Không tải được hồ sơ**
  - *Điều kiện: Không tải được hồ sơ.*
  - E1.1. Hệ thống thông báo chưa thể tải thông tin.
  - E1.2. Người dùng chọn tải lại.
  - E1.3. Không hiển thị dữ liệu của tài khoản khác để thay thế.

**Điều kiện trước:** Người dùng đã đăng nhập bằng tài khoản hoạt động.

**Điều kiện sau:** Hiển thị hồ sơ của người đang đăng nhập; không làm thay đổi dữ liệu.

**Business Rules**

- BR1. Không trả về mật khẩu hoặc giá trị băm.
- BR2. Quyền xem hồ sơ cá nhân không đồng nghĩa quyền xem danh sách tài khoản.

### UC02.2 Cập nhật thông tin cá nhân

**Mô tả:** Cho phép người dùng chỉnh sửa các thông tin hồ sơ cá nhân được phép thay đổi.

**Đường dẫn:** HTT Express >> Tài khoản >> Thông tin cá nhân >> Chỉnh sửa

**Tác nhân:** Shop, Nhân viên/Admin, Shipper

**Luồng cơ bản**

1. Người dùng mở Chỉnh sửa hồ sơ.
2. Hệ thống hiển thị thông tin hiện tại và các trường được chỉnh sửa.
3. Người dùng cập nhật họ tên, thông tin liên hệ hoặc địa chỉ theo trường được phép và chọn Lưu.
4. Hệ thống kiểm tra quyền đối với hồ sơ, trường bắt buộc, định dạng và thông tin trùng theo quy tắc tài khoản.
5. Hệ thống lưu các trường hợp lệ và ghi nhận thời điểm cập nhật.
6. Hệ thống thông báo thành công và hiển thị hồ sơ sau sửa.

**Luồng thay thế**

- **A1 – Người dùng chọn Hủy trước khi lưu**
  - *Điều kiện: Người dùng chọn Hủy trước khi lưu.*
  - A1.1. Hệ thống bỏ các thay đổi chưa lưu.
  - A1.2. Hồ sơ hiện tại được giữ nguyên.

**Luồng ngoại lệ**

- **E1 – Thông tin thiếu, sai định dạng hoặc trùng**
  - *Điều kiện: Thông tin thiếu, sai định dạng hoặc trùng.*
  - E1.1. Hệ thống không lưu, chỉ rõ trường cần sửa.
  - E1.2. Người dùng bổ sung dữ liệu và gửi lại.

**Điều kiện trước:** Người dùng đã đăng nhập; hồ sơ của mình tồn tại.

**Điều kiện sau:** Thành công: hồ sơ được cập nhật. Hủy hoặc lỗi: dữ liệu đã lưu không thay đổi.

**Business Rules**

- BR1. Không tự sửa vai trò, trạng thái tài khoản hoặc chủ sở hữu hồ sơ.
- BR2. Không sửa lịch sử người gửi, người nhận hoặc nhiệm vụ đã phát sinh chỉ vì hồ sơ cá nhân thay đổi.

### UC02.3 Đổi mật khẩu

**Mô tả:** Cho phép người dùng đang đăng nhập thay đổi mật khẩu của chính mình.

**Đường dẫn:** HTT Express >> Tài khoản >> Đổi mật khẩu

**Tác nhân:** Shop, Nhân viên/Admin, Shipper

**Luồng cơ bản**

1. Người dùng mở Đổi mật khẩu.
2. Hệ thống hiển thị trường mật khẩu hiện tại, mật khẩu mới và xác nhận mật khẩu mới.
3. Người dùng nhập thông tin và chọn Xác nhận.
4. Hệ thống đối chiếu mật khẩu hiện tại và kiểm tra mật khẩu mới theo chính sách đang áp dụng.
5. Hệ thống kiểm tra hai lần nhập mật khẩu mới khớp nhau.
6. Hệ thống lưu mật khẩu mới dưới dạng băm và thông báo đổi thành công.

**Luồng thay thế**

- **A1 – Người dùng không nhớ mật khẩu hiện tại**
  - *Điều kiện: Người dùng không nhớ mật khẩu hiện tại.*
  - A1.1. Người dùng dừng thao tác đổi.
  - A1.2. Hệ thống hướng dẫn thực hiện Quên mật khẩu theo UC01.3.

**Luồng ngoại lệ**

- **E1 – Mật khẩu hiện tại sai hoặc mật khẩu mới chưa hợp lệ**
  - *Điều kiện: Mật khẩu hiện tại sai hoặc mật khẩu mới chưa hợp lệ.*
  - E1.1. Hệ thống không thay đổi mật khẩu và thông báo trường lỗi.
  - E1.2. Người dùng kiểm tra, nhập lại và xác nhận.

**Điều kiện trước:** Người dùng có phiên hợp lệ và biết mật khẩu hiện tại.

**Điều kiện sau:** Thành công: mật khẩu mới có hiệu lực. Thất bại: mật khẩu cũ vẫn có hiệu lực.

**Business Rules**

- BR1. Chỉ đổi mật khẩu của tài khoản trong phiên.
- BR2. Không ghi nội dung mật khẩu vào lịch sử thao tác hoặc thông báo.

### UC02.4 Quản lý tài khoản người dùng

**Mô tả:** Cho phép Nhân viên quản lý danh sách tài khoản và thực hiện thêm, chỉnh sửa, khóa hoặc mở khóa trong quyền được cấp.

**Đường dẫn:** HTT Express >> Quản lý tài khoản

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở Quản lý tài khoản.
2. Hệ thống hiển thị danh sách theo loại tài khoản và trạng thái.
3. Nhân viên chọn tài khoản cần chỉnh sửa.
4. Hệ thống hiển thị hồ sơ và các trường quản trị được phép sửa.
5. Nhân viên cập nhật thông tin và chọn Lưu.
6. Hệ thống kiểm tra quyền, dữ liệu bắt buộc và thông tin trùng.
7. Hệ thống lưu thay đổi, ghi người thực hiện và thông báo kết quả.

**Luồng thay thế**

- **A1 – Nhân viên chọn Thêm tài khoản**
  - *Điều kiện: Nhân viên chọn Thêm tài khoản.*
  - A1.1. Hệ thống mở biểu mẫu tạo tài khoản.
  - A1.2. Nhân viên nhập thông tin và vai trò được phép cấp.
  - A1.3. Hệ thống kiểm tra, tạo tài khoản và ghi lịch sử.
  - A1.4. Thêm Shipper xem UC06.2.

- **A2 – Nhân viên chọn Khóa hoặc Mở khóa**
  - *Điều kiện: Nhân viên chọn Khóa hoặc Mở khóa.*
  - A2.1. Hệ thống hiển thị trạng thái và cảnh báo ảnh hưởng.
  - A2.2. Nhân viên xác nhận.
  - A2.3. Hệ thống cập nhật trạng thái, ghi lịch sử và vô hiệu hóa phiên nếu khóa.
  - A2.4. Nếu là Shipper, áp dụng UC06.4.

**Luồng ngoại lệ**

- **E1 – Dữ liệu trùng hoặc thao tác ảnh hưởng Admin hoạt động cuối cùng**
  - *Điều kiện: Dữ liệu trùng hoặc thao tác ảnh hưởng Admin hoạt động cuối cùng.*
  - E1.1. Hệ thống từ chối lưu và nêu nguyên nhân phù hợp.
  - E1.2. Nhân viên sửa dữ liệu hoặc chọn phương án quản trị khác.

**Điều kiện trước:** Nhân viên đã đăng nhập và có quyền quản lý tài khoản.

**Điều kiện sau:** Tài khoản được cập nhật đúng thao tác; nếu lỗi thì giữ dữ liệu trước khi xử lý.

**Business Rules**

- BR1. Không xóa cứng tài khoản đã có lịch sử nghiệp vụ.
- BR2. Không khóa quản trị viên hoạt động cuối cùng.
- BR3. Nhân viên tạo tài khoản Shop qua chức năng này là phương án quản lý được đề xuất; chức năng tự đăng ký chưa thuộc phạm vi.

## 6 Theo dõi vận đơn

### UC03.1 Tra cứu vận đơn

**Mô tả:** Cho phép tìm vận đơn theo mã và xem trạng thái trong phạm vi dữ liệu được cấp.

**Đường dẫn:** HTT Express >> Theo dõi vận đơn >> Tra cứu

**Tác nhân:** Shop, Nhân viên/Admin

**Luồng cơ bản**

1. Người dùng mở Tra cứu vận đơn.
2. Hệ thống hiển thị ô nhập mã vận đơn.
3. Người dùng nhập mã và chọn Tra cứu.
4. Hệ thống kiểm tra dữ liệu và tìm vận đơn trong phạm vi được xem.
5. Hệ thống trả về mã, trạng thái hiện tại và thông tin tóm tắt.
6. Người dùng chọn xem chi tiết hoặc lịch sử vận chuyển.

**Luồng thay thế**

- **A1 – Không có kết quả trong phạm vi được xem**
  - *Điều kiện: Không có kết quả trong phạm vi được xem.*
  - A1.1. Hệ thống hiển thị không tìm thấy vận đơn phù hợp.
  - A1.2. Người dùng kiểm tra mã và tra cứu lại.

**Luồng ngoại lệ**

- **E1 – Mã rỗng hoặc yêu cầu truy vấn bị lỗi**
  - *Điều kiện: Mã rỗng hoặc yêu cầu truy vấn bị lỗi.*
  - E1.1. Hệ thống yêu cầu nhập mã hợp lệ hoặc thông báo chưa thể tra cứu.
  - E1.2. Người dùng nhập lại hoặc thử lại khi có kết nối.

**Điều kiện trước:** Người dùng đã đăng nhập với vai trò Shop hoặc Nhân viên.

**Điều kiện sau:** Người dùng xem được kết quả hợp lệ; vận đơn không bị thay đổi.

**Business Rules**

- BR1. Shop chỉ tra cứu vận đơn của mình; Nhân viên tra cứu toàn hệ thống theo quyền.
- BR2. Không tiết lộ thông tin đơn Shop khác và không có tra cứu công khai trong phạm vi này.

### UC03.2 Xem lịch sử vận chuyển

**Mô tả:** Cho phép xem các mốc xử lý của vận đơn theo trình tự thời gian.

**Đường dẫn:** HTT Express >> Vận đơn >> Chi tiết >> Lịch sử vận chuyển

**Tác nhân:** Shop, Nhân viên/Admin

**Luồng cơ bản**

1. Người dùng mở chi tiết vận đơn và chọn Lịch sử vận chuyển.
2. Hệ thống kiểm tra quyền xem đối với vận đơn.
3. Hệ thống lấy các sự kiện tạo, duyệt, phân công, lấy, giao và hoàn đã phát sinh.
4. Hệ thống sắp xếp theo thời gian và hiển thị trạng thái, thời điểm, người xử lý, lý do nếu có.
5. Người dùng xem các mốc và phân biệt từng lần lấy hoặc giao lại.

**Luồng thay thế**

- **A1 – Chưa có mốc vận chuyển sau khi duyệt**
  - *Điều kiện: Chưa có mốc vận chuyển sau khi duyệt.*
  - A1.1. Hệ thống chỉ hiển thị các mốc đã có và thông báo chưa phát sinh vận chuyển.
  - A1.2. Người dùng quay lại theo dõi sau.

**Luồng ngoại lệ**

- **E1 – Vận đơn không thuộc quyền xem hoặc không tải được lịch sử**
  - *Điều kiện: Vận đơn không thuộc quyền xem hoặc không tải được lịch sử.*
  - E1.1. Hệ thống từ chối truy cập hoặc báo lỗi tải dữ liệu.
  - E1.2. Không hiển thị lịch sử từ đơn khác.

**Điều kiện trước:** Người dùng đã đăng nhập và được xem vận đơn đã chọn.

**Điều kiện sau:** Lịch sử được hiển thị theo quyền; các sự kiện đã lưu không thay đổi.

**Business Rules**

- BR1. Lịch sử chỉ thêm mới, không ghi đè sự kiện cũ.
- BR2. Thời gian hiển thị phải thống nhất múi giờ; giữ riêng các lần giao lại và thay Shipper.

### UC03.3 Theo dõi vị trí Shipper

**Mô tả:** Cho phép xem vị trí cập nhật gần nhất của Shipper đang thực hiện nhiệm vụ liên quan vận đơn.

**Đường dẫn:** HTT Express >> Vận đơn >> Chi tiết >> Theo dõi vị trí

**Tác nhân:** Shop, Nhân viên/Admin

**Luồng cơ bản**

1. Người dùng chọn Theo dõi vị trí trong chi tiết vận đơn.
2. Hệ thống xác định nhiệm vụ và Shipper đang phụ trách.
3. Hệ thống kiểm tra quyền xem vị trí của người dùng đối với nhiệm vụ.
4. Hệ thống lấy tọa độ được phép chia sẻ gần nhất.
5. Hệ thống hiển thị vị trí trên bản đồ, thời điểm cập nhật và trạng thái kết nối vị trí.
6. Trong khi màn hình mở, hệ thống cập nhật dữ liệu khi có vị trí mới hợp lệ.

**Luồng thay thế**

- **A1 – Chưa có vị trí hoặc vị trí không còn mới**
  - *Điều kiện: Chưa có vị trí hoặc vị trí không còn mới.*
  - A1.1. Hệ thống hiển thị Chưa có vị trí hoặc thời điểm cập nhật gần nhất.
  - A1.2. Người dùng tiếp tục xem trạng thái vận đơn, không coi vị trí cũ là vị trí hiện tại.

**Luồng ngoại lệ**

- **E1 – Nhiệm vụ đã kết thúc hoặc người dùng không còn quyền xem**
  - *Điều kiện: Nhiệm vụ đã kết thúc hoặc người dùng không còn quyền xem.*
  - E1.1. Hệ thống dừng cập nhật và thông báo không thể tiếp tục theo dõi.
  - E1.2. Không trả thêm tọa độ của Shipper.

**Điều kiện trước:** Người dùng có quyền xem đơn; có nhiệm vụ đang thực hiện được phép chia sẻ vị trí.

**Điều kiện sau:** Hiển thị vị trí hợp lệ gần nhất hoặc tình trạng chưa có dữ liệu; không làm đổi nhiệm vụ.

**Business Rules**

- BR1. Shop chỉ theo dõi nhiệm vụ đang thực hiện của đơn mình.
- BR2. Không cung cấp toàn bộ hành trình cá nhân hoặc vị trí ngoài thời gian nhiệm vụ.

### UC03.4 Xem bản đồ và tuyến đường

**Mô tả:** Hỗ trợ Shipper xác định địa chỉ điểm đến và tuyến đường dự kiến của nhiệm vụ được giao.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Chi tiết >> Bản đồ và tuyến đường

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở chi tiết nhiệm vụ và chọn Xem tuyến đường.
2. Hệ thống kiểm tra Shipper phụ trách và xác định điểm đến theo loại lấy, giao hoặc hoàn.
3. Hệ thống yêu cầu quyền vị trí nếu chưa có.
4. Shipper cho phép truy cập vị trí.
5. Hệ thống lấy vị trí hiện tại và yêu cầu hiển thị tuyến đến địa chỉ đích.
6. Hệ thống hiển thị bản đồ và tuyến đường dự kiến để Shipper tham khảo.

**Luồng thay thế**

- **A1 – Shipper không cấp quyền vị trí**
  - *Điều kiện: Shipper không cấp quyền vị trí.*
  - A1.1. Hệ thống vẫn hiển thị địa chỉ điểm đến.
  - A1.2. Shipper sử dụng địa chỉ để tự tìm đường, không hiển thị tuyến giả.

**Luồng ngoại lệ**

- **E1 – Dịch vụ bản đồ lỗi hoặc địa chỉ chưa xác định được tọa độ**
  - *Điều kiện: Dịch vụ bản đồ lỗi hoặc địa chỉ chưa xác định được tọa độ.*
  - E1.1. Hệ thống báo chưa tải được tuyến đường và giữ thông tin địa chỉ.
  - E1.2. Shipper kiểm tra địa chỉ hoặc thử tải lại.

**Điều kiện trước:** Shipper đã đăng nhập; có nhiệm vụ được phân công và địa chỉ điểm đến.

**Điều kiện sau:** Shipper xem được tuyến dự kiến hoặc địa chỉ điểm đến; trạng thái đơn không thay đổi.

**Business Rules**

- BR1. Chỉ hỗ trợ nhiệm vụ của Shipper đang đăng nhập.
- BR2. Tuyến đường là thông tin tham khảo, không phải cam kết thời gian giao.

### UC03.5 Chia sẻ vị trí GPS khi thực hiện nhiệm vụ

**Mô tả:** Gửi vị trí của Shipper trong thời gian thực hiện nhiệm vụ để phục vụ theo dõi giao nhận.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Thực hiện nhiệm vụ >> Chia sẻ vị trí

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở nhiệm vụ đang thực hiện.
2. Hệ thống giải thích việc dùng vị trí và yêu cầu cấp quyền.
3. Shipper cho phép truy cập vị trí.
4. Hệ thống lấy tọa độ và thời điểm ghi nhận trên thiết bị.
5. Hệ thống gửi vị trí theo cơ chế cập nhật của ứng dụng.
6. Hệ thống kiểm tra phiên, Shipper và nhiệm vụ trước khi lưu tọa độ.
7. Khi nhiệm vụ kết thúc, người dùng thu hồi quyền hoặc đăng xuất, hệ thống dừng gửi vị trí từ phiên đó.

**Luồng thay thế**

- **A1 – Shipper từ chối hoặc thu hồi quyền vị trí**
  - *Điều kiện: Shipper từ chối hoặc thu hồi quyền vị trí.*
  - A1.1. Hệ thống ngừng thu thập và hiển thị chưa có GPS.
  - A1.2. Shipper vẫn xem được địa chỉ nhiệm vụ.

**Luồng ngoại lệ**

- **E1 – Mất tín hiệu GPS hoặc kết nối mạng**
  - *Điều kiện: Mất tín hiệu GPS hoặc kết nối mạng.*
  - E1.1. Hệ thống hiển thị chưa thể cập nhật vị trí.
  - E1.2. Khi có kết nối, chỉ gửi dữ liệu phù hợp với nhiệm vụ còn hiệu lực, không coi tọa độ cũ là vị trí mới.

**Điều kiện trước:** Shipper có phiên hợp lệ và nhiệm vụ hoạt động; thiết bị hỗ trợ vị trí.

**Điều kiện sau:** Vị trí hợp lệ được lưu gắn với nhiệm vụ; khi dừng chia sẻ không phát sinh vị trí mới.

**Business Rules**

- BR1. Không nhận vị trí gửi thay cho Shipper khác.
- BR2. Không thu thập khi chưa được cho phép hoặc không còn nhiệm vụ được phép chia sẻ.
- BR3. Trong bàn giao đổi Shipper, người cũ chỉ chia sẻ vị trí phục vụ nhiệm vụ bàn giao còn hiệu lực.

## 7 Quản lý đơn hàng và nhiệm vụ giao nhận

### UC04.1 Xem nhiệm vụ lấy hàng

**Mô tả:** Cho phép Shipper xem các nhiệm vụ lấy hàng được phân công và thông tin cần thiết để đến Shop nhận hàng.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Lấy hàng

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở danh sách Lấy hàng.
2. Hệ thống lấy nhiệm vụ lấy hàng gắn với Shipper trong phiên.
3. Hệ thống hiển thị mã vận đơn, Shop, địa chỉ lấy, liên hệ và trạng thái nhiệm vụ.
4. Shipper chọn một nhiệm vụ.
5. Hệ thống kiểm tra lại quyền và hiển thị chi tiết kiện hàng cùng các thao tác hợp lệ.

**Luồng thay thế**

- **A1 – Chưa được phân công nhiệm vụ lấy hàng**
  - *Điều kiện: Chưa được phân công nhiệm vụ lấy hàng.*
  - A1.1. Hệ thống hiển thị danh sách trống.
  - A1.2. Shipper có thể tải lại để kiểm tra phân công mới.

**Luồng ngoại lệ**

- **E1 – Nhiệm vụ đã chuyển cho người khác khi mở chi tiết**
  - *Điều kiện: Nhiệm vụ đã chuyển cho người khác khi mở chi tiết.*
  - E1.1. Hệ thống không cho thao tác và cập nhật lại danh sách.
  - E1.2. Shipper không được xác nhận lấy hàng trên nhiệm vụ cũ.

**Điều kiện trước:** Shipper đã đăng nhập bằng tài khoản hoạt động.

**Điều kiện sau:** Shipper xem nhiệm vụ thuộc mình; không thay đổi kết quả lấy hàng.

**Business Rules**

- BR1. Không hiển thị nhiệm vụ lấy của Shipper khác.
- BR2. Nhiệm vụ đã đóng hoặc đang chờ bàn giao chỉ có thao tác phù hợp trạng thái.

### UC04.2 Xác nhận lấy hàng thành công

**Mô tả:** Ghi nhận Shipper đã thực tế nhận kiện hàng từ Shop.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Lấy hàng >> Chi tiết >> Đã lấy hàng

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở nhiệm vụ và đối chiếu mã đơn, Shop, số kiện cùng thông tin hàng.
2. Shipper nhận hàng thực tế và chọn Đã lấy hàng.
3. Hệ thống hiển thị nội dung xác nhận để Shipper kiểm tra.
4. Shipper xác nhận kết quả.
5. Hệ thống kiểm tra quyền phụ trách, trạng thái nhiệm vụ và việc chưa ghi kết quả trước đó.
6. Hệ thống lưu thời gian lấy, người đang giữ hàng, đóng kết quả nhiệm vụ lấy và đặt đơn Đã lấy hàng.
7. Hệ thống thêm lịch sử và thông báo cho Shop.

**Luồng thay thế**

- **A1 – Phát hiện hàng không khớp trước khi xác nhận**
  - *Điều kiện: Phát hiện hàng không khớp trước khi xác nhận.*
  - A1.1. Shipper chưa xác nhận thành công và làm rõ với Shop.
  - A1.2. Nếu không thể nhận, thực hiện ghi nhận lấy thất bại theo UC04.3.

**Luồng ngoại lệ**

- **E1 – Nhiệm vụ đã bị thay thế hoặc không còn cho xác nhận**
  - *Điều kiện: Nhiệm vụ đã bị thay thế hoặc không còn cho xác nhận.*
  - E1.1. Hệ thống từ chối cập nhật, tải lại trạng thái mới.
  - E1.2. Không ghi thêm kết quả lấy thành công.

**Điều kiện trước:** Shipper phụ trách nhiệm vụ lấy còn hiệu lực; vận đơn đã phân công lấy; Shop đã bàn giao kiện hàng.

**Điều kiện sau:** Thành công: đơn Đã lấy hàng, ghi nhận Shipper giữ hàng và chờ bàn giao điểm tập kết. Lỗi: không đổi trạng thái.

**Business Rules**

- BR1. Đã lấy hàng khác Đã nhập điểm tập kết; Nhân viên xác nhận tiếp nhận ở UC04.10.
- BR2. Gửi lại cùng yêu cầu đã xử lý chỉ trả kết quả hiện tại, không tạo lịch sử trùng.

### UC04.3 Cập nhật lấy hàng thất bại

**Mô tả:** Ghi nhận lần đến lấy không nhận được hàng và chuyển Nhân viên xử lý.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Lấy hàng >> Chi tiết >> Lấy hàng thất bại

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở nhiệm vụ lấy hàng.
2. Shipper chọn Lấy hàng thất bại.
3. Hệ thống hiển thị trường lý do và ghi chú.
4. Shipper chọn hoặc nhập lý do, bổ sung ghi chú và xác nhận.
5. Hệ thống kiểm tra quyền, trạng thái và dữ liệu lý do.
6. Hệ thống lưu lần lấy thất bại, kết thúc nhiệm vụ lấy tương ứng và đặt đơn Lấy hàng thất bại.
7. Hệ thống thông báo cho Nhân viên và Shop, đưa đơn vào danh sách chờ xử lý.

**Luồng thay thế**

- **A1 – Shipper chọn Hủy trước xác nhận**
  - *Điều kiện: Shipper chọn Hủy trước xác nhận.*
  - A1.1. Hệ thống đóng biểu mẫu.
  - A1.2. Nhiệm vụ lấy tiếp tục ở trạng thái trước đó.

**Luồng ngoại lệ**

- **E1 – Chưa nhập lý do hoặc nhiệm vụ đã có kết quả**
  - *Điều kiện: Chưa nhập lý do hoặc nhiệm vụ đã có kết quả.*
  - E1.1. Hệ thống không lưu và thông báo nguyên nhân.
  - E1.2. Shipper bổ sung lý do hoặc tải lại nhiệm vụ.

**Điều kiện trước:** Nhiệm vụ lấy thuộc Shipper, còn hiệu lực và chưa có kết quả cuối.

**Điều kiện sau:** Đơn Lấy hàng thất bại, có lý do và lịch sử; chưa phát sinh nhiệm vụ lấy lại.

**Business Rules**

- BR1. Chỉ Nhân viên quyết định lấy lại hay kết thúc theo UC04.13.
- BR2. Không ghi đã lấy hàng hoặc người giữ hàng khi thực tế chưa nhận.

### UC04.4 Xem nhiệm vụ giao hàng

**Mô tả:** Cho phép Shipper xem các đơn cần giao thuộc phân công của mình.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Giao hàng

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở danh sách Giao hàng.
2. Hệ thống lọc nhiệm vụ giao theo Shipper đang đăng nhập.
3. Hệ thống hiển thị mã đơn, người nhận, địa chỉ, COD và trạng thái nhiệm vụ.
4. Shipper chọn nhiệm vụ cần thực hiện.
5. Hệ thống kiểm tra quyền và hiển thị thông tin giao, số lần đã giao cùng thao tác hợp lệ.

**Luồng thay thế**

- **A1 – Không có nhiệm vụ phù hợp**
  - *Điều kiện: Không có nhiệm vụ phù hợp.*
  - A1.1. Hệ thống hiển thị chưa có nhiệm vụ giao hàng.
  - A1.2. Shipper tải lại hoặc quay về trang nhiệm vụ.

**Luồng ngoại lệ**

- **E1 – Nhiệm vụ bị thu hồi hoặc thay thế trước khi xem chi tiết**
  - *Điều kiện: Nhiệm vụ bị thu hồi hoặc thay thế trước khi xem chi tiết.*
  - E1.1. Hệ thống báo nhiệm vụ không còn khả dụng.
  - E1.2. Không cho cập nhật kết quả và làm mới danh sách.

**Điều kiện trước:** Shipper đã đăng nhập bằng tài khoản hoạt động.

**Điều kiện sau:** Shipper xem được nhiệm vụ giao được phép truy cập; chưa ghi kết quả giao.

**Business Rules**

- BR1. Không truy cập danh sách giao của người khác.
- BR2. Thông tin liên hệ người nhận chỉ dùng để thực hiện nhiệm vụ được phân công.

### UC04.5 Xác nhận giao hàng thành công

**Mô tả:** Ghi nhận người nhận đã nhận hàng và lưu kết quả giao cùng COD thực thu.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Giao hàng >> Chi tiết >> Giao thành công

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở nhiệm vụ, đối chiếu mã đơn và người nhận.
2. Shipper chọn Giao thành công sau khi người nhận nhận hàng.
3. Hệ thống hiển thị COD phải thu; Shipper nhập hoặc xác nhận tiền thực thu theo UC04.7.
4. Shipper kiểm tra thông tin và xác nhận hoàn tất.
5. Hệ thống kiểm tra quyền, trạng thái, số lần giao và COD thực thu bằng phải thu.
6. Hệ thống đồng thời lưu kết quả thành công, COD, thời gian và số thứ tự lần giao; đặt đơn Đã giao hàng, đóng nhiệm vụ.
7. Hệ thống thêm lịch sử, dừng chia sẻ vị trí của nhiệm vụ và thông báo Shop.

**Luồng thay thế**

- **A1 – Đơn không có COD**
  - *Điều kiện: Đơn không có COD.*
  - A1.1. Hệ thống xác định phải thu và thực thu là 0.
  - A1.2. Shipper xác nhận và tiếp tục bước 5.

**Luồng ngoại lệ**

- **E1 – COD thiếu, thừa hoặc dữ liệu chưa hợp lệ**
  - *Điều kiện: COD thiếu, thừa hoặc dữ liệu chưa hợp lệ.*
  - E1.1. Hệ thống không hoàn tất giao, không lưu kết quả thành công.
  - E1.2. Shipper kiểm tra số tiền.
  - E1.3. Nếu thực tế chưa thu đủ thì ghi giao thất bại theo UC04.6, không ghi thu một phần.

**Điều kiện trước:** Đơn Đang giao hàng; Shipper phụ trách nhiệm vụ còn hiệu lực; đã giao thực tế và thu đủ COD nếu có.

**Điều kiện sau:** Thành công: Đã giao hàng, có COD hợp lệ và nhiệm vụ đóng. Thất bại: không có trạng thái thành công hoặc khoản thu bị lưu rời rạc.

**Business Rules**

- BR1. Mỗi lần giao chỉ có một kết quả cuối; tối đa 3 lần giao thực tế.
- BR2. Ghi COD và kết quả giao trong cùng lần xử lý; gửi lại không cộng tiền hay tăng số lần.

### UC04.6 Cập nhật giao hàng thất bại

**Mô tả:** Ghi nhận lần giao không thành công để Nhân viên quyết định giao lại hoặc hoàn.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Giao hàng >> Chi tiết >> Giao thất bại

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper chọn Giao thất bại trong nhiệm vụ.
2. Hệ thống hiển thị lý do và ghi chú.
3. Shipper ghi nhận lý do thực tế như không liên hệ được, từ chối nhận hoặc chưa thu đủ COD.
4. Shipper xác nhận kết quả.
5. Hệ thống kiểm tra quyền và xác định số thứ tự lần giao chưa được ghi trước đó.
6. Hệ thống lưu kết quả thất bại, tăng số lần đã giao một lần, đóng nhiệm vụ giao và đặt đơn Giao hàng thất bại.
7. Hệ thống lưu người đang giữ hàng và thông báo Nhân viên, Shop; không tự tạo nhiệm vụ tiếp theo.

**Luồng thay thế**

- **A1 – Đây là lần giao thứ ba thất bại**
  - *Điều kiện: Đây là lần giao thứ ba thất bại.*
  - A1.1. Hệ thống đánh dấu chỉ được xử lý hoàn.
  - A1.2. Nhân viên quyết định hoàn theo UC04.12, không được phân công lần giao thứ tư.

**Luồng ngoại lệ**

- **E1 – Thiếu lý do hoặc kết quả cùng lần đã được ghi**
  - *Điều kiện: Thiếu lý do hoặc kết quả cùng lần đã được ghi.*
  - E1.1. Hệ thống yêu cầu bổ sung lý do hoặc trả kết quả đã có.
  - E1.2. Không ghi thêm lần thất bại và không tăng bộ đếm trùng.

**Điều kiện trước:** Đơn Đang giao hàng; nhiệm vụ thuộc Shipper, chưa có kết quả cuối.

**Điều kiện sau:** Đơn Giao hàng thất bại, có lịch sử và số lần chính xác, chờ quyết định Nhân viên.

**Business Rules**

- BR1. Đổi Shipper không đặt lại số lần giao.
- BR2. Khách từ chối nhận có thể được Nhân viên quyết định hoàn sớm; Shipper không tự quyết định hoàn.

### UC04.7 Ghi nhận tiền COD đã thu

**Mô tả:** Ghi nhận khoản COD thực thu khi hoàn tất giao thành công, đồng thời với kết quả giao.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Giao hàng >> Giao thành công >> COD

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở biểu mẫu Giao thành công.
2. Hệ thống hiển thị số COD phải thu của đơn.
3. Shipper kiểm tra số tiền nhận thực tế và nhập tiền thực thu.
4. Hệ thống kiểm tra số tiền bằng VND, không âm và bằng COD phải thu.
5. Shipper xác nhận lưu kết quả giao.
6. Hệ thống lưu COD gắn với đơn, nhiệm vụ, người thu và thời điểm trong cùng xử lý UC04.5.
7. Hệ thống hiển thị số tiền đã ghi nhận trên kết quả giao.

**Luồng thay thế**

- **A1 – Đơn không COD**
  - *Điều kiện: Đơn không COD.*
  - A1.1. Hệ thống xác định số phải thu và thực thu bằng 0.
  - A1.2. Tiếp tục xác nhận giao mà không phát sinh khoản thu tiền.

**Luồng ngoại lệ**

- **E1 – Thực thu khác phải thu**
  - *Điều kiện: Thực thu khác phải thu.*
  - E1.1. Hệ thống từ chối lưu kết quả thành công và chỉ rõ chênh lệch.
  - E1.2. Shipper kiểm tra lại.
  - E1.3. Nếu chưa thu đủ, không thu một phần và ghi giao thất bại theo UC04.6.

**Điều kiện trước:** Đơn có nhiệm vụ giao của Shipper còn hiệu lực; số COD phải thu đã được lưu trên đơn.

**Điều kiện sau:** COD được ghi đúng một lần cùng kết quả giao; nếu kiểm tra/lưu thất bại thì không ghi khoản thu thành công.

**Business Rules**

- BR1. Không hỗ trợ thu một phần, đối soát, Shipper nộp tiền hoặc trả tiền Shop.
- BR2. Không cộng COD vào doanh thu vận chuyển; không sửa số phải thu để làm khớp số thực thu.
- BR3. UC này là phần nghiệp vụ trong giao thành công, không tạo khoản thu độc lập sau khi đóng đơn.

### UC04.8 Xem nhiệm vụ hoàn hàng

**Mô tả:** Cho phép Shipper xem nhiệm vụ đưa hàng hoàn về điểm tập kết đã được phân công.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Hoàn hàng

**Tác nhân:** Shipper

**Luồng cơ bản**

1. Shipper mở Hoàn hàng.
2. Hệ thống lấy các nhiệm vụ hoàn của Shipper.
3. Hệ thống hiển thị mã đơn, tình trạng hàng, điểm tập kết và trạng thái nhiệm vụ.
4. Shipper chọn nhiệm vụ.
5. Hệ thống kiểm tra quyền và hiển thị chi tiết để đưa hàng về đúng điểm tập kết.

**Luồng thay thế**

- **A1 – Chưa được giao nhiệm vụ hoàn**
  - *Điều kiện: Chưa được giao nhiệm vụ hoàn.*
  - A1.1. Hệ thống hiển thị danh sách trống.
  - A1.2. Shipper quay lại hoặc tải lại khi có phân công mới.

**Luồng ngoại lệ**

- **E1 – Nhiệm vụ không còn thuộc Shipper**
  - *Điều kiện: Nhiệm vụ không còn thuộc Shipper.*
  - E1.1. Hệ thống không cho thao tác hoàn và cập nhật danh sách.
  - E1.2. Shipper liên hệ Nhân viên nếu thông tin phân công cần làm rõ.

**Điều kiện trước:** Shipper đã đăng nhập; nhiệm vụ hoàn chỉ phát sinh sau quyết định Nhân viên.

**Điều kiện sau:** Shipper xem được nhiệm vụ hoàn của mình; chưa ghi nhận điểm tập kết đã nhận hàng.

**Business Rules**

- BR1. Không tự tạo nhiệm vụ hoàn từ kết quả giao thất bại.
- BR2. Đích hoàn trong phạm vi này là điểm tập kết để Shop đến lấy.

### UC04.9 Bàn giao hàng hoàn

**Mô tả:** Ghi nhận Shipper đưa hàng hoàn về điểm tập kết và Nhân viên đã nhận thực tế.

**Đường dẫn:** HTT Express >> Nhiệm vụ >> Hoàn hàng >> Bàn giao; Nhân viên >> Tiếp nhận hàng hoàn

**Tác nhân:** Shipper; Nhân viên/Admin xác nhận tiếp nhận

**Luồng cơ bản**

1. Shipper đưa hàng về điểm tập kết, mở nhiệm vụ và chọn Bàn giao hàng hoàn.
2. Hệ thống hiển thị mã đơn, kiện hàng và thông tin Shipper.
3. Shipper bàn giao thực tế và ghi nhận đề nghị tiếp nhận.
4. Nhân viên đối chiếu mã đơn, số kiện và tình trạng hàng.
5. Nhân viên xác nhận đã nhận hàng.
6. Hệ thống kiểm tra quyền, trạng thái và lưu thời gian, người giao/nhận; đặt đơn Chờ Shop đến lấy, đóng nhiệm vụ hoàn.
7. Hệ thống thêm lịch sử và thông báo Shop đến nhận.

**Luồng thay thế**

- **A1 – Shipper đã ghi bàn giao nhưng Nhân viên chưa xác nhận**
  - *Điều kiện: Shipper đã ghi bàn giao nhưng Nhân viên chưa xác nhận.*
  - A1.1. Hệ thống giữ đề nghị chờ xác nhận, đơn vẫn Đang hoàn.
  - A1.2. Chỉ chuyển Chờ Shop đến lấy sau bước 5.

**Luồng ngoại lệ**

- **E1 – Sai mã, thiếu kiện hoặc tình trạng hàng sai lệch**
  - *Điều kiện: Sai mã, thiếu kiện hoặc tình trạng hàng sai lệch.*
  - E1.1. Nhân viên ghi rõ sai lệch, chưa xác nhận tiếp nhận hoàn tất.
  - E1.2. Hệ thống giữ trạng thái đang xử lý và lưu ghi chú để kiểm tra.

**Điều kiện trước:** Đơn Đang hoàn; có nhiệm vụ hợp lệ; Shipper đang giữ kiện hàng cần hoàn.

**Điều kiện sau:** Thành công: hàng ở điểm tập kết, đơn Chờ Shop đến lấy. Chưa nhận/sai lệch: không kết thúc nhiệm vụ như đã nhận đủ.

**Business Rules**

- BR1. Shipper không tự xác nhận thay Nhân viên.
- BR2. Chờ Shop đến lấy chưa phải Đã hoàn về Shop; kết thúc hoàn tại UC04.11.

### UC04.10 Xác nhận nhập điểm tập kết

**Mô tả:** Ghi nhận điểm tập kết đã nhận hàng do Shipper lấy từ Shop, làm điều kiện phân công giao.

**Đường dẫn:** HTT Express >> Quản lý đơn hàng >> Chờ tiếp nhận >> Xác nhận nhập điểm tập kết

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở danh sách đơn Đã lấy hàng và chọn đơn cần tiếp nhận.
2. Hệ thống hiển thị mã vận đơn, Shop, kiện hàng và Shipper giữ hàng.
3. Nhân viên đối chiếu thông tin và nhận kiện hàng thực tế.
4. Nhân viên chọn Xác nhận tiếp nhận.
5. Hệ thống kiểm tra quyền và trạng thái chưa tiếp nhận trước đó.
6. Hệ thống ghi người giao/nhận, thời gian, đặt đơn Đã nhập điểm tập kết và ghi nhận hàng ở điểm tập kết.
7. Hệ thống thêm lịch sử và đưa đơn vào danh sách đủ điều kiện phân công giao.

**Luồng thay thế**

- **A1 – Chưa có hàng bàn giao thực tế**
  - *Điều kiện: Chưa có hàng bàn giao thực tế.*
  - A1.1. Nhân viên chưa xác nhận và giữ đơn trong danh sách chờ nhận.
  - A1.2. Shipper tiếp tục thực hiện bàn giao.

**Luồng ngoại lệ**

- **E1 – Thông tin kiện hàng không khớp hoặc đã được tiếp nhận**
  - *Điều kiện: Thông tin kiện hàng không khớp hoặc đã được tiếp nhận.*
  - E1.1. Hệ thống không tạo thêm xác nhận.
  - E1.2. Hiển thị trạng thái hoặc cho Nhân viên ghi sai lệch.
  - E1.3. Nhân viên kiểm tra trước khi xử lý tiếp.

**Điều kiện trước:** Đơn Đã lấy hàng; kiện hàng đã được Shipper đưa đến điểm tập kết.

**Điều kiện sau:** Thành công: Đã nhập điểm tập kết và đủ điều kiện phân công giao. Thất bại: giữ trạng thái trước đó.

**Business Rules**

- BR1. Không phân công giao lần đầu trước bước tiếp nhận này.
- BR2. Chỉ ghi nhận bàn giao, không tạo nghiệp vụ tồn kho, kệ hoặc quản lý kho.

### UC04.11 Xác nhận Shop nhận hàng hoàn

**Mô tả:** Ghi nhận hàng hoàn đã được bàn giao thực tế cho đúng Shop tại điểm tập kết.

**Đường dẫn:** HTT Express >> Quản lý đơn hàng >> Chờ Shop đến lấy >> Xác nhận Shop nhận hàng hoàn

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở đơn trong danh sách Chờ Shop đến lấy.
2. Hệ thống hiển thị mã đơn, Shop và thông tin hàng hoàn.
3. Nhân viên kiểm tra người đến nhận thuộc Shop hoặc có quyền đại diện theo quy trình bàn giao.
4. Nhân viên đối chiếu và giao kiện hàng thực tế.
5. Nhân viên chọn Xác nhận Shop đã nhận.
6. Hệ thống kiểm tra trạng thái, lưu người bàn giao, người nhận và thời gian; đặt Đã hoàn về Shop.
7. Hệ thống thêm lịch sử và thông báo hoàn tất cho Shop.

**Luồng thay thế**

- **A1 – Shop chưa đến nhận hoặc chưa xác định được người đại diện**
  - *Điều kiện: Shop chưa đến nhận hoặc chưa xác định được người đại diện.*
  - A1.1. Nhân viên chưa bàn giao, chưa xác nhận.
  - A1.2. Đơn giữ Chờ Shop đến lấy.

**Luồng ngoại lệ**

- **E1 – Sai kiện hàng hoặc đơn đã hoàn tất trước đó**
  - *Điều kiện: Sai kiện hàng hoặc đơn đã hoàn tất trước đó.*
  - E1.1. Hệ thống không ghi thêm xác nhận hoàn về Shop.
  - E1.2. Nhân viên kiểm tra sai lệch hoặc xem kết quả đã lưu.

**Điều kiện trước:** Đơn Chờ Shop đến lấy; hàng đang ở điểm tập kết; Shop hoặc người đại diện hợp lệ đã đến nhận.

**Điều kiện sau:** Thành công: Đã hoàn về Shop, kết thúc luồng hoàn. Chưa bàn giao: vẫn Chờ Shop đến lấy.

**Business Rules**

- BR1. Shop không tự bấm xác nhận thay Nhân viên.
- BR2. Không cho kết thúc hoàn chỉ vì Shipper đã mang hàng về điểm tập kết.

### UC04.12 Quyết định giao lại hoặc hoàn hàng

**Mô tả:** Cho phép Nhân viên chọn hướng xử lý sau một lần giao thất bại.

**Đường dẫn:** HTT Express >> Quản lý đơn hàng >> Giao hàng thất bại >> Xử lý

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn đơn giao thất bại.
2. Hệ thống hiển thị lý do, các lần giao, số lần đã giao và người đang giữ hàng.
3. Nhân viên kiểm tra thông tin, liên hệ làm rõ nếu cần và chọn Giao lại khi số lần đã giao nhỏ hơn 3.
4. Nhân viên nhập lý do/quyết định và xác nhận.
5. Hệ thống kiểm tra lại số lần và trạng thái.
6. Hệ thống lưu quyết định, chuyển Chờ giao lại và giữ toàn bộ lịch sử.
7. Nhân viên tiếp tục phân công giao qua UC06.6 khi đủ điều kiện.

**Luồng thay thế**

- **A1 – Nhân viên chọn hoàn sớm hoặc đã thất bại lần thứ ba**
  - *Điều kiện: Nhân viên chọn hoàn sớm hoặc đã thất bại lần thứ ba.*
  - A1.1. Hệ thống chỉ cho chọn hoàn nếu đã đủ 3 lần.
  - A1.2. Các lần trước có thể hoàn theo lý do thực tế.
  - A1.3. Nhân viên nhập lý do và xác nhận.
  - A1.4. Hệ thống đặt Chờ xử lý hoàn, lưu quyết định và thông báo.
  - A1.5. Phân công hoàn thực hiện UC06.7.

**Luồng ngoại lệ**

- **E1 – Chọn giao lại khi đã đủ 3 lần hoặc đơn đã được xử lý đồng thời**
  - *Điều kiện: Chọn giao lại khi đã đủ 3 lần hoặc đơn đã được xử lý đồng thời.*
  - E1.1. Hệ thống từ chối và hiển thị trạng thái mới.
  - E1.2. Nhân viên xem lại và chọn hướng xử lý được phép.

**Điều kiện trước:** Đơn Giao hàng thất bại, có kết quả và lý do cần xử lý; chưa có quyết định tiếp theo có hiệu lực.

**Điều kiện sau:** Đơn chuyển Chờ giao lại hoặc Chờ xử lý hoàn; có người, thời gian và lý do quyết định.

**Business Rules**

- BR1. Tối đa 3 lần giao thực tế, tính cả lần thành công nếu có.
- BR2. Không tự tạo nhiệm vụ hoàn chỉ vì đạt ngưỡng; Nhân viên phải quyết định.
- BR3. Thay người hoặc giao lại không xóa số lần và kết quả trước.

### UC04.13 Xử lý lấy hàng thất bại

**Mô tả:** Cho phép Nhân viên quyết định lấy lại hoặc kết thúc vận đơn khi chưa nhận được hàng từ Shop.

**Đường dẫn:** HTT Express >> Quản lý đơn hàng >> Lấy hàng thất bại >> Xử lý

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở đơn Lấy hàng thất bại.
2. Hệ thống hiển thị Shop, lịch sử lấy, Shipper và lý do thất bại.
3. Nhân viên kiểm tra khả năng tiếp tục nhận hàng và chọn Lấy lại.
4. Nhân viên nhập lý do xử lý và xác nhận.
5. Hệ thống kiểm tra trạng thái, lưu quyết định và chuyển Chờ lấy hàng.
6. Hệ thống thông báo Shop; Nhân viên phân công nhiệm vụ mới qua UC06.5.

**Luồng thay thế**

- **A1 – Không tiếp tục lấy hàng**
  - *Điều kiện: Không tiếp tục lấy hàng.*
  - A1.1. Nhân viên chọn Kết thúc do không lấy được hàng và nhập lý do.
  - A1.2. Hệ thống yêu cầu xác nhận, lưu quyết định và đặt trạng thái kết thúc tương ứng.
  - A1.3. Hệ thống thông báo Shop, không tạo nhiệm vụ mới.

**Luồng ngoại lệ**

- **E1 – Thiếu lý do hoặc đơn đã được người khác xử lý**
  - *Điều kiện: Thiếu lý do hoặc đơn đã được người khác xử lý.*
  - E1.1. Hệ thống từ chối lưu, thông báo trường thiếu hoặc trạng thái mới.
  - E1.2. Nhân viên bổ sung hoặc tải lại để tránh quyết định trùng.

**Điều kiện trước:** Đơn Lấy hàng thất bại; nhiệm vụ lấy trước đã có kết quả cuối và chưa có quyết định xử lý mới.

**Điều kiện sau:** Đơn Chờ lấy hàng hoặc Kết thúc do không lấy được hàng; mã vận đơn và lịch sử vẫn được giữ.

**Business Rules**

- BR1. Đây là xử lý sau duyệt, khác Shop hủy yêu cầu trước duyệt.
- BR2. Shipper không tự chọn kết thúc hoặc tự phân công lần lấy tiếp theo.

## 8 Quản lý vận đơn

### UC05.1 Chỉnh sửa yêu cầu gửi hàng

**Mô tả:** Cho phép Shop sửa nội dung yêu cầu của mình trước khi Nhân viên duyệt.

**Đường dẫn:** HTT Express >> Yêu cầu gửi hàng >> Chờ xác nhận >> Chỉnh sửa

**Tác nhân:** Shop

**Luồng cơ bản**

1. Shop chọn yêu cầu cần sửa.
2. Hệ thống kiểm tra quyền sở hữu và trạng thái, hiển thị thông tin hiện tại.
3. Shop sửa người gửi/nhận, địa chỉ, kiện hàng hoặc COD trong biểu mẫu.
4. Shop chọn Lưu.
5. Hệ thống kiểm tra trường bắt buộc, địa chỉ Hà Nội và số liệu kiện hàng, COD.
6. Hệ thống kiểm tra lại yêu cầu vẫn Chờ xác nhận trước khi lưu.
7. Hệ thống cập nhật nội dung, giữ mã yêu cầu và ghi thời gian sửa; hiển thị kết quả.

**Luồng thay thế**

- **A1 – Shop hủy chỉnh sửa trước khi lưu**
  - *Điều kiện: Shop hủy chỉnh sửa trước khi lưu.*
  - A1.1. Hệ thống bỏ dữ liệu chưa lưu.
  - A1.2. Yêu cầu giữ nội dung trước đó.

**Luồng ngoại lệ**

- **E1 – Yêu cầu vừa được duyệt hoặc dữ liệu không hợp lệ**
  - *Điều kiện: Yêu cầu vừa được duyệt hoặc dữ liệu không hợp lệ.*
  - E1.1. Hệ thống không ghi đè.
  - E1.2. Thông báo trạng thái mới hoặc trường cần sửa.
  - E1.3. Shop tải lại hoặc bổ sung thông tin nếu vẫn còn được sửa.

**Điều kiện trước:** Yêu cầu thuộc Shop đang đăng nhập, còn Chờ xác nhận.

**Điều kiện sau:** Yêu cầu được cập nhật nhưng vẫn Chờ xác nhận; nếu lỗi thì nội dung đã lưu không đổi.

**Business Rules**

- BR1. Shop không sửa sau khi vận đơn chính thức được tạo.
- BR2. Không đổi chủ Shop, tự cấp mã vận đơn hoặc tự chuyển trạng thái qua biểu mẫu sửa.

### UC05.2 Tạo yêu cầu gửi hàng

**Mô tả:** Cho phép Shop gửi yêu cầu vận chuyển để Nhân viên kiểm tra và duyệt.

**Đường dẫn:** HTT Express >> Yêu cầu gửi hàng >> Tạo yêu cầu

**Tác nhân:** Shop

**Luồng cơ bản**

1. Shop chọn Tạo yêu cầu gửi hàng.
2. Hệ thống mở biểu mẫu và xác định Shop từ phiên đăng nhập.
3. Shop nhập người gửi, người nhận, điện thoại và địa chỉ lấy/giao.
4. Shop nhập mô tả kiện hàng, số kiện, thông tin khối lượng nếu áp dụng và COD bằng 0 nếu không thu hộ.
5. Shop kiểm tra nội dung và chọn Gửi yêu cầu.
6. Hệ thống kiểm tra dữ liệu bắt buộc, giá trị hợp lệ và địa chỉ trong phạm vi Hà Nội.
7. Hệ thống lưu yêu cầu, sinh mã yêu cầu, đặt Chờ xác nhận và ghi lịch sử.
8. Hệ thống thông báo đã tiếp nhận và hiển thị yêu cầu vừa tạo.

**Luồng thay thế**

- **A1 – Shop chưa muốn gửi**
  - *Điều kiện: Shop chưa muốn gửi.*
  - A1.1. Shop chọn Hủy hoặc rời biểu mẫu trước khi gửi.
  - A1.2. Hệ thống không tạo yêu cầu từ dữ liệu chưa gửi.

**Luồng ngoại lệ**

- **E1 – Thiếu thông tin, địa chỉ ngoài phạm vi hoặc COD âm**
  - *Điều kiện: Thiếu thông tin, địa chỉ ngoài phạm vi hoặc COD âm.*
  - E1.1. Hệ thống từ chối tạo và chỉ rõ trường chưa hợp lệ.
  - E1.2. Shop sửa dữ liệu và gửi lại.

**Điều kiện trước:** Shop đã đăng nhập bằng tài khoản hoạt động.

**Điều kiện sau:** Thành công: một yêu cầu Chờ xác nhận gắn với Shop được tạo; chưa có mã vận đơn chính thức.

**Business Rules**

- BR1. Chỉ Nhân viên duyệt mới sinh mã vận đơn.
- BR2. Không nhận Shop sở hữu do người dùng tùy ý gửi thay cho Shop trong phiên.
- BR3. Không tự thêm nghiệp vụ tính phí hoặc thanh toán trực tuyến.

### UC05.3 Xem danh sách vận đơn của Shop

**Mô tả:** Cho phép Shop xem yêu cầu và vận đơn thuộc mình, phân biệt tình trạng chờ duyệt và đã duyệt.

**Đường dẫn:** HTT Express >> Vận đơn của tôi >> Danh sách

**Tác nhân:** Shop

**Luồng cơ bản**

1. Shop mở Vận đơn của tôi.
2. Hệ thống xác định Shop và lấy dữ liệu trong phạm vi sở hữu.
3. Hệ thống hiển thị mã yêu cầu/mã vận đơn, người nhận, thời gian và trạng thái.
4. Shop chọn bộ lọc trạng thái hoặc nhập từ khóa theo trường hỗ trợ.
5. Hệ thống áp dụng bộ lọc trong dữ liệu của Shop và trả danh sách phù hợp.
6. Shop chọn một dòng để xem chi tiết hoặc thao tác được phép.

**Luồng thay thế**

- **A1 – Không có dữ liệu hoặc không khớp bộ lọc**
  - *Điều kiện: Không có dữ liệu hoặc không khớp bộ lọc.*
  - A1.1. Hệ thống hiển thị chưa có kết quả.
  - A1.2. Shop bỏ bộ lọc hoặc tạo yêu cầu mới.

**Luồng ngoại lệ**

- **E1 – Không tải được danh sách**
  - *Điều kiện: Không tải được danh sách.*
  - E1.1. Hệ thống thông báo tải thất bại và cho thử lại.
  - E1.2. Không hiển thị dữ liệu không đúng Shop.

**Điều kiện trước:** Shop đã đăng nhập.

**Điều kiện sau:** Shop xem danh sách hợp lệ, không làm thay đổi đơn.

**Business Rules**

- BR1. Mọi bộ lọc và trang dữ liệu đều giới hạn theo Shop.
- BR2. Yêu cầu chưa duyệt hiển thị mã yêu cầu, không giả định đã có mã vận đơn.

### UC05.4 Xem chi tiết vận đơn của Shop

**Mô tả:** Cho phép Shop xem thông tin yêu cầu hoặc vận đơn của mình và các thao tác theo trạng thái.

**Đường dẫn:** HTT Express >> Vận đơn của tôi >> Danh sách >> Chi tiết

**Tác nhân:** Shop

**Luồng cơ bản**

1. Shop chọn một yêu cầu hoặc vận đơn.
2. Hệ thống kiểm tra quyền sở hữu trên bản ghi được chọn.
3. Hệ thống lấy thông tin người gửi/nhận, kiện hàng, COD và trạng thái.
4. Hệ thống hiển thị lịch sử, kết quả xử lý và phân công được phép công bố.
5. Hệ thống hiển thị Sửa/Hủy nếu Chờ xác nhận; theo dõi vận chuyển nếu đã có nhiệm vụ phù hợp.
6. Shop xem thông tin hoặc chọn chức năng liên quan.

**Luồng thay thế**

- **A1 – Yêu cầu chưa được duyệt**
  - *Điều kiện: Yêu cầu chưa được duyệt.*
  - A1.1. Hệ thống hiển thị mã yêu cầu và trạng thái Chờ xác nhận.
  - A1.2. Shop có thể sửa theo UC05.1 hoặc hủy theo UC05.5.

**Luồng ngoại lệ**

- **E1 – Truy cập bản ghi không thuộc Shop hoặc bản ghi không tồn tại**
  - *Điều kiện: Truy cập bản ghi không thuộc Shop hoặc bản ghi không tồn tại.*
  - E1.1. Hệ thống từ chối và không trả dữ liệu chi tiết.
  - E1.2. Shop quay lại danh sách được phép xem.

**Điều kiện trước:** Shop đã đăng nhập; bản ghi thuộc quyền sở hữu của Shop.

**Điều kiện sau:** Chi tiết được hiển thị đúng quyền; không tự thay đổi trạng thái.

**Business Rules**

- BR1. Truy cập bằng đường dẫn trực tiếp cũng phải kiểm tra quyền.
- BR2. Shop không có quyền sửa kết quả giao, COD đã ghi nhận hoặc phân công Shipper.

### UC05.5 Hủy yêu cầu gửi hàng

**Mô tả:** Cho phép Shop ngừng yêu cầu của mình trước khi được duyệt.

**Đường dẫn:** HTT Express >> Yêu cầu gửi hàng >> Chi tiết >> Hủy yêu cầu

**Tác nhân:** Shop

**Luồng cơ bản**

1. Shop mở yêu cầu và chọn Hủy yêu cầu.
2. Hệ thống kiểm tra quyền và trạng thái hiện tại.
3. Hệ thống hiển thị nội dung yêu cầu xác nhận hủy.
4. Shop xác nhận hủy.
5. Hệ thống kiểm tra lại trạng thái để tránh xung đột với việc duyệt.
6. Hệ thống đặt Đã hủy, ghi người/thời gian và lịch sử.
7. Hệ thống thông báo hủy thành công và cập nhật danh sách.

**Luồng thay thế**

- **A1 – Shop chọn Không hủy trên hộp xác nhận**
  - *Điều kiện: Shop chọn Không hủy trên hộp xác nhận.*
  - A1.1. Hệ thống đóng hộp xác nhận.
  - A1.2. Yêu cầu giữ nguyên trạng thái.

**Luồng ngoại lệ**

- **E1 – Yêu cầu đã duyệt, bị từ chối hoặc đã hủy**
  - *Điều kiện: Yêu cầu đã duyệt, bị từ chối hoặc đã hủy.*
  - E1.1. Hệ thống không hủy thêm và thông báo trạng thái mới.
  - E1.2. Shop xem lại chi tiết, không xóa yêu cầu.

**Điều kiện trước:** Yêu cầu thuộc Shop, còn Chờ xác nhận và chưa tạo vận đơn chính thức.

**Điều kiện sau:** Thành công: Đã hủy, không được tiếp tục duyệt. Thất bại: giữ trạng thái hiện có.

**Business Rules**

- BR1. Không xóa cứng bản ghi.
- BR2. Shop không dùng chức năng này để hủy vận đơn đang vận chuyển.

### UC05.6 Xác nhận vận đơn

**Mô tả:** Duyệt yêu cầu hợp lệ của Shop để tạo vận đơn chính thức và cho phép điều phối lấy hàng.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Chờ xác nhận >> Xác nhận

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn yêu cầu chờ xác nhận.
2. Hệ thống hiển thị người gửi/nhận, địa chỉ, kiện hàng và COD.
3. Nhân viên kiểm tra nội dung và phạm vi vận chuyển Hà Nội.
4. Nhân viên chọn Xác nhận và xác nhận thao tác.
5. Hệ thống kiểm tra lại trạng thái và việc chưa có vận đơn cho yêu cầu.
6. Hệ thống sinh mã vận đơn duy nhất, liên kết yêu cầu và đặt Chờ lấy hàng trong cùng lần xử lý.
7. Hệ thống lưu lịch sử, thông báo Shop và hiển thị đơn đủ điều kiện phân công lấy.

**Luồng thay thế**

- **A1 – Nhân viên nhận thấy không thể chấp nhận yêu cầu**
  - *Điều kiện: Nhân viên nhận thấy không thể chấp nhận yêu cầu.*
  - A1.1. Nhân viên không duyệt.
  - A1.2. Nếu từ chối, chuyển sang UC05.8 để nhập lý do và xử lý.

**Luồng ngoại lệ**

- **E1 – Shop vừa hủy/sửa hoặc yêu cầu đã được duyệt**
  - *Điều kiện: Shop vừa hủy/sửa hoặc yêu cầu đã được duyệt.*
  - E1.1. Hệ thống từ chối duyệt trên dữ liệu cũ và hiển thị kết quả hiện tại.
  - E1.2. Nhân viên tải lại trước khi quyết định.

**Điều kiện trước:** Nhân viên có quyền duyệt; yêu cầu Chờ xác nhận và thông tin đầy đủ.

**Điều kiện sau:** Một vận đơn chính thức Chờ lấy hàng được tạo cho yêu cầu; lỗi thì không tạo vận đơn dở dang.

**Business Rules**

- BR1. Một yêu cầu chỉ được duyệt thành một vận đơn.
- BR2. Gửi lại thao tác duyệt không sinh thêm mã vận đơn.
- BR3. Mã yêu cầu và mã vận đơn có ý nghĩa riêng, không thay thế lịch sử của nhau.

### UC05.7 Xem chi tiết vận đơn của Nhân viên

**Mô tả:** Cho phép Nhân viên xem thông tin đầy đủ phục vụ duyệt, điều phối và xử lý vận đơn.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Danh sách >> Chi tiết

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn yêu cầu hoặc vận đơn từ danh sách.
2. Hệ thống kiểm tra quyền quản lý.
3. Hệ thống tải thông tin Shop, người nhận, kiện hàng, COD và trạng thái hiện tại.
4. Hệ thống hiển thị lịch sử xử lý, phân công, người giữ hàng và các lần giao.
5. Hệ thống hiển thị các hành động được phép theo trạng thái.
6. Nhân viên xem và chọn tác vụ tương ứng nếu cần.

**Luồng thay thế**

- **A1 – Yêu cầu chưa được duyệt**
  - *Điều kiện: Yêu cầu chưa được duyệt.*
  - A1.1. Hệ thống hiển thị chi tiết yêu cầu và thao tác duyệt/từ chối.
  - A1.2. Các thông tin chưa phát sinh như Shipper và kết quả giao được để trống có nhãn rõ ràng.

**Luồng ngoại lệ**

- **E1 – Không tìm thấy bản ghi hoặc không tải đủ thông tin**
  - *Điều kiện: Không tìm thấy bản ghi hoặc không tải đủ thông tin.*
  - E1.1. Hệ thống báo lỗi phù hợp, không cho thao tác dựa trên dữ liệu chưa tải.
  - E1.2. Nhân viên quay lại danh sách hoặc tải lại.

**Điều kiện trước:** Nhân viên đã đăng nhập và có quyền quản lý vận đơn.

**Điều kiện sau:** Nhân viên xem dữ liệu nghiệp vụ; chưa phát sinh thay đổi nếu chưa chọn tác vụ riêng.

**Business Rules**

- BR1. Không có thao tác tự đặt bất kỳ trạng thái nào để bỏ qua các bước bàn giao.
- BR2. Quyền xem COD không bao gồm quyền sửa khoản thu đã chốt hoặc đối soát.

### UC05.8 Từ chối vận đơn

**Mô tả:** Từ chối yêu cầu chưa được duyệt và thông báo rõ lý do cho Shop.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Chờ xác nhận >> Từ chối

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở yêu cầu và kiểm tra nội dung.
2. Nhân viên chọn Từ chối.
3. Hệ thống hiển thị trường lý do và xác nhận.
4. Nhân viên nhập lý do phù hợp và xác nhận.
5. Hệ thống kiểm tra trạng thái hiện tại và lý do bắt buộc.
6. Hệ thống đặt yêu cầu Bị từ chối, lưu người/thời gian và lý do.
7. Hệ thống thông báo Shop, không sinh mã vận đơn.

**Luồng thay thế**

- **A1 – Nhân viên hủy thao tác trước xác nhận**
  - *Điều kiện: Nhân viên hủy thao tác trước xác nhận.*
  - A1.1. Hệ thống đóng biểu mẫu.
  - A1.2. Yêu cầu vẫn Chờ xác nhận.

**Luồng ngoại lệ**

- **E1 – Lý do trống hoặc yêu cầu không còn Chờ xác nhận**
  - *Điều kiện: Lý do trống hoặc yêu cầu không còn Chờ xác nhận.*
  - E1.1. Hệ thống từ chối lưu và nêu nguyên nhân.
  - E1.2. Nhân viên bổ sung lý do hoặc tải lại thông tin.

**Điều kiện trước:** Yêu cầu đang Chờ xác nhận; Nhân viên có quyền xử lý.

**Điều kiện sau:** Yêu cầu Bị từ chối kèm lý do; nếu lỗi thì không thay đổi trạng thái.

**Business Rules**

- BR1. Tên UC giữ theo danh mục, nhưng đối tượng bị từ chối là yêu cầu trước duyệt.
- BR2. Không dùng chức năng này để từ chối vận đơn đã điều phối hoặc đang vận chuyển.

### UC05.9 Xem danh sách vận đơn của Nhân viên

**Mô tả:** Cho phép Nhân viên tìm và lọc toàn bộ yêu cầu, vận đơn để xử lý theo trạng thái.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Danh sách

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở Quản lý vận đơn.
2. Hệ thống lấy danh sách theo quyền quản lý.
3. Hệ thống hiển thị mã yêu cầu/vận đơn, Shop, người nhận, thời gian và trạng thái.
4. Nhân viên nhập mã hoặc chọn bộ lọc trạng thái, Shop và thời gian nếu được hỗ trợ.
5. Hệ thống kiểm tra điều kiện lọc và trả danh sách phù hợp.
6. Nhân viên chọn bản ghi để xem chi tiết và xử lý theo UC05.7.

**Luồng thay thế**

- **A1 – Không có dữ liệu theo điều kiện lọc**
  - *Điều kiện: Không có dữ liệu theo điều kiện lọc.*
  - A1.1. Hệ thống hiển thị Không có kết quả.
  - A1.2. Nhân viên điều chỉnh hoặc xóa bộ lọc.

**Luồng ngoại lệ**

- **E1 – Điều kiện lọc không hợp lệ hoặc lỗi tải**
  - *Điều kiện: Điều kiện lọc không hợp lệ hoặc lỗi tải.*
  - E1.1. Hệ thống thông báo trường lỗi hoặc chưa thể tải danh sách.
  - E1.2. Nhân viên sửa điều kiện hoặc tải lại.

**Điều kiện trước:** Nhân viên đã đăng nhập và có quyền quản lý.

**Điều kiện sau:** Danh sách phù hợp được hiển thị; trạng thái vận đơn không thay đổi.

**Business Rules**

- BR1. Phân biệt yêu cầu chờ duyệt và vận đơn chính thức.
- BR2. Danh sách là nơi chọn tác vụ, không cho sửa trạng thái trực tiếp tùy ý.

## 9 Quản lý Shipper

### UC06.1 Xem danh sách Shipper

**Mô tả:** Cho phép Nhân viên xem hồ sơ tóm tắt và trạng thái tài khoản Shipper phục vụ quản lý.

**Đường dẫn:** HTT Express >> Quản lý Shipper >> Danh sách

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên mở Quản lý Shipper.
2. Hệ thống lấy các tài khoản có vai trò Shipper.
3. Hệ thống hiển thị họ tên, tên đăng nhập, liên hệ và trạng thái hoạt động/khóa.
4. Nhân viên tìm theo thông tin hoặc lọc theo trạng thái.
5. Hệ thống trả danh sách phù hợp.
6. Nhân viên chọn xem hoặc thực hiện thao tác quản lý được cấp.

**Luồng thay thế**

- **A1 – Danh sách chưa có Shipper hoặc không khớp bộ lọc**
  - *Điều kiện: Danh sách chưa có Shipper hoặc không khớp bộ lọc.*
  - A1.1. Hệ thống hiển thị danh sách trống.
  - A1.2. Nhân viên có thể bỏ lọc hoặc chọn Thêm Shipper.

**Luồng ngoại lệ**

- **E1 – Không tải được danh sách**
  - *Điều kiện: Không tải được danh sách.*
  - E1.1. Hệ thống thông báo chưa thể tải dữ liệu.
  - E1.2. Nhân viên tải lại, không sử dụng dữ liệu chưa xác nhận để phân công.

**Điều kiện trước:** Nhân viên đã đăng nhập và có quyền quản lý Shipper.

**Điều kiện sau:** Hiển thị danh sách đúng vai trò; chưa thay đổi tài khoản hoặc phân công.

**Business Rules**

- BR1. Không trả về mật khẩu, giá trị băm hoặc thông tin phiên.
- BR2. Trạng thái tài khoản hoạt động không đồng nghĩa Shipper chưa có nhiệm vụ; khi phân công vẫn kiểm tra riêng.

### UC06.2 Thêm Shipper

**Mô tả:** Cho phép Nhân viên tạo tài khoản Shipper để tham gia nhận nhiệm vụ.

**Đường dẫn:** HTT Express >> Quản lý Shipper >> Thêm Shipper

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn Thêm Shipper.
2. Hệ thống hiển thị biểu mẫu thông tin và tài khoản.
3. Nhân viên nhập họ tên, liên hệ, tên đăng nhập và thông tin cấp tài khoản theo cơ chế đang dùng.
4. Nhân viên chọn Lưu.
5. Hệ thống kiểm tra trường bắt buộc, định dạng và thông tin trùng.
6. Hệ thống tạo tài khoản gắn vai trò Shipper, lưu thông tin xác thực an toàn.
7. Hệ thống ghi người tạo, thời gian và thông báo kết quả.

**Luồng thay thế**

- **A1 – Nhân viên hủy biểu mẫu trước khi lưu**
  - *Điều kiện: Nhân viên hủy biểu mẫu trước khi lưu.*
  - A1.1. Hệ thống không tạo tài khoản.
  - A1.2. Quay lại danh sách Shipper.

**Luồng ngoại lệ**

- **E1 – Tên đăng nhập hoặc thông tin định danh bị trùng**
  - *Điều kiện: Tên đăng nhập hoặc thông tin định danh bị trùng.*
  - E1.1. Hệ thống không tạo tài khoản thứ hai và chỉ rõ trường cần kiểm tra.
  - E1.2. Nhân viên sửa thông tin hoặc tìm tài khoản đã có.

**Điều kiện trước:** Nhân viên có quyền tạo tài khoản Shipper.

**Điều kiện sau:** Thành công: có một tài khoản Shipper mới; lỗi thì không có tài khoản dở dang.

**Business Rules**

- BR1. Chức năng này luôn cấp vai trò Shipper, không tự cấp quyền Admin.
- BR2. Quy tắc định danh duy nhất áp dụng thống nhất với Quản lý tài khoản.
- BR3. Không thêm bước tự đăng ký hoặc OTP/email ngoài cơ chế tài khoản hiện có.

### UC06.3 Cập nhật thông tin Shipper

**Mô tả:** Cho phép Nhân viên sửa hồ sơ Shipper mà vẫn giữ các dữ liệu nghiệp vụ đã phát sinh.

**Đường dẫn:** HTT Express >> Quản lý Shipper >> Chọn Shipper >> Chỉnh sửa

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn Shipper và mở Chỉnh sửa.
2. Hệ thống tải hồ sơ hiện tại và các trường được sửa.
3. Nhân viên cập nhật thông tin liên hệ hoặc thông tin hồ sơ.
4. Nhân viên chọn Lưu.
5. Hệ thống kiểm tra quyền, định dạng và thông tin trùng.
6. Hệ thống lưu hồ sơ, ghi người sửa và thời gian.
7. Hệ thống hiển thị thông tin sau cập nhật.

**Luồng thay thế**

- **A1 – Nhân viên hủy chỉnh sửa**
  - *Điều kiện: Nhân viên hủy chỉnh sửa.*
  - A1.1. Hệ thống bỏ dữ liệu chưa lưu.
  - A1.2. Hồ sơ cũ tiếp tục có hiệu lực.

**Luồng ngoại lệ**

- **E1 – Thông tin không hợp lệ hoặc tài khoản vừa thay đổi**
  - *Điều kiện: Thông tin không hợp lệ hoặc tài khoản vừa thay đổi.*
  - E1.1. Hệ thống không ghi đè dữ liệu và báo nguyên nhân.
  - E1.2. Nhân viên sửa hoặc tải lại để cập nhật từ hồ sơ mới.

**Điều kiện trước:** Shipper tồn tại; Nhân viên có quyền chỉnh sửa hồ sơ.

**Điều kiện sau:** Hồ sơ cập nhật hợp lệ; lịch sử phân công và giao nhận còn nguyên.

**Business Rules**

- BR1. Không đổi vai trò bằng biểu mẫu hồ sơ Shipper.
- BR2. Khóa/mở khóa dùng UC06.4; đổi người phụ trách nhiệm vụ dùng UC06.8, không sửa qua hồ sơ.

### UC06.4 Khóa hoặc mở khóa tài khoản Shipper

**Mô tả:** Cho phép Nhân viên điều chỉnh quyền truy cập của Shipper và nhận biết nhiệm vụ cần xử lý khi khóa.

**Đường dẫn:** HTT Express >> Quản lý Shipper >> Chọn Shipper >> Khóa hoặc Mở khóa

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn tài khoản Shipper đang hoạt động và chọn Khóa.
2. Hệ thống hiển thị trạng thái và các nhiệm vụ đang mở của Shipper.
3. Nhân viên kiểm tra ảnh hưởng và xác nhận khóa.
4. Hệ thống kiểm tra quyền và trạng thái mới nhất.
5. Hệ thống đặt tài khoản Bị khóa, vô hiệu hóa phiên và chặn phân công mới.
6. Hệ thống ghi lịch sử; giữ nhiệm vụ đang mở và đánh dấu cần Nhân viên xử lý.
7. Nhân viên tổ chức bàn giao/phân công lại theo UC06.8 nếu có nhiệm vụ chưa hoàn tất.

**Luồng thay thế**

- **A1 – Mở khóa tài khoản**
  - *Điều kiện: Mở khóa tài khoản.*
  - A1.1. Nhân viên chọn Mở khóa và xác nhận.
  - A1.2. Hệ thống kiểm tra, đặt tài khoản hoạt động và ghi lịch sử.
  - A1.3. Shipper đăng nhập lại để dùng chức năng, không khôi phục quyền trên nhiệm vụ đã thay thế.

**Luồng ngoại lệ**

- **E1 – Tài khoản đã có trạng thái yêu cầu hoặc lỗi lưu**
  - *Điều kiện: Tài khoản đã có trạng thái yêu cầu hoặc lỗi lưu.*
  - E1.1. Hệ thống trả trạng thái hiện tại hoặc báo chưa thay đổi được.
  - E1.2. Không tự đóng nhiệm vụ để hoàn tất thao tác khóa.

**Điều kiện trước:** Nhân viên có quyền quản lý; tài khoản Shipper tồn tại.

**Điều kiện sau:** Trạng thái tài khoản được cập nhật; nhiệm vụ còn được giữ và xử lý riêng.

**Business Rules**

- BR1. Tài khoản khóa không được đăng nhập, gọi chức năng được bảo vệ hoặc nhận phân công mới.
- BR2. Nếu Shipper khóa đang giữ hàng, Nhân viên xác nhận tiếp nhận thực tế; không yêu cầu tài khoản khóa đăng nhập để bàn giao.

### UC06.5 Phân công Shipper lấy hàng

**Mô tả:** Tạo nhiệm vụ lấy hàng cho Shipper trên vận đơn đã duyệt hoặc đã được quyết định lấy lại.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Chờ lấy hàng >> Phân công lấy hàng

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn đơn Chờ lấy hàng.
2. Hệ thống hiển thị thông tin Shop, địa chỉ và danh sách Shipper hoạt động.
3. Nhân viên chọn Shipper và xác nhận phân công.
4. Hệ thống kiểm tra quyền, trạng thái đơn và tài khoản được chọn.
5. Hệ thống kiểm tra chưa có phân công lấy có hiệu lực cho cùng đơn.
6. Hệ thống tạo nhiệm vụ lấy, đặt Đã phân công lấy hàng và ghi người/thời gian phân công.
7. Hệ thống thông báo Shipper; nhiệm vụ xuất hiện trong danh sách lấy hàng của người được giao.

**Luồng thay thế**

- **A1 – Không có Shipper phù hợp**
  - *Điều kiện: Không có Shipper phù hợp.*
  - A1.1. Hệ thống thông báo chưa thể chọn người nhận nhiệm vụ.
  - A1.2. Nhân viên giữ đơn Chờ lấy hàng và phân công sau.

**Luồng ngoại lệ**

- **E1 – Shipper vừa bị khóa hoặc đơn đã được phân công**
  - *Điều kiện: Shipper vừa bị khóa hoặc đơn đã được phân công.*
  - E1.1. Hệ thống từ chối tạo nhiệm vụ trùng và tải lại trạng thái.
  - E1.2. Nhân viên chọn lại theo dữ liệu mới.

**Điều kiện trước:** Đơn Chờ lấy hàng; chưa có nhiệm vụ lấy đang mở; Shipper được chọn hoạt động.

**Điều kiện sau:** Có một nhiệm vụ lấy hợp lệ; đơn Đã phân công lấy hàng. Nếu lỗi: chưa tạo nhiệm vụ mới.

**Business Rules**

- BR1. Lấy lại chỉ sau quyết định UC04.13 và giữ lịch sử lần trước.
- BR2. Thay thế phân công còn mở phải dùng UC06.8, không tạo phân công song song.

### UC06.6 Phân công Shipper giao hàng

**Mô tả:** Tạo đợt nhiệm vụ giao lần đầu hoặc giao lại khi hàng và số lần giao đáp ứng điều kiện.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Đủ điều kiện giao >> Phân công giao hàng

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn đơn đủ điều kiện giao.
2. Hệ thống hiển thị điểm đang giữ hàng, quyết định giao lại nếu có và số lần đã giao.
3. Nhân viên chọn Shipper hoạt động và kiểm tra việc bàn giao thực tế cho người được chọn.
4. Nhân viên xác nhận phân công khi Shipper đã nhận hàng theo điều kiện bàn giao.
5. Hệ thống kiểm tra trạng thái, số lần và việc không có nhiệm vụ giao đang mở khác.
6. Hệ thống tạo nhiệm vụ giao, ghi người phụ trách và đặt Đang giao hàng.
7. Hệ thống lưu lịch sử và thông báo Shipper, Shop.

**Luồng thay thế**

- **A1 – Giao lại bằng Shipper cũ còn giữ hàng**
  - *Điều kiện: Giao lại bằng Shipper cũ còn giữ hàng.*
  - A1.1. Hệ thống kiểm tra đã có quyết định giao lại và còn lượt.
  - A1.2. Nhân viên tạo nhiệm vụ đợt mới cho người đó.
  - A1.3. Lịch sử đợt cũ không bị sửa.

- **A2 – Đổi Shipper khi người cũ còn giữ hàng**
  - *Điều kiện: Đổi Shipper khi người cũ còn giữ hàng.*
  - A2.1. Nhân viên thực hiện bàn giao về điểm tập kết theo UC06.8.
  - A2.2. Chỉ phân công mới sau xác nhận nhận hàng thực tế.

**Luồng ngoại lệ**

- **E1 – Chưa nhận tại điểm tập kết, đủ 3 lần hoặc Shipper bị khóa**
  - *Điều kiện: Chưa nhận tại điểm tập kết, đủ 3 lần hoặc Shipper bị khóa.*
  - E1.1. Hệ thống từ chối phân công và nêu điều kiện chưa đạt.
  - E1.2. Nhân viên xử lý điều kiện hoặc chuyển quyết định hoàn khi đủ ngưỡng.

**Điều kiện trước:** Lần đầu: Đã nhập điểm tập kết. Giao lại: Chờ giao lại, số lần đã giao < 3 và người giữ hàng được xác định.

**Điều kiện sau:** Một nhiệm vụ giao hợp lệ được tạo; đơn Đang giao hàng, chưa tăng số lần đã giao chỉ vì phân công.

**Business Rules**

- BR1. Lần đầu không bỏ qua UC04.10.
- BR2. Tối đa 3 lần giao thực tế; đổi người không cấp thêm lượt.
- BR3. Không có hai nhiệm vụ giao hiệu lực cùng đơn.

### UC06.7 Phân công Shipper hoàn hàng

**Mô tả:** Tạo nhiệm vụ đưa hàng về điểm tập kết sau quyết định hoàn của Nhân viên.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Chờ xử lý hoàn >> Phân công hoàn hàng

**Tác nhân:** Nhân viên/Admin

**Luồng cơ bản**

1. Nhân viên chọn đơn Chờ xử lý hoàn.
2. Hệ thống hiển thị quyết định hoàn, kiện hàng và người đang giữ hàng.
3. Nhân viên chọn Shipper hoạt động để đưa hàng về điểm tập kết.
4. Hệ thống kiểm tra điều kiện nhận hàng và việc chưa có nhiệm vụ hoàn hiệu lực.
5. Nhân viên xác nhận phân công sau khi đủ điều kiện bàn giao.
6. Hệ thống tạo nhiệm vụ hoàn, đặt Đang hoàn, lưu lịch sử và thông báo Shipper.
7. Shipper xem nhiệm vụ và thực hiện bàn giao theo UC04.9.

**Luồng thay thế**

- **A1 – Shipper khác được chọn nhưng người cũ còn giữ hàng**
  - *Điều kiện: Shipper khác được chọn nhưng người cũ còn giữ hàng.*
  - A1.1. Nhân viên tổ chức đưa hàng về điểm tập kết theo quy tắc UC06.8 trước khi cấp quyền cho người mới.
  - A1.2. Nếu hàng đã được tiếp nhận tại điểm tập kết, ghi nhận tiếp nhận hàng hoàn theo UC04.9 và Chờ Shop đến lấy.
  - A1.3. Không tạo chuyến hoàn thừa.

**Luồng ngoại lệ**

- **E1 – Chưa có quyết định hoàn hoặc người được chọn bị khóa**
  - *Điều kiện: Chưa có quyết định hoàn hoặc người được chọn bị khóa.*
  - E1.1. Hệ thống từ chối phân công.
  - E1.2. Nhân viên hoàn tất quyết định hoặc chọn Shipper hoạt động đủ điều kiện.

**Điều kiện trước:** Đơn Chờ xử lý hoàn; có quyết định UC04.12 và xác định được người/địa điểm giữ hàng.

**Điều kiện sau:** Có nhiệm vụ hoàn hợp lệ, đơn Đang hoàn; hoặc đã nhận hàng hoàn tại điểm tập kết và chuyển Chờ Shop đến lấy theo nhánh A1.

**Business Rules**

- BR1. Không đặt Đã hoàn về Shop tại bước phân công.
- BR2. Không cấp nhiệm vụ mới cho người chưa thực tế nhận hàng; giữ lịch sử vận chuyển trước đó.

### UC06.8 Đổi Shipper hoặc phân công lại

**Mô tả:** Cho phép thay người thực hiện nhiệm vụ chưa hoàn tất mà không làm mất lịch sử hoặc bỏ qua việc bàn giao kiện hàng.

**Đường dẫn:** HTT Express >> Quản lý vận đơn >> Chi tiết >> Phân công >> Đổi Shipper

**Tác nhân:** Nhân viên/Admin; Shipper cũ tham gia bàn giao khi đang giữ hàng

**Luồng cơ bản**

1. Nhân viên mở phân công, kiểm tra tiến trình và chọn Đổi Shipper.
2. Hệ thống hiển thị người cũ, nhiệm vụ, tình trạng giữ hàng và danh sách Shipper hoạt động.
3. Nhân viên chọn người thay thế khác người cũ, nhập lý do và xác nhận.
4. Nếu người cũ chưa nhận hàng, hệ thống kiểm tra điều kiện và thay thế phân công trong cùng lần xử lý.
5. Hệ thống đóng nhiệm vụ cũ là Đã thay thế, tạo nhiệm vụ mới đúng loại cho người mới và giữ trạng thái nghiệp vụ phù hợp.
6. Hệ thống thu hồi quyền cập nhật của người cũ, cấp quyền nhiệm vụ cho người mới và thông báo các bên.
7. Hệ thống lưu lịch sử thay người, lý do, thời gian và người điều phối.

**Luồng thay thế**

- **A1 – Shipper cũ đã giữ hàng**
  - *Điều kiện: Shipper cũ đã giữ hàng.*
  - A1.1. Hệ thống đặt nhiệm vụ Chờ bàn giao đổi Shipper.
  - A1.2. Người mới chỉ là lựa chọn dự kiến, chưa có quyền nhiệm vụ.
  - A1.3. Người cũ đưa hàng về điểm tập kết, chỉ được xem, chia sẻ vị trí phục vụ bàn giao và ghi nhận bàn giao.
  - A1.4. Nhân viên kiểm tra và xác nhận nhận thực tế, lưu người giao/nhận và thời gian.
  - A1.5. Hệ thống kiểm tra lại người mới còn hoạt động, đóng nhiệm vụ cũ và tạo nhiệm vụ thay thế đúng tiến trình.
  - A1.6. Hàng hoàn đã về điểm tập kết thì tiếp nhận UC04.9, không tạo chuyến hoàn mới.

- **A2 – Nhiệm vụ trước đã kết thúc bằng kết quả thất bại**
  - *Điều kiện: Nhiệm vụ trước đã kết thúc bằng kết quả thất bại.*
  - A2.1. Nhân viên xử lý lấy lại qua UC04.13 hoặc giao lại/hoàn qua UC04.12.
  - A2.2. Phân công đợt mới qua UC06.5, UC06.6 hoặc UC06.7.
  - A2.3. Giữ nguyên kết quả cũ, không đổi nhiệm vụ thất bại thành Đã thay thế.

**Luồng ngoại lệ**

- **E1 – Chưa nhận đủ hàng, người cũ bị khóa hoặc người mới không còn hợp lệ**
  - *Điều kiện: Chưa nhận đủ hàng, người cũ bị khóa hoặc người mới không còn hợp lệ.*
  - E1.1. Nếu sai lệch, Nhân viên ghi chú và chưa cấp quyền người mới.
  - E1.2. Người cũ bị khóa: Nhân viên ghi nhận bàn giao thực tế thay thao tác trên tài khoản khóa.
  - E1.3. Người mới bị khóa: giữ hàng tại điểm tập kết và chọn người khác trước khi tạo nhiệm vụ.

**Điều kiện trước:** Có nhiệm vụ chưa hoàn tất hoặc cần phân công lại sau kết quả thất bại; xác định được người đang giữ hàng; Nhân viên có quyền điều phối.

**Điều kiện sau:** Thành công: nhiệm vụ mới đúng quyền, người cũ mất quyền cập nhật và có lịch sử bàn giao nếu cần. Chờ bàn giao: chưa cấp quyền người mới.

**Business Rules**

- BR1. Không đổi đơn đã giao/hoàn tất về trạng thái đang xử lý.
- BR2. Không có hai người đồng thời cập nhật kết quả hoặc COD của cùng nhiệm vụ.
- BR3. Không xóa số lần giao, kết quả hoặc COD cũ.
- BR4. Nếu nhiệm vụ lấy cũ đã lấy xong, tiếp nhận tại điểm tập kết rồi phân công giao; không tạo nhiệm vụ lấy lại giả.
