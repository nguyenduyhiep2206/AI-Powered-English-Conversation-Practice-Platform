
**TÀI LIỆU ĐẶC TẢ CHỨC NĂNG**

**EnglishFlow**

*AI-Powered English Learning Platform*



|**Thông tin**|**Nội dung**|
| :-: | :-: |
|Tên dự án|EnglishFlow — AI English Conversation Practice|
|Loại tài liệu|Đặc tả chức năng (Functional Specification)|
|Phiên bản|v1.0|
|Stack|FastAPI · Next.js 15 · MySQL · MongoDB · Redis · LangChain|
|Mục tiêu|Tài liệu tham khảo khi code — tập trung vào flow + API|


# **1. Tổng quan hệ thống**
## **1.1 Mục tiêu sản phẩm**
EnglishFlow là web app luyện hội thoại tiếng Anh text-based với AI Agent theo kịch bản thực tế (phỏng vấn, đặt phòng, giao tiếp công sở...). Điểm khác biệt so với các app trên thị trường:

- Hội thoại AI tự nhiên — AI dùng kỹ thuật recast thay vì ngắt mạch sửa lỗi
- Từ vựng sống — lấy thẳng từ hội thoại thực tế của chính user
- Story Fill-In — AI tạo câu chuyện cá nhân hoá từ bộ từ user chọn
- Roadmap cá nhân — dựa trên survey + placement test, tự điều chỉnh theo progress

## **1.2 Vai trò người dùng**

|**Role**|**Mô tả**|**Quyền chính**|
| :-: | :-: | :-: |
|admin|Quản trị nội dung hệ thống|CRUD scenarios, xem analytics toàn hệ thống|
|learner|Người học tiếng Anh (default)|Chat AI, học từ vựng, làm quiz, xem roadmap cá nhân|

## **1.3 Tech stack & kiến trúc tổng quan**

|**Layer**|**Technology**|**Vai trò**|
| :-: | :-: | :-: |
|Frontend|Next.js 15 (App Router)|UI, SSR/CSR, WebSocket client|
|Backend|FastAPI + Uvicorn|REST API, WebSocket server, JWT auth|
|AI Layer|LangChain + OpenAI|Conversation agent, grammar checker, story generator|
|Primary DB|MySQL + SQLAlchemy|Dữ liệu có cấu trúc (users, progress, vocab...)|
|Document DB|MongoDB + PyMongo|Chat logs dài hạn, RAG chunks|
|Cache|Redis|JWT blacklist, streak cache, vocab due today|
|Realtime|FastAPI WebSocket + SSE|Chat stream, push notifications|
|Infra|Docker Compose + Nginx|Reverse proxy, multi-service orchestration|

## **1.4 User journey tổng quan**

|**📋 Survey & Placement Test  →  🏠 Dashboard  →  💬 Chat Scenario  →  📊 Session Report  →  📖 Vocab Bank  →  📝 Story Fill-In  →  🎮 Quiz  →  🔔 Nhắc nhở hôm sau**|
| :- |


# **2. Module Onboarding — Survey & Placement Test**
## **2.1 Mô tả chức năng**
Người dùng mới bắt buộc hoàn thành onboarding trước khi vào dashboard. Gồm 2 bước: (1) Survey cá nhân, (2) Placement Test 10 câu. Kết quả được lưu vào 

- survey\_done = true trong bảng user\_profiles
- current\_level = A1/A2/B1/B2/C1 dựa theo điểm placement test
- Roadmap và scenario list được generate tự động sau khi hoàn thành

## **2.2 Survey — các trường thu thập**

|**Trường**|**Giá trị**|**Lưu vào**|
| :-: | :-: | :-: |
|Nghề nghiệp|Developer, Marketing, Sinh viên, Kinh doanh, Khác|occupation VARCHAR(100)|
|Mục tiêu học|job\_interview / daily\_conversation / travel / ielts / business|goal ENUM|
|Điểm yếu tự nhận|grammar / vocabulary / confidence / writing|weak\_point ENUM|
|Thời gian mỗi ngày|15 / 30 / 60+ phút|daily\_time\_min SMALLINT|

## **2.3 Placement Test**
10 câu text-based, 3 dạng câu hỏi:

