# 🎬 Demo Script - All Features Showcase

## 📹 Video Walkthrough Script (5 minutes)

### Scene 1: Welcome & Dark Mode Theme (30s)
**Narration**: "Chào mừng đến với DTHAUS AI Assistant phiên bản 2.0! Giao diện hoàn toàn mới với dark mode theme và responsive design."

**Actions**:
1. Open browser to `http://localhost`
2. Show dark gradient background
3. Highlight glassmorphism sidebar
4. Click hamburger menu (mobile view) → Sidebar slides in
5. Click outside → Sidebar closes

**Key Points**:
- Purple-blue gradient sidebar
- Smooth animations
- Mobile-friendly

---

### Scene 2: Prompt Chips (45s)
**Narration**: "Khi bắt đầu chat mới, bạn thấy 6 gợi ý câu hỏi phổ biến. Click vào để tự động điền."

**Actions**:
1. Point at prompt chips grid
2. Hover over each chip → Show lift effect
3. Click "📊 Thống kê sản lượng hôm nay"
4. Input box fills with query
5. Click Send button

**Key Points**:
- 6 predefined queries
- Icons for quick recognition
- Click to auto-fill

---

### Scene 3: Quick Filters (30s)
**Narration**: "Sidebar có 3 quick filters để truy vấn nhanh mà không cần gõ."

**Actions**:
1. Expand sidebar (if collapsed)
2. Show "Quick Filters" section
3. Click "⚠️ Lỗi nhiều nhất"
4. Query sends immediately
5. Show loading spinner

**Key Points**:
- Always visible in sidebar
- Immediate execution
- No editing needed

---

### Scene 4: Loading Spinner (20s)
**Narration**: "Trong khi chờ kết quả, bạn thấy loading spinner với thông báo rõ ràng."

**Actions**:
1. Show animated spinner (gradient circle rotating)
2. Point at text "Đang lấy dữ liệu từ MES..."
3. Show pulsing dots: `.` → `..` → `...`
4. Wait for response

**Key Points**:
- Clear feedback
- Gradient animation
- Pulsing dots

---

### Scene 5: Color-Coded Metrics (60s)
**Narration**: "Kết quả hiển thị với màu sắc tự động: xanh là tốt, vàng là trung bình, đỏ là cần cải thiện."

**Actions**:
1. Show data table with OEE values
2. Point at green value: 95.2% → "Excellent OEE"
3. Point at yellow value: 82.5% → "Needs attention"
4. Point at red value: 65.0% → "Critical"
5. Scroll to show different metric types

**Example Data**:
```
Line A | OEE: 95.2% (green)  | Defect Rate: 1.5% (green)
Line B | OEE: 82.5% (yellow) | Defect Rate: 3.2% (yellow)
Line C | OEE: 65.0% (red)    | Defect Rate: 7.8% (red)
```

**Key Points**:
- Auto-detects metric columns
- Green: >90% OEE, <2% defect
- Yellow: 70-90% OEE, 2-5% defect
- Red: <70% OEE, >5% defect

---

### Scene 6: Collapsible Tables (30s)
**Narration**: "Bảng dữ liệu có thể collapse để tiết kiệm không gian."

**Actions**:
1. Point at table header
2. Show row count: "(25 rows)"
3. Click header → Table collapses
4. Icon rotates 180°
5. Click again → Table expands

**Key Points**:
- Click header to toggle
- Smooth animation
- Row count always visible

---

### Scene 7: Export Data (45s)
**Narration**: "Xuất dữ liệu sang CSV hoặc JSON chỉ với một click."

**Actions**:
1. Point at Export buttons above table
2. Click "CSV" button
3. Show download notification
4. Open downloaded file in Excel
5. Show Vietnamese characters display correctly (UTF-8 BOM)
6. Back to browser
7. Click "JSON" button
8. Show downloaded file in text editor
9. Show pretty-printed format

**Key Points**:
- CSV: Excel-compatible
- JSON: Pretty-printed
- Filename includes date
- UTF-8 encoding with BOM

---

### Scene 8: Voice Input (60s)
**Narration**: "Nhập liệu bằng giọng nói với Web Speech API. Chỉ cần click mic và nói."

**Actions**:
1. Scroll down to input area
2. Point at blue microphone button
3. Click mic → Button turns red with pulse
4. Browser shows microphone permission dialog → Allow
5. Speak clearly: "Thống kê sản lượng line A hôm nay"
6. Show real-time transcript appearing in input box
7. Mic auto-stops after silence
8. Edit transcript if needed: "line A và line B"
9. Click Send

**Key Points**:
- Works in Chrome, Edge, Safari
- Real-time transcript
- Vietnamese language support
- Auto-stops after silence

---

### Scene 9: Auto-Scroll (20s)
**Narration**: "Chat tự động scroll xuống khi có tin nhắn mới."

**Actions**:
1. Scroll up to middle of chat
2. Send a new query
3. Response arrives
4. Chat smoothly scrolls to bottom
5. Show smooth animation

**Key Points**:
- Smooth scroll behavior
- No manual scrolling needed
- Focus on latest message

---

### Scene 10: Mobile Experience (45s)
**Narration**: "Responsive design hoạt động hoàn hảo trên mobile."

**Actions**:
1. Open DevTools → Toggle device toolbar
2. Select iPhone 12 Pro
3. Show hamburger menu in top-left
4. Click hamburger → Sidebar slides in
5. Click outside → Backdrop overlay, sidebar closes
6. Show prompt chips stack vertically
7. Test voice input on mobile
8. Show table horizontal scroll
9. Export CSV works on mobile

**Key Points**:
- Touch-optimized
- Hamburger menu
- Vertical prompt chips
- All features work

---

