# Actor vai trò và phân quyền hệ thống HTT Express

Ngày lập: 19/11/2026. Tài liệu bàn giao cho người viết code, dùng cùng `HTT_EXPRESS_Checklist_chuc_nang.md` và bản nguồn `HTT_EXPRESS_Dac_ta_42_Use_Case.docx` (bản Markdown để tra cứu: `HTT_EXPRESS_Dac_ta_42_Use_Case.md`).

Tài liệu mô tả quyền cần triển khai, chưa xác nhận mã nguồn hiện tại đã có những quyền này. Phạm vi giao nhận, đổi Shipper, ba lần giao và COD đã được chốt theo checklist cập nhật. Phần tạo tài khoản và quên mật khẩu giữ nguyên bản trước, không bổ sung cơ chế tài khoản.

## 1. Danh sách actor và vai trò

| Actor | Mã vai trò đề xuất trong code | Vai trò nghiệp vụ | Phạm vi dữ liệu |
|---|---|---|---|
| Shop | `SHOP` | Tạo và quản lý yêu cầu gửi hàng; theo dõi vận đơn; xem tiến độ giao và đến nhận hàng hoàn | Chỉ hồ sơ, yêu cầu, vận đơn, thông báo của chính Shop; GPS liên quan nhiệm vụ đang thực hiện của đơn thuộc Shop |
| Nhân viên/Admin | `ADMIN` | Quản lý tài khoản, duyệt yêu cầu, điều phối Shipper, xác nhận bàn giao tại điểm tập kết, xử lý giao lại/hoàn | Dữ liệu nghiệp vụ toàn hệ thống phục vụ quản lý; GPS trong thời gian nhiệm vụ đang hoạt động |
| Shipper | `SHIPPER` | Thực hiện nhiệm vụ lấy, giao, hoàn; ghi nhận kết quả và COD; chia sẻ GPS khi làm nhiệm vụ | Hồ sơ cá nhân, nhiệm vụ được giao và thông tin cần thiết của đơn liên quan; quyền cập nhật chỉ khi nhiệm vụ còn hiệu lực |

Trong bộ bàn giao này, **Nhân viên và Admin dùng chung một vai trò** để khớp mô hình ba actor. Đây là cách chuẩn hóa để code; nếu nhóm muốn có Nhân viên điều phối và Quản trị viên riêng, phải tách quyền quản lý tài khoản và cập nhật ma trận trước khi triển khai.

**Người nhận hàng** tham gia nhận hàng và trả COD ngoài thực tế nhưng chưa có tài khoản hay màn hình riêng trong phạm vi nguồn. **Hệ thống** là phần xử lý tự động bên trong, không phải actor bên ngoài. **Điểm tập kết** là địa điểm bàn giao, không phải actor hoặc phân hệ kho. Dịch vụ bản đồ nếu tích hợp là thành phần kỹ thuật hỗ trợ, chưa mặc định thành actor có quyền đăng nhập.

## 2. Trách nhiệm và giới hạn từng actor

### 2.1. Shop

- Nhập đúng thông tin người gửi, người nhận, kiện hàng, địa chỉ Hà Nội và COD.
- Sửa/hủy yêu cầu của mình khi còn Chờ xác nhận; sau duyệt chỉ theo dõi theo chức năng được cấp.
- Tra cứu trạng thái, lịch sử và vị trí Shipper trong nhiệm vụ đang thực hiện của đơn thuộc mình.
- Nhận thông báo nội bộ; đến điểm tập kết lấy hàng hoàn khi được thông báo.
- Không tự duyệt yêu cầu, phân công Shipper, cập nhật kết quả giao nhận hoặc xác nhận đã hoàn về Shop trong hệ thống.

### 2.2. Nhân viên/Admin

