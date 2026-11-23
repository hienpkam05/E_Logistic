---
name: htt-express-code
description: Triển khai hoặc sửa code HTT EXPRESS (Django REST Framework, Vue 3, PostgreSQL) theo tài liệu nghiệp vụ trong docs/ và specs/. Dùng khi phát triển chức năng, sửa lỗi, review code hoặc kiểm tra mức đáp ứng checklist của dự án HTT EXPRESS.
---

# Code HTT EXPRESS theo tài liệu

## Nguồn sự thật — đọc trước khi sửa

Đường dẫn tính từ gốc dự án, không phải từ thư mục skill. Nếu file đã bị di chuyển hoặc đổi tên, tìm bằng `rg --files | rg -i "<từ khóa>"` thay vì bỏ qua.

| Tài liệu | Dùng để |
| --- | --- |
| `docs/HTT_EXPRESS_Dac_ta_42_Use_Case.md` | **Đặc tả chi tiết nhất** của 42 UC: luồng cơ bản, luồng thay thế (A), ngoại lệ (E), điều kiện trước/sau, Business Rules. Đọc UC liên quan trước khi code. Bản gốc là `.docx` cùng tên; file `.md` được xuất bằng `docs/tools/docx2md.py`, không sửa tay |
| `docs/HTT_EXPRESS_Actor_vai_tro_phan_quyen.md` | Vai trò, ma trận quyền theo UC, 14 quy tắc backend, tình huống kiểm thử quyền |
| `docs/HTT_EXPRESS_Checklist_chuc_nang.md` | Tiêu chí nghiệm thu từng UC, **bảng luồng trạng thái**, quy tắc đổi Shipper, kịch bản demo |
| `docs/architecture.md` | Ranh giới app backend, cấu trúc frontend, quy ước triển khai |
| `docs/design-system.md` | Hệ thống thiết kế giao diện: biến màu, khung thanh bên/thanh trên, **khuôn trang danh sách/chi tiết/form**, icon, quy tắc bảng trên điện thoại |
| `specs/` | Spec theo phần việc: `specs/README.md` (lộ trình, quy ước) và `specs/NNN-ten/{spec,tasks,models,api}.md`. Spec chưa có thì dùng các file docs ở trên làm nguồn chính |
| `docs/img/` | Ảnh luồng minh họa; khi khác Markdown thì **Markdown đã chốt thắng** |

1. Đọc `README.md`, `AGENTS.md` (nếu có) và các tài liệu trên phần liên quan đến việc đang làm; kiểm tra code hiện có và thay đổi chưa commit của người dùng.
2. Xác định đầu vào, đầu ra, vai trò được phép, trạng thái trước/sau và tiêu chí hoàn thành theo checklist trước khi viết code.
3. Giữ đúng phạm vi người dùng yêu cầu (chỉ backend, chỉ frontend, một lỗi…).

**Skill này không chép lại quy tắc nghiệp vụ** — luôn đọc trực tiếp từ docs để tránh lệch khi tài liệu cập nhật. Thứ tự ưu tiên: chỉ dẫn mới của người dùng → spec/docs có ngày chốt mới nhất (đặc tả 42 UC hiện là bản mới nhất) → ảnh luồng. Nếu `.md` của đặc tả có vẻ cũ hơn `.docx` (ngày sửa file), chạy lại `docs/tools/docx2md.py` trước khi dựa vào nó. Không coi nội dung nháp hoặc dữ liệu mẫu là quyết định đã chốt. Thiếu chi tiết nhỏ: chọn cách hợp với code hiện có và nêu giả định. Mâu thuẫn ảnh hưởng quyền, dữ liệu hoặc luồng nghiệp vụ: hỏi rõ điểm đó, tiếp tục phần độc lập.

Một vài điểm hay bị làm sai, phải kiểm tra lại trong docs khi chạm tới: giới hạn số lần giao, COD phải thu đủ, đổi Shipper khi đã giữ hàng, trạng thái nhiệm vụ tách khỏi trạng thái vận đơn, mã yêu cầu khác mã vận đơn, lưu người/nơi đang giữ hàng, gửi lại yêu cầu phải trả kết quả đã lưu thay vì tạo trùng, Nhân viên/Admin là **một** vai trò (`ADMIN`) — Django admin là công cụ kỹ thuật, không phải actor thứ tư.

