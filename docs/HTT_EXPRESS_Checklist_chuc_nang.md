# Checklist chức năng hệ thống HTT Express

Ngày lập: 19/11/2026. Dùng để bàn giao phạm vi cho người viết code và kiểm tra sự thống nhất với báo cáo.

Nguồn đối chiếu: `HTT_EXPRESS_Dac_ta_42_Use_Case.docx` (bản Markdown: `HTT_EXPRESS_Dac_ta_42_Use_Case.md`) đã lập từ sáu nhóm use case UC01–UC06. Đây là checklist yêu cầu, chưa phải kết quả kiểm tra mã nguồn. Mọi ô để trống vì chưa xác minh việc triển khai.

## 1. Phạm vi và cách sử dụng

- Hệ thống giao nhận tại Hà Nội, gồm Shop, Nhân viên/Admin và Shipper.
- Shipper lấy hàng tại Shop, đưa về điểm tập kết, sau đó giao cho người nhận. Hàng hoàn đưa về điểm tập kết để Shop đến lấy.
- Điểm tập kết chỉ ghi nhận tiếp nhận và bàn giao; không triển khai quản lý kho, tồn kho, kệ hàng hay điều chuyển liên kho.
- Thông báo hiển thị trong hệ thống; không yêu cầu gửi email hoặc SMS.
- Nhân viên và Admin là một vai trò trong phương án code ba vai trò của bộ bàn giao này. Nếu tách vai trò sau này, cần sửa đồng thời báo cáo và ma trận quyền.
- Đánh dấu `[x]` sau khi chức năng chạy đúng điều kiện nghiệm thu và kiểm tra quyền trên backend. Không đánh dấu chỉ vì đã có giao diện.
- Giữ nguyên mã UC để đối chiếu báo cáo. Các UC04.10–UC04.13 và UC06.8 là chức năng bổ sung đã chốt trong bộ bàn giao này; cần cập nhật tương ứng vào đặc tả và sơ đồ báo cáo. Phần tạo tài khoản và quên mật khẩu giữ nguyên như bản trước.

## 2. Checklist theo use case

### UC01 — Đăng nhập hệ thống

- [ ] **UC01.1 — Đăng nhập:** Cả ba vai trò đăng nhập bằng tài khoản hoạt động; điều hướng đúng vai trò; từ chối mật khẩu sai và tài khoản khóa; không tiết lộ tài khoản có tồn tại hay không.
- [ ] **UC01.2 — Đăng xuất:** Phiên đăng nhập hết hiệu lực; dùng lại thông tin phiên cũ để gọi chức năng có quyền phải bị từ chối.
- [ ] **UC01.3 — Quên mật khẩu:** Có bước xác minh danh tính trước khi đặt mật khẩu mới; không cho đổi mật khẩu chỉ dựa vào tên đăng nhập. Phương án đề xuất cho đồ án: Nhân viên xác minh và hỗ trợ đặt lại; chưa mặc định có OTP/email.

### UC02 — Quản lý tài khoản

- [ ] **UC02.1 — Xem thông tin tài khoản:** Mỗi người chỉ xem hồ sơ của mình ở màn hình cá nhân; không trả về mật khẩu hoặc giá trị băm mật khẩu.
- [ ] **UC02.2 — Cập nhật thông tin cá nhân:** Kiểm tra trường bắt buộc và dữ liệu trùng; không cho tự đổi vai trò, chủ sở hữu hoặc trạng thái tài khoản.
- [ ] **UC02.3 — Đổi mật khẩu:** Kiểm tra mật khẩu hiện tại, xác nhận mật khẩu mới và lưu dưới dạng băm.
- [ ] **UC02.4 — Quản lý tài khoản người dùng:** Nhân viên thêm, sửa, khóa/mở khóa tài khoản đúng quyền; ghi nhận người thao tác; không khóa quản trị viên hoạt động cuối cùng. Không xóa cứng tài khoản đã có lịch sử nghiệp vụ.