- Chọn từ đúng trong câu (4 options)
- Sửa lỗi ngữ pháp trong câu cho sẵn
- Điền từ vào đoạn văn ngắn

|**Điểm**|**Level**|**Roadmap bắt đầu**|
| :-: | :-: | :-: |
|0 – 3|A1 — Beginner|Greetings & Self-introduction|
|4 – 5|A2 — Elementary|Daily Conversations|
|6 – 7|B1 — Intermediate|Workplace & Job Interview|
|8 – 9|B2 — Upper-Intermediate|Professional Communication|
|10|C1 — Advanced|Advanced Business & Academic|

## **2.4 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|POST[object Object]|/api/v1/onboarding/survey|Lưu kết quả survey|
|POST[object Object]|/api/v1/onboarding/placement|Nộp bài placement test, nhận level|
|GET[object Object]|/api/v1/onboarding/questions|Lấy 10 câu hỏi placement test|
|GET[object Object]|/api/v1/onboarding/status|Kiểm tra user đã survey chưa|

|**📝 Ghi chú** Nếu survey\_done = false, middleware tự redirect về /onboarding. Dùng Redis cache questions list (TTL 24h) để tránh query DB mỗi request.|
| :- |


# **3. Module Dashboard**
## **3.1 Mô tả**
Trang chủ sau khi login. Render SSR từ Next.js. Cá nhân hoá theo user\_profiles và dữ liệu học hàng ngày. Gồm 5 block chính:

|**Block**|**Nội dung**|**Data source**|
| :-: | :-: | :-: |
|Today's Mission|1 scenario AI gợi ý theo roadmap step tiếp theo|roadmap\_steps + user\_progress|
|Streak Counter 🔥|Chuỗi ngày liên tiếp + heatmap 90 ngày|user\_streaks (Redis cache)|
|Vocab Due Today|Số từ cần ôn hôm nay theo SRS|vocabulary\_bank WHERE next\_review <= TODAY|
|Weekly Progress|Line chart clarity score 7 ngày|chat\_sessions.clarity\_score|
|Quick Actions|Nút tắt: Chat / Ôn từ / Quiz|—|

## **3.2 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/dashboard/summary|Trả về toàn bộ data cho dashboard (1 call)|
|GET[object Object]|/api/v1/dashboard/heatmap|Activity data 90 ngày cho heatmap|
|GET[object Object]|/api/v1/dashboard/progress-chart|Clarity score 7 ngày gần nhất|

|**💡 Tip** dashboard/summary nên được Redis cache với key user:{id}:dashboard, TTL 5 phút. Invalidate khi user hoàn thành session hoặc ôn từ.|
| :- |


# **4. Module Chat — AI Conversation**
## **4.1 Luồng chức năng**
1. User chọn scenario (hoặc hệ thống gợi ý từ roadmap)
1. Hiển thị Pre-chat Briefing: context kịch bản, vai AI, vai user, vocab gợi ý
1. Bắt đầu session → tạo record trong chat\_sessions (status = active)
1. Kết nối WebSocket: ws://api/v1/chat/{session\_id}
1. User gõ text → gửi qua WS → AI Agent xử lý → stream token response về
1. Sau mỗi tin nhắn user: AI tạo inline feedback (grammar + vocab), lưu vào chat\_messages.feedback
1. User kết thúc → gọi POST /chat/{session\_id}/end → AI tổng hợp Session Report
1. Report lưu vào chat\_sessions.feedback\_summary, từ mới auto-save vào vocabulary\_bank

## **4.2 Pre-chat Briefing**
Hiển thị trước khi vào chat, thời gian tối đa 30 giây. Bao gồm:

- 📍 Tên scenario và category
- 🎭 Vai của user và vai của AI
- 🎯 Mục tiêu buổi học (goal\_prompt)
- 💡 3-5 từ vựng gợi ý nên dùng trong buổi này

## **4.3 AI Conversation Agent**
### **Kỹ thuật Recast (không ngắt mạch)**
AI không nói "Bạn sai rồi". Thay vào đó, AI tự nhiên dùng lại câu đúng trong reply:

|User:  "I work in this project 3 month"|
| :- |
|AI:    "Oh interesting! So you've been working on this project|
|`        `for 3 months — what was the biggest challenge?"|
||
|→ AI ngầm sửa: "work in" → "working on", "3 month" → "3 months"|
|`  `mà không phá vỡ flow hội thoại.|