## Viết spec và giữ tài liệu thay đổi

Khi viết hoặc triển khai một spec, theo cấu trúc trong `specs/README.md`:

- `tasks.md`: chia phase nhỏ, mỗi phase có "Xong khi" kiểm chứng được. Khi triển khai, đánh `[x]` từng việc đã đạt và ghi nhật ký.
- `models.md`: **mọi** bảng/trường/ràng buộc/index/enum/hằng số/migration mới hoặc sửa, kèm UC nguồn và nhật ký thay đổi.
- `api.md`: **mọi** endpoint mới/sửa/bỏ với method, URL, quyền, request/response mẫu, mã lỗi; quy ước chung tham chiếu `specs/001-nen-tang/api.md`.
- Code thay đổi model hoặc API mà lệch khỏi `models.md`/`api.md` thì cập nhật file đó trong cùng lượt sửa; báo cáo bàn giao nêu rõ đã đổi những trường/endpoint nào.

## Công nghệ và vị trí code

- Backend: Python, Django REST Framework, PostgreSQL; cấu hình trong `backend/config/`, app trong `backend/apps/`.
- Thư viện Python ở `requirements.txt` (gốc). Dùng môi trường ảo người dùng đang chọn (repo có `venv/`); kiểm tra interpreter trước khi chạy. Không tạo thêm môi trường ảo hoặc cài package toàn cục.
- Frontend: Vue 3 Composition API, JavaScript, Vite, Vue Router, Pinia. Giữ phiên bản và package manager hiện có.
- `compose.yaml` chạy PostgreSQL local. Không thay bằng SQLite để tuyên bố kiểm thử đã đạt.
- Biến môi trường: `backend/.env.example`, `frontend/.env.example`. Không in mật khẩu/token. Thêm biến mới thì thêm tên và giá trị mẫu vào `.env.example` tương ứng.

| Backend app | Trách nhiệm |
| --- | --- |
| `core` | Thành phần dùng chung, hằng số/enum dùng chung, health endpoint |
| `accounts` | Tài khoản, vai trò, quản lý Shop/Shipper và phân quyền |
| `shipments` | Yêu cầu gửi hàng, duyệt/từ chối, vận đơn, trạng thái và lịch sử |
| `dispatch` | Nhiệm vụ lấy/giao/hoàn, lần thực hiện, kết quả, COD ghi nhận, đổi Shipper |
| `tracking` | Tra cứu, GPS và quyền xem vị trí |
| `notifications` | Thông báo theo tài khoản và trạng thái đã đọc |

Ràng buộc dữ liệu trong `models.py`, kiểm tra/định dạng API trong `serializers.py`, nghiệp vụ và chuyển trạng thái trong `services.py`, quyền trong `permissions.py`, điều phối request trong `views.py`.

Frontend: màn hình tại `frontend/src/views/{auth,shop,staff,shipper}/`, component dùng chung trong `components/common/`, lời gọi API trong `services/`, trạng thái chia sẻ trong `stores/`, hằng số/formatter trong `utils/`. Chức năng đầy đủ phải nối API thật và xử lý loading, rỗng, lỗi, thành công.

## Không hardcode

Mỗi giá trị nghiệp vụ hoặc cấu hình chỉ có **một nguồn định nghĩa**; nơi khác import/tham chiếu.