- Quản lý tài khoản Shop và Shipper; thực hiện tác vụ quản trị tài khoản trong quyền được cấp.
- Kiểm tra yêu cầu, duyệt hoặc từ chối có lý do; chỉ khi duyệt mới sinh mã vận đơn chính thức.
- Phân công lấy/giao/hoàn cho Shipper hoạt động và kiểm tra trạng thái hợp lệ.
- Xác nhận tiếp nhận hàng tại điểm tập kết; tiếp nhận hàng hoàn; xác nhận Shop đã nhận hàng hoàn.
- Xem các lần giao thất bại và quyết định giao lại hoặc hoàn; tối đa 3 lần giao, sau lần thất bại thứ ba phải chọn hoàn.
- Xử lý lấy hàng thất bại: chọn lấy lại hoặc kết thúc do không lấy được hàng.
- Đổi Shipper cho nhiệm vụ chưa hoàn tất; nếu đã giữ hàng thì xác nhận bàn giao về điểm tập kết trước khi giao người mới.
- Không được sửa tùy ý lịch sử, tiền COD đã ghi nhận hay đặt trạng thái cuối để bỏ qua bàn giao thực tế. Nhu cầu sửa sai nghiệp vụ cần có quy trình riêng nếu nhóm bổ sung sau.

### 2.3. Shipper

- Xem nhiệm vụ do Nhân viên phân công cho mình, địa chỉ, liên hệ và COD cần thu.
- Xác nhận lấy/giao thành công hoặc thất bại, nhập lý do và ghi nhận COD theo đúng nhiệm vụ. Đơn COD chỉ hoàn tất giao thành công khi thu đủ; không hỗ trợ thu một phần.
- Khi đổi người mà đang giữ hàng, bàn giao hàng về điểm tập kết; không tự bàn giao trực tiếp cho Shipper khác trong phạm vi đồ án.
- Xem tuyến đường và chia sẻ GPS trong thời gian thực hiện nhiệm vụ có cấp quyền vị trí.
- Bàn giao hàng hoàn về điểm tập kết; chờ Nhân viên xác nhận nhận hàng.
- Không tự nhận đơn chưa phân công, chuyển đơn cho Shipper khác, quyết định hoàn/giao lại hoặc xác nhận Shop đã nhận hàng hoàn.

## 3. Ma trận phân quyền theo use case

Quy ước: **Có** = được thực hiện khi thỏa điều kiện; **Không** = không có quyền. “Của mình” với Shop là quyền sở hữu; với Shipper là nhiệm vụ được phân công. Quyền xem không đồng nghĩa quyền sửa. Quyền của Nhân viên cũng phải qua kiểm tra trạng thái nghiệp vụ.

