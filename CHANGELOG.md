# 📝 Changelog

All notable changes to DTHAUS AI Assistant.

## [2.0.0] - 2026-01-20 - Complete Feature Release 🚀

### 🎨 Added - UI/UX Enhancements
- **Dark Mode Theme**: Full dark color scheme with purple-blue gradients
- **Responsive Design**: Mobile, tablet, desktop layouts with hamburger menu
- **Glassmorphism Effects**: Blur and transparency for modern look
- **Inter Typography**: Google Fonts with optimized spacing (-0.011em)
- **Auto-Scroll**: Smooth scroll to bottom on new messages
- **Mobile Menu**: Slide-in sidebar with backdrop overlay

### 🎤 Added - Smart Input Features
- **Voice Input**: Web Speech API for hands-free queries (Chrome/Edge/Safari)
  - Real-time transcript updates
  - Red pulse animation when listening
  - Vietnamese and English language support
- **Prompt Chips**: 6 suggested queries on empty chat
  - Click to auto-fill input box
  - Responsive grid layout
- **Quick Filters**: 3 sidebar buttons for instant queries
  - Always visible
  - Immediate execution

### 📊 Added - Data Features
- **Color-Coded Metrics**: Traffic light colors for instant insights
  - Green: OEE ≥90%, Defect ≤2% (Excellent)
  - Yellow: OEE 70-90%, Defect 2-5% (Needs Attention)
  - Red: OEE <70%, Defect >5% (Critical)
- **Collapsible Tables**: Click header to expand/collapse
  - Smooth max-height animation
  - Row count display
- **Export Buttons**: Download data with one click
  - CSV: UTF-8 with BOM (Excel-compatible)
  - JSON: Pretty-printed format
  - Filenames include date

### 🔧 Added - Developer Features
- **Loading Spinner**: Animated gradient spinner with pulsing dots
- **CSS Variables**: Centralized theme configuration
- **Table Helpers**: Utility functions for metric detection and formatting
- **Enhanced Components**: CollapsibleTable, ExportButton, VoiceInput

### 📚 Added - Documentation
- `COMPLETE_FEATURES_GUIDE.md`: Complete feature list with examples
- `DEMO_SCRIPT.md`: Video recording script and presentation materials
- `DARK_MODE_GUIDE.md`: Dark theme setup and customization
- `IMPLEMENTATION_COMPLETE.md`: Final summary and metrics

### 🐛 Fixed
- Table cell color coding now works with numeric values
- Voice input permission handling improved
- Mobile sidebar overlay z-index corrected
- CSV export encoding fixed for Vietnamese characters

### 🔄 Changed
- Input box placeholder: "Nhập câu hỏi của bạn hoặc nói..."
- Sidebar background: Purple-blue gradient instead of white glassmorphism
- Button styles: Gradient backgrounds with shadow effects
- Table headers: Sticky positioning for large datasets

### ⚡ Performance
- Build time: 5.91s (improved from 7.92s)
- Bundle size: +6.1 KB gzipped (+2.9% increase)
- CSS size: +3.5 KB original (+19.2%, mostly new components)
- Page load: ~1.5s full load

### 🧪 Testing
- All 82 backend tests passing ✅
- No build errors or warnings ✅
- Manual testing on Chrome, Edge, Safari ✅
- Responsive testing on mobile devices ✅

---

## [1.5.0] - 2026-01-19 - Semantic Resolver Bug Fixes

### 🐛 Fixed
- **Dimensional Query Logic**: "chi tiết lỗi theo line" now correctly returns line info
  - Modified semantic_resolver.py to NOT add symptom when spatial dimensions requested
  - Added "cho" to spatial_dimension_pattern (not just "theo")
  - Result: User queries respect spatial dimensions (line/model/process)

### 🧪 Testing
- Fixed 6 test failures → 82/82 passing ✅
- Added factoryCode to multi-turn test contexts

---

## [1.0.0] - 2026-01-15 - Initial Release

