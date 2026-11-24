# Quy ước kiến trúc HTT EXPRESS

Tài liệu nghiệp vụ đã chốt (nguồn sự thật cho quyền, trạng thái và tiêu chí nghiệm thu):

- [HTT_EXPRESS_Dac_ta_42_Use_Case.md](HTT_EXPRESS_Dac_ta_42_Use_Case.md): đặc tả chi tiết nhất của 42 UC (luồng A/E, điều kiện trước/sau, Business Rules). Bản gốc là `HTT_EXPRESS_Dac_ta_42_Use_Case.docx`; file `.md` xuất bằng `python -I docs/tools/docx2md.py docs/HTT_EXPRESS_Dac_ta_42_Use_Case.docx docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md`, không sửa tay.
- [HTT_EXPRESS_Actor_vai_tro_phan_quyen.md](HTT_EXPRESS_Actor_vai_tro_phan_quyen.md): vai trò, ma trận quyền, quy tắc backend, tình huống kiểm thử quyền.
- [HTT_EXPRESS_Checklist_chuc_nang.md](HTT_EXPRESS_Checklist_chuc_nang.md): checklist UC, luồng trạng thái, quy tắc đổi Shipper, kịch bản demo.

Tài liệu này chỉ mô tả kiến trúc code. Khi có khác biệt về nghiệp vụ, ba file trên được ưu tiên (đặc tả 42 UC có ngày chốt mới nhất); ảnh trong `img/` là minh họa.

## Ranh giới backend

| App | Trách nhiệm |
| --- | --- |
| `core` | Thành phần chung, hằng số/enum dùng chung, kiểm tra ứng dụng |
| `accounts` | Tài khoản, ba vai trò, quyền theo đối tượng và quản lý Shop/Shipper |
| `shipments` | Yêu cầu gửi, xác nhận/từ chối, mã vận đơn, trạng thái vận đơn và lịch sử |
| `dispatch` | Phân công, nhiệm vụ lấy/giao/hoàn, lần thực hiện, kết quả, COD ghi nhận, đổi Shipper, trạng thái nhiệm vụ |
| `tracking` | Tra cứu vận đơn, GPS khi có nhiệm vụ và quyền xem vị trí |
| `notifications` | Thông báo theo tài khoản, danh sách và trạng thái đã đọc |

Trong mỗi app nghiệp vụ:

- `models.py`: dữ liệu, ràng buộc database và enum (`TextChoices`).
- `serializers.py`: kiểm tra đầu vào và định dạng dữ liệu API.
- `views.py`: nhận request và trả response.
- `services.py`: nghiệp vụ, giao dịch và chuyển trạng thái.
- `permissions.py`: quyền thao tác và giới hạn dữ liệu.
- `urls.py`: khai báo các endpoint của app.
- `admin.py`: đăng ký công cụ quản trị Django khi có model.
- `migrations/`: các thay đổi schema được quản lý bằng Git.

Các app đã có model/API và nghiệp vụ của spec 001–009. Tra cứu chuyên biệt/lịch sử spec 010
đã triển khai trong `shipments`; `tracking` spec 011 đã có LocationPing, API gửi/xem GPS theo nhiệm vụ
và lệnh purge theo thời điểm nhận (Phase 1–2). Task mở và GPS được đọc trong cùng snapshot SQL.
Frontend đã có trackingService, useLocationSharing và LiveLocationMap/Leaflet, Phase 4 đã gắn vào
chi tiết nhiệm vụ Shipper và chi tiết đơn Shop/NV. Chỉ đường D7 mở Google Maps bằng địa chỉ theo phương án
đã trình bày/yêu cầu tiếp tục; không tích hợp dịch vụ định tuyến hoặc tọa độ địa chỉ mới.

Tiền tố API: `/api/v1/`. Có health, meta/choices, tài khoản/xác thực, vận đơn, điều phối nhiệm vụ và thông báo.
Hợp đồng chi tiết theo `specs/NNN-ten/api.md`; spec 009 bổ sung đổi người/bàn giao và danh sách nhiệm vụ mở theo Shipper.

## Vai trò

Ba vai trò: `SHOP`, `ADMIN` (Nhân viên/Admin dùng chung), `SHIPPER`. Django admin là công cụ kỹ thuật, không phải actor thứ tư. Người nhận hàng không có tài khoản; Điểm tập kết là địa điểm, không phải actor hay phân hệ kho.

## Quy ước triển khai

