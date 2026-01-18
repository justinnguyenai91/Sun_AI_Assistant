# Chatbox Request Catalog (VI + EN) — v1 (Plan / Actual / Defect)

This document is a **review list** of realistic user requests your chatbox should handle, based on the currently-configured ontology + templates:

- Plan (Production Order plan): `/productionOrder/search`
- Actual result details (Final output): `/production-result/details/search`
- Defect details: `/process-defect/search-v2`

The three objects are linked by **Production Order** (PO). In practice you have two “production data surfaces”:

1) **PO summary surface** (plan + actual + defect + tact/status): templates `prod.stat.*` (returns fields like `totalPlanQty`, `totalActualQty`, `totalDefectQty`, `avgTactTime`, ...)
2) **Result-details surface** (actual qty only): templates `kpi.actual_qty.daily*` / `prod.result.actual.*` (returns `actual_production_qty` grouped by date/shift, with higher time buckets derived)
3) **Quality surface** (defect count): templates `quality.process_defect.*` (returns `defect_count` grouped by date/shift, with higher time buckets derived)

## Legend

---

# Chatbox Request Catalog (VI + EN) — v1 Review (Plan / Actual / Defect / KPI)

Mục tiêu của tài liệu này: liệt kê **đầy đủ các kịch bản user có thể hỏi** (VI + EN), bao gồm:

- Tổ hợp **đối tượng**: Plan / Actual / Defect (và các KPI tính toán từ chúng)
- Tổ hợp **dimension + filter (WHERE)**: line, model, shift, process, status, PO...
- Tổ hợp **thời gian**: ngày / tháng / range + (tuần / quý / năm — theo guideline)
- Các nhóm câu hỏi quản lý: compare / ranking / exception-alert

Tài liệu này bám theo cấu hình hiện tại trong `ontology.yaml` + `templates.yaml` (không overpromise). Những gì chưa support sẽ được đánh dấu rõ.

## 0) Data surfaces (đang có) & giới hạn quan trọng

1) **PO summary surface** (`/productionOrder/search`)
  - Templates: `prod.stat.*`, `prod.plan.daily`, `prod.query.raw`
  - Có thể aggregate tốt theo: `line`, `model`, `processType`, `prodStatus`, (month+line+status…)
  - Dùng cho: Plan + Actual + Defect + tact/status theo PO summary

2) **Actual result-details surface** (`/production-result/details/search`)
  - Templates: `kpi.actual_qty.daily`, `kpi.actual_qty.daily_shift` (+ base `prod.result.actual.*`)
  - Group-by chính: `date` hoặc `date+shift` (tuần/quý/năm là derived bucket từ date)
  - Có filter vendor hỗ trợ nhiều key (linePks/processPks/modelCode...), nhưng hiện **catalog sẽ coi “group-by line/model/process” là không chắc chắn** trên surface này.

3) **Quality / defect surface** (`/process-defect/search-v2`)
  - Templates: `quality.process_defect.daily`, `quality.process_defect.daily_shift`
  - Group-by hiện tại: `date` hoặc `date+shift` (tuần/quý/năm là derived bucket từ date)
  - Có filter vendor: `linePks`, `processPks`, ...
  - Chưa có template “defect symptom / defect type” (Pareto/detail)

## Legend (Support level)

- ✅ Supported now (đã có template + routing ổn)
- ⚠️ Partially supported (có thể chạy nhưng có constraint / experimental)
- ❌ Not supported yet (cần thêm template/ontology/routing)

Theo guideline: v1 **official**: Day / Month / Range. Week + Quarter: **experimental** (⚠️) cho tới khi chốt chuẩn.

## 1) “WHERE” patterns — tổ hợp dimension & filter trong câu hỏi

Mục tiêu phần này: mô tả các cụm từ user hay dùng để “lọc” dữ liệu.

### 1.1 Filter theo Line