| Mã UC | Chức năng | Shop | Nhân viên/Admin | Shipper | Điều kiện hoặc giới hạn |
|---|---|---|---|---|---|
| UC01.1 | Đăng nhập | Có | Có | Có | Tài khoản hoạt động, thông tin xác thực hợp lệ |
| UC01.2 | Đăng xuất | Có | Có | Có | Phiên của chính mình |
| UC01.3 | Quên mật khẩu | Có | Có | Có | Được yêu cầu khôi phục tài khoản mình; phải xác minh trước khi đặt lại |
| UC02.1 | Xem tài khoản cá nhân | Có | Có | Có | Hồ sơ của mình |
| UC02.2 | Cập nhật thông tin cá nhân | Có | Có | Có | Không tự sửa vai trò/trạng thái |
| UC02.3 | Đổi mật khẩu | Có | Có | Có | Kiểm tra mật khẩu hiện tại |
| UC02.4 | Quản lý tài khoản người dùng | Không | Có | Không | Tác vụ quản trị, không xóa lịch sử hoặc khóa Admin hoạt động cuối cùng |
| UC03.1 | Tra cứu vận đơn | Có | Có | Không | Shop chỉ đơn của mình; Shipper xem đơn qua nhiệm vụ |
| UC03.2 | Xem lịch sử vận chuyển | Có | Có | Không | Shop chỉ đơn của mình; không cấp Shipper màn hình tra cứu lịch sử toàn hệ thống |
| UC03.3 | Theo dõi vị trí Shipper | Có | Có | Không | Chỉ nhiệm vụ đang thực hiện; Shop chỉ đơn thuộc mình |
| UC03.4 | Xem bản đồ và tuyến đường | Không | Không | Có | Nhiệm vụ được giao, có địa chỉ điểm đến |
| UC03.5 | Chia sẻ GPS | Không | Không | Có | Vị trí của mình, nhiệm vụ hoạt động, đã cấp quyền vị trí |
| UC04.1 | Xem nhiệm vụ lấy hàng | Không | Không | Có | Chỉ nhiệm vụ của mình |
| UC04.2 | Xác nhận lấy hàng thành công | Không | Không | Có | Nhiệm vụ lấy còn hiệu lực, đã nhận hàng thực tế |
| UC04.3 | Cập nhật lấy hàng thất bại | Không | Không | Có | Nhiệm vụ lấy của mình, bắt buộc lý do |
| UC04.4 | Xem nhiệm vụ giao hàng | Không | Không | Có | Chỉ nhiệm vụ của mình |
| UC04.5 | Xác nhận giao thành công | Không | Không | Có | Nhiệm vụ còn hiệu lực; COD thực thu bằng phải thu, lưu cùng kết quả giao |
| UC04.6 | Cập nhật giao thất bại | Không | Không | Có | Nhiệm vụ của mình; lý do bắt buộc; một kết quả chỉ tính một lần giao |
| UC04.7 | Ghi nhận COD đã thu | Không | Không | Có | Gắn nhiệm vụ giao của mình; thu đủ khi giao thành công, không cộng trùng |
| UC04.8 | Xem nhiệm vụ hoàn hàng | Không | Không | Có | Nhiệm vụ hoàn của mình |
| UC04.9 | Bàn giao hàng hoàn | Không | Có, xác nhận tiếp nhận | Có, ghi nhận bàn giao | Shipper không tự xác nhận thay Nhân viên |
| UC04.10* | Xác nhận nhập điểm tập kết | Không | Có | Không | Đã lấy hàng và bàn giao thực tế |
| UC04.11* | Xác nhận Shop nhận hàng hoàn | Không | Có | Không | Chờ Shop đến lấy, Shop đã nhận thực tế |
| UC04.12* | Quyết định giao lại hoặc hoàn | Không | Có | Không | Chỉ giao lại khi chưa đủ 3 lần; sau lần thất bại thứ ba chỉ chọn hoàn |
| UC04.13* | Xử lý lấy hàng thất bại | Không | Có | Không | Chọn lấy lại hoặc kết thúc do không lấy được hàng; bắt buộc lý do |
| UC05.1 | Chỉnh sửa yêu cầu gửi hàng | Có | Không | Không | Yêu cầu của mình còn Chờ xác nhận |
| UC05.2 | Tạo yêu cầu gửi hàng | Có | Không | Không | Gắn Shop theo phiên đăng nhập |
| UC05.3 | Danh sách vận đơn của Shop | Có | Không | Không | Chỉ dữ liệu Shop sở hữu |
| UC05.4 | Chi tiết vận đơn của Shop | Có | Không | Không | Chỉ dữ liệu Shop sở hữu |
| UC05.5 | Hủy yêu cầu gửi hàng | Có | Không | Không | Yêu cầu của mình chưa duyệt |
| UC05.6 | Xác nhận vận đơn | Không | Có | Không | Yêu cầu Chờ xác nhận, mã vận đơn duy nhất |
| UC05.7 | Chi tiết vận đơn của Nhân viên | Không | Có | Không | Xem thông tin nghiệp vụ để điều phối |
| UC05.8 | Từ chối vận đơn | Không | Có | Không | Chờ xác nhận, bắt buộc lý do |
| UC05.9 | Danh sách vận đơn của Nhân viên | Không | Có | Không | Dữ liệu toàn hệ thống |
| UC06.1 | Danh sách Shipper | Không | Có | Không | Không trả dữ liệu mật khẩu |
| UC06.2 | Thêm Shipper | Không | Có | Không | Kiểm tra thông tin trùng |
| UC06.3 | Cập nhật Shipper | Không | Có | Không | Không sửa lịch sử phân công |
| UC06.4 | Khóa/mở khóa Shipper | Không | Có | Không | Không tự kết thúc nhiệm vụ đang mở |
| UC06.5 | Phân công Shipper lấy hàng | Không | Có | Không | Đơn đã duyệt, Shipper hoạt động |
| UC06.6 | Phân công Shipper giao hàng | Không | Có | Không | Đã nhập điểm tập kết hoặc đủ điều kiện giao lại; số lần đã giao < 3; đổi người qua UC06.8 |
| UC06.7 | Phân công Shipper hoàn hàng | Không | Có | Không | Đã quyết định hoàn, Chờ xử lý hoàn |
| UC06.8* | Đổi Shipper hoặc phân công lại | Không | Có | Không | Nhiệm vụ chưa hoàn tất; có lý do; đã giữ hàng phải qua xác nhận nhận tại điểm tập kết |