### UC03 — Theo dõi vận đơn

- [ ] **UC03.1 — Tra cứu vận đơn:** Shop tra cứu đơn của mình; Nhân viên tra cứu toàn hệ thống; không có tra cứu công khai trong phạm vi này.
- [ ] **UC03.2 — Xem lịch sử vận chuyển:** Hiển thị trạng thái, thời gian và người thực hiện; lịch sử được thêm mới, không sửa đè các mốc cũ.
- [ ] **UC03.3 — Theo dõi vị trí Shipper:** Shop chỉ xem vị trí gắn với nhiệm vụ đang thực hiện của đơn thuộc Shop; Nhân viên theo dõi nhiệm vụ đang hoạt động; hiển thị thời điểm cập nhật và tình trạng chưa có/mất GPS.
- [ ] **UC03.4 — Xem bản đồ và tuyến đường:** Shipper xem điểm đến của nhiệm vụ được giao; khi không lấy được GPS vẫn xem được địa chỉ để xử lý.
- [ ] **UC03.5 — Chia sẻ vị trí GPS:** Xin quyền vị trí; chỉ nhận vị trí khi Shipper có nhiệm vụ đang hoạt động; dừng khi kết thúc. Backend không nhận vị trí thay cho Shipper khác.

### UC04 — Quản lý đơn hàng và nhiệm vụ giao nhận

- [ ] **UC04.1 — Xem nhiệm vụ lấy hàng:** Shipper chỉ thấy nhiệm vụ được phân công cho mình và thông tin Shop cần cho việc lấy hàng.
- [ ] **UC04.2 — Xác nhận lấy hàng thành công:** Chỉ Shipper đang phụ trách được xác nhận; lưu thời gian và trạng thái Đã lấy hàng; chưa coi là đã nhập điểm tập kết.
- [ ] **UC04.3 — Cập nhật lấy hàng thất bại:** Bắt buộc lý do; lưu lịch sử; đưa vào danh sách Nhân viên cần xử lý, không tự chuyển thành lấy thành công.
- [ ] **UC04.4 — Xem nhiệm vụ giao hàng:** Chỉ hiển thị nhiệm vụ của Shipper, người nhận, địa chỉ và COD cần thu.
- [ ] **UC04.5 — Xác nhận giao hàng thành công:** Chỉ Shipper phụ trách nhiệm vụ giao còn hiệu lực được thao tác; đơn COD phải ghi nhận thu đủ, đơn không COD ghi nhận 0. Lưu kết quả giao, COD và lịch sử trong cùng một lần xử lý; thiếu/thừa COD thì từ chối hoàn tất. Thông báo cho Shop sau khi lưu thành công.
- [ ] **UC04.6 — Cập nhật giao hàng thất bại:** Bắt buộc lý do; mỗi lần giao có kết quả thất bại chỉ tăng bộ đếm một lần; tối đa 3 lần giao thực tế cho một vận đơn. Sau lần thứ ba thất bại, chặn giao lại; Nhân viên phải chọn xử lý hoàn. Có thể quyết định hoàn sớm nếu người nhận từ chối nhận hàng.
- [ ] **UC04.7 — Ghi nhận tiền COD đã thu:** Lưu tiền phải thu và thực thu bằng VND, không âm; chỉ hoàn tất giao thành công khi thực thu bằng phải thu. Không hỗ trợ thu một phần; nếu chưa thu đủ thì ghi nhận giao thất bại với lý do phù hợp. Ghi nhận cùng UC04.5, không cộng trùng khi gửi lại. Không triển khai Shipper nộp tiền, đối soát hoặc trả COD cho Shop.
- [ ] **UC04.8 — Xem nhiệm vụ hoàn hàng:** Shipper chỉ thấy nhiệm vụ hoàn được giao sau quyết định hoàn của Nhân viên.
- [ ] **UC04.9 — Bàn giao hàng hoàn:** Shipper ghi nhận bàn giao về điểm tập kết; Nhân viên kiểm tra và xác nhận tiếp nhận mới chuyển Chờ Shop đến lấy. Nếu chưa nhận hoặc có sai lệch, lưu tình trạng xử lý; chưa kết thúc hoàn về Shop.
- [ ] **UC04.10 — Xác nhận nhập điểm tập kết — Bổ sung đã chốt:** Nhân viên xác nhận đã nhận kiện hàng từ Shipper lấy hàng; ghi thời gian/người nhận; chỉ sau bước này mới cho phân công giao.
- [ ] **UC04.11 — Xác nhận Shop nhận hàng hoàn — Bổ sung đã chốt:** Khi Shop đến điểm tập kết nhận hàng, Nhân viên xác nhận bàn giao; chuyển Đã hoàn về Shop và kết thúc luồng hoàn.
- [ ] **UC04.12 — Quyết định giao lại hoặc hoàn hàng — Bổ sung đã chốt:** Nhân viên xem lý do và số lần giao thất bại; chỉ chọn giao lại khi chưa đủ 3 lần, hoặc chọn hoàn. Lần thứ ba thất bại chỉ cho chọn hoàn; không tự tạo nhiệm vụ hoàn trước quyết định của Nhân viên. Giao lại qua UC06.6; hoàn qua UC06.7.