### **Hint khi user bí từ**
User gõ "?" → AI trả về 3 cách diễn đạt để chọn, ví dụ:

|User:  "?"|
| :- |
|AI:    "Here are some ways to say it:",|
|`       `"1. I have experience working with..."|
|`       `"2. During my time at [company], I..."|
|`       `"3. One project I'm proud of is..."|

### **Inline Feedback JSON**
Sau mỗi tin nhắn của user, AI tạo feedback lưu vào chat\_messages.feedback:

|{|
| :- |
|`  `"grammar\_errors": [|
|`    `{|
|`      `"original": "I works as developer",|
|`      `"correction": "I work as a developer",|
|`      `"rule": "Subject-verb agreement + missing article"|
|`    `}|
|`  `],|
|`  `"vocab\_suggestions": [|
|`    `{|
|`      `"used": "make the feature",|
|`      `"better": "implement the feature",|
|`      `"context": "technical / formal register"|
|`    `}|
|`  `]|
|}|

## **4.4 WebSocket Protocol**

|**Event (client → server)**|**Payload**|
| :-: | :-: |
|send\_message[object Object]|{"content": "I work as developer for 2 year"}|
|request\_hint[object Object]|{"context": "[last 3 messages]"}|
|end\_session[object Object]|{"session\_id": 42}|

|**Event (server → client)**|**Payload**|
| :-: | :-: |
|token\_stream[object Object]|{"delta": "Oh interesting! So you"}|
|message\_complete[object Object]|{"message\_id": 99, "feedback": {...}}|
|session\_ended[object Object]|{"report\_url": "/sessions/42/report"}|

## **4.5 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/scenarios|Danh sách scenario, filter by level/category|
|GET[object Object]|/api/v1/scenarios/{id}|Chi tiết 1 scenario + suggested\_vocab|
|POST[object Object]|/api/v1/sessions|Tạo chat session mới → trả session\_id|
|WS[object Object]|/api/v1/ws/chat/{session\_id}|WebSocket connection cho realtime chat|
|POST[object Object]|/api/v1/sessions/{id}/end|Kết thúc session, trigger tạo report|
|GET[object Object]|/api/v1/sessions/{id}/report|Lấy Session Report sau khi end|
|GET[object Object]|/api/v1/sessions/history|Lịch sử các phiên chat của user|


# **5. Module Session Report**
## **5.1 Mô tả**
Sau khi kết thúc chat, AI tổng hợp toàn bộ phiên học thành report. Đây là trigger chính để cập nhật streak, vocab bank, và roadmap progress.

## **5.2 Cấu trúc report**

|{|
| :- |
|`  `"clarity\_score":      74,              // 0-100, tổng hợp từ toàn phiên|
|`  `"message\_count":      12,|
|`  `"duration\_sec":       840,|
|`  `"grammar\_errors": [                    // top 3 lỗi phổ biến nhất|
|`    `{ "rule": "Subject-verb agreement", "count": 2,|
|`      `"example": "I works → I work" }|
|`  `],|
|`  `"vocab\_suggestions": [|
|`    `{ "used": "good", "better": "appropriate", "context": "formal" }|
|`  `],|
|`  `"strengths":          ["Câu trả lời logic", "Dùng tốt: scalable"],|
|`  `"new\_words": [                         // auto-save vào vocabulary\_bank|
|`    `{ "word": "implement", "definition": "...", "example": "..." }|
|`  `]|
|}|

## **5.3 Sau-report actions (tự động)**

|**Action**|**Logic**|
| :-: | :-: |
|Lưu feedback\_summary|POST /sessions/{id}/end → lưu JSON vào chat\_sessions.feedback\_summary|
|Auto-save từ mới|Duyệt new\_words, INSERT vào vocabulary\_bank (source='chat'), srs\_level=0|
|Cập nhật streak|Kiểm tra last\_activity trong user\_streaks, nếu khác hôm nay → current\_streak++|
|Cập nhật roadmap|Nếu clarity\_score >= 60 → mark roadmap\_step là completed|
|Unlock step tiếp theo|Kiểm tra unlock\_condition của step kế, nếu đủ → status = in\_progress|
|Sync MongoDB|Lưu full chat log sang MongoDB collection chat\_sessions\_archive (async)|