`*` Năm UC bổ sung UC04.10–UC04.13 và UC06.8 đã chốt để triển khai; cần cập nhật sơ đồ và báo cáo tương ứng. Trong đó UC04.10–UC04.12 đã được bản nguồn kiến nghị trước đó. UC04.9 có Nhân viên tham gia xác nhận theo chính luồng chi tiết của nguồn, dù mục Actor đầu UC nguồn chỉ ghi Shipper.

Nhân viên xem nhiệm vụ/phân công và kết quả thông qua màn hình quản lý vận đơn, không sử dụng quyền thao tác nhiệm vụ dành cho Shipper. Tương tự, Nhân viên xem đơn qua UC05.7/UC05.9 thay vì dùng màn hình Shop.

## 4. Phân quyền xử lý dùng chung

| Xử lý | Shop | Nhân viên/Admin | Shipper |
|---|---|---|---|
| Xem thông báo nội bộ, đánh dấu đã đọc | Thông báo của mình | Thông báo của mình | Thông báo của mình |
| Xem dữ liệu COD | Đơn của Shop, theo chi tiết đơn | Xem theo đơn trong quản lý | Đơn thuộc nhiệm vụ của mình |
| Sửa/xóa lịch sử vận chuyển | Không | Không | Không |
| Ghi lịch sử và gửi thông báo nghiệp vụ | Hệ thống tự thực hiện sau thao tác hợp lệ | Hệ thống tự thực hiện sau thao tác hợp lệ | Hệ thống tự thực hiện sau thao tác hợp lệ |
| Đặt lại mật khẩu người khác | Không | Chỉ qua quy trình hỗ trợ đã xác minh | Không |
| Tạo tài khoản Shop | Không tự đăng ký trong phạm vi hiện tại | Đề xuất thực hiện qua UC02.4 | Không |
| Sửa trực tiếp COD đã chốt hoặc đối soát tiền | Chưa có chức năng trong nguồn | Chưa có chức năng trong nguồn | Không |

Quy trình hỗ trợ mật khẩu và tạo tài khoản Shop là phương án triển khai đề xuất, không phải chi tiết đã được nguồn chốt. Khôi phục tài khoản Admin cuối cùng cần cơ chế quản trị riêng, không mở chức năng đặt lại mật khẩu không xác minh cho khách chưa đăng nhập.

## 5. Quy tắc backend cần thực hiện

