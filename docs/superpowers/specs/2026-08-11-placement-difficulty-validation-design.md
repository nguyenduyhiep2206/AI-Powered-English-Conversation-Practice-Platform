# Thiết kế: Placement assemble theo blueprint độ khó (CEFR proxy)

**Ngày:** 2026-08-11  
**Trạng thái:** Implemented (assemble CEFR + PART_BAND_QUOTA) — L2–L4 vẫn ngoài phạm vi  
**Cập nhật:** Chốt hướng **CEFR → band thuần** + **blueprint cố định theo Part** (không dùng strata đều 33/33/33; không bắt buộc đo `% đúng` từ user).  
**Mở rộng:** `docs/superpowers/specs/2026-07-28-toeic-rw-placement-design.md` (giữ full TOEIC R+W)  
**Plan:** `docs/superpowers/plans/2026-08-11-placement-difficulty-validation.md`

---

## 1. Vấn đề

Placement hiện tại assemble **random** trong từng `toeic_part` — không kiểm soát hỗn hợp độ khó. Nếu bank nghiêng A1–A2, đề có thể quá dễ so với hướng TOEIC thật (P5 thường dễ hơn trung bình, P7 khó hơn).

Mục tiêu product hiện tại: **phân bổ đề gần thật nhất có thể trong phạm vi làm được ngay** — không xây equating ETS hay pipeline validate cohort.

---

## 2. Gần đề thật đến đâu?

| Khía cạnh | TOEIC ETS | Hướng này |
|-----------|-----------|-----------|
| Số câu theo Part | Có (30/16/54…) | **Giống** (đã có) |
| Độ khó lệch theo Part | Có (đo bằng thống kê) | **Xấp xỉ** bằng quota band (r5 nhiều easy, r7 nhiều hard) |
| Nhãn easy/mid/hard công bố | Không | Dùng nội bộ; map từ **CEFR** item |
| Equating form | Có | **Không** (ngoài phạm vi) |
| Calibrate item bằng thí sinh | Có | **Không bắt buộc** phase này |

→ Đây là mức **gần nhất hợp lý** cho product khi chưa có data thí sinh / equating: đủ Part + đường cong độ khó theo Part. Không phải bản sao ETS.

---

## 3. Mục tiêu / Ngoài phạm vi

### Mục tiêu (in scope)

1. Gán mỗi item published `easy | mid | hard` từ **CEFR proxy** (không lệch thêm theo part).  
2. Lắp đề theo bảng **`PART_BAND_QUOTA`** cố định (heuristic gần hướng P5 dễ / P7 khó).  
3. Gate start nếu thiếu `(part, band)`.  
4. Giữ scoring / session API hiện tại.

### Ngoài phạm vi (phase này)

- L2: `difficulty_p` / aggregate từ user answers.  
- L3: neo TOEIC/IELTS + report.  
- L4: tune `score_map` từ pilot.  
- Adaptive/CAT/IRT; Listening; equating ETS.  
- Claim “điểm TOEIC chính thức”.

*(L2–L4 có thể mở lại sau nếu cần claim validation chặt hơn.)*

---

## 4. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| Độ dài / timer | Giữ spec 2026-07-28 (R 100 + W 8; 75/58) |
| Band từ CEFR | A1, A2 → easy; B1 → mid; B2, C1 → hard |
| Lệch band theo part | **Không** (không ±1 bậc vì r5/r7) |
| Fallback thiếu CEFR | `difficulty` string `easy\|medium\|hard` → `easy\|mid\|hard`; nếu vẫn thiếu → coi như `mid` |
| Phân bổ form | Lookup `PART_BAND_QUOTA[part]` — **không** chia đều 33% |
| Adaptive lúc làm bài | Không |
| Empirical p-value | Không trong phase này |

### 4.1 `PART_BAND_QUOTA` (heuristic đề xuất)

| Part | Quota | easy / mid / hard |
|------|-------|-------------------|
| r5 | 30 | 15 / 10 / 5 |
| r6 | 16 | 4 / 8 / 4 |
| r7 | 54 | 8 / 19 / 27 |
| w1 | 5 | 3 / 2 / 0 |
| w2 | 2 | 0 / 2 / 0 |
| w3 | 1 | 0 / 0 / 1 |

Tổng mỗi hàng = quota part. Đây **không** phải số ETS công bố — là blueprint nội bộ để form nghiêng giống pattern “P5 dễ hơn / P7 khó hơn”.

Có thể chỉnh bảng sau khi quan sát bank/real use; đổi constants + tests, không đổi kiến trúc.

---

## 5. Pipeline

```text
published pool (toeic_part set)
  → band_for_item từ cefr_level (fallback difficulty string)
  → với mỗi part: sample theo PART_BAND_QUOTA[part]
  → r6/r7 ưu tiên nguyên passage group
  → form_snapshot → session Reading → Writing → complete
  → score_map hiện tại → current_level + placement_score
```

---

## 6. Assemble chi tiết

### 6.1 `band_for_item`

```text
cefr A1|A2 → easy
cefr B1    → mid
cefr B2|C1 → hard
else map difficulty easy/medium/hard → easy/mid/hard
else mid
```

### 6.2 Pick

- **r5, w1–w3:** với mỗi band có `need > 0`, `random.sample` từ bucket `(part, band)`. Thiếu → `BankTooSmallError("Need {need} published {part}/{band}, have {have}")`.
- **r6/r7:** group theo `passage_id`; band group = majority item band (tie → mid). Chọn groups để tổng items ≈ N và gần đủ từng band; dung sai **±1** mỗi band so với target, hoặc fail.

### 6.3 Gate

Không start placement nếu pool không thỏa `PART_BAND_QUOTA` (sau khi xét constraints r6/r7).

---

## 7. API / scoring

- Không đổi paths session.  
- Chỉ đổi bên trong `assemble_form` (+ `_question_to_item` cần `cefr_level`, `difficulty`).  
- `score_map` /Writing grader giữ nguyên.

---

## 8. Claim / messaging

Khi bị hỏi phân bổ đề:

1. Đề đủ Part giống blueprint TOEIC R+W.  
2. Độ khó được kiểm soát theo Part (grammar/incomplete nghiêng dễ hơn; reading dài nghiêng khó hơn) qua nhãn CEFR của item + quota cố định.  
3. Không equating ETS; không claim điểm chính thức.

Tránh: “chuẩn ETS”, “giống hệt đề thi thật từng câu”.

---

## 9. Rủi ro

| Rủi ro | Giảm nhẹ |
|--------|----------|
| Bank thiếu hard ở r7 / easy ở r5 | Gate + publish thêm câu đúng CEFR |
| CEFR gắn sai trên item | Admin QA khi publish |
| r6/r7 conflict group vs band | ±1; fail rõ ràng |
| Heuristic quota chưa tối ưu | Đổi bảng constants sau |

---

## 10. Tiêu chí xong

- [x] `difficulty.py`: `band_for_item` + `PART_BAND_QUOTA`  
- [x] `assembler` strata theo bảng; tests  
- [x] `_question_to_item` expose fields cần thiết  
- [x] Không thêm migration `difficulty_p` / external exam trong phase này  
- [x] Spec/plan đồng bộ

---

## 11. File map (phase này)

**Mới:** `backend/app/services/placement/difficulty.py`, `backend/tests/test_placement_difficulty.py`  
**Sửa:** `assembler.py`, `session_service.py` (`_question_to_item`), `test_placement_assembler.py`  
**Không đụng:** `quiz_questions` schema mới, `profile` external columns, calibration, concordance