# **6. Module Vocabulary Bank**
## **6.1 Các nguồn thêm từ**

|**Source**|**Trigger**|**source field**|
| :-: | :-: | :-: |
|Chat auto-save|AI detect từ hay trong hội thoại + session report|'chat'|
|AI suggestion|Vocab suggestion trong inline feedback|'suggestion'|
|User bookmark|User click ⭐ trong chat hoặc story|'bookmark'|
|Quiz|Từ user trả lời sai trong quiz → thêm vào để ôn|'quiz'|

## **6.2 Spaced Repetition System (SRS)**
SRS 5 cấp độ, interval tăng dần:

|**srs\_level**|**Tên**|**Interval ôn lại**|**Điều kiện lên cấp**|
| :-: | :-: | :-: | :-: |
|0|New|Hôm nay|Trả lời đúng lần đầu|
|1|Learning|3 ngày|correct\_streak >= 2|
|2|Familiar|7 ngày|correct\_streak >= 3|
|3|Known|14 ngày|correct\_streak >= 3|
|4|Mastered|30 ngày|Duy trì, không tụt cấp|

|**⚠️ Lưu ý** Nếu trả lời sai: srs\_level giảm 1 (không giảm dưới 0), correct\_streak reset về 0, next\_review = hôm nay.|
| :- |

## **6.3 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/vocab|Danh sách từ trong kho, filter by srs\_level/source|
|GET[object Object]|/api/v1/vocab/due-today|Từ cần ôn hôm nay (next\_review <= TODAY)|
|POST[object Object]|/api/v1/vocab|Thêm từ thủ công vào kho|
|PUT[object Object]|/api/v1/vocab/{id}|Cập nhật definition / example / register|
|DELETE[object Object]|/api/v1/vocab/{id}|Xoá từ khỏi kho|
|POST[object Object]|/api/v1/vocab/{id}/review|Ghi nhận kết quả ôn (correct: true/false) → cập nhật SRS|


# **7. Module Story Fill-In**
## **7.1 Luồng chức năng**
1. User vào trang Vocabulary Bank, chọn 3+ từ muốn luyện
1. Bấm "Tạo bộ từ" → điền tên bộ (optional) → lưu vào story\_vocab\_selections
1. Hệ thống thêm từng từ vào story\_vocab\_items (nhiều-nhiều)
1. Bấm "Generate Story" → gọi POST /api/v1/stories/generate
1. Backend gọi AI (LangChain): truyền danh sách từ + occupation/goal của user
1. AI tạo story ~150 từ, chèn placeholder {{vocab\_id}} vào vị trí các từ cần điền
1. Backend parse story → tạo blanks JSON → lưu vào story\_exercises
1. Frontend render story với các ô input tại vị trí placeholder
1. User điền từng ô → bấm "Nộp bài" → POST /api/v1/stories/{id}/submit
1. AI chấm từng ô, tạo feedback → lưu story\_answers → cập nhật SRS từng từ

## **7.2 AI Story Generation Prompt**
Prompt template gửi cho AI khi generate:

|Write a short story (~150 words) about a {occupation} professional.|
| :- |
|The story must naturally use these words in context:|
|{word\_list}  // ["implement", "collaborate", "scalable"]|
||
|Requirements:|
|- Replace each target word with the placeholder {{word\_id}}|
|- Include a hint in parentheses after each blank: {{42}}(v. put into action)|
|- Make the story realistic for someone with goal: {goal}|
|- Formal register unless goal is daily\_conversation|
||
|Return JSON: { "title": "...", "content": "Sarah had to {{42}}(v. put into action)..." }|

## **7.3 Trạng thái bộ từ (story\_vocab\_selections.status)**

|**Status**|**Ý nghĩa**|
| :-: | :-: |
|draft|User đang chọn từ, chưa generate|
|generating|Đã gọi AI, đang chờ kết quả (show spinner)|
|generated|Story đã tạo xong, user có thể vào làm bài|
|archived|Bộ từ cũ, đã tạo story và hoàn thành|