1. **Kiểm tra ở mọi yêu cầu:** Phiên hợp lệ → tài khoản hoạt động → đúng vai trò → đúng chủ sở hữu/người được phân công → đúng trạng thái → dữ liệu hợp lệ.
2. **Shop sở hữu dữ liệu:** Lấy `shop_id` từ phiên đăng nhập. Không tin `shop_id` do phía giao diện gửi để quyết định quyền tạo, xem hoặc cập nhật.
3. **Shipper có nhiệm vụ:** Kiểm tra nhiệm vụ gắn với vận đơn, loại nhiệm vụ, Shipper phụ trách và tình trạng còn hiệu lực. Không cho quyền cập nhật chỉ vì Shipper từng xử lý đơn đó ở quá khứ.
4. **Giới hạn trường cập nhật:** API hồ sơ cá nhân không nhận thay đổi vai trò, trạng thái khóa hay ID chủ sở hữu. API kết quả nhiệm vụ không cho đổi Shipper hoặc chủ Shop.
5. **Trạng thái theo hành động:** Dùng thao tác duyệt, phân công, lấy hàng, giao hàng, tiếp nhận, bàn giao; không cung cấp API cho người dùng tự gửi bất kỳ trạng thái đích nào.
6. **Chống xử lý trùng:** Duyệt chỉ sinh một vận đơn; một đợt nhiệm vụ chỉ có một người phụ trách; COD và bàn giao không ghi hai lần khi nhấn lại hoặc gửi lại yêu cầu.
7. **Lưu dấu vết:** Mỗi thay đổi nghiệp vụ lưu người thực hiện, thời gian, trạng thái trước/sau và lý do nếu yêu cầu; không cho vai trò thông thường sửa hoặc xóa dấu vết.
8. **Giới hạn dữ liệu trả về:** Shop không thấy đơn Shop khác; Shipper chỉ nhận thông tin liên hệ cần cho nhiệm vụ; không trả mật khẩu, giá trị băm hoặc dữ liệu phiên của tài khoản khác.
9. **GPS theo nhiệm vụ:** Không cấp quyền xem toàn bộ hành trình cá nhân của Shipper. Shop chỉ thấy vị trí liên quan nhiệm vụ đang thực hiện của đơn mình; dừng nhận/chia sẻ vị trí khi nhiệm vụ kết thúc hoặc quyền bị thu hồi.
10. **Khóa và đăng xuất:** Phiên cũ không tiếp tục dùng được sau đăng xuất hoặc khóa tài khoản. Nhiệm vụ đang mở của Shipper bị khóa vẫn được giữ để Nhân viên xử lý theo nghiệp vụ đã thống nhất.

11. **Số lần giao:** Tối đa 3 lần giao thực tế trên một vận đơn; chỉ tính khi lưu kết quả cuối của lần giao, không tính khi mới phân công hoặc thay người. Sau lần thất bại thứ ba, Nhân viên chỉ có thể quyết định hoàn; không tự tạo nhiệm vụ hoàn trước quyết định đó.
12. **Đổi Shipper:** Chỉ Nhân viên chọn người thay thế và nhập lý do. Chưa giữ hàng thì thay phân công ngay; đã giữ hàng thì chờ bàn giao về điểm tập kết và Nhân viên xác nhận nhận. Trong lúc chờ, người cũ chỉ được xem, cập nhật GPS phục vụ bàn giao và ghi nhận bàn giao, không cập nhật kết quả giao hoặc COD; người mới chưa có quyền nhiệm vụ. Nếu người cũ bị khóa thì Nhân viên ghi nhận tiếp nhận thực tế. Sau bàn giao, kết thúc nhiệm vụ cũ là Đã thay thế và cấp nhiệm vụ mới đúng loại, không cho hai người cùng có quyền cập nhật. Hàng hoàn đã về điểm tập kết thì tiếp nhận theo UC04.9, không tạo chuyến hoàn mới.
13. **COD:** Chỉ ghi nhận phải thu và thực thu bằng VND. Đơn không COD ghi 0; đơn COD phải thu đủ mới được giao thành công. Lưu COD cùng kết quả giao để tránh đơn thành công mà thiếu tiền; không hỗ trợ thu một phần. Chưa thu đủ thì ghi giao thất bại, không xác nhận giao thành công. Nộp tiền, đối soát và trả tiền Shop nằm ngoài phạm vi.
14. **Lấy hàng thất bại:** Chỉ Nhân viên quyết định lấy lại hoặc kết thúc. Lấy lại đưa về Chờ lấy hàng để phân công qua UC06.5; kết thúc dùng trạng thái Kết thúc do không lấy được hàng, có lý do và thông báo Shop. Không xóa vận đơn hay lịch sử cũ.

