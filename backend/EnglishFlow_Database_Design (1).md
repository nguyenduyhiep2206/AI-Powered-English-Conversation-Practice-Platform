
**THIẾT KẾ CƠ SỞ DỮ LIỆU**

**EnglishFlow — AI-Powered English Learning Platform**

*Final Project · Full Stack Web Development · 21 bảng MySQL*

# **1. Tổng quan hệ thống**
EnglishFlow là web app luyện hội thoại tiếng Anh theo kịch bản thực tế thông qua AI Agent text-based. Database được thiết kế theo 3-layer: MySQL (dữ liệu cấu trúc — 21 bảng), MongoDB (chat logs + RAG), Redis (cache + session).

*Phần tài liệu này trình bày thiết kế MySQL — lớp dữ liệu quan hệ chính.*

# **2. Nhóm bảng: Auth & Phân quyền**
*Quản lý tài khoản, vai trò, quyền hạn và JWT token — theo chuẩn RBAC (Role-Based Access Control)*
## **2.1 Bảng users**
*Thông tin tài khoản cơ bản của người dùng.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK|ID người dùng|
|**username**|VARCHAR(50)|✅|UNIQUE|Tên đăng nhập|
|**email**|VARCHAR(100)|✅|UNIQUE|Email người dùng|
|**password\_hash**|VARCHAR(255)|✅||Mật khẩu (đã hash bcrypt)|
|**full\_name**|VARCHAR(100)|❌||Họ và tên|
|**avatar\_url**|VARCHAR(512)|❌||Ảnh đại diện|
|**is\_active**|BOOLEAN DEFAULT TRUE|✅||Trạng thái hoạt động|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅||Thời gian tạo|
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅||Thời gian cập nhật|

## **2.2 Bảng roles**
*Các vai trò trong hệ thống: admin, learner. Admin quản lý kịch bản và nội dung; learner là người học.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK|Khoá chính|
|**name**|VARCHAR(50)|✅|UNIQUE|Tên vai trò (admin, learner)|
|**description**|VARCHAR(255)|❌||Mô tả vai trò|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅||Cập nhật tự động|

## **2.3 Bảng permissions**
*Danh sách các quyền chi tiết, ví dụ: scenario:create, vocab:view, report:export.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK|Khoá chính|
|**name**|VARCHAR(100)|✅||Tên quyền (vd: Xem kịch bản)|
|**code**|VARCHAR(100)|✅|UNIQUE|Mã quyền (vd: scenario:view)|
|**description**|VARCHAR(255)|❌||Mô tả chi tiết|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||

## **2.4 Bảng role\_permissions**
*Quan hệ nhiều-nhiều: mỗi role có thể có nhiều permission.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**role\_id**|BIGINT UNSIGNED|✅|FK → roles.id|Vai trò|
|**permission\_id**|BIGINT UNSIGNED|✅|FK → permissions.id|Quyền hạn|
|**PRIMARY KEY**|(role\_id, permission\_id)|✅||Quan hệ nhiều-nhiều|

## **2.5 Bảng user\_roles**
*Gán vai trò cho từng người dùng. Một user có thể có nhiều role (hiếm, nhưng hỗ trợ).*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id|Người dùng|
|**role\_id**|BIGINT UNSIGNED|✅|FK → roles.id|Vai trò|
|**PRIMARY KEY**|(user\_id, role\_id)|✅||Quan hệ nhiều-nhiều|

## **2.6 Bảng refresh\_tokens**
*Lưu refresh token để hỗ trợ JWT rotation và thu hồi token khi logout hoặc phát hiện bất thường.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id|Người sở hữu token|
|**jti**|VARCHAR(128)|✅|UNIQUE|JWT ID (jti claim)|
|**revoked**|TINYINT(1) DEFAULT 0|✅||0 = còn hiệu lực, 1 = đã thu hồi|
|**ip\_address**|VARCHAR(45)|❌||IPv4 / IPv6|
|**user\_agent**|VARCHAR(512)|❌||Trình duyệt / thiết bị|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**expired\_at**|TIMESTAMP|✅||Thời điểm hết hạn|