VI:
- “line A”, “dây chuyền A”, “theo line A”, “ở line A”, “của line A”
EN:
- “for line A”, “by line A”, “line A only”

### 1.2 Filter theo Model

VI:
- “model XYZ”, “mã hàng XYZ”, “theo model XYZ”
EN:
- “for model XYZ”, “by model”

### 1.3 Filter theo Shift

VI:
- “theo ca”, “ca 1/2/3”, “shift A/B/C”
EN:
- “by shift”, “shift 1”

### 1.4 Filter theo Process / công đoạn

VI:
- “theo công đoạn”, “process welding”, “ở công đoạn lắp ráp”
EN:
- “by process”, “for process welding”

### 1.5 Filter theo Status (PO status)

VI:
- “theo trạng thái”, “đang chạy/đã hoàn thành/đang chờ…”
EN:
- “by status”, “running/closed/pending…”

### 1.6 Filter theo Production Order (PO)

VI:
- “PO12345”, “lệnh PO12345”, “theo PO …”
EN:
- “PO12345 details”, “for PO PO12345”

### 1.7 Tổ hợp filter (ví dụ user yêu cầu cùng lúc line+model+shift)

VI:
- “Sản lượng thực tế theo ca **của line A** **model X** từ 2026-01-01 đến 2026-01-15”
- “Số lỗi theo ngày **line A** **công đoạn hàn** tháng 1/2026”
EN:
- “Actual by shift for **line A**, **model X**, from 2026-01-01 to 2026-01-15”
- “Defect count by day for **line A**, **process welding**, for Jan 2026”

## 2) Timeframes — ngày / tháng / range + tuần / quý / năm

### 2.1 Supported (official v1)

- Single day: `2026-01-15`
- Date range: `2026-01-01 ~ 2026-01-15`
- Single month: `01/2026` hoặc `2026-01`
- Month range (cross-year): `10/2025 ~ 01/2026` ✅

### 2.2 Experimental (đưa vào catalog + test sau khi chốt)

**Week** (ISO week) ⚠️
- Format canonical: `2026-W01`, `2026-W06`
- Range: `2026-W01 ~ 2026-W06`
VI examples:
- “Tuần 1 đến tuần 6 của năm 2026”
- “So sánh tuần này và tuần trước” ❌ (relative week chưa chốt)
EN examples:
- “From 2026-W01 to 2026-W06”

**Quarter** ⚠️
- “Q1/2026”, “2026-Q1”, “quý 1 năm 2026”
- Range: “Q4/2025 đến Q1/2026”

**Year** ⚠️
- “năm 2025”, “year 2025”
- Range: “2024 đến 2026”

### 2.3 Explicit reject tests (để tránh false-fail)

Theo guideline: “today / yesterday / this week / last week” hiện **chưa support chính thức**.

VI:
- “Hiện hệ thống chưa hỗ trợ truy vấn hôm nay/hôm qua/tuần này. Vui lòng nhập ngày cụ thể (YYYY-MM-DD) hoặc khoảng ngày.”
EN:
- “Today/this week is not supported yet. Please provide an explicit date or date range.”

---

# A) Plan (Kế hoạch) — PO summary surface

## A1. Plan quantity theo ngày/tháng/range (có filter WHERE)

- Objects/API: Plan (PO summary)
- Time: Day / Month / Range ✅ (Week/Quarter/Year ⚠️)
- WHERE filters: factory, line, model, process, status, poType ✅
- Support: ✅

VI examples (có tổ hợp filter)
- “Kế hoạch theo ngày từ 2026-01-01 đến 2026-01-15 **line A**”
- “Kế hoạch tháng 1/2026 **model X** **công đoạn hàn**”
- “Kế hoạch theo tháng từ 10/2025 đến 01/2026 **line A** **trạng thái running**”

EN examples
- “Plan qty by day from 2026-01-01 to 2026-01-15 for line A”
- “Planned quantity for Jan 2026 for model X”

