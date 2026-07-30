# EnglishFlow — Nghiệp vụ hệ thống

> Tài liệu nghiệp vụ. Cách chạy repo: [../README.md](../README.md) · Backend: [../backend/README.md](../backend/README.md)

## EnglishFlow làm gì?

EnglishFlow giúp người học:

1. Xác định trình độ (survey + placement nếu cần)
2. Nhận lộ trình học theo **skill** ở cấp CEFR (A1–C1)
3. Luyện từng skill (Learn + Quiz)

Admin nuôi hệ thống bằng cách **đưa sách vào → biến thành skill → sinh câu hỏi / bài học → xuất bản**.

> **Nguyên tắc quan trọng:** Học viên không “học theo cuốn sách”. Sách chỉ là **nguồn nguyên liệu**. Đơn vị học & đánh giá là **skill theo CEFR** (ví dụ: Present Perfect @ B1). Một skill có thể lấy nội dung từ nhiều sách.

---

## Hai phía nghiệp vụ

| Phía | Việc chính |
|------|------------|
| **Learner** | Đăng ký → onboarding → (placement) → roadmap → luyện skill |
| **Admin** | Upload sách → index → sync skill → sinh quiz/lesson → publish |

---

## Phần 1 — Nghiệp vụ học viên

### 1. Đăng ký / đăng nhập

- Tạo tài khoản hoặc đăng nhập
- Hệ thống đưa learner vào onboarding (nếu chưa xong) hoặc dashboard

### 2. Onboarding (survey)

Learner trả lời:

- Mục tiêu học
- Thời gian học mỗi ngày
- Mình biết tiếng Anh mức nào?

Nhánh xử lý:

| Lựa chọn | Kết quả |
|----------|---------|
| Beginner | Gán A1, bỏ qua placement |
| Tự chọn CEFR | Chọn A1–C1, bỏ qua placement |
| Cần đo trình độ | Vào bài placement |

### 3. Placement (nếu cần)

- Làm bài Reading + Writing (kiểu TOEIC)
- Reading chấm tự động; Writing có feedback
- Kết quả: cấp CEFR (`current_level`) + điểm phụ (`placement_score`)

Câu hỏi placement lấy từ **ngân hàng câu đã publish** — không gắn “cuốn sách X”.

### 4. Roadmap (My plan)

- Hệ thống chọn skill ở level hiện tại, ưu tiên skill còn yếu
- Hiện khoảng 3 tuần phía trước (1 đang học + 2 khóa)
- Hoàn thành tuần → hệ thống lập tiếp tuần mới

### 5. Luyện skill

Với mỗi skill trên roadmap:

1. **Learn** (nếu có bài đã publish): đọc → kiểm tra → viết → nhận feedback
2. **Practice**: làm quiz theo skill, cập nhật mức nắm vững (mastery)

---

## Phần 2 — Nghiệp vụ admin: cuốn sách đi đâu?

Đây là pipeline cốt lõi. Mục tiêu: biến PDF thành nguồn để sinh **skill / quiz / lesson**.

### Tổng quan một dòng

```text
Upload PDF
  → Hệ thống tự tách cấu trúc (unit / chapter)
  → (nếu đạt chất lượng) tự index văn bản
  → Sách Ready
  → Admin sync skill
  → Admin sinh quiz / lesson
  → Admin publish
  → Học viên dùng qua placement + roadmap + practice
```

### Bước A — Admin upload sách

Admin nhập:

- Tiêu đề
- Loại sách (grammar / reading / test bank / freeform)
- Cấp CEFR (nên điền ngay — cần cho bước sync skill)
- File PDF

Sau khi bấm Upload, **hệ thống tự chạy** (admin không cần bấm Detect):

| # | Hệ thống làm gì | Trạng thái sách |
|---|-----------------|-----------------|
| 1 | Lưu file, tạo bản ghi sách | `uploaded` — đang detect |
| 2 | Đọc PDF, tìm mục lục / heading → danh sách **unit** (tiêu đề + khoảng trang) | vẫn `uploaded` đến khi detect xong |
| 3 | (Nếu bật AI) gộp các cách detect thành 1 cấu trúc sạch hơn | — |
| 4 | **Kiểm tra chất lượng cấu trúc** (unit có hợp lý không: tiêu đề, trang, độ phủ) | — |
| 5a | **Đạt** → tự bắt đầu index | `processing` → rồi `ready` |
| 5b | **Không đạt** / detect yếu / lỗi | `needs_review` — chờ admin |