## **7.4 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/vocab-sets|Danh sách bộ từ của user|
|POST[object Object]|/api/v1/vocab-sets|Tạo bộ từ mới (name, vocab\_ids[])|
|POST[object Object]|/api/v1/vocab-sets/{id}/items|Thêm 1 từ vào bộ|
|DELETE[object Object]|/api/v1/vocab-sets/{id}/items/{vocab\_id}|Xoá 1 từ khỏi bộ|
|POST[object Object]|/api/v1/stories/generate|Generate story từ bộ từ {selection\_id}|
|GET[object Object]|/api/v1/stories|Danh sách story exercises của user|
|GET[object Object]|/api/v1/stories/{id}|Chi tiết story + blanks (chưa có đáp án)|
|POST[object Object]|/api/v1/stories/{id}/submit|Nộp tất cả đáp án, nhận feedback + score|
|GET[object Object]|/api/v1/stories/{id}/result|Kết quả sau khi nộp|

|**💡 Tip** Generate story là async job. Sau khi gọi POST /generate, status chuyển sang 'generating' và push SSE event 'story\_ready' khi AI xong. Frontend lắng nghe SSE để auto-refresh.|
| :- |


# **8. Module Quiz Game**
## **8.1 Các loại quiz**

|**Quiz Type**|**Mô tả**|**Số câu / Thời gian**|
| :-: | :-: | :-: |
|Word Snap|Ghép từ với nghĩa, càng nhanh càng nhiều điểm|10 cặp / 60 giây|
|Fix the Chat|Cho đoạn hội thoại 3-4 lỗi, tìm và sửa|1 đoạn / không giới hạn|
|Context Challenge|Chọn từ đúng theo ngữ cảnh formal/informal|10 câu / không giới hạn|
|Streak Quiz|5 câu mỗi ngày, trả lời đúng hết giữ streak|5 câu / không giới hạn|

## **8.2 Cơ chế Lives (Streak Quiz)**
- Mỗi ngày có tối đa 3 lives
- Sai 1 câu → mất 1 life
- Hết 3 lives mà chưa đủ 5 câu đúng → streak quiz fail (streak không gãy, chỉ không +1)
- Lives được reset lúc 00:00 mỗi ngày (Redis TTL)

## **8.3 Câu hỏi Fix the Chat — ví dụ**

|Đoạn hội thoại:|
| :- |
|"Yesterday I goes to interview. The manager were very nice.|
|` `I think I did good in the technical test."|
||
|Tìm và sửa 3 lỗi:|
|`  `1. "goes" → "went"         (past tense)|
|`  `2. "were" → "was"          (subject-verb agreement)|
|`  `3. "did good" → "did well" (adverb vs adjective)|

## **8.4 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|POST[object Object]|/api/v1/quiz/start|Bắt đầu quiz session {quiz\_type}|
|GET[object Object]|/api/v1/quiz/{session\_id}/questions|Lấy câu hỏi cho quiz session|
|POST[object Object]|/api/v1/quiz/{session\_id}/answer|Nộp đáp án 1 câu|
|POST[object Object]|/api/v1/quiz/{session\_id}/finish|Kết thúc quiz, nhận tổng kết|
|GET[object Object]|/api/v1/quiz/lives|Số lives còn lại hôm nay (từ Redis)|


# **9. Module Roadmap & Progress**
## **9.1 Cấu trúc roadmap**
Mỗi level CEFR gồm nhiều tuần, mỗi tuần gắn với 1 scenario chính:

|Level B1 — Intermediate|
| :- |
|├── Week 1: Workplace Basics|
|│   ├── scenario: "Introducing yourself at a new job"|
|│   └── unlock\_condition: null  (luôn mở khi vào B1)|
|├── Week 2: Describing Your Work|
|│   ├── scenario: "Explaining your role to a client"|
|│   └── unlock\_condition: "complete\_week\_1\_80pct"|
|├── Week 3: Job Interview|
|│   └── unlock\_condition: "complete\_week\_2\_80pct"|
|...|
|Unlock B2: complete 80% of B1 weeks|

## **9.2 Điều kiện mở khoá**

|**unlock\_condition value**|**Logic kiểm tra**|
| :-: | :-: |
|null|Luôn mở (bước đầu tiên của level)|
|complete\_week\_N\_80pct|user\_progress của week N = completed|
|clarity\_avg\_60|Average clarity\_score 3 sessions gần nhất >= 60|
|vocab\_mastered\_20|Số từ srs\_level=4 (Mastered) >= 20|

