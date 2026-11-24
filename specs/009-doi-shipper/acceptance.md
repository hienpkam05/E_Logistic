# Spec 009 — Kết quả nghiệm thu kỹ thuật

Ngày: **23/11/2026**. Trạng thái: chức năng và kiểm thử tự động đạt; **chưa chốt nghiệm thu toàn bộ**.
Người dùng đã trả lời **"Chưa tự thử"** đối với bước 6.3. Audit dev còn các mục mở bên dưới.

## Các kiểm tra đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Django `check` | Không lỗi |
| `makemigrations --check --dry-run` | Không phát sinh migration |
| Backend PostgreSQL, thứ tự thường | **531/531**, 70,269 giây sau sửa lỗi nghiệm thu |
| Backend PostgreSQL, `--reverse` | **531/531**, 72,775 giây |
| Vitest | **326/326**, 43 file, 25,74 giây |
| Build production | **Đạt**, 1.831 module, 6,39 giây; outDir cache riêng |
| Chrome headless + API/PostgreSQL thật | **Đạt**, 3 kịch bản và hộp khóa; 33,465 giây |
| Đột biến Phase 2 chạy lại | Mốc **20/20**; **13/13** đột biến bị bắt, không sửa source server |
| Vue warning / lỗi JavaScript khi bấm thật | **0 / 0** |
| Desktop/mobile | 10 ảnh 1440/390, kiểm không tràn ngang; xem artifacts/phase6 |
| Npm audit production | **0** mục; exit 0 |
| Npm audit đầy đủ | **7** mục dev: **5 moderate, 2 critical**; exit 1, chưa đạt sạch |
| Rà hardcode | Không thấy vi phạm mới trong source nghiệp vụ spec 009 |

Build dùng `npm.cmd run build -- --outDir node_modules/.cache/spec009-phase6-build --emptyOutDir false`:
`dist` mặc định vẫn có hạn chế quyền xóa `EPERM` đã ghi từ Phase 4. Cấu hình dự án không đổi.
Vitest vẫn in warning từ fixture AccountCreateView / navActive ngoài phần sửa của spec 009;
trang trình duyệt thật và nhóm AccountDetailView đã dựng đúng RouterView không có warning đó.

## Lỗi tìm thấy và đã sửa

1. **Báo bàn giao đồng thời khóa tài khoản:** đã thêm hai test PostgreSQL thật trước khi sửa.
   Khóa trước thì báo vẫn được nhận; báo trước thì khóa gặp `deadlock detected`.
   Báo bàn giao nay khóa **đơn → user người ghi → nhiệm vụ**, kiểm lại tài khoản sau khi lấy khóa;
   khóa thắng trước trả `401`, báo thắng trước lưu một lần rồi thao tác khóa tiếp tục bình thường.
   Dùng chung cho báo hàng hoàn và báo bàn giao đổi người; các thao tác ghi kết quả khác giữ luồng cũ.
2. **Thông báo lý do đổi người:** trước sửa, ghi chú nhận hàng như "Đủ hàng" bị dùng làm lý do `TASK_REPLACED`.
   Nay lấy lý do của sự kiện đổi người gần nhất gắn nhiệm vụ cũ; ghi chú bàn giao vẫn lưu đúng ở Handover/lịch sử.
   Đã bổ sung assertion kiểm nội dung thông báo, và cập nhật test thứ tự khóa báo hoàn theo thứ tự mới.

Cả ba kiểm chứng đã thất bại trên code trước sửa; bộ đầy đủ xuôi/đảo thứ tự đạt sau sửa.
Không thêm bảng/cột/endpoint; hợp đồng `401` cho tài khoản bị khóa giữ nguyên, kể cả trường hợp khóa giữa request.

## Phạm vi chứng minh

- Lấy: thay ngay, người cũ chỉ xem, người mới nhận hàng bằng nút trên UI.
- Giao: chờ bàn giao, người dự kiến chưa có quyền, người cũ không giao/thất bại/COD, báo đã đưa về,
  Nhân viên xác nhận nhận thực tế rồi mới có nhiệm vụ thay thế đúng lần giao.
- Ba lần giao: bấm thất bại lần 2, giao lại lần 3, đổi người khi đang ở lần 3, bàn giao, thất bại lần 3;
  không còn Giao lại/lần 4 và Nhân viên chuyển hoàn được. Lần thất bại đầu là fixture nghiệp vụ hợp lệ.
- API/test DB kiểm thêm gửi lại, rollback lỗi thông báo, hai NV xác nhận, hai thiết bị báo,
  người mới/cũ bị khóa, sai lệch giữ chờ, không đổi nhiệm vụ hoàn/kết thúc, nhận về và giao lại/hoàn thẳng.
- `KEEP`, bảng trạng thái và ràng buộc DB có test; kiểm không N+1 và EXPLAIN index có bằng chứng tại tasks.md.
- Rà source: enum/hành động dùng hằng chung; giới hạn lấy từ meta/constants; API đi qua service/http chung;
  route dùng name, không ID/tài khoản demo/URL máy chủ/màu hex trong logic màn hình mới.

Chrome chạy trên **test DB**, LiveServer 8010 và Vite 5180 riêng; Django dọn fixture và dừng server khi kết thúc.
Các ảnh dùng dữ liệu giả, không chứa mật khẩu/token. Không dừng server người dùng 8000/5173.

## Audit còn mở

Bằng chứng: [audit đầy đủ](artifacts/phase6/npm-audit-full.json),
[audit production](artifacts/phase6/npm-audit-production.json).

| Nhóm phụ thuộc | Phát hiện từ npm audit |
|---|---|
| `vitest`, `tinypool` | 2 mục critical trong graph dev; npm đề xuất thay đổi Vitest major |
| `@vitest/mocker` | Moderate, thuộc graph Vitest |
| `js-beautify`, `editorconfig`, `glob`, `minimatch` | 4 mục moderate thuộc graph `@vue/test-utils` |

Đã chạy `npm audit fix` **không force**: 0 thêm/xóa/đổi package, 7 mục còn nguyên, package.json/lockfile không có diff.
Các URL GHSA và khoảng phiên bản cụ thể nằm trong JSON; phân loại trên là kết quả máy quét, chưa kết luận điều kiện khai thác.

[Skill dự án](../../.agents/skills/htt-express-code/SKILL.md) yêu cầu:
> Giữ phiên bản và package manager hiện có.

Do đó lượt nghiệm thu giữ các major hiện tại và ghi rõ khoản audit còn mở. Việc nâng major/override dependency
cần được xử lý thành thay đổi riêng có kiểm chứng tương thích; không đánh dấu audit đầy đủ là sạch.

## Còn để chốt

1. Người dùng thực hiện [manual-test.md](manual-test.md), ghi người thử/ngày/kết quả.
2. Xử lý hoặc quyết định chấp nhận các phát hiện audit dev theo quy trình của dự án.
3. Khi xuất build vào `dist` mặc định, xử lý quyền/khóa file trên máy; bản build kiểm tra riêng hiện đã đạt.

Không đánh dấu hoàn thành toàn bộ spec chỉ dựa vào test tự động.
