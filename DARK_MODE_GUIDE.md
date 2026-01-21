# Dark Mode & Responsive Design - User Guide

## 🎨 Thiết Kế Mới

### 1. **Dark Mode Theme**
- **Background**: Gradient tối từ `#0F172A` → `#1E293B` 
- **Sidebar**: Gradient tím-xanh (`#1e1b4b` → `#312e81` → `#1e3a8a`)
- **Accent Color**: Blue `#3B82F6` cho buttons và highlights
- **Typography**: Inter font với letter-spacing tối ưu

### 2. **Responsive Layout**

#### Desktop (>1024px)
- Sidebar: 280px fixed width
- Main content: Tự động scale với max-width 900px
- Split-screen layout với glassmorphism effects

#### Tablet (768px - 1024px)
- Sidebar: 280px fixed, có thể toggle
- Main content: Full width

#### Mobile (<768px)
- Sidebar: Hidden by default, slide in khi click hamburger menu
- Hamburger menu button: Top-left corner
- Mobile overlay: Click outside sidebar để đóng

### 3. **Quick Filters**
Sidebar có 3 quick filter buttons:
- 📊 **Thống kê hôm nay**: "Thống kê sản lượng hôm nay"
- ⚠️ **Lỗi nhiều nhất**: "Top 5 lỗi nhiều nhất tháng này"
- 📈 **OEE các line**: "OEE của các line tháng này"

Click vào button sẽ tự động điền query vào input box.

### 4. **Color-Coded Metrics**
Tables tự động highlight metrics theo thresholds:

#### OEE / Performance / Availability
- 🟢 **Green** (>90%): Tốt
- 🟡 **Yellow** (70-90%): Trung bình
- 🔴 **Red** (<70%): Cần cải thiện

#### Quality
- 🟢 **Green** (>98%)
- 🟡 **Yellow** (95-98%)
- 🔴 **Red** (<95%)

#### Defect Rate
- 🟢 **Green** (<2%): Tốt (inverted logic)
- 🟡 **Yellow** (2-5%)
- 🔴 **Red** (>5%)

### 5. **Collapsible Tables**
- Tables có thể collapse/expand bằng cách click header
- Hiển thị số rows trong header
- Icon table với animation smooth

### 6. **Mini Charts** (Coming Soon)
- Inline bar charts bên cạnh numeric values
- Hiển thị trend cho time-series data
- Auto-generated từ column values

---

## 🔧 Technical Details

### CSS Variables (Dark Mode)
```css
--bg-primary: #0F172A;
--bg-secondary: #1E293B;
--text-primary: #F1F5F9;
--text-secondary: #CBD5E1;
--accent-primary: #3B82F6;
--success: #10B981;
--warning: #F59E0B;
--error: #EF4444;
```

### Component Structure
```
App.jsx (root)
├── ConversationHistory.jsx (sidebar)
│   ├── Quick Filters
│   ├── New Chat Button
│   └── Session List
├── ChatWindow.jsx (main content)
│   └── MessageBubble.jsx
│       ├── CollapsibleTable.jsx
│       └── EnhancedTableCell.jsx
└── ChatInput.jsx (floating input)
```

### Helper Functions
- `getMetricColorClass(value, type)`: Determine color class
- `formatMetricValue(value, type, unit)`: Format with color
- `generateMiniChart(values)`: Create mini bar chart data
- `detectMetricType(columnName)`: Auto-detect metric type

---

## 🚀 Build & Deploy

### Development
```bash
cd Frontend
npm install
npm run dev
```

### Production Build
```bash
npm run build
# Output: dist/ folder
# CSS: ~18 KB (gzip: 4.25 KB)
# JS: ~401 KB (gzip: 131.78 KB)
```

### Docker Deployment
```bash
docker-compose up --build frontend
# Nginx serves static files from dist/
```

---

## 📱 Mobile Experience

### Hamburger Menu
- Click hamburger icon (top-left) để mở sidebar
- Click outside sidebar hoặc click lại hamburger để đóng
- Smooth slide-in animation với backdrop blur

### Touch Optimizations
- Larger touch targets (minimum 44x44px)
- Smooth scroll với momentum
- Swipe gestures (coming soon)

### Performance
- Lazy loading cho tables lớn (coming soon)
- Virtual scrolling cho 1000+ rows (coming soon)
- Service Worker caching (coming soon)

---

## 🎯 Future Enhancements

### Phase 2 (Planned)
- [ ] Voice input button
- [ ] Prompt chips (suggested queries)
- [ ] Auto-scroll to bottom on new messages
- [ ] Loading spinner with "Đang lấy dữ liệu từ MES..."
- [ ] Export table to Excel/CSV

### Phase 3 (Future)
- [ ] Chart visualization (Chart.js or Recharts)
- [ ] Real-time updates with WebSocket
- [ ] Notification system
- [ ] Theme switcher (Light/Dark/Auto)
- [ ] Multi-language support (EN/VI)

---

## 🐛 Known Issues

1. **Mini charts**: Not yet implemented, placeholder code ready
2. **Auto-scroll**: Need to add useEffect with scrollIntoView
3. **Table pagination**: Large tables may slow down rendering
4. **Mobile landscape**: May need optimization for small heights

---

## 📝 Changelog

### v2.0.0 - Dark Mode & Responsive (2026-01-20)
- ✅ Dark mode theme with gradient backgrounds
- ✅ Responsive layout (mobile, tablet, desktop)
- ✅ Quick filters in sidebar
- ✅ Color-coded metrics (OEE, quality, defect rate)
- ✅ Collapsible table cards
- ✅ Mobile hamburger menu
- ✅ Glassmorphism effects
- ✅ Inter font with optimized typography

### v1.0.0 - Initial Release
- Basic chat interface
- Table rendering
- Multi-turn conversations
- Session management