Expected columns (typical)
- `date`/`month` (+ optional dimension columns)
- `plan_qty` hoặc `totalPlanQty`

## A2. PO status distribution (theo line/model/process)

- Objects/API: Plan (PO summary)
- Time: Range / Month ✅
- Support: ✅

VI
- “Thống kê số PO theo trạng thái tháng 1/2026 theo line”
- “Tình trạng PO theo công đoạn từ 2026-01-01 đến 2026-01-15”

EN
- “Count POs by status by line for Jan 2026”

---

# B) Actual (Kết quả sản xuất)

## B1. Actual final output theo ngày/ca (result-details surface)

- Objects/API: Actual (result details)
- Time: Day / Shift / Range ✅ (Month derived ✅)
- WHERE filters: line/process/model (as filters) ⚠️, poNo ✅, finalYn/reflect defaults ✅
- Support: ✅ cho date/shift; ⚠️ cho filter phức tạp (tuỳ vendor trả field ổn định)

VI
- “Sản lượng thực tế theo ngày từ 2026-01-01 đến 2026-01-15”
- “Sản lượng thực tế theo ca tháng 1/2026”
- “Sản lượng thực tế theo ca từ 2026-01-01 đến 2026-01-15 **line A** **model X**” ⚠️

EN
- “Actual output by shift for Jan 2026”

Expected columns
- `date`/`shift` (+ derived `month/week/quarter/year` nếu cần)
- `actual_production_qty`

## B2. Actual theo line/model/process (PO summary surface)

- Objects/API: Actual (PO summary)
- Time: Month / Range ✅
- GROUP BY: `line`, `model`, `processType`, `prodStatus` ✅
- Support: ✅

VI (tổ hợp line+model)
- “Sản lượng thực tế theo line từ 2026-01-01 đến 2026-01-15”
- “Sản lượng theo line và model tháng 1/2026”
- “Sản lượng theo công đoạn tháng 1/2026 **line A**”

EN
- “Actual qty by line and model for Jan 2026”

---

# C) Defect / Quality (Thông tin lỗi)

## C1. Defect count (NG quantity) theo ngày/ca + WHERE filters

- Objects/API: Quality (process defect v2)
- Time: Day / Shift / Range ✅ (Month derived ✅)
- WHERE filters: line/process ✅
- Support: ✅

VI
- “Số lượng NG theo ngày từ 2026-01-01 đến 2026-01-15”
- “NG theo ca tháng 1/2026”
- “NG theo ngày tháng 1/2026 **line A** **công đoạn hàn**”

EN
- “Reject quantity (NG) by day from 2026-01-01 to 2026-01-15”
- “NG quantity by shift for Jan 2026”

Expected columns
- `date`/`shift`/`month`
- `defect_count` (aka reject_qty)

## C2. Defect detail / symptom / defect type (Pareto)

Theo guideline: API defect có thể trả chi tiết (symptom/type), nhưng hiện `templates.yaml` **chưa có template** group-by symptom/type.

- Objects/API: Quality (process defect v2)
- Time: Month / Range
- GROUP BY: `symptom` / `defectType` / `defectCode` / `reason` (tuỳ vendor)
- Support: ❌ (needs new template + dimension_fields)

VI examples
- “Top 5 loại lỗi nhiều nhất tháng 1/2026”
- “Pareto lỗi tháng 1/2026 theo line A”
- “Chi tiết symptom lỗi từ 2026-01-01 đến 2026-01-15”

EN examples
- “Top defect types for Jan 2026”
- “Pareto defects by symptom for line A in Jan 2026”

---

# D) Manufacturing performance KPIs (Computed layer)

Các KPI nhóm này không cần API mới, nhưng cần **computed template** cung cấp metric + post-processing layer.

## D1. Plan achievement rate (% đạt kế hoạch)

- Formula: `achievement_rate = totalActualQty / totalPlanQty * 100`
- Objects: Plan + Actual (PO summary)
- Time: Day / Month / Range
- Support: ❌ (ontology có `plan_attainment_percent` nhưng chưa có template `provides`/routing cho metric-only)