## **9.3 AI điều chỉnh roadmap động**
- clarity\_score < 50 liên tục 3 session → chèn thêm bước "Review & Practice" cùng topic
- clarity\_score > 85 và complete nhanh → gợi ý skip ahead (user chọn có/không)
- Hay sai grammar → tự động chèn quiz type Fix the Chat trước step tiếp theo

## **9.4 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/roadmap|Roadmap đầy đủ của user (có status từng step)|
|GET[object Object]|/api/v1/roadmap/next|Step tiếp theo user nên làm|
|GET[object Object]|/api/v1/progress|Tổng tiến độ: % hoàn thành từng level|


# **10. Module Gamification — Streak, Badge, Notification**
## **10.1 Streak**

|**Sự kiện**|**Hành động**|
| :-: | :-: |
|Hoàn thành ≥1 chat session trong ngày|current\_streak + 1, last\_activity = TODAY|
|Không học ngày hôm qua|current\_streak reset về 0|
|current\_streak > longest\_streak|Cập nhật longest\_streak|
|Streak >= 7, 30, 100 ngày|Tự động tặng badge tương ứng|

|**📝 Ghi chú** Streak được cache trong Redis (key: streak:{user\_id}) để đọc nhanh trên dashboard. MySQL là source of truth, sync mỗi khi có update.|
| :- |

## **10.2 Danh sách Badge**

|**badge\_code**|**Tên hiển thị**|**Điều kiện**|
| :-: | :-: | :-: |
|first\_chat|First Step 🎉|Hoàn thành chat session đầu tiên|
|streak\_7|Week Warrior 🔥|Streak 7 ngày liên tiếp|
|streak\_30|Monthly Legend 💎|Streak 30 ngày liên tiếp|
|vocab\_50|Word Collector 📚|Thu thập 50 từ trong kho|
|vocab\_100|Vocabulary Master 🏆|100 từ đạt Mastered (srs\_level=4)|
|grammar\_ninja|Grammar Ninja ⚔️|Clarity score >= 85 trong 3 session liên tiếp|
|story\_5|Storyteller 📖|Hoàn thành 5 Story Fill-In|
|level\_up|Level Up! ⬆️|Unlock level CEFR mới|

## **10.3 Notification**

|**type**|**Trigger**|**Kênh**|
| :-: | :-: | :-: |
|daily\_reminder|Cron job theo giờ user cài trong settings|SSE + Email|
|streak\_alert|current\_streak > 0 và chưa học hôm nay (9PM)|SSE push|
|milestone|Đạt badge mới hoặc unlock level|SSE push (realtime)|
|weekly\_digest|Mỗi tối Chủ Nhật|Email|

|**💡 Tip** SSE endpoint: GET /api/v1/notifications/stream — client giữ kết nối, server push event khi có notification mới.|
| :- |

## **10.4 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/streak|Thông tin streak hiện tại|
|GET[object Object]|/api/v1/badges|Danh sách badge user đã đạt|
|GET[object Object]|/api/v1/notifications|Danh sách notification (phân trang)|
|PUT[object Object]|/api/v1/notifications/{id}/read|Đánh dấu đã đọc|
|GET[object Object]|/api/v1/notifications/stream|SSE endpoint — realtime push|


# **11. Module Auth & Phân quyền**
## **11.1 Luồng xác thực**
1. User đăng ký / đăng nhập → nhận access\_token (JWT, 15 phút) + refresh\_token (7 ngày)
1. Mọi request gửi kèm: Authorization: Bearer {access\_token}
1. Khi access\_token hết hạn → POST /auth/refresh với refresh\_token → nhận access\_token mới
1. Logout → jti của refresh\_token bị blacklist trong Redis (key: blacklist:{jti}, TTL = thời gian còn lại)

## **11.2 RBAC — Phân quyền theo role**

|**Permission code**|**Ai có**|**Endpoint áp dụng**|
| :-: | :-: | :-: |
|scenario:view|learner, admin|GET /scenarios, GET /scenarios/{id}|
|scenario:create|admin|POST /scenarios|
|scenario:edit|admin|PUT /scenarios/{id}|
|chat:start|learner, admin|POST /sessions, WS /ws/chat/{id}|
|vocab:manage|learner (own), admin|CRUD /vocab/\*|
|report:view\_all|admin|GET /admin/reports/\*|
|book:manage|admin|CRUD /admin/books/\*|