- [ ] **UC04.13 — Xử lý lấy hàng thất bại — Bổ sung đã chốt:** Nhân viên chọn lấy lại (chuyển Chờ lấy hàng, sau đó phân công qua UC06.5) hoặc Kết thúc do không lấy được hàng. Bắt buộc lý do, lưu người/thời gian xử lý và thông báo Shop; giữ nguyên mã vận đơn và lịch sử lần lấy trước. Đây là kết thúc sau duyệt, khác với Shop hủy yêu cầu trước duyệt.

### UC05 — Quản lý vận đơn

- [ ] **UC05.1 — Chỉnh sửa yêu cầu gửi hàng:** Shop chỉ sửa yêu cầu của mình khi Chờ xác nhận; nếu đã duyệt trong lúc đang sửa thì từ chối lưu dữ liệu cũ.
- [ ] **UC05.2 — Tạo yêu cầu gửi hàng:** Nhập người gửi/nhận, điện thoại, địa chỉ, kiện hàng, COD; kiểm tra phạm vi Hà Nội; sinh mã yêu cầu và trạng thái Chờ xác nhận, chưa sinh mã vận đơn chính thức.
- [ ] **UC05.3 — Xem danh sách vận đơn của Shop:** Chỉ lấy dữ liệu của Shop đang đăng nhập; phân biệt yêu cầu chờ duyệt và vận đơn đã được duyệt.
- [ ] **UC05.4 — Xem chi tiết vận đơn của Shop:** Kiểm tra quyền sở hữu kể cả khi truy cập trực tiếp bằng ID; xem thông tin, trạng thái và lịch sử.
- [ ] **UC05.5 — Hủy yêu cầu gửi hàng:** Shop chỉ hủy yêu cầu của mình khi chưa duyệt; lưu trạng thái Đã hủy và lịch sử, không xóa cứng.
- [ ] **UC05.6 — Xác nhận vận đơn:** Nhân viên duyệt yêu cầu Chờ xác nhận, sinh mã vận đơn duy nhất, chuyển Chờ lấy hàng và thông báo Shop; duyệt lặp không sinh thêm vận đơn.
- [ ] **UC05.7 — Xem chi tiết vận đơn của Nhân viên:** Xem đầy đủ thông tin nghiệp vụ, lịch sử phân công và kết quả giao; không cung cấp nút tùy ý sửa trạng thái.
- [ ] **UC05.8 — Từ chối vận đơn:** Chỉ từ chối yêu cầu Chờ xác nhận; bắt buộc lý do; không sinh mã vận đơn; thông báo Shop.
- [ ] **UC05.9 — Xem danh sách vận đơn của Nhân viên:** Xem toàn bộ theo quyền, tìm kiếm và lọc trạng thái; có trạng thái danh sách trống và lỗi tải dữ liệu.