VI
- “Tỷ lệ đạt kế hoạch tháng 1/2026”
- “Line A đạt bao nhiêu % kế hoạch từ 2026-01-01 đến 2026-01-15”

EN
- “Plan achievement rate for Jan 2026”
- “Achievement % by line from 2026-01-01 to 2026-01-15”

Constraint
- Nếu `totalPlanQty = 0` -> warning “No plan data”

## D2. Yield / Good rate (% đạt sau lỗi)

- Formula: `good_qty = totalActualQty - totalDefectQty`, `yield_rate = good_qty / totalActualQty * 100`
- Objects: Actual + Defect (PO summary)
- Support: ❌ (chưa có metric + template)

VI
- “Tỷ lệ đạt chất lượng tháng 1/2026”
- “Yield theo ngày từ 2026-01-01 đến 2026-01-15”

EN
- “Yield rate by day”

## D3. Defect rate (%) (khác PPM)

- Formula: `defect_rate = totalDefectQty / totalActualQty * 100`
- Objects: Actual + Defect (PO summary)
- Support: ❌ (ontology có `defect_percent` nhưng chưa có template `provides`/routing cho metric-only)

VI
- “Tỷ lệ lỗi (%) tháng 1/2026”
EN
- “Defect percentage by day”

## D4. Defect PPM

- Objects: Actual + Defect (computed)
- Support: ✅ (templates `kpi.defect_ppm.daily*`)

VI
- “PPM lỗi theo ngày từ 2026-01-01 đến 2026-01-15”

---

# E) Trend / Comparison / Ranking / Exception (quản lý hay hỏi)

## E1. Compare 2 kỳ (Jan vs Dec, this month vs last month)

- Support: ❌ (cần dual-period query + diff compute)

VI
- “So sánh sản lượng tháng 12/2025 và tháng 1/2026”
- “Tuần này so với tuần trước” ❌

EN
- “Compare actual output Jan vs Dec”

## E2. Top/Bottom ranking

- Support: ❌ (cần sorting + limit layer + rule chọn dimension)

VI
- “Top 5 line sản xuất nhiều nhất tháng 1/2026”
- “Line nào lỗi nhiều nhất?”

EN
- “Top 5 lines by output for Jan 2026”

## E3. Exception / Alert (condition-based)

- Support: ❌ (cần condition filtering layer)

VI
- “Line nào không đạt kế hoạch hôm nay?” ❌
- “PO nào có defect vượt 3% tháng 1/2026?”

EN
- “Which lines did not meet plan today?” ❌

---

# F) Conversation-flow & robustness (đề xuất bổ sung coverage)

Các case này giúp tránh fail do thiếu context hoặc input “lai”.

## F1. Clarification flow (ASK_FACTORY)

VI
- User: “Thống kê sản lượng tháng 1/2026”
- Expected: hỏi nhà máy

## F2. Multi-turn context

VI
- User: “Thống kê sản lượng tháng 1/2026”
- Bot: “Nhà máy nào?”
- User: “FAC01”
- Expected: reuse intent trước đó

## F3. Mixed language robustness

VI/EN mix
- “Actual tháng 1 line A”

## F4. Invalid dimension

VI
- “Actual theo công nhân” -> trả message “chưa hỗ trợ dimension công nhân”

---

# What I need from you (duyệt v1)

Bạn giúp mình confirm 3 điểm để chốt scope trước khi chuyển thành YAML test cases:

1) Week/Quarter/Year: v1 để **⚠️ experimental** hay **❌ loại khỏi v1**?
2) Defect symptom/type (Pareto): đưa vào v1 dưới dạng **❌ (planned)** hay muốn mình implement template trước?
3) KPI computed (achievement/yield/defect rate): đưa vào v1 dưới dạng **❌ (planned)** hay muốn mình ưu tiên implement ngay (High priority)?