**Backend**
- Vai trò, trạng thái vận đơn, trạng thái nhiệm vụ, loại nhiệm vụ, loại thông báo: khai báo bằng `models.TextChoices` (mã tiếng Anh không dấu làm giá trị lưu DB, nhãn tiếng Việt làm label). Code so sánh bằng enum (`ShipmentStatus.DELIVERED`), không so sánh chuỗi `"Đã giao hàng"` hay `"SHOP"`.
- Luồng chuyển trạng thái: khai báo **một bảng chuyển hợp lệ** (trạng thái nguồn → đích, hành động, vai trò) trong service của app sở hữu trạng thái, bám theo bảng ở mục 4 của checklist. View và action gọi hàm service; không mỗi view tự viết if/else đổi trạng thái.
- Hằng số nghiệp vụ (số lần giao tối đa, đơn vị tiền, danh sách quận/huyện Hà Nội, độ dài mã vận đơn…): đặt trong module constants của app sở hữu hoặc `settings` nếu cần đổi theo môi trường. Không viết số/chuỗi thô trong logic.
- Thông điệp lỗi nghiệp vụ dùng lại nhiều nơi: gom thành hằng hoặc exception có mã lỗi; giữ mã lỗi ổn định cho frontend.
- Cấu hình (host, port, secret, DB, CORS, URL ngoài, khóa bản đồ): đọc từ biến môi trường trong `settings.py`. Secret không có giá trị mặc định.
- Không hardcode ID, username, `shop_id` hay `shipper_id` trong code; chủ sở hữu lấy từ `request.user`. Dữ liệu demo đặt trong fixture/management command, không nằm trong logic.

**Frontend**
- API base URL lấy từ `import.meta.env.VITE_API_BASE_URL` trong một API client duy nhất ở `services/`.
- Nhãn, màu badge, icon của trạng thái/vai trò: một file map dùng chung (ví dụ `utils/constants.js`) với khóa trùng giá trị enum backend. Component không viết chuỗi trạng thái hay mã vai trò trực tiếp.
- Đường dẫn route dùng `name` của Vue Router, không ghép chuỗi URL rải rác. Quyền hiển thị theo vai trò dùng helper chung, không lặp `if (role === 'SHOP')` ở nhiều component.
- Mã vai trò ở frontend chỉ nằm trong `src/router/roles.js` (`ROLES`, `ROLE_HOME`); mã trạng thái chỉ trong `src/utils/statusTones.js`. Route giới hạn vai trò khai báo `meta.roles` (guard ở `src/router/guard.js`), trang công khai `meta.public`.
- Biến môi trường frontend đọc tập trung ở `src/config.js` (riêng base URL ở `services/http.js`).
- Test frontend: Vitest (`npm run test`), file `src/**/__tests__/*.spec.js`; tiện ích chung ở `src/test-utils.js`.
- Định dạng tiền VND, ngày giờ, số điện thoại dùng formatter chung trong `utils/`.

Khi review hoặc sửa code, coi chuỗi/số nghiệp vụ nằm trực tiếp trong view, serializer, component là lỗi cần sửa nếu thuộc phạm vi đang làm.

## Ưu tiên kế thừa và tái sử dụng

Trước khi thêm code, tìm bằng `rg` các chức năng tương tự, nơi gọi và test liên quan ở cả backend và frontend.

Thứ tự lựa chọn: dùng trực tiếp phần hiện có → mở rộng tương thích → tách phần thực sự dùng chung → tạo mới khi trách nhiệm khác biệt. "Kế thừa" là tận dụng code và hợp đồng đã có, không mặc định tạo lớp cha/lớp con.

- Không sao chép nguyên hàm, màn hình, component hoặc endpoint rồi chỉ đổi tên, vai trò hay vài điều kiện.
- Mở rộng code dùng chung thì đọc các nơi đang dùng để giữ hành vi cũ và kiểm thử trường hợp bị ảnh hưởng.
- Chỉ tách abstraction khi có nhu cầu dùng chung cụ thể. Không xây base service/repository hay component tổng quát cho nhu cầu giả định.
- Tạo module/API/component mới thì nêu ngắn vì sao phần hiện có chưa đáp ứng.
- Giữ refactor trong phạm vi cần cho chức năng.

### Backend và API