## **11.3 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|POST[object Object]|/api/v1/auth/register|Đăng ký: {username, email, password}|
|POST[object Object]|/api/v1/auth/login|Đăng nhập → trả access + refresh token|
|POST[object Object]|/api/v1/auth/refresh|Làm mới access\_token|
|POST[object Object]|/api/v1/auth/logout|Thu hồi refresh\_token (blacklist jti)|
|GET[object Object]|/api/v1/auth/me|Thông tin user hiện tại|


# **16. Module Admin Books (RAG — Phase 1)**
## **16.1 Mô tả chức năng**
Admin upload sách PDF để chuẩn bị nguồn dữ liệu RAG. Phase 1 chỉ quản lý metadata + lưu file; indexing/chunking là Phase 2.

## **16.2 Luồng upload**
1. Admin gửi `multipart/form-data`: `file` (PDF), `title`, `book_type` (bắt buộc), `description` và `cefr_level` (optional)
1. Backend validate: extension `.pdf`, content-type PDF, size ≤ 50MB, `pypdf.PdfReader` mở thử — reject nếu corrupt
1. Upload file lên **Supabase Storage** bucket `books` (private mặc định; backend dùng service role key)
1. Tạo record PostgreSQL: `status=uploaded`, `chunk_count=0`, `detection_method=null`
1. **Không** trigger indexing tại API này

## **16.3 book\_type — chọn chiến lược chunk (Phase 2)**

|**Giá trị**|**Mô tả**|
| :-: | :-: |
|grammar\_textbook|Sách ngữ pháp — chunk theo mục/bài|
|reading\_practice|Sách đọc hiểu — chunk theo đoạn văn|
|test\_bank|Ngân hàng đề — chunk theo câu hỏi/section|
|freeform|Tài liệu tự do — chunk semantic/generic|

## **16.4 Trạng thái status**

|**Status**|**Ý nghĩa**|
| :-: | :-: |
|uploaded|Vừa upload, chưa index|
|needs\_review|Cần admin review cấu trúc trước khi index (Phase 2)|
|processing|Đang chunk + embed|
|ready|Sẵn sàng cho RAG|
|failed|Indexing thất bại|

## **16.5 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|POST|/api/v1/admin/books/upload|Upload PDF + metadata (`book_type` bắt buộc)|
|GET|/api/v1/admin/books|Danh sách sách|
|GET|/api/v1/admin/books/{id}|Chi tiết sách|
|DELETE|/api/v1/admin/books/{id}|Xóa Supabase Storage object + record Postgres (Mongo chunks: Phase 2)|

Permission: `book:manage` (pattern `require_permission` giống các route admin khác).

### **Ví dụ curl**

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your_password"}' \
  | jq -r '.access_token')

# Upload
curl -s -X POST http://localhost:8001/api/v1/admin/books/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./book.pdf" \
  -F "title=Grammar A2" \
  -F "book_type=grammar_textbook" \
  -F "cefr_level=A2"