### ✨ Features
- Natural language query parsing
- MES data integration
- Multi-turn conversation support
- Table visualization
- Session management
- Chart rendering (basic)

### 🎨 UI
- Light mode theme
- Basic responsive layout
- Sidebar with conversation history
- Chat window with message bubbles

### 🔧 Technical
- FastAPI backend
- React + Vite frontend
- Docker deployment
- Nginx reverse proxy

---

## [Unreleased] - Future Enhancements

### Planned (Phase 4)
- [ ] Theme switcher (Light/Dark/Auto)
- [ ] Real-time charts with Chart.js
- [ ] WebSocket for live updates
- [ ] Notification system
- [ ] Search conversation history
- [ ] Keyboard shortcuts (Cmd+K for search)

### Planned (Phase 5)
- [ ] Voice output (Text-to-Speech)
- [ ] AI suggestions based on patterns
- [ ] Custom dashboard builder
- [ ] Scheduled reports
- [ ] Email/SMS alerts
- [ ] Mobile native app

---

## Version History Summary

| Version | Date | Key Features | Status |
|---------|------|--------------|--------|
| 2.0.0 | 2026-01-20 | Dark mode, Voice input, Export, Color coding | ✅ Released |
| 1.5.0 | 2026-01-19 | Semantic resolver fixes | ✅ Released |
| 1.0.0 | 2026-01-15 | Initial release | ✅ Released |

---

## Breaking Changes

### v2.0.0
- None (fully backward compatible)
- New CSS variables added (old styles still work)
- Voice input requires HTTPS in production

### v1.5.0
- None (backend logic improved, API unchanged)

---

## Upgrade Guide

### From v1.0 to v2.0

#### Backend
No changes required. v2.0 is frontend-only update.

#### Frontend
```bash
cd Frontend
git pull origin main
npm install  # No new dependencies!
npm run build
```

#### Environment Variables
No new variables required. Optional:
```bash
# .env (optional)
VITE_API_BASE=http://your-backend-url
VITE_API_KEY=your-dev-key
```

#### Docker
```bash
docker-compose down
docker-compose up --build
```

### Rollback
If issues occur:
```bash
git checkout v1.0.0
npm install
npm run build
```

---

## Known Issues

### v2.0.0
1. **Voice Input**:
   - Not supported in Firefox (no Web Speech API)
   - Requires HTTPS in production (browser security)
   - Microphone permission prompt may be confusing

2. **Mobile**:
   - Landscape mode may need optimization for small heights
   - iOS Safari voice input may have slight delay

3. **Export**:
   - Large tables (>10,000 rows) may slow down CSV generation
   - JSON export limited to 5 MB by browser

### Workarounds
1. **Voice Input on Firefox**: Use Chrome/Edge/Safari, or type instead
2. **HTTPS Requirement**: Deploy with SSL certificate or use localhost
3. **Large Exports**: Add pagination or server-side export endpoint

---

## Credits

### Development Team
- **Backend**: Semantic NLP, MES integration
- **Frontend**: React components, UX design
- **DevOps**: Docker, nginx configuration
- **Testing**: Test suite and QA

### Technologies Used
- **Frontend**: React 18, Vite 7.1, Vanilla CSS
- **Backend**: Python 3.12, FastAPI
- **Database**: PostgreSQL (MES data)
- **Deployment**: Docker, nginx
- **Fonts**: Google Fonts (Inter)
- **APIs**: Web Speech API

### Libraries
- React: UI framework
- Vite: Build tool
- FastAPI: Backend framework
- Docker: Containerization

---

## License

Proprietary - DTHAUS Internal Use Only

---

## Support

For questions or issues:
- **Slack**: #ai-assistant-support
- **Email**: data-team@dthaus.com
- **Documentation**: [COMPLETE_FEATURES_GUIDE.md](COMPLETE_FEATURES_GUIDE.md)

---

**Latest Version**: 2.0.0  
**Release Date**: January 20, 2026  
**Next Planned Release**: v2.1 (March 2026)