# **3. Nhóm bảng: Hồ sơ & Onboarding**
*Lưu kết quả survey và placement test để cá nhân hoá roadmap và nội dung học cho từng người dùng.*
## **3.1 Bảng user\_profiles**
*1-1 với users. Lưu kết quả survey (mục tiêu, nghề nghiệp, điểm yếu) và kết quả placement test (level A1-C1).*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id UNIQUE|1-1 với users|
|**occupation**|VARCHAR(100)|❌||Nghề nghiệp / ngành học|
|**goal**|ENUM('job\_interview','daily\_conversation','travel','ielts','business')|✅||Mục tiêu học|
|**weak\_point**|ENUM('grammar','vocabulary','confidence','writing')|❌||Điểm yếu tự nhận|
|**daily\_time\_min**|SMALLINT DEFAULT 30|✅||Thời gian học mỗi ngày (phút)|
|**current\_level**|ENUM('A1','A2','B1','B2','C1')|✅||Trình độ hiện tại (từ placement test)|
|**placement\_score**|TINYINT UNSIGNED|❌||Điểm placement test (0-100)|
|**survey\_done**|BOOLEAN DEFAULT FALSE|✅||Đã hoàn thành survey chưa|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||

# **4. Nhóm bảng: Kịch bản & Lộ trình học**
*Quản lý toàn bộ kịch bản hội thoại và lộ trình học theo cấp độ CEFR.*
## **4.1 Bảng scenarios**
*Mỗi kịch bản là một tình huống thực tế: phỏng vấn việc làm, đặt phòng khách sạn, gọi đồ ăn... AI sẽ nhận vai theo ai\_role và người dùng nhận user\_role.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**title**|VARCHAR(255)|✅||Tiêu đề kịch bản (vd: Tech Job Interview)|
|**slug**|VARCHAR(255)|✅|UNIQUE|Slug URL thân thiện|
|**description**|TEXT|❌||Mô tả ngắn kịch bản|
|**category**|ENUM('job\_interview','hotel','restaurant','shopping','travel','small\_talk','medical','custom')|✅||Nhóm kịch bản|
|**level**|ENUM('A1','A2','B1','B2','C1')|✅||Cấp độ yêu cầu|
|**ai\_role**|VARCHAR(150)|✅||Vai AI đóng (vd: Senior Engineering Manager)|
|**user\_role**|VARCHAR(150)|✅||Vai người dùng (vd: Junior Developer)|
|**goal\_prompt**|TEXT|✅||Mục tiêu buổi học dạng prompt|
|**suggested\_vocab**|JSON|❌||Từ vựng gợi ý cho kịch bản này|
|**order\_index**|SMALLINT DEFAULT 0|✅||Thứ tự trong roadmap|
|**is\_active**|BOOLEAN DEFAULT TRUE|✅||Hiển thị hay ẩn|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||

## **4.2 Bảng roadmap\_steps**
*Sắp xếp các kịch bản theo từng tuần, từng cấp độ. Có điều kiện mở khoá để tạo progression tuyến tính.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**level**|ENUM('A1','A2','B1','B2','C1')|✅||Cấp độ thuộc về|
|**week\_number**|TINYINT UNSIGNED|✅||Tuần thứ mấy trong level|
|**title**|VARCHAR(255)|✅||Tên chủ đề tuần (vd: Workplace Basics)|
|**scenario\_id**|BIGINT UNSIGNED|✅|FK → scenarios.id|Kịch bản liên kết|
|**unlock\_condition**|VARCHAR(255)|❌||Điều kiện mở khoá (vd: complete 80% week1)|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||

## **4.3 Bảng user\_progress**
*Theo dõi tiến độ của từng người dùng trên từng bước roadmap. Dùng để tính % hoàn thành và mở khoá bước tiếp theo.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id||
|**roadmap\_step\_id**|BIGINT UNSIGNED|✅|FK → roadmap\_steps.id||
|**status**|ENUM('locked','in\_progress','completed')|✅||Trạng thái bước roadmap|
|**completed\_at**|TIMESTAMP|❌||Thời gian hoàn thành|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||
|**UNIQUE KEY**|(user\_id, roadmap\_step\_id)|✅||Mỗi user – mỗi bước là duy nhất|