### UC06 — Quản lý Shipper

- [ ] **UC06.1 — Xem danh sách Shipper:** Nhân viên xem danh sách và trạng thái tài khoản; không trả về thông tin mật khẩu.
- [ ] **UC06.2 — Thêm Shipper:** Tạo tài khoản vai trò Shipper, kiểm tra dữ liệu bắt buộc và tên đăng nhập/số điện thoại trùng theo quy tắc đã chọn.
- [ ] **UC06.3 — Cập nhật thông tin Shipper:** Nhân viên sửa hồ sơ hợp lệ; giữ nguyên lịch sử nhiệm vụ và phân công đã phát sinh.
- [ ] **UC06.4 — Khóa/mở khóa Shipper:** Tài khoản khóa không đăng nhập, gọi API được bảo vệ hoặc nhận nhiệm vụ mới; nhiệm vụ đang mở phải được Nhân viên xử lý, không âm thầm đánh dấu hoàn tất.
- [ ] **UC06.5 — Phân công lấy hàng:** Chỉ đơn đã duyệt và đủ điều kiện lấy hàng; chỉ chọn Shipper hoạt động; tạo nhiệm vụ và thông báo; không tạo trùng nhiệm vụ lấy đang mở cho cùng đơn.
- [ ] **UC06.6 — Phân công giao hàng:** Lần đầu chỉ sau xác nhận nhập điểm tập kết. Giao lại phải có quyết định của Nhân viên và số lần đã giao nhỏ hơn 3. Cùng Shipper còn giữ hàng có thể được phân công đợt mới; đổi người khi đã giữ hàng phải qua bàn giao về điểm tập kết theo UC06.8. Không tạo hai nhiệm vụ giao đang mở cho cùng đơn.
- [ ] **UC06.7 — Phân công hoàn hàng:** Chỉ sau quyết định hoàn và trạng thái Chờ xử lý hoàn; tạo nhiệm vụ đưa hàng về điểm tập kết, chuyển Đang hoàn; không đặt Đã hoàn về Shop ngay.

- [ ] **UC06.8 — Đổi Shipper hoặc phân công lại — Bổ sung đã chốt:** Chỉ Nhân viên thực hiện với nhiệm vụ chưa hoàn tất, bắt buộc lý do. Chưa nhận hàng: kết thúc phân công cũ ở trạng thái Đã thay thế rồi tạo nhiệm vụ cho người mới. Đã giữ hàng: chuyển Chờ bàn giao đổi Shipper, Shipper cũ đưa hàng về điểm tập kết; Nhân viên xác nhận tiếp nhận mới phân công người mới. Không cho hai người cùng cập nhật nhiệm vụ; giữ đầy đủ lịch sử.

## 3. Checklist xử lý chung cần có để các use case hoạt động

Các mục dưới đây là xử lý dùng chung, không tự gán thêm mã UC chính thức.

