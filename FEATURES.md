# ✨ Sun MES AI Assistant - Feature Highlights

## 🎯 What Makes This Smart?

### 1. **Auto-Computed Metrics** 📊
The system automatically calculates important KPIs without you asking:

**Example Query:**
```
"Báo cáo sản xuất FAC01 tháng 1/2026"
```

**You Get (automatically):**
- ✅ `achievementRate`: 95.5%
- ✅ `defectRate`: 2.3%
- ✅ `yieldRate`: 97.7%
- ✅ `efficiency`: 95.5%
- ✅ `oee`: 93.2%

**No need to ask separately!**

---

### 2. **Context Memory** 🧠
The AI remembers your conversation:

**Conversation Flow:**
```
You: "Báo cáo sản xuất FAC01 tháng 1/2026"
AI: [Shows FAC01 data for January 2026]

You: "Còn tháng 12 thì sao?"
AI: [Remembers FAC01, shows December data]

You: "So với DJVN1?"
AI: [Compares FAC01 vs DJVN1 for December]
```

**What it remembers:**
- Factory code (FAC01, DJVN1)
- Time range (last query dates)
- Metrics you care about
- Line/model filters

---

### 3. **Proactive Insights** 💡
The AI analyzes data and tells you what matters:

**Query:**
```
"Phân tích hiệu suất các line tháng 1/2026"
```

**Insights You Get:**
```json
{
  "insights": [
    {
      "type": "trend",
      "message": "Tỷ lệ đạt kế hoạch đang cải thiện",
      "sentiment": "positive"
    },
    {
      "type": "ranking",
      "message": "Top performers: Line A, Line B",
      "sentiment": "positive"
    },
    {
      "type": "anomaly",
      "message": "Line C: Hiệu suất thấp bất thường (65%)",
      "sentiment": "warning"
    }
  ],
  "suggestions": [
    {
      "type": "action",
      "message": "Phân tích chi tiết Line C để tìm giải pháp"
    }
  ]
}
```

**Types of Insights:**
- 📈 **Trends**: improving, declining, stable
- 🏆 **Rankings**: top/bottom performers
- ⚠️ **Anomalies**: unusual highs/lows (2σ deviation)
- 📊 **Summaries**: overall statistics

---

### 4. **Smart Query Patterns** 🎯

#### **Achievement Rate Queries**
```vietnamese
"Tỷ lệ đạt kế hoạch theo line tháng 1/2026"
"Đạt kế hoạch của FAC01"
"Plan attainment rate by line"
```

#### **Defect Analysis**
```vietnamese
"Tỷ lệ lỗi theo model"
"Phân tích defect FAC01"
"Top 10 line có lỗi nhiều nhất"
```

#### **OEE & Efficiency**
```vietnamese
"Tính OEE các line tháng 1/2026"
"Hiệu suất theo line"
"Năng suất sản xuất"
```

#### **Trends & Comparisons**
```vietnamese
"Xu hướng sản lượng tháng 1"
"So sánh model A với model B"
"Top 5 line xuất sắc nhất"
```

---

### 5. **Bilingual Support** 🌍

**Vietnamese:**
```
"Thống kê sản lượng theo line tháng 1/2026"
"Tỷ lệ đạt kế hoạch FAC01"
"Phân tích lỗi theo công đoạn"
```

**English:**
```
"Show production statistics by line for January 2026"
"Achievement rate for FAC01"
"Analyze defects by process"
```

---

## 🔥 Quick Start Examples

### **Example 1: Basic Production Report**
```
Query: "Báo cáo sản xuất FAC01 từ tháng 10/2025 đến 1/2026"

Response:
- Month-by-month breakdown
- Auto-computed achievement rates
- Defect rates
- Insights: "Tháng 12 có tỷ lệ đạt thấp nhất (85%)"
```

### **Example 2: Line Performance Analysis**
```
Query: "Phân tích hiệu suất các line tháng 1/2026"

Response:
- Line-by-line metrics
- Achievement, defect, yield rates
- Insights: "Line A xuất sắc (105%), Line C cần cải thiện (75%)"
- Suggestions: "Kiểm tra Line C để tìm nguyên nhân"
```

### **Example 3: Top Performers**
```
Query: "Top 10 line tốt nhất về tỷ lệ đạt kế hoạch"

Response:
- Ranked list (highest achievement first)
- Achievement rates shown
- Comparison stats
```