# **5. Nhóm bảng: Phiên hội thoại**
*Lưu metadata các phiên chat (MySQL). Nội dung tin nhắn chi tiết và lịch sử dài hạn lưu ở MongoDB để tối ưu hiệu năng.*
## **5.1 Bảng chat\_sessions**
*Mỗi buổi luyện với AI là một session. Lưu điểm clarity\_score, số tin nhắn, và feedback\_summary dạng JSON.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id||
|**scenario\_id**|BIGINT UNSIGNED|✅|FK → scenarios.id||
|**status**|ENUM('active','completed','abandoned')|✅||Trạng thái phiên|
|**clarity\_score**|TINYINT UNSIGNED|❌||Điểm rõ ràng 0-100|
|**message\_count**|SMALLINT DEFAULT 0|✅||Tổng số tin nhắn|
|**duration\_sec**|INT DEFAULT 0|✅||Thời lượng buổi (giây)|
|**feedback\_summary**|JSON|❌||Tóm tắt feedback: grammar\_errors, vocab\_suggestions, strengths|
|**started\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅||Bắt đầu phiên|
|**ended\_at**|TIMESTAMP|❌||Kết thúc phiên|

## **5.2 Bảng chat\_messages**
*Tin nhắn trong phiên hội thoại — bao gồm cả tin của user và AI. Trường feedback lưu inline grammar/vocab suggestion cho từng tin nhắn của user.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**session\_id**|BIGINT UNSIGNED|✅|FK → chat\_sessions.id||
|**role**|ENUM('user','assistant')|✅||Người gửi|
|**content**|TEXT|✅||Nội dung tin nhắn|
|**feedback**|JSON|❌||Feedback inline: {errors[], suggestions[]}|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||

# **6. Nhóm bảng: Từ vựng thông minh**
*Hệ thống kho từ vựng cá nhân kết hợp Story Fill-In — tính năng độc đáo của EnglishFlow. Flow: user thêm từng từ vào kho → chọn 3-4+ từ tạo thành bộ → bấm Generate → AI tạo story có ô trống → user điền → nhận feedback.*
## **6.1 Bảng vocabulary\_bank**
*Kho từ vựng cá nhân của user. Từ được thêm tự động từ hội thoại (chat/suggestion) hoặc user tự bookmark. Tích hợp SRS 5 cấp độ để lên lịch ôn tập thông minh.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id|Chủ sở hữu từ|
|**word**|VARCHAR(150)|✅||Từ / cụm từ (vd: implement, major challenge)|
|**definition**|TEXT|✅||Định nghĩa tiếng Anh|
|**example**|TEXT|❌||Câu ví dụ từ hội thoại thực tế của user|
|**synonyms**|JSON|❌||Danh sách từ đồng nghĩa: ["execute","apply"]|
|**register**|ENUM('formal','informal','neutral','technical')|❌||Phong cách sử dụng|
|**source**|ENUM('chat','suggestion','bookmark','quiz')|✅||Nguồn thêm từ vào kho|
|**session\_id**|BIGINT UNSIGNED|❌|FK → chat\_sessions.id|Phiên hội thoại tạo ra từ này (nếu có)|
|**srs\_level**|TINYINT DEFAULT 0|✅||Cấp độ SRS: 0=New, 1=Learning, 2=Familiar, 3=Known, 4=Mastered|
|**next\_review**|DATE|❌||Ngày ôn lại tiếp theo (do SRS tính)|
|**review\_count**|SMALLINT DEFAULT 0|✅||Tổng số lần đã ôn|
|**correct\_streak**|TINYINT DEFAULT 0|✅||Chuỗi trả lời đúng liên tiếp hiện tại|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||