- [ ] **Thông báo nội bộ:** Đúng người nhận khi duyệt/từ chối yêu cầu, phân công, lấy/giao hàng và hàng hoàn về điểm tập kết; xem danh sách và đánh dấu đã đọc; không đọc được thông báo của người khác.
- [ ] **Lịch sử nghiệp vụ:** Lưu trạng thái trước/sau, người thực hiện, thời gian và lý do khi cần; mỗi thao tác thất bại không để lại trạng thái thành công giả.
- [ ] **Kiểm tra quyền backend:** Mọi API kiểm tra phiên, vai trò, quyền sở hữu/phân công và trạng thái nghiệp vụ; việc ẩn nút trên giao diện chỉ là hỗ trợ sử dụng.
- [ ] **Xử lý thao tác đồng thời:** Hai người cùng duyệt, phân công, ghi COD hoặc xác nhận bàn giao không tạo dữ liệu trùng hoặc làm mất lịch sử.
- [ ] **Dữ liệu đầu vào:** Chặn COD âm, trường bắt buộc rỗng, địa chỉ ngoài phạm vi và các giá trị kiện hàng không hợp lệ theo quy tắc nhóm chốt.
- [ ] **Trạng thái màn hình:** Có tải dữ liệu, danh sách trống, lỗi nhập liệu, lỗi mạng và thông báo thao tác thành công/thất bại.

## 4. Luồng trạng thái để người code đối chiếu

Tên trạng thái dưới đây là bộ tên dùng cho phạm vi đã chốt, cần đồng bộ trong backend, giao diện và báo cáo. Trạng thái Chờ bàn giao đổi Shipper là trạng thái nhiệm vụ, tách khỏi tiến trình của vận đơn.

| Tình huống | Trạng thái trước | Trạng thái sau | Người thao tác |
|---|---|---|---|
| Tạo yêu cầu | Chưa có | Chờ xác nhận | Shop |
| Sửa yêu cầu | Chờ xác nhận | Chờ xác nhận | Shop sở hữu |
| Hủy yêu cầu | Chờ xác nhận | Đã hủy | Shop sở hữu |
| Từ chối yêu cầu | Chờ xác nhận | Bị từ chối | Nhân viên |
| Duyệt yêu cầu | Chờ xác nhận | Chờ lấy hàng | Nhân viên |
| Phân công lấy | Chờ lấy hàng | Đã phân công lấy hàng | Nhân viên |
| Lấy thành công | Đã phân công lấy hàng | Đã lấy hàng | Shipper phụ trách |
| Lấy thất bại | Đã phân công lấy hàng | Lấy hàng thất bại | Shipper phụ trách |
| Quyết định lấy lại | Lấy hàng thất bại | Chờ lấy hàng | Nhân viên |
| Kết thúc không lấy được hàng | Lấy hàng thất bại | Kết thúc do không lấy được hàng | Nhân viên |
| Nhận hàng tại điểm tập kết | Đã lấy hàng | Đã nhập điểm tập kết | Nhân viên |
| Phân công giao lần đầu | Đã nhập điểm tập kết | Đang giao hàng | Nhân viên |
| Giao thành công | Đang giao hàng | Đã giao hàng | Shipper phụ trách |
| Giao thất bại | Đang giao hàng | Giao hàng thất bại | Shipper phụ trách |
| Quyết định giao lại | Giao hàng thất bại, số lần đã giao < 3 | Chờ giao lại | Nhân viên |
| Phân công giao lại | Chờ giao lại, đủ điều kiện bàn giao thực tế | Đang giao hàng | Nhân viên |
| Quyết định hoàn | Giao hàng thất bại; bắt buộc chọn hoàn sau lần thứ ba | Chờ xử lý hoàn | Nhân viên |
| Phân công hoàn | Chờ xử lý hoàn | Đang hoàn | Nhân viên |
| Tiếp nhận hàng hoàn | Đang hoàn, Shipper đã bàn giao thực tế | Chờ Shop đến lấy | Nhân viên |
| Tiếp nhận hàng hoàn đã ở điểm tập kết (UC06.7 A1.2) | Chờ xử lý hoàn, hàng đã được Nhân viên xác nhận nhận tại điểm tập kết | Chờ Shop đến lấy | Nhân viên |
| Shop nhận hàng hoàn | Chờ Shop đến lấy | Đã hoàn về Shop | Nhân viên |

Dòng tiếp nhận hàng hoàn đã ở điểm tập kết áp dụng khi hàng đã về điểm tập kết trước lúc phân công hoàn (ví dụ sau bàn giao đổi Shipper); không tạo chuyến hoàn thừa.