1. Tạo custom User và ba vai trò trước khi migrate lần đầu. Mỗi thao tác kiểm tra quyền ở backend theo thứ tự: phiên → tài khoản hoạt động → vai trò → chủ sở hữu/người được phân công → trạng thái → dữ liệu.
2. Shop chỉ xem dữ liệu của mình (`shop_id` lấy từ phiên); Shipper chỉ truy cập nhiệm vụ đang được giao; `ADMIN` xem toàn hệ thống nhưng vẫn qua kiểm tra trạng thái.
3. Trạng thái chỉ đổi qua hành động nghiệp vụ, không có API gửi thẳng trạng thái đích. Bảng chuyển hợp lệ khai báo một chỗ trong service, bám theo mục 4 của checklist.
4. Trạng thái vận đơn (`shipments`) và trạng thái nhiệm vụ (`dispatch`) lưu riêng; mỗi lần phân công/giao lại là bản ghi mới, không ghi đè lần trước. Mã yêu cầu sinh khi Shop tạo, mã vận đơn chỉ sinh khi duyệt. Lưu người/nơi đang giữ hàng làm điều kiện phân công giao lại, hoàn, đổi Shipper.
5. Đổi trạng thái, ghi lịch sử, ghi COD và tạo thông báo trong cùng một transaction; chống xử lý trùng khi duyệt, phân công, ghi COD, bàn giao.
6. Mỗi lần lấy/giao thất bại lưu thời gian, người thực hiện và lý do. **Tối đa 3 lần giao thực tế** trên một vận đơn; sau lần thất bại thứ ba chỉ được quyết định hoàn. Đổi Shipper không đặt lại bộ đếm.
7. COD ghi phải thu và thực thu bằng VND; đơn COD chỉ giao thành công khi thu đủ, không thu một phần. Không có nộp tiền, đối soát hay trả COD cho Shop.
8. Đổi Shipper khi người cũ đang giữ hàng phải bàn giao về điểm tập kết và `ADMIN` xác nhận nhận trước khi người mới có quyền.
9. Hàng hoàn đưa về điểm tập kết; Shop đến lấy và `ADMIN` xác nhận Shop đã nhận.
10. GPS chỉ cập nhật trong nhiệm vụ đang hoạt động và chỉ hiển thị cho người có quyền. GPS/bản đồ là mức "Nên có".
11. Phạm vi Hà Nội, một điểm tập kết cố định. Không có quản lý kho, tra cứu công khai hay thông báo email/SMS.

## Cấu hình và hằng số

- Cấu hình môi trường đọc từ biến môi trường; mẫu tại `backend/.env.example` và `frontend/.env.example`. Secret không có giá trị mặc định trong code.
- Vai trò, trạng thái, loại nhiệm vụ dùng `TextChoices`; hằng số nghiệp vụ (số lần giao tối đa, đơn vị tiền, phạm vi địa bàn) đặt trong module constants của app sở hữu. Không viết chuỗi/số nghiệp vụ trực tiếp trong view, serializer hoặc component.

## Frontend

Vue 3 dùng Composition API và JavaScript, Vite, Vue Router và Pinia. Màn hình nghiệp vụ được chia theo `auth`, `shop`, `staff`, `shipper`; thành phần dùng chung nằm trong `components/common`. Một API client duy nhất trong `services/` dùng `VITE_API_BASE_URL`; nhãn/màu trạng thái đặt trong một map dùng chung ở `utils/` với khóa trùng enum backend. Chỉ trang giới thiệu và trang không tìm thấy đã được tạo.

## Điểm đã chốt so với ảnh luồng

Các điểm từng chưa thống nhất giữa Markdown và ảnh luồng đã được chốt theo Markdown:

- Luồng 5: Shipper đưa hàng hoàn về **điểm tập kết**, Shop đến lấy; không giao hoàn tận Shop.
- Luồng 6: không có tra cứu cho Người nhận; chỉ Shop (đơn của mình) và `ADMIN` tra cứu.
- Luồng 1: dữ liệu không hợp lệ phải dẫn tới hiển thị lỗi, không tạo yêu cầu. Nhãn Có/Không trên ảnh cần chỉnh lại.
- Luồng 4: thêm giới hạn 3 lần giao và bước `ADMIN` quyết định giao lại/hoàn.

Ảnh luồng và báo cáo cần cập nhật tương ứng, kể cả 5 UC bổ sung (UC04.10–UC04.13, UC06.8).