**Index nghĩa là gì?**  
Với mỗi unit, hệ thống cắt nội dung thành các đoạn text nhỏ (chunk), lưu lại để sau này sinh quiz/lesson và tìm ngữ cảnh. Khi có đủ chunk → sách **Ready**.

### Các trạng thái của một cuốn sách

| Trạng thái | Ý nghĩa với admin | Admin cần làm gì? |
|------------|-------------------|-------------------|
| **uploaded** | Đang tự detect cấu trúc | Đợi |
| **needs_review** | Cấu trúc cần xem lại / chưa index | Xem preview unit → **Retry detect** hoặc **Confirm & index** |
| **processing** | Đang cắt text + nhúng dữ liệu | Đợi |
| **ready** | Đã index, dùng được cho Quiz/Lesson | Qua bước B bên dưới |
| **failed** | Index thất bại | Retry / Reindex / kiểm tra file |

> Sách **không** có trạng thái “publish cho học viên”.  
> Học viên chỉ thấy nội dung khi admin **publish quiz / lesson** gắn với skill.

### Khi nào admin phải can thiệp sau upload?

**Happy path (thường gặp):** detect đạt → hệ thống tự index → sách **Ready**. Admin gần như chỉ upload rồi đợi.

**Khi hệ thống dừng ở `needs_review`:**

1. Mở **Structure preview** — xem danh sách unit (tên + trang)
2. Nếu unit sai / thiếu → **Retry detect**
3. Nếu unit chấp nhận được → **Confirm & index** (ép index dù kiểm tra tự động chưa đạt)
4. Đợi status → **Ready**

Có thể làm thêm nếu cần sửa:

- **Reindex** một unit lỗi
- **Retry embed** nếu embedding chậm/lỗi
- **Delete** sách nếu upload nhầm

### Bước B — Sách đã Ready: admin còn phải làm gì?

Upload xong **chưa** đủ để học viên học. Admin tiếp tục pipeline nội dung:

```text
Sách Ready
   │
   ├─ 1. Sync skills     (map mỗi unit → skill chuẩn theo CEFR)
   ├─ 2. Generate quiz   (sinh câu Reading / Writing dạng draft)
   ├─ 3. Publish quiz    (duyệt draft → published → vào ngân hàng câu hỏi)
   ├─ 4. Generate lesson (tuỳ chọn: bài Learn cho skill)
   └─ 5. Publish lesson  (học viên mới thấy bước Learn)
```

Chi tiết từng bước:

| Bước | Admin làm gì | Hệ thống làm gì | Kết quả nghiệp vụ |
|------|--------------|-----------------|-------------------|
| **Sync skills** | Vào Quiz của sách, bấm sync | Map unit → skill chuẩn; có thể loại unit không dùng được (answer key, appendix…) | Skill tồn tại trong đồ thị học, gắn nguồn từ sách |
| **Generate quiz** | Chọn skill, sinh Reading / Writing | AI lấy ngữ cảnh từ chunk của sách → tạo câu **draft** | Có ngân hàng nháp để duyệt |
| **Publish quiz** | Chọn câu đạt → Publish | Đổi status `draft` → `published` | Câu vào bank dùng cho placement + practice |
| **Generate lesson** | Chọn skill, Generate | AI soạn mini-unit Learn (dựa excerpt sách nếu có) | Lesson dạng draft |
| **Publish lesson** | Publish | Bật Learn cho skill đó | Học viên thấy bước Learn |

### Sách kết nối thế nào với học viên?

| Bề mặt học viên | Có “mở cuốn sách” không? | Lấy nội dung từ đâu? |
|-----------------|--------------------------|----------------------|
| Placement | Không | Câu hỏi **đã publish** theo level / dạng bài |
| Roadmap | Không | Skill đang active ở `current_level` + khoảng trống mastery |
| Practice quiz | Không trực tiếp | Câu hỏi publish theo **skill_id** (sách chỉ là nguồn gốc khi sinh) |
| Learn | Không trực tiếp | Lesson publish của skill (thường grounded từ sách primary) |

---

## Checklist thao tác admin (một cuốn sách mới)

1. Upload PDF + chọn loại + gắn CEFR  
2. Đợi Ready (hoặc Review → Confirm & index)  
3. Sync skills  
4. Generate quiz cho các skill quan trọng → duyệt → Publish  
5. (Tuỳ chọn) Generate + Publish lesson  
6. Kiểm tra: placement / practice ở level đó đã có đủ câu chưa  

---

## Một câu tóm tắt

> Admin đưa sách vào để hệ thống tách unit và index text; sau đó admin phải **đồng bộ skill → sinh & xuất bản quiz/lesson**. Học viên học theo skill trên roadmap, không học theo từng file PDF.