Trạng thái nhiệm vụ và trạng thái vận đơn cần được lưu riêng nếu có nhiều lần phân công/giao lại. Không ghi đè Shipper hoặc kết quả lần trước để biểu diễn lần giao mới.

## 5. Quy tắc triển khai đã chốt và phần giữ nguyên

Các quyết định dưới đây thay thế phần gợi ý tương ứng trong bản trước. Riêng hai dòng Quên mật khẩu và Tạo tài khoản Shop giữ nguyên nội dung cũ, không chốt thêm cơ chế tài khoản.

| Nội dung | Phạm vi triển khai |
|---|---|
| Xử lý sau lấy hàng thất bại | UC04.13: Nhân viên chọn lấy lại qua UC06.5 hoặc kết thúc do không lấy được hàng, có lý do và thông báo Shop. |
| Giới hạn giao thất bại | Tối đa 3 lần giao thực tế, tính cả lần giao thành công nếu có. Chỉ một kết quả cuối cho mỗi lần; phân công/đổi người chưa giao không tính thêm lần. Sau 3 lần thất bại chỉ được xử lý hoàn. |
| Hàng nằm ở đâu khi giao lại | Ghi nhận người đang giữ hàng. Cùng Shipper còn giữ hàng được giao lại khi đủ điều kiện; đổi người phải đưa về điểm tập kết, Nhân viên xác nhận nhận hàng trước khi phân công mới. |
| Quên mật khẩu | Đề xuất Nhân viên hỗ trợ sau xác minh; chốt thông tin xác minh và cách giao mật khẩu tạm. Không mặc định tích hợp email/SMS. |
| Tạo tài khoản Shop | Đề xuất Nhân viên tạo qua UC02.4; tự đăng ký Shop chưa nằm trong nguồn. |
| COD chênh lệch | Chỉ ghi nhận thu đủ để hoàn tất giao thành công; không hỗ trợ thu một phần. Chênh lệch phải bị chặn, chưa thu đủ ghi nhận giao thất bại. Không nộp tiền, đối soát hay trả COD cho Shop. |
| Phí giao hàng, báo cáo, đối soát | Chưa có UC tương ứng trong nguồn; không tự bổ sung thành chức năng bắt buộc. |
| Nền tảng và công nghệ | Nhóm tự chọn; bộ bàn giao không áp đặt framework, cơ sở dữ liệu hay ứng dụng di động. |

### Quy tắc bàn giao khi đổi Shipper

1. Nhân viên chọn người thay thế đang hoạt động và nhập lý do; với người cũ đã giữ hàng, lựa chọn này chỉ là dự kiến, chưa cấp quyền cho người mới.
2. Nếu người cũ chưa nhận hàng, thay thế phân công ngay trong một lần xử lý; người cũ mất quyền cập nhật ngay.
3. Nếu người cũ đang giữ hàng, tạm dừng quyền ghi kết quả lấy/giao/hoàn và thu COD của nhiệm vụ cũ; người cũ chỉ xem, cập nhật vị trí phục vụ bàn giao và ghi nhận bàn giao về điểm tập kết. Nếu người cũ bị khóa, Nhân viên ghi nhận tiếp nhận thực tế thay cho thao tác trên tài khoản bị khóa.
4. Nhân viên xác nhận đúng kiện hàng đã nhận tại điểm tập kết; lưu thời gian, người giao/nhận. Nếu có sai lệch, giữ Chờ bàn giao đổi Shipper để xử lý, chưa giao cho người mới.
5. Đóng nhiệm vụ cũ là Đã thay thế, kiểm tra lại người mới còn hoạt động rồi tạo nhiệm vụ thay thế đúng loại và tiến trình vận đơn. Với nhiệm vụ hoàn, hàng đã về điểm tập kết thì tiếp nhận theo UC04.9 và chờ Shop lấy, không tạo chuyến hoàn thừa.
6. Không đặt đơn đã giao/đã hoàn thành về trạng thái đang xử lý. Không đổi Shipper để xóa số lần giao thất bại, vượt giới hạn 3 lần hoặc ghi đè COD.