## **6.2 Bảng story\_vocab\_selections  ★ Bảng mới**
*Mỗi bộ từ là một nhóm user tạo ra để generate story. User có thể tạo nhiều bộ khác nhau (vd: 'Interview Vocab', 'Hotel Phrases'). Status theo dõi trạng thái từ lúc đang chọn từ đến khi story đã được AI tạo xong.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id|User tạo bộ từ này|
|**name**|VARCHAR(150)|❌||Tên bộ từ do user đặt (vd: 'Interview Vocab Week 2')|
|**status**|ENUM('draft','generating','generated','archived')|✅||draft = đang chọn từ | generating = AI đang tạo | generated = đã có story|
|**word\_count**|TINYINT UNSIGNED DEFAULT 0|✅||Số từ đã thêm vào bộ (cache, tránh COUNT mỗi lần)|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||

## **6.3 Bảng story\_vocab\_items  ★ Bảng mới**
*Quan hệ nhiều-nhiều giữa bộ từ và kho từ vựng. Mỗi record là 1 từ user đã add vào bộ. Khi bộ đủ 3+ từ, user bấm Generate — hệ thống đọc bảng này để lấy danh sách từ gửi cho AI.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**selection\_id**|BIGINT UNSIGNED|✅|FK → story\_vocab\_selections.id|Thuộc bộ từ nào|
|**vocab\_id**|BIGINT UNSIGNED|✅|FK → vocabulary\_bank.id|Từ được thêm vào bộ|
|**added\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅||Thời điểm user thêm từ này vào bộ|
|**UNIQUE KEY**|(selection\_id, vocab\_id)|✅||Mỗi từ chỉ xuất hiện 1 lần trong 1 bộ|

## **6.4 Bảng story\_exercises**
*Story do AI tạo ra từ bộ từ. Cột selection\_id liên kết về bộ từ đã dùng. Cột blanks lưu JSON metadata vị trí và gợi ý từng ô trống. Số ô trống = số từ trong bộ.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id||
|**selection\_id**|BIGINT UNSIGNED|✅|FK → story\_vocab\_selections.id|Bộ từ đã dùng để generate story này|
|**title**|VARCHAR(255)|✅||Tiêu đề câu chuyện (AI tự đặt, vd: The Product Launch)|
|**content**|TEXT|✅||Nội dung câu chuyện đầy đủ (chứa {{vocab\_id}} làm placeholder)|
|**blanks**|JSON|✅||Metadata ô trống: [{"pos":1,"vocab\_id":42,"hint":"v. put into action"}]|
|**total\_blanks**|TINYINT UNSIGNED DEFAULT 0|✅||Tổng số ô trống trong story (= số từ trong bộ)|
|**status**|ENUM('pending','in\_progress','completed')|✅||pending = chưa làm | in\_progress = đang điền | completed = đã nộp|
|**score**|TINYINT UNSIGNED|❌||Điểm sau khi hoàn thành (0-100)|
|**generated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅||Thời gian AI tạo xong story|
|**completed\_at**|TIMESTAMP|❌||Thời gian user nộp bài|

## **6.5 Bảng story\_answers**
*Từng đáp án user điền vào mỗi ô trống. Mỗi ô trống có duy nhất 1 đáp án cuối (UNIQUE KEY trên exercise\_id + blank\_pos). AI tạo feedback riêng cho từng ô giải thích tại sao đúng/sai.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**exercise\_id**|BIGINT UNSIGNED|✅|FK → story\_exercises.id|Bài tập thuộc về|
|**vocab\_id**|BIGINT UNSIGNED|✅|FK → vocabulary\_bank.id|Từ đúng cần điền (đáp án gốc)|
|**blank\_pos**|TINYINT UNSIGNED|✅||Vị trí ô trống trong story (1, 2, 3...)|
|**user\_answer**|VARCHAR(255)|✅||Đáp án user nhập vào|
|**is\_correct**|BOOLEAN|✅||Đúng hay sai so với từ gốc|
|**ai\_feedback**|TEXT|❌||AI giải thích tại sao đúng/sai + gợi ý từ tốt hơn|
|**answered\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**UNIQUE KEY**|(exercise\_id, blank\_pos)|✅||Mỗi ô trống chỉ có 1 đáp án cuối cùng|