### **Example 4: Multi-Turn Conversation**
```
1. "Báo cáo FAC01 tháng 1/2026"
   → Shows January data

2. "Còn DJVN1 thì sao?"
   → Shows DJVN1 for January (remembers timeframe)

3. "So sánh cả 2 nhà máy"
   → Compares FAC01 vs DJVN1

4. "Line nào tốt nhất?"
   → Shows top lines from both factories
```

---

## 📊 Available Metrics

### **Base Metrics** (from MES)
- `planQty` - Planned quantity
- `actualQty` - Actual quantity
- `defectQty` - Defect quantity
- `tactTime` - Takt time

### **Computed Metrics** (automatic)
- `achievementRate` - (actual/plan) × 100
- `defectRate` - (defect/actual) × 100
- `yieldRate` - ((actual-defect)/actual) × 100
- `efficiency` - Same as achievement
- `oee` - Overall Equipment Effectiveness
- `good_qty` - actual - defect

### **All Metrics Formatted:**
Each metric appears in 2 forms:
- Numeric: `achievementRate: 95.5`
- Display: `achievement_rate_percent: "95.5%"`

---

## 🎨 Sample Queries for Demo

### **For Sales Presentation:**

1. **Opening** (Vietnamese, shows context memory):
   ```
   "Tỷ lệ đạt kế hoạch FAC01 từ tháng 6/2025 đến 1/2026"
   ```

2. **Follow-up** (tests context retention):
   ```
   "Còn DJVN1 thì sao?"
   ```

3. **Insights** (shows proactive analysis):
   ```
   "Line nào cần cải thiện?"
   ```

4. **Bilingual** (English query):
   ```
   "Show me top 10 performers for achievement rate"
   ```

5. **Deep Dive** (detailed analysis):
   ```
   "Phân tích chi tiết các line có tỷ lệ đạt dưới 90%"
   ```

---

## 🚀 Performance Features

### **Caching**
- MES API responses cached for 10 minutes
- LLM responses cached for 30 minutes
- Session context cached for 1 hour
- **Result**: 5-10x faster for repeated queries

### **Session Management**
- Every conversation has a `session_id`
- Context automatically saved
- Works across page refreshes
- Multi-factory support

### **Database Storage**
- All conversations stored
- Message history retrievable
- Analytics on query patterns
- Audit trail for production

---

## 💡 Tips for Best Results

### **1. Be Specific with Time Ranges**
✅ Good: "tháng 1/2026"
✅ Good: "từ 2025-10-01 đến 2026-01-31"
❌ Avoid: "gần đây" (too vague)

### **2. Mention Factory Code**
✅ Good: "FAC01"
✅ Good: "nhà máy FAC01"
❌ Note: Without factory code, uses last saved context

### **3. Use Follow-ups**
✅ First: "Báo cáo FAC01 tháng 1/2026"
✅ Then: "Còn tháng 2 thì sao?" (reuses FAC01)
✅ Then: "Line nào tốt nhất?" (reuses FAC01, time range)

### **4. Ask for Analysis**
✅ Good: "Phân tích hiệu suất"
✅ Good: "Line nào bất thường?"
✅ Good: "So sánh model A và B"

---

## 🎯 Success Metrics

**You'll know it's working when:**
- ✅ See `achievementRate`, `defectRate` in results (not asked for)
- ✅ Follow-up questions work without repeating factory code
- ✅ Get insights like "Line A xuất sắc", "Line C cần cải thiện"
- ✅ Response includes `insights` and `suggestions` fields
- ✅ English and Vietnamese both work perfectly

---

## 🔮 What's Next?

**Coming Soon:**
- 📊 Chart visualizations in chat
- 🔔 Real-time alerts for anomalies
- 📱 Mobile app
- 🌍 Korean language support
- 🤖 Predictive analytics (forecast defects)
- 📈 Custom dashboards

---

## 📞 Need Help?

**Check logs:**
```powershell
docker logs sun_backend --tail 100
```

**Test a query:**
```powershell
$body = @{
    input = "Báo cáo FAC01 tháng 1/2026"
    context = @{
        factoryCode = "FAC01"
    }
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer dev-key-123"
    "Content-Type" = "application/json"
}

Invoke-RestMethod -Uri "http://localhost:9000/analyze" -Method Post -Body $body -Headers $headers
```

**View database:**
```powershell
docker exec -it sun_postgres psql -U sun_user -d sun_mes
```

---

**Happy querying! 🎉**