## 6. Tài khoản và tình huống kiểm tra quyền

Chuẩn bị dữ liệu kiểm thử: Shop A, Shop B, Shipper A, Shipper B và một Nhân viên/Admin. Tạo ít nhất một đơn cho mỗi Shop, phân công cho hai Shipper khác nhau. Dùng dữ liệu giả cho điện thoại và địa chỉ khi demo.

| Tình huống thử | Kết quả bắt buộc |
|---|---|
| Shop A đổi ID trên URL/API để đọc đơn Shop B | Từ chối, không lộ dữ liệu đơn Shop B |
| Shop A gọi API quản lý tài khoản, duyệt hoặc phân công | Từ chối |
| Shop sửa yêu cầu đã được duyệt | Từ chối, giữ dữ liệu hiện tại |
| Shop gửi `shop_id` của Shop khác khi tạo yêu cầu | Không tạo đơn dưới quyền sở hữu Shop khác |
| Người dùng gửi thêm trường vai trò Admin khi sửa hồ sơ | Không đổi vai trò |
| Shipper A gửi kết quả cho nhiệm vụ Shipper B | Từ chối, không ghi kết quả hoặc tiền COD |
| Shipper cũ thao tác sau khi nhiệm vụ đã chuyển người phụ trách hợp lệ | Từ chối cập nhật |
| Shipper đặt ngay Đã hoàn về Shop sau khi mang hàng về điểm tập kết | Từ chối; chờ bước xác nhận Nhân viên |
| Nhân viên phân công giao trước khi nhận tại điểm tập kết | Từ chối |
| Shop xem GPS khi nhiệm vụ liên quan đã kết thúc | Không được tiếp tục theo dõi vị trí |
| Tài khoản đã khóa hoặc phiên đã đăng xuất gọi API có quyền | Từ chối |
| Hai lần duyệt cùng yêu cầu hoặc gửi COD lặp | Không tạo trùng vận đơn hoặc tiền thu |
| Nhân viên xác nhận hàng hoàn khi Shop chưa đến lấy | Không cho kết thúc luồng hoàn nếu chưa đủ điều kiện thực tế |
| Nhân viên chọn giao lại sau lần thất bại thứ ba | Từ chối, chỉ cho quyết định hoàn |
| Nhân viên đổi Shipper nhưng chưa nhận hàng từ người cũ đang giữ | Người mới chưa được thực hiện nhiệm vụ; người cũ chỉ có quyền phục vụ bàn giao |
| Nhân viên kết thúc do không lấy được hàng | Có lý do, thông báo Shop, giữ nguyên lịch sử và mã vận đơn |
| Shipper giao thành công với COD thiếu hoặc thừa | Từ chối hoàn tất; không lưu trạng thái giao thành công |
| Đổi Shipper sau các lần giao thất bại | Giữ nguyên tổng số lần đã giao, không cấp thêm lượt vượt giới hạn |

## 7. Ngoài phạm vi hiện tại

Không tự bổ sung actor khách vãng lai, người nhận có tài khoản, kế toán hoặc nhân viên kho. Chưa có chức năng quản lý kho/tồn kho, tự đăng ký Shop, tra cứu công khai, thanh toán trực tuyến, trả COD/đối soát Shop, báo cáo doanh thu hay thông báo email/SMS trong bản nguồn. Nếu nhóm chọn làm thêm, cần bổ sung use case, quyền và báo cáo trước khi tính là phạm vi bàn giao.