# **7. Nhóm bảng: Quiz Game & Gamification**
*Các bảng hỗ trợ tính năng quiz mini-game, streak học hàng ngày, badge thành tích và hệ thống thông báo.*
## **7.1 Bảng quiz\_sessions**
*Ghi lại kết quả mỗi lượt chơi quiz. Hỗ trợ 4 loại: Word Snap, Fix the Chat, Context Challenge, Streak Quiz.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id||
|**quiz\_type**|ENUM('word\_snap','fix\_the\_chat','context\_challenge','streak\_quiz')|✅||Loại mini-game|
|**score**|SMALLINT DEFAULT 0|✅||Điểm đạt được|
|**total\_q**|TINYINT DEFAULT 0|✅||Tổng số câu hỏi|
|**correct\_q**|TINYINT DEFAULT 0|✅||Số câu đúng|
|**lives\_used**|TINYINT DEFAULT 0|✅||Số mạng đã dùng|
|**completed**|BOOLEAN DEFAULT FALSE|✅||Hoàn thành hay chưa|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||
|**ended\_at**|TIMESTAMP|❌|||

## **7.2 Bảng user\_streaks**
*1-1 với users. Theo dõi chuỗi ngày học liên tiếp, được Redis cache để đọc nhanh — MySQL là nguồn sự thật (source of truth).*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id UNIQUE|1-1 với users|
|**current\_streak**|SMALLINT DEFAULT 0|✅||Chuỗi ngày học hiện tại|
|**longest\_streak**|SMALLINT DEFAULT 0|✅||Chuỗi dài nhất mọi thời|
|**last\_activity**|DATE|❌||Ngày học gần nhất|
|**total\_sessions**|INT DEFAULT 0|✅||Tổng số phiên hội thoại đã làm|
|**total\_words**|INT DEFAULT 0|✅||Tổng từ đã thu thập|
|**updated\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|✅|||

## **7.3 Bảng user\_badges**
*Lưu các huy hiệu thành tích người dùng đã đạt được: Grammar Ninja, 30-Day Streak, 100 Words Mastered...*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id||
|**badge\_code**|VARCHAR(100)|✅||Mã badge (vd: grammar\_ninja, streak\_30)|
|**badge\_name**|VARCHAR(150)|✅||Tên hiển thị|
|**earned\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅||Thời điểm đạt được|
|**UNIQUE KEY**|(user\_id, badge\_code)|✅||Mỗi user chỉ có 1 badge mỗi loại|

## **7.4 Bảng notifications**
*Lưu thông báo lịch học hàng ngày, cảnh báo streak sắp gãy, weekly digest. Kết hợp với SSE để push realtime lên frontend.*

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT UNSIGNED AUTO\_INCREMENT|✅|PK||
|**user\_id**|BIGINT UNSIGNED|✅|FK → users.id||
|**type**|ENUM('daily\_reminder','streak\_alert','milestone','weekly\_digest')|✅||Loại thông báo|
|**title**|VARCHAR(255)|✅||Tiêu đề thông báo|
|**body**|TEXT|❌||Nội dung chi tiết|
|**is\_read**|BOOLEAN DEFAULT FALSE|✅||Đã đọc chưa|
|**send\_at**|TIMESTAMP|✅||Thời điểm gửi (có thể schedule)|
|**created\_at**|TIMESTAMP DEFAULT CURRENT\_TIMESTAMP|✅|||

# **8. Tóm tắt quan hệ giữa các bảng**

|**🔐  Auth & RBAC: users → user\_roles → roles → role\_permissions → permissions**|
| :- |

|**👤  Onboarding: users → user\_profiles  (1-1, survey + placement test)**|
| :- |

|**🗺️  Roadmap: scenarios → roadmap\_steps → user\_progress ← users**|
| :- |

|**💬  Chat: users → chat\_sessions → chat\_messages  |  session → vocabulary\_bank**|
| :- |

|**📖  Story: vocabulary\_bank ← story\_vocab\_items → story\_vocab\_selections → story\_exercises → story\_answers**|
| :- |

|**🎮  Game: users → quiz\_sessions  |  users → user\_streaks  |  users → user\_badges**|
| :- |

|**🔔  Notification: users → notifications  (push qua SSE realtime)**|
| :- |

