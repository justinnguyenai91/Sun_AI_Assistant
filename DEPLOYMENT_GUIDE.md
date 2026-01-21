# 🚀 Sun MES AI Assistant - MVP Deployment Guide

## What's New in This Release

### ✨ **Phase 1: Quick Wins (Option C)**
1. ✅ **Auto-computed Metrics** - Achievement rate, defect rate, yield, efficiency, OEE automatically calculated
2. ✅ **Factory Context Persistence** - System remembers your factory across conversation
3. ✅ **Proactive Insights** - Automatic trend detection, anomaly alerts, top/bottom performers
4. ✅ **Trend Analysis** - "improving", "declining", "stable" trends in responses
5. ✅ **Bilingual Support** - Vietnamese and English fully supported

### 🚀 **Phase 2: Scalability Foundations**
6. ✅ **Redis Caching** - Fast response times, reduced MES API load
7. ✅ **PostgreSQL Storage** - Conversation history, session management
8. ✅ **Structured Logging** - JSON logs with trace IDs for debugging
9. ✅ **Session Management** - Multi-turn conversations with context memory

### 📈 **Phase 3: Query Coverage**
10. ✅ **15+ New Templates** - Achievement rate, OEE, yield, Pareto, trends, comparisons
11. ✅ **Enhanced Ontology** - 20+ new metrics (productivity, OEE, downtime, cycle time)
12. ✅ **13 New Test Cases** - Multi-turn, insights, computed metrics

---

## 📦 Prerequisites

- Docker & Docker Compose installed
- Ports available: 5432 (PostgreSQL), 6379 (Redis), 8080 (LLM), 8081 (Frontend), 9000 (Backend)
- `.env.docker` configured with MES API credentials

---

## 🔧 Deployment Steps

### 1️⃣ **Build and Start Services**

```powershell
# Navigate to project root
cd D:\AI_Project\Sun

# Build and start all services (PostgreSQL, Redis, Backend, Frontend, LLM)
docker compose up -d --build
```

**Services starting:**
- `sun_postgres` - PostgreSQL database (port 5432)
- `sun_redis` - Redis cache (port 6379)
- `sun_model` - Qwen2-7B LLM (port 8080)
- `sun_backend` - FastAPI backend (port 9000)
- `sun_frontend` - React frontend (port 8081)

### 2️⃣ **Verify Services**

```powershell
# Check all containers are running
docker ps

# Check backend health
curl http://localhost:9000/healthz

# Check logs
docker logs sun_backend --tail 50
docker logs sun_postgres --tail 20
docker logs sun_redis --tail 20
```

Expected output:
```json
{
  "status": "ok",
  "backend": "llama",
  "ts": 1737244800
}
```

### 3️⃣ **Database Initialization**

Database tables are **automatically created** on first backend startup:
- `conversations` - Chat sessions
- `messages` - Individual messages
- `session_contexts` - Persistent context (factory, time range, etc.)
- `query_cache` - Query result cache

**Verify database:**
```powershell
docker exec -it sun_postgres psql -U sun_user -d sun_mes -c "\dt"
```

### 4️⃣ **Access the Application**

🌐 **Frontend**: http://localhost:8081

**Try these queries:**
1. "Tỷ lệ đạt kế hoạch của nhà máy FAC01 theo line từ tháng 6/2025 đến 1/2026"
2. "Còn tháng 12 thì sao?" (follow-up using context)
3. "Top 10 line tốt nhất"
4. "Show me production achievement rate by line for January 2026" (English)

---

## 🎯 Key Features Demo

### **1. Auto-Computed Metrics**
Query: "Báo cáo sản xuất FAC01 tháng 1/2026"

**Response includes:**
- `achievementRate` - (actualQty / planQty) * 100
- `defectRate` - (defectQty / actualQty) * 100
- `yieldRate` - ((actualQty - defectQty) / actualQty) * 100
- `efficiency` - Same as achievement
- `oee` - Overall Equipment Effectiveness

### **2. Proactive Insights**
Query: "Phân tích hiệu suất các line tháng 1/2026"

**Response includes:**
```json
{
  "insights": [
    {"type": "trend", "message": "Tỷ lệ đạt kế hoạch đang cải thiện", "sentiment": "positive"},
    {"type": "ranking", "message": "Top performers: Line A, Line B", "sentiment": "positive"},
    {"type": "anomaly", "message": "Line C: Hiệu suất thấp bất thường (65%)", "sentiment": "warning"}
  ],
  "suggestions": [
    {"type": "action", "message": "Phân tích chi tiết Line C để tìm giải pháp"}
  ]
}
```

### **3. Multi-Turn Conversations**
```
User: "Báo cáo sản lượng FAC01 tháng 1/2026"
AI: [Returns data for FAC01]

User: "Còn tháng 12 thì sao?"
AI: [Remembers FAC01, returns data for December]

User: "So sánh với DJVN1"
AI: [Compares FAC01 and DJVN1]
```

**Context Persistence:**
- Factory code
- Time ranges
- Last metrics requested
- Line/model filters

---

## 🧪 Running Tests

```powershell
# Set environment variables
$env:SUN_ANALYZE_BASE_URL = "http://localhost:9000"
$env:SUN_API_KEY = "dev-key-123"

# Run all tests
python Backend/tests/run_chat_tests.py

# Run specific test
python Backend/tests/run_chat_tests.py --only achievement_rate_by_line
```

**Test Coverage:**
- 25+ test cases
- Multi-turn conversations
- Computed metrics validation
- Insights generation
- Bilingual support
- Context persistence