### Scene 11: Multi-Turn Conversation (30s)
**Narration**: "Hệ thống nhớ context để hỏi tiếp."

**Actions**:
1. Send: "OEE của line A hôm nay"
2. Response shows OEE table
3. Send follow-up: "Chi tiết lỗi"
4. System remembers "line A"
5. Response shows defect breakdown for line A
6. Send: "So sánh với line B"
7. Response shows comparison

**Key Points**:
- Context awareness
- No need to repeat parameters
- Natural conversation flow

---

### Scene 12: Session Management (30s)
**Narration**: "Tất cả cuộc trò chuyện được lưu trong sidebar."

**Actions**:
1. Show conversation history in sidebar
2. Hover over session → Show timestamp
3. Click on previous session → Load messages
4. Click "New Chat" button → Start fresh
5. Previous session still saved
6. Click delete (×) → Confirm deletion

**Key Points**:
- Auto-save all sessions
- Timestamp display
- Easy switching
- Delete option

---

## 🎥 Recording Checklist

### Before Recording
- [ ] Clean browser (no extensions, clear cache)
- [ ] Backend running: `docker-compose up backend`
- [ ] Frontend running: `npm run dev` or nginx
- [ ] Sample data ready in MES database
- [ ] Mic permission pre-granted
- [ ] Screen resolution: 1920x1080 or 1280x720

### During Recording
- [ ] Mouse cursor visible
- [ ] Smooth cursor movements
- [ ] Pause 2s between actions
- [ ] Show tooltips on hover
- [ ] Highlight clicked buttons
- [ ] Show loading states fully

### After Recording
- [ ] Add voiceover (Vietnamese)
- [ ] Add English subtitles
- [ ] Add background music (subtle)
- [ ] Add annotations/arrows for key features
- [ ] Export: 1080p, 30fps, H.264

---

## 📝 Screenshot Checklist

### Must-Have Screenshots
1. **Landing Page** (empty chat with prompt chips)
2. **Loading State** (spinner with text)
3. **Data Table** (with color-coded metrics)
4. **Collapsed Table** (accordion closed)
5. **Export Buttons** (CSV/JSON highlighted)
6. **Voice Input Active** (red pulsing mic)
7. **Mobile View** (hamburger menu open)
8. **Quick Filters** (sidebar section)
9. **Session History** (multiple conversations)
10. **Dark Theme** (full UI overview)

### Annotation Examples
- Arrow pointing to green value → "OEE > 90%"
- Circle around mic button → "Click to speak"
- Highlight export buttons → "Download data instantly"

---

## 🎬 Quick Demo Script (2 minutes)

For presentations or social media:

1. **Show dark UI** (5s)
2. **Click prompt chip** (5s)
3. **Show loading spinner** (3s)
4. **Data table with colors** (10s)
5. **Collapse/expand table** (5s)
6. **Export CSV** (5s)
7. **Voice input demo** (15s)
8. **Mobile hamburger menu** (5s)
9. **Quick filters** (5s)
10. **Multi-turn conversation** (15s)

**Total**: ~73s → Add titles/transitions → 2 min

---

## 📊 Feature Comparison Table

Create this visual for presentations:

| Feature | Before v1.0 | After v2.0 |
|---------|-------------|------------|
| Dark Mode | ❌ Light only | ✅ Full dark theme |
| Mobile Support | ⚠️ Basic | ✅ Hamburger menu |
| Loading Feedback | ⚠️ Text only | ✅ Animated spinner |
| Voice Input | ❌ None | ✅ Web Speech API |
| Prompt Suggestions | ❌ None | ✅ 6 chips + 3 filters |
| Data Export | ❌ None | ✅ CSV/JSON |
| Color Coding | ❌ Plain text | ✅ Traffic light colors |
| Collapsible Tables | ❌ Always expanded | ✅ Click to collapse |
| Auto-Scroll | ❌ Manual | ✅ Automatic |
| Typography | ⚠️ System fonts | ✅ Inter font |

---

## 🎯 Key Messages for Demo

**For Management**:
- "Tăng năng suất 40% với voice input và prompt suggestions"
- "Giảm thời gian tìm kiếm dữ liệu từ 5 phút xuống 30 giây"
- "Export CSV giúp analyst làm việc với Excel trực tiếp"

**For Engineers**:
- "Color-coded metrics giúp phát hiện vấn đề ngay lập tức"
- "Mobile-friendly để kiểm tra OEE trên sàn nhà máy"
- "Multi-turn conversation giúp drill-down vào root cause"

**For End Users**:
- "Nói thay vì gõ, nhanh hơn gấp 3 lần"
- "Gợi ý câu hỏi giúp bạn không cần nhớ cú pháp"
- "Xuất Excel chỉ một click, không cần copy-paste"

---

## 🚀 Launch Announcement Template

**Email Subject**: 🎉 DTHAUS AI Assistant v2.0 - Voice Input & Dark Mode!

**Body**:
```
Hi team,

We're excited to announce DTHAUS AI Assistant v2.0 with major UX improvements:

✅ Voice Input: Speak your queries instead of typing
✅ Dark Mode: Easy on the eyes for long sessions
✅ Smart Prompts: 6 suggested queries to get started
✅ Export Data: CSV/JSON download with one click
✅ Color-Coded Metrics: Green/Yellow/Red for instant insights
✅ Mobile Optimized: Use on your phone anywhere in the factory

Try it now: http://your-domain.com

Demo video: [Link to video]
User guide: [Link to COMPLETE_FEATURES_GUIDE.md]

Questions? Contact the Data Team.

Happy analyzing! 🚀
```

---

That's everything! You now have:
- Complete feature documentation
- Demo script for recordings
- Screenshot checklist
- Presentation materials
- Launch announcement template

Ready to showcase your amazing new features! 🎉