# List / Detail / Delete
curl -s http://localhost:8001/api/v1/admin/books -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8001/api/v1/admin/books/1 -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE http://localhost:8001/api/v1/admin/books/1 -H "Authorization: Bearer $TOKEN"
```

## **16.6 Frontend**
- Route: `/admin/books`
- Form upload có chọn `book_type`, hiển thị status badge kèm `needs_review`

# **12. Module Profile & Analytics**
## **12.1 Nội dung trang Profile**

|**Thành phần**|**Dữ liệu**|**Kỹ thuật render**|
| :-: | :-: | :-: |
|Avatar + tên + level|users + user\_profiles|SSR|
|Clarity score chart|chat\_sessions 30 ngày|CSR (Recharts)|
|Activity heatmap 90 ngày|chat\_sessions grouped by date|CSR|
|Vocab stats|COUNT by srs\_level|SSR|
|Badge collection|user\_badges JOIN badge\_meta|SSR|
|Session history|chat\_sessions (phân trang)|CSR + Infinite scroll|

## **12.2 API Endpoints**

|**Method**|**Endpoint**|**Mô tả**|
| :-: | :-: | :-: |
|GET[object Object]|/api/v1/profile|Thông tin profile đầy đủ|
|PUT[object Object]|/api/v1/profile|Cập nhật full\_name, avatar\_url, daily\_time\_min|
|GET[object Object]|/api/v1/profile/analytics|Clarity chart + vocab stats tổng hợp|
|GET[object Object]|/api/v1/profile/sessions|Lịch sử session (page, limit, filter)|


# **13. Redis Cache Strategy**

|**Key pattern**|**TTL**|**Dữ liệu**|
| :-: | :-: | :-: |
|user:{id}:dashboard|5 phút|Dashboard summary response|
|user:{id}:streak|Until 00:00|Streak hiện tại (sync từ MySQL)|
|user:{id}:vocab-due|1 giờ|Danh sách vocab\_id due today|
|user:{id}:lives|Until 00:00|Số quiz lives còn lại hôm nay|
|blacklist:{jti}|= JWT exp|Token đã bị thu hồi|
|onboarding:questions|24 giờ|Danh sách câu hỏi placement test|
|scenario:list:{level}|1 giờ|Danh sách scenario theo level|
|notif:{user\_id}:pending|30 giây|SSE notification queue|

|**⚠️ Lưu ý** Invalidation rule: khi user hoàn thành session → xoá dashboard cache và streak cache của user đó.|
| :- |


# **14. Error Handling & Response Format**
## **14.1 Response format chuẩn**

|// Success|
| :- |
|{|
|`  `"success": true,|
|`  `"data": { ... },|
|`  `"message": "Session ended successfully"|
|}|
||
|// Error|
|{|
|`  `"success": false,|
|`  `"error": {|
|`    `"code":    "VOCAB\_NOT\_FOUND",|
|`    `"message": "Vocabulary item with id 99 not found",|
|`    `"detail":  null|
|`  `}|
|}|

## **14.2 HTTP Status codes**

|**Code**|**Tên**|**Dùng khi**|
| :-: | :-: | :-: |
|200|OK|Request thành công, có data trả về|
|201|Created|Tạo mới resource thành công|
|400|Bad Request|Validation lỗi, thiếu field bắt buộc|
|401|Unauthorized|Thiếu hoặc sai JWT token|
|403|Forbidden|Có token nhưng không đủ quyền|
|404|Not Found|Resource không tồn tại|
|409|Conflict|Duplicate (email đã tồn tại, từ đã trong bộ...)|
|422|Unprocessable|Pydantic validation error từ FastAPI|
|500|Server Error|Lỗi server / AI API timeout|


# **15. Danh sách trang Frontend (Next.js 15)**

|**Route**|**Tên trang**|**Render**|**Kỹ thuật đặc biệt**|
| :-: | :-: | :-: | :-: |
|/onboarding|Survey + Test|CSR|Multi-step form, progress bar|
|/dashboard|Dashboard|SSR|Skeleton loading, streak heatmap|
|/scenarios|Danh sách kịch bản|CSR|Filter by level/category|
|/scenarios/[id]|Briefing + vào chat|SSR|Prefetch scenario data|
|/chat/[sessionId]|Chat Interface|CSR|WebSocket, stream tokens, inline feedback|
|/sessions/[id]/report|Session Report|SSR|Biểu đồ, từ mới, nút luyện lại|
|/vocab|Vocabulary Bank|CSR|Virtual scroll (danh sách lớn), SRS filter|
|/vocab/sets|Quản lý bộ từ|CSR|Drag-to-add, status badge|
|/stories|Danh sách Story|CSR|Filter by status|
|/stories/[id]|Story Fill-In|CSR|Interactive fill-in UI, timer|
|/quiz|Chọn loại Quiz|CSR|—|
|/quiz/[type]|Chơi Quiz|CSR|Countdown timer (Word Snap)|
|/roadmap|Roadmap cá nhân|SSR|Timeline UI, lock/unlock visual|
|/profile|Profile & Analytics|SSR + CSR|Recharts, infinite scroll history|
|/settings|Cài đặt|CSR|Notification time, timezone|
|/admin/books|Quản lý sách PDF (admin)|CSR|Upload PDF, chọn book\_type, theo dõi status|

*EnglishFlow · Functional Specification v1.0 · Tài liệu tham khảo nội bộ*