|**📚  Books (RAG): users → books  |  PDF metadata (PostgreSQL) + chunks (MongoDB Phase 2)**|
| :- |

# **9. Nhóm bảng: Admin Books (RAG metadata)**
*Bảng `books` lưu metadata sách PDF do admin upload. File PDF lưu trên **Supabase Storage**; nội dung chunk + embedding lưu MongoDB ở Phase 2.*

## **9.1 Bảng books**

|**Tên trường**|**Kiểu dữ liệu**|**NOT NULL**|**Khóa**|**Mô tả**|
| :-: | :-: | :-: | :-: | :-: |
|**id**|BIGINT AUTO\_INCREMENT|✅|PK|ID sách|
|**title**|VARCHAR(255)|✅||Tiêu đề sách|
|**description**|VARCHAR(2000)|❌||Mô tả ngắn|
|**cefr_level**|ENUM('A1','A2','B1','B2','C1')|❌||Cấp độ CEFR gợi ý (optional)|
|**book\_type**|ENUM('grammar\_textbook','reading\_practice','test\_bank','freeform')|✅||Loại sách — admin chọn khi upload; dùng chọn chiến lược chunk Phase 2|
|**detection\_method**|VARCHAR(50)|❌||Phương pháp detect cấu trúc: `toc`, `font_style`, `regex`, `semantic` — điền ở Phase 2, để trống lúc upload|
|**file\_path**|VARCHAR(500)|✅||URL truy cập file (public URL hoặc signed URL)|
|**file\_public\_id**|VARCHAR(500)|❌||Object path trong Supabase bucket (dùng download/delete)|
|**file\_size**|BIGINT|✅||Kích thước file (bytes)|
|**page\_count**|INT|❌||Số trang (đọc bằng pypdf khi upload)|
|**status**|ENUM('uploaded','needs\_review','processing','ready','failed')|✅||Trạng thái pipeline indexing|
|**chunk\_count**|INT DEFAULT 0|✅||Số chunk đã index (Phase 2 cập nhật)|
|**uploaded\_by**|BIGINT|❌|FK → users.id|Admin upload|
|**created\_at**|TIMESTAMP WITH TIME ZONE|✅||Thời gian tạo|
|**updated\_at**|TIMESTAMP WITH TIME ZONE|✅||Thời gian cập nhật|

### **Ghi chú triển khai Phase 1**
- Upload validate: chỉ `.pdf`, tối đa `MAX_BOOK_UPLOAD_MB` (mặc định 50MB), reject file rỗng/corrupt bằng `pypdf.PdfReader` **trước khi** lưu Supabase Storage.
- `status` mặc định `uploaded` khi upload; **không** trigger indexing tại API upload.
- `detection_method` và `needs_review` chuẩn bị sẵn cho Phase 2.
- DELETE Phase 1: xóa record Postgres + object Supabase Storage; **chưa** xóa Mongo chunks (Phase 2).

### **Migration Alembic liên quan**
- `d7e2a91f4c30` — tạo bảng `books`, permission `book:manage`
- `e5f3c2b8a41d` — thêm `file_public_id` (storage object path)
- `f1a2b3c4d5e6` — thêm `book_type`, `detection_method`, giá trị `needs_review` vào enum `status`

# **10. Phân tầng lưu trữ (cập nhật)**

|**Storage**|**Dữ liệu lưu**|**Lý do**|
| :-: | :-: | :-: |
|**MySQL**|Users, Roles, Scenarios, Roadmap, Progress, Vocab, Streaks, Badges, Notifications, **Books (metadata)**|Dữ liệu có cấu trúc, cần JOIN và transaction ACID|
|**MongoDB**|Chat logs dài hạn, **RAG document chunks (Phase 2)**, Feedback JSON phức tạp|Lưu trữ JSON linh hoạt, scale tốt cho dữ liệu hội thoại lớn|
|**Redis**|JWT blacklist, Streak cache, Vocab due today, Session WebSocket state|Đọc/ghi cực nhanh, TTL tự động, pub/sub cho realtime|

*EnglishFlow · Database Design Document · Final Project*