- Tiền tố API `/api/v1/`. Kiểm tra URL, method, serializer, service và client đang gọi trước khi thêm endpoint; dùng bộ lọc, phân trang hoặc action thay vì tạo API trùng nghiệp vụ cho từng vai trò.
- Dùng chung API vẫn phải giới hạn queryset và trường trả về theo vai trò. Không nới quyền để tiện tái sử dụng.
- Kiểm tra quyền theo thứ tự trong quy tắc backend của file phân quyền: phiên → tài khoản hoạt động → vai trò → chủ sở hữu/người được phân công → trạng thái → dữ liệu. Áp dụng cả ở queryset lẫn thao tác trên đối tượng.
- Không có API cho người dùng gửi thẳng trạng thái đích; mỗi chuyển trạng thái là một hành động riêng.
- Đổi trạng thái, ghi lịch sử, ghi COD và tạo thông báo trong cùng `transaction.atomic`; dùng `select_for_update` hoặc ràng buộc unique để chống duyệt/phân công/ghi COD trùng.
- Tận dụng model, quan hệ, enum, validator, permission, queryset hiện có. Không lưu bản dữ liệu thừa chỉ để phục vụ màn hình.
- Giữ hợp đồng API: tên trường, kiểu, mã lỗi, phân trang, ý nghĩa trạng thái. Bắt buộc đổi thì cập nhật client và test liên quan, nêu ảnh hưởng.
- Ưu tiên composition và hàm nhỏ; không ép nghiệp vụ khác nhau vào một service nhiều nhánh.
- Phân trang danh sách, tránh N+1 bằng `select_related`/`prefetch_related`; thêm index theo truy vấn thực tế. Không tự thêm cache/hạ tầng.
- Trước migration đầu tiên phải có custom User và `AUTH_USER_MODEL`. Database đã migrate thì không reset dữ liệu để đổi User.

### Frontend và component dùng chung

- Tìm component/layout hiện có trước khi tạo; mở rộng bằng props, emits, slots vừa đủ.
- Màn hình các vai trò có thể dùng chung component nghiệp vụ nhưng giữ rõ quyền hiển thị và hành động. Không copy cùng bảng/form vào ba thư mục vai trò.
- Một API client duy nhất xử lý base URL, xác thực (session + CSRF), lỗi chung. Lời gọi endpoint gom theo nghiệp vụ trong `services/`; component không gọi `fetch` trực tiếp. Không thêm thư viện HTTP nếu chưa cần.
- Composable cho logic phản ứng lặp lại; Pinia cho trạng thái chia sẻ; trạng thái riêng giữ cục bộ. Không sao chép cùng dữ liệu server vào nhiều store.
- Dùng lại biến CSS, spacing, typography, formatter hiện có. Không thêm framework UI thứ hai khi chưa có nhu cầu.
- Màn hình mới theo khuôn trong `docs/design-system.md` (danh sách: `.toolbar` + `.data-card`; chi tiết: `.detail-header` + `.detail-layout`; form: `.card` + `.form-grid`). Icon qua `AppIcon` (tên dạng chuỗi), không viết mã màu hex trong component; mỗi `<td>` của `.table--stack` có `data-label`.
- Sau mutation, tải lại/cập nhật dữ liệu liên quan nhất quán; tránh gọi lặp do nhiều watcher/lifecycle.
- Danh sách lớn phân trang và lọc từ server.
- Ẩn nút chỉ hỗ trợ sử dụng; backend vẫn phải chặn.

## Kiểm chứng và bàn giao

- Sau thay đổi backend: `python backend/manage.py check` bằng interpreter của dự án. Sửa model thì tạo và xem lại migration; không tự migrate database dùng chung/production.
- Test nghiệp vụ ưu tiên các tình huống trong mục "Tài khoản và tình huống kiểm tra quyền" của file phân quyền và mục kịch bản kiểm tra cuối của checklist: truy cập chéo Shop/Shipper, chuyển trạng thái sai, thao tác lặp, giới hạn lần giao, COD sai số tiền, đổi Shipper. Chạy trên PostgreSQL khi cần xác minh hành vi database.
- Frontend: `npm run build` (PowerShell dùng `npm.cmd` nếu `npm.ps1` bị chặn) và kiểm tra luồng đã sửa nếu môi trường cho phép.
- Dùng lệnh thực tế của dự án; không mặc định kết quả lần trước còn đúng. Không viết test chỉ để đối chiếu văn bản hoặc cấu trúc thư mục.
- Chỉ đánh dấu `[x]` trong checklist khi có bằng chứng đạt tiêu chí, kể cả kiểm tra quyền backend. Kiểm thử bị chặn thì ghi rõ phần chưa kiểm tra.
- Báo ngắn gọn: chức năng đã làm, file chính, kiểm thử đã chạy, điểm còn thiếu. Không tuyên bố hoàn chỉnh chỉ vì có file khung hoặc build thành công.