---

## 📊 Monitoring

### **PostgreSQL Queries**
```sql
-- View recent conversations
SELECT id, session_id, factory_code, locale, created_at 
FROM conversations 
ORDER BY created_at DESC 
LIMIT 10;

-- View message history
SELECT c.session_id, m.role, m.content, m.latency_ms 
FROM messages m 
JOIN conversations c ON m.conversation_id = c.id 
ORDER BY m.created_at DESC 
LIMIT 20;

-- Check session context
SELECT conversation_id, factory_code, last_entity, last_metrics 
FROM session_contexts;
```

### **Redis Cache**
```powershell
docker exec -it sun_redis redis-cli

# Check cache status
INFO stats
DBSIZE

# View cached sessions
KEYS session:*

# Check MES data cache
KEYS mes_data:*

# Monitor cache hits/misses
MONITOR
```

### **Backend Logs**
```powershell
# Real-time logs
docker logs sun_backend -f

# Search for errors
docker logs sun_backend 2>&1 | findstr ERROR

# Check specific session
docker logs sun_backend 2>&1 | findstr "session_001"
```

---

## 🔒 Security Configuration

### **Production Checklist:**
1. ✅ Change default database password in `docker-compose.yml`
2. ✅ Update API keys in `.env.docker`
3. ✅ Enable TLS for Redis: `redis-server --tls-port 6380 --port 0`
4. ✅ Set secure PostgreSQL password
5. ✅ Configure CORS origins in `.env.docker`: `ALLOW_ORIGINS=https://yourdomain.com`
6. ✅ Enable rate limiting (already configured)

### **Environment Variables:**
```env
# Redis
REDIS_URL=redis://redis:6379/0
REDIS_ENABLED=true

# PostgreSQL
DATABASE_URL=postgresql://sun_user:CHANGE_THIS_PASSWORD@postgres:5432/sun_mes
DATABASE_ENABLED=true

# API Keys (change these!)
API_KEYS=your-secure-api-key-here
EXTERNAL_API_TOKEN=your-mes-token-here
```

---

## 🐛 Troubleshooting

### **Issue: Backend can't connect to PostgreSQL**
```powershell
# Check PostgreSQL logs
docker logs sun_postgres

# Verify connection
docker exec -it sun_postgres psql -U sun_user -d sun_mes -c "SELECT 1"

# Restart backend
docker restart sun_backend
```

### **Issue: Redis connection failed**
```powershell
# Check Redis status
docker exec -it sun_redis redis-cli ping

# Should return: PONG

# Check Redis logs
docker logs sun_redis
```

### **Issue: Context not persisting**
```powershell
# Check database tables exist
docker exec -it sun_postgres psql -U sun_user -d sun_mes -c "\dt"

# Check session_contexts table
docker exec -it sun_postgres psql -U sun_user -d sun_mes -c "SELECT * FROM session_contexts"
```

### **Issue: Computed metrics missing**
- Check planner logs for errors: `docker logs sun_backend | findstr metrics`
- Verify `metrics_insights.py` loaded correctly
- Ensure data has required fields: `totalPlanQty`, `totalActualQty`, `totalDefectQty`

---

## 📈 Performance Tuning

### **Redis Memory Management**
```bash
# Current setting: 256MB with LRU eviction
# Adjust in docker-compose.yml:
command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### **PostgreSQL Connection Pool**
```python
# Backend/app/models/database.py
pool_size=10        # Increase for high concurrency
max_overflow=20     # Additional connections when needed
```

### **Cache TTL Tuning**
```python
# Backend/app/cache/redis_cache.py
MES_DATA_TTL = 600      # 10 minutes (increase for stable data)
LLM_RESULT_TTL = 1800   # 30 minutes
SESSION_TTL = 3600      # 1 hour (increase for long sessions)
```

---

## 🎓 Next Steps

### **For Sales Demo:**
1. Load sample data for smooth demo
2. Prepare 5-7 key queries showcasing features
3. Demonstrate multi-turn conversation flow
4. Show insights and proactive suggestions
5. Compare Vietnamese and English queries

### **For Production:**
1. Set up backup for PostgreSQL: `pg_dump sun_mes > backup.sql`
2. Configure monitoring (Grafana + Prometheus)
3. Set up log aggregation (ELK stack)
4. Implement user authentication (JWT)
5. Add row-level security for multi-tenant

### **Feature Roadmap:**
- 📊 RAG with MES knowledge base
- 📈 Predictive analytics (defect prediction)
- 🔔 Real-time alerts via WebSocket
- 📱 Mobile app support
- 🌍 Korean language support
- 📑 Export to Excel/PDF

---

## 📞 Support

**Logs Location:**
- Backend: `docker logs sun_backend`
- Database: `docker logs sun_postgres`
- Redis: `docker logs sun_redis`

**Configuration Files:**
- Backend: `Backend/.env.docker`
- Docker: `docker-compose.yml`
- Ontology: `Backend/app/config/ontology.yaml`
- Templates: `Backend/app/config/templates.yaml`

---

## ✅ Success Criteria

Your MVP is ready when:
- ✅ All 5 containers running
- ✅ Health check returns `{"status": "ok"}`
- ✅ Frontend loads at http://localhost:8081
- ✅ First query returns data with computed metrics
- ✅ Follow-up query uses saved context
- ✅ Insights appear in response
- ✅ Test cases pass (>90%)

**Congratulations! Your MES AI Assistant MVP is live! 🎉**