## 6. Kịch bản kiểm tra cuối trước khi bàn giao demo

- [ ] **Giao thành công:** Shop tạo → Nhân viên duyệt → phân công lấy → Shipper lấy → Nhân viên nhận tại điểm tập kết → phân công giao → Shipper giao và ghi COD nếu có → Shop xem trạng thái/lịch sử.
- [ ] **Yêu cầu không được thực hiện:** Shop sửa/hủy trước duyệt; Nhân viên từ chối có lý do; không phát sinh vận đơn từ yêu cầu đã hủy hoặc bị từ chối.
- [ ] **Giao thất bại và giao lại:** Lưu lý do/lần giao → Nhân viên quyết định → phân công đợt mới đủ điều kiện → lịch sử lần trước vẫn còn.
- [ ] **Hoàn hàng:** Giao thất bại → quyết định hoàn → phân công hoàn → Shipper bàn giao → Nhân viên nhận → Chờ Shop đến lấy → Nhân viên xác nhận Shop nhận → Đã hoàn về Shop.
- [ ] **Phân quyền:** Shop A không xem/sửa đơn Shop B; Shipper A không thao tác nhiệm vụ Shipper B; Shop/Shipper không gọi được API Nhân viên.
- [ ] **Khóa và đăng xuất:** Phiên hết hiệu lực/khóa không tiếp tục gọi được chức năng có quyền; không giao nhiệm vụ mới cho Shipper khóa.
- [ ] **GPS:** Mất quyền vị trí vẫn hiển thị địa chỉ; kết thúc nhiệm vụ thì dừng theo dõi; Shop không theo dõi Shipper ngoài nhiệm vụ liên quan.
- [ ] **Thao tác lặp:** Nhấn duyệt, phân công, giao thành công, ghi COD hoặc nhận hàng hoàn nhiều lần không sinh thêm đơn, nhiệm vụ hoặc tiền thu trùng.

- [ ] **Lấy thất bại:** Nhân viên chọn lấy lại thì tạo nhiệm vụ mới qua UC06.5; chọn kết thúc thì đơn kết thúc đúng lý do, Shop nhận thông báo và lịch sử cũ còn nguyên.
- [ ] **Đổi Shipper chưa giữ hàng:** Phân công mới có hiệu lực, người cũ không cập nhật được và người mới chỉ thấy nhiệm vụ của mình.
- [ ] **Đổi Shipper đã giữ hàng:** Chưa có xác nhận Nhân viên nhận tại điểm tập kết thì người mới chưa được cập nhật; sau xác nhận mới phân công, lịch sử bàn giao đủ người/thời gian.
- [ ] **Ba lần giao:** Gửi lại cùng kết quả không tăng số lần; sau lần thất bại thứ ba không giao lại được; Nhân viên chỉ chọn hoàn. Đổi Shipper không đặt lại bộ đếm.
- [ ] **COD:** Đơn COD 200.000 VND chỉ hoàn tất khi thực thu 200.000; 0/150.000/250.000 đều không cho hoàn tất. Đơn không COD ghi 0; gửi lại không cộng thêm tiền.

## 7. Mẫu ghi nhận tiến độ

Copy một dòng cho mỗi UC; phần kiểm thử ghi bằng chứng ngắn như tài khoản sử dụng, tình huống và kết quả.

| Mã UC | Người thực hiện | Backend | Giao diện | Đã kiểm tra quyền và nghiệp vụ | Bằng chứng/lỗi còn lại |
|---|---|---|---|---|---|
| UC… | … | Chưa làm | Chưa làm | Chưa kiểm tra | … |

