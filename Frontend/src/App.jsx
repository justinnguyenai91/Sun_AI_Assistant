// src/App.jsx
import { useRef, useState } from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import { detectLocaleFromText } from "./utils/columnI18n.js";
import { t } from "./utils/i18n.js";
import { aggregateRows } from "./utils/aggregateRows.js";

// API base:
// - Prod (nginx): use same-origin and let nginx proxy /analyze -> backend
// - Dev (vite): can override via VITE_API_BASE, otherwise fallback to localhost backend
const BASE_URL = import.meta.env.PROD ? "" : import.meta.env.VITE_API_BASE || "http://127.0.0.1:9000";
const DEFAULT_KEY = import.meta.env.VITE_API_KEY || ""; // dev only

function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [locale, setLocale] = useState("vi");
  const [pendingFollowUp, setPendingFollowUp] = useState(null);
  const [lastDataQuery, setLastDataQuery] = useState(null); // { text, locale, factoryCodes }
  const inFlightAbortRef = useRef(null);

  // Factory context memory (e.g., FAC01, DJVN1): remembered for this session
  const [factoryCodes, setFactoryCodes] = useState([]);
  const [pendingFactory, setPendingFactory] = useState(null); // { originalText: string, locale: string }

  const MAX_MODEL_RETRIES = 3;

  const detectFactoryCodes = (text) => {
    const up = String(text || "").toUpperCase();
    const matches = up.match(/\b[A-Z]{2,6}\d{1,4}\b/g);
    if (!matches || matches.length === 0) return [];
    const out = [];
    const seen = new Set();
    matches.forEach((m) => {
      const s = String(m || "").trim();
      if (!s || seen.has(s)) return;
      seen.add(s);
      out.push(s);
    });
    return out;
  };

  const looksLikeDataRequest = (text) => {
    const s = String(text || "").toLowerCase();
    // Keep it broad; backend still decides exact intent.
    return /\b(th\u1ed1ng k\u00ea|t\u1ed5ng h\u1ee3p|b\u00e1o c\u00e1o|s\u1ea3n l\u01b0\u1ee3ng|yield|defect|productivity|statistic|report|output|l\u1ea5y\s+d\u1eef\s+li\u1ec7u|fetch\s+data)\b/.test(s);
  };

  const normalizeGroupBy = (gb) => {
    if (!gb) return [];
    if (Array.isArray(gb)) return gb.map((x) => String(x).trim()).filter(Boolean);
    if (typeof gb === "string") {
      const s = gb.trim();
      if (!s) return [];
      return s.includes(",") ? s.split(",").map((x) => x.trim()).filter(Boolean) : [s];
    }
    return [];
  };

  const groupColsFromDims = (dims) => {
    const out = [];
    const add = (...cols) => cols.forEach((c) => out.push(c));
    (dims || []).forEach((d) => {
      const dim = String(d || "").toLowerCase();
      if (dim === "date") add("date", "planDate");
      else if (dim === "week") add("week");
      else if (dim === "quarter") add("quarter");
      else if (dim === "year") add("year");
      else if (dim === "month") add("month");
      else if (dim === "line") add("lineCode", "lineName", "lineId");
      else if (dim === "model") add("modelCode", "modelName");
      else if (dim === "status" || dim === "prodstatus") add("productionStatusLabel", "productionStatusCode", "productionStatusLabels", "productionStatusCodes");
      else if (dim === "processtype" || dim === "process" || dim === "processtype") add("processTypeLabel", "processTypeCode", "processTypeLabels", "processTypes");
    });
    return out;
  };

  const dimsAffectedByColumns = (dims, cols) => {
    const requested = new Set((cols || []).map(String));
    const affected = [];
    (dims || []).forEach((d) => {
      const dim = String(d || "").trim();
      if (!dim) return;
      const keys = groupColsFromDims([dim]);
      if (keys.some((k) => requested.has(String(k)))) affected.push(dim);
    });
    return affected;
  };

  const dimsToPhrase = (dims, nextLocale) => {
    const isVi = String(nextLocale || "en").toLowerCase().startsWith("vi");
    const names = (dims || []).map((d) => {
      const dim = String(d || "").toLowerCase();
      if (dim === "date") return isVi ? "ngày" : "date";
      if (dim === "week") return isVi ? "tuần" : "week";
      if (dim === "month") return isVi ? "tháng" : "month";
      if (dim === "quarter") return isVi ? "quý" : "quarter";
      if (dim === "year") return isVi ? "năm" : "year";
      if (dim === "line") return "line";
      if (dim === "model") return "model";
      if (dim === "status" || dim === "prodstatus") return isVi ? "trạng thái" : "status";
      if (dim === "processtype" || dim === "process") return isVi ? "process type" : "process type";
      return dim;
    });
    if (names.length === 0) return "";
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]} ${isVi ? "và" : "and"} ${names[1]}`;
    return `${names.slice(0, -1).join(", ")}${isVi ? ", và " : ", and "}${names[names.length - 1]}`;
  };

  const findLastTableMessage = (msgs) => {
    for (let i = (msgs || []).length - 1; i >= 0; i -= 1) {
      const m = msgs[i];
      if (m && m.type === "table" && Array.isArray(m.rows) && m.rows.length > 0) {
        return m;
      }
    }
    return null;
  };

  const mapColumnPhraseToKeys = (phrase) => {
    // Map natural language column names -> actual row keys.
    const s = String(phrase || "").trim();
    if (!s) return [];
    const lc = s.toLowerCase();
    const out = [];
    const has = (re) => re.test(lc);

    // Dates (special-case to avoid matching "plan" as plan qty)
    const isPlanDate = has(/\bplan\s*date\b|\bplanned\s*date\b|ngày\s*kế\s*hoạch|ngay\s*ke\s*hoach/i);
    if (isPlanDate) {
      out.push("date", "planDate");
      return Array.from(new Set(out));
    }
    if (has(/\bdate\b|ngày\b|ngay\b/i)) out.push("date");

    // Line
    if (has(/line\s*id|lineid|mã\s*dây\s*chuyền\s*id/i)) out.push("lineId");
    if (has(/line\s*code|linecode|mã\s*dây\s*chuyền(?!\s*id)/i)) out.push("lineCode");
    if (has(/line\s*name|tên\s*dây\s*chuyền|ten\s*day\s*chuyen/i)) out.push("lineName");

    // Orders
    if (has(/order\b|orders\b|số\s*lệnh|so\s*lenh/i)) out.push("orderCount", "orderNo", "poNo", "productionOrderNo");

    // Model
    if (has(/model\s*code|mã\s*model|ma\s*model/i)) out.push("modelCode");
    if (has(/model\s*name|tên\s*model|ten\s*model/i)) out.push("modelName");

    // Process / operation (công đoạn)
    // - "Mã công đoạn" maps to code fields
    // - "Công đoạn" maps to label fields
    if (has(/mã\s*công\s*đoạn|ma\s*cong\s*doan|process\s*code/i)) out.push("processTypeCode", "processTypes");
    if (has(/công\s*đoạn|cong\s*doan|process\s*type|process\b/i) && !has(/mã\s*công\s*đoạn|ma\s*cong\s*doan|process\s*code/i)) {
      out.push("processTypeLabel", "processTypeLabels");
    }

    // Status
    if (has(/trạng\s*thái|trang\s*thai|status\b/i))
      out.push("productionStatusLabel", "productionStatusCode", "productionStatusLabels", "productionStatusCodes");

    // Metrics
    if (has(/kế\s*hoạch|ke\s*hoach|planned|plan\b/i)) out.push("totalPlanQty", "planQty");
    if (has(/thực\s*tế|thuc\s*te|actual\b/i)) out.push("totalActualQty", "actualQty");
    if (has(/lỗi|loi|defect\b/i)) out.push("totalDefectQty", "defectQty");
    if (has(/tact|takt|chu\s*kỳ|chu\s*ky/i)) out.push("avgTactTime", "tactTime");

    return Array.from(new Set(out));
  };

  const detectColumnVisibilityTransform = (text) => {
    const s = String(text || "").trim();
    if (!s) return null;
    const lc = s.toLowerCase();

    const hideMatch = lc.match(/\b(bỏ|ẩn|xoá|xóa|remove|hide)\s+(cột|column)\s+(.+)$/i);
    const showMatch = lc.match(/\b(hiện|show|thêm|them|add)\s+(cột|column)\s+(.+)$/i);
    const kind = hideMatch ? "hideColumns" : showMatch ? "showColumns" : null;
    if (!kind) return null;

    let tail = String((hideMatch || showMatch || [])[3] || "").trim();
    if (!tail) return null;

    // Strip common trailing filler words (vi/en)
    // e.g. "... đi", "... nhé", "... lên"
    while (true) {
      const next = tail.replace(/\s+(đi|nhé|nhe|lên|len|please|pls)\s*$/i, "").trim();
      if (next === tail) break;
      tail = next;
    }

    // Split column list: comma, "/", and "và/and"
    const parts = tail
      .split(/,|\/|\bvà\b|\band\b/gi)
      .map((p) => String(p || "").trim())
      .filter(Boolean);

    // If we can't split reliably, fallback to whole string mapping.
    const tokens = parts.length ? parts : [tail];

    const cols = [];
    tokens.forEach((tok) => mapColumnPhraseToKeys(tok).forEach((k) => cols.push(k)));

    if (cols.length === 0) return null;
    return { kind, columns: Array.from(new Set(cols)) };
  };

  const sendToBackend = async (text, nextLocale, ctxFactoryCodes) => {
    const apiKey = await ensureApiKey();
    if (!apiKey) throw new Error("Missing API key");

    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

    let attempt = 0;
    while (true) {
      setLoading(true);

      // Cancel any previous in-flight request
      try {
        inFlightAbortRef.current?.abort?.();
      } catch {
        // ignore
      }
      const controller = new AbortController();
      inFlightAbortRef.current = controller;

      // Chat-first: use /analyze for both chat + structured results
      const ctx = {};
      const codes = Array.isArray(ctxFactoryCodes) ? ctxFactoryCodes.filter(Boolean).map(String) : [];
      if (codes.length === 1) ctx.factoryCode = codes[0];
      if (codes.length > 1) ctx.factoryCodes = codes;
      let resp;
      try {
        resp = await fetch(`${BASE_URL}/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        signal: controller.signal,
        body: JSON.stringify({ input: text, context: ctx }),
        });
      } catch (err) {
        if (err && (err.name === "AbortError" || String(err).includes("AbortError"))) {
          // Cancellation is handled by onCancel; just stop quietly.
          return;
        }
        throw err;
      }

      // Try parse JSON (even for errors)
      const data = await resp.json().catch(() => ({}));

      // Handle model loading/unavailable with retry
      if (resp.status === 503 && attempt < MAX_MODEL_RETRIES) {
        const retryAfterHeader = resp.headers.get("Retry-After");
        const baseDelaySec = Number.parseInt(retryAfterHeader || "30", 10);
        const delaySec = Number.isFinite(baseDelaySec) && baseDelaySec > 0 ? baseDelaySec * Math.pow(2, attempt) : 30;

        const detail = data?.detail || data?.error || "Model đang khởi động";
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: t("ui.modelLoadingRetry", nextLocale, {
              detail,
              seconds: delaySec,
              attempt: attempt + 1,
              max: MAX_MODEL_RETRIES,
            }),
          },
        ]);

        setLoading(false);
        attempt += 1;
        await sleep(delaySec * 1000);
        continue;
      }

      if (!resp.ok) {
        const detail = data?.detail || data?.error || "Unknown error";
        const rid = data?.request_id ? ` | rid=${String(data.request_id)}` : "";
        throw new Error(`HTTP ${resp.status}: ${detail}${rid}`);
      }

      // Backend UI commands (e.g., hide/show column) should apply to the last dataset
      // instead of being treated as an empty data response.
      const uiCmd = data?.decision?.ui_command;
      const uiMode = String(data?.decision?.mode || "").toLowerCase() === "ui";
      if (uiMode && uiCmd && (uiCmd.type === "hide_column" || uiCmd.type === "show_column")) {
        const lastTable = findLastTableMessage(messages);
        if (!lastTable) {
          setMessages((prev) => [
            ...prev,
            { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
          ]);
          break;
        }

        const cols = mapColumnPhraseToKeys(uiCmd.column || "");
        if (cols.length === 0) {
          setMessages((prev) => [
            ...prev,
            {
              sender: "ai",
              type: "text",
              locale: nextLocale,
              text: nextLocale.startsWith("vi")
                ? `Mình nhận yêu cầu rồi nhưng chưa map được cột: ${String(uiCmd.column || "")}.`
                : `Got it, but I couldn't map that column: ${String(uiCmd.column || "")}.`,
            },
          ]);
          break;
        }

        const baseHidden = Array.isArray(lastTable.hiddenColumns) ? lastTable.hiddenColumns.map(String) : [];
        const nextHidden =
          uiCmd.type === "show_column"
            ? baseHidden.filter((c) => !cols.includes(c))
            : Array.from(new Set([...baseHidden, ...cols]));

        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "table",
            locale: nextLocale,
            rows: lastTable.rows,
            decision: lastTable.decision,
            hiddenColumns: nextHidden,
            visibleColumns: lastTable.visibleColumns,
            groupBy: lastTable.groupBy,
          },
        ]);
        break;
      }

      const assistantMsgs = normalizeAnalyzeResponseToMessages(text, data, nextLocale);

      // Remember last successful data query so we can refresh it later.
      if (Array.isArray(assistantMsgs) && assistantMsgs.some((m) => m?.type === "table" && Array.isArray(m?.rows) && m.rows.length > 0)) {
        setLastDataQuery({ text, locale: nextLocale, factoryCodes: codes.length ? codes : null });
      }

      // If the user combined data query + "hide column" in one sentence,
      // apply the hide transform to the returned table message.
      const inlineColTransform = detectColumnVisibilityTransform(text);
      if (inlineColTransform && Array.isArray(assistantMsgs) && assistantMsgs.some((m) => m?.type === "table")) {
        const firstTable = assistantMsgs.find((m) => m?.type === "table" && Array.isArray(m?.rows));
        const dims = normalizeGroupBy(firstTable?.groupBy || firstTable?.decision?.group_by || null);
        const cols = (inlineColTransform.columns || []).map(String);

        // If user is hiding a group-by key, ask for confirmation.
        if (inlineColTransform.kind === "hideColumns") {
          const affectedDims = dimsAffectedByColumns(dims, cols);
          if (affectedDims.length > 0) {
            setMessages((prev) => [...prev, ...assistantMsgs]);
            setPendingFollowUp({
              kind: "confirmHideGroupBy",
              action: "hide",
              columns: cols,
              currentDims: dims,
              affectedDims,
              factoryCodes: codes.length ? codes : null,
              originalQueryText: text,
              locale: nextLocale,
            });

            const isVi = String(nextLocale || "en").toLowerCase().startsWith("vi");
            const dimsPhrase = dimsToPhrase(affectedDims, nextLocale);
            setMessages((prev) => [
              ...prev,
              {
                sender: "ai",
                type: "text",
                locale: nextLocale,
                text: t("ui.confirmHideGroupBy", nextLocale, { dims: dimsPhrase }),
              },
            ]);
            break;
          }
        }

        const patched = assistantMsgs.map((m) => {
          if (!m || m.type !== "table") return m;
          const baseHidden = Array.isArray(m.hiddenColumns) ? m.hiddenColumns.map(String) : [];
          if (inlineColTransform.kind === "showColumns") {
            return { ...m, hiddenColumns: baseHidden.filter((c) => !cols.includes(String(c))) };
          }
          return { ...m, hiddenColumns: Array.from(new Set([...baseHidden, ...cols].map(String))) };
        });
        setMessages((prev) => [...prev, ...patched]);
      } else {
        setMessages((prev) => [...prev, ...assistantMsgs]);
      }
      break;
    }
  };

  const parseGroupByFromText = (text) => {
    const s = String(text || "").toLowerCase();
    const dims = [
      { dim: "date", patterns: [/plan\s*date/i, /planned\s*date/i, /by\s*date/i, /date\b/i, /theo\s*ngày/i, /theo\s*ngay/i, /ngày\b/i, /ngay\b/i] },
      { dim: "week", patterns: [/by\s*week/i, /weekly/i, /week\b/i, /theo\s*tuần/i, /theo\s*tuan/i, /tuần\b/i, /tuan\b/i] },
      { dim: "quarter", patterns: [/by\s*quarter/i, /quarterly/i, /quarter\b/i, /theo\s*quý/i, /theo\s*quy/i, /quý\b/i, /quy\b/i] },
      { dim: "year", patterns: [/by\s*year/i, /yearly/i, /year\b/i, /theo\s*năm/i, /theo\s*nam/i, /năm\b/i, /nam\b/i] },
      { dim: "month", patterns: [/tháng\b/i, /by\s*month/i, /monthly/i, /month\b/i] },
      { dim: "line", patterns: [/dây\s*chuyền/i, /theo\s*line/i, /by\s*line/i, /line\b/i] },
      { dim: "model", patterns: [/model\b/i, /by\s*model/i, /mã\s*model/i, /mã\s*hàng/i] },
      { dim: "status", patterns: [/trạng\s*thái/i, /by\s*status/i, /status\b/i] },
      { dim: "processType", patterns: [/công\s*đoạn/i, /cong\s*doan/i, /process\s*type/i, /by\s*process/i, /process\b/i] },
    ];
    const hits = [];
    dims.forEach((d) => {
      let best = Number.POSITIVE_INFINITY;
      d.patterns.forEach((re) => {
        const m = s.match(re);
        if (m && typeof m.index === "number") best = Math.min(best, m.index);
      });
      if (Number.isFinite(best)) hits.push({ dim: d.dim, idx: best });
    });
    hits.sort((a, b) => a.idx - b.idx);
    const out = [];
    hits.forEach((h) => {
      if (!out.includes(h.dim)) out.push(h.dim);
    });
    return out;
  };

  const parseMetricSelection = (text, groupByDims) => {
    const s = String(text || "").toLowerCase();
    const only = /\b(chỉ|chi|only|just)\b/i.test(s) || /\b(thôi|thoi)\b/i.test(s);
    if (!only) return null;

    const metrics = [];
    if (/(kế\s*hoạch|ke\s*hoach|planned|plan\b)/i.test(s)) metrics.push("totalPlanQty");
    if (/(thực\s*tế|thuc\s*te|actual)/i.test(s)) metrics.push("totalActualQty");
    if (/(lỗi|loi|defect)/i.test(s)) metrics.push("totalDefectQty");
    if (/(tact|takt)/i.test(s)) metrics.push("avgTactTime");

    if (metrics.length === 0) return null;

    const groupCols = [];
    (groupByDims || []).forEach((d) => {
      if (d === "date") groupCols.push("date");
      if (d === "week") groupCols.push("week");
      if (d === "quarter") groupCols.push("quarter");
      if (d === "year") groupCols.push("year");
      if (d === "month") groupCols.push("month");
      if (d === "line") groupCols.push("lineName", "lineId");
      if (d === "model") groupCols.push("modelCode", "modelName");
      if (d === "status") groupCols.push("productionStatusLabel", "productionStatusCode");
      if (d === "processType") groupCols.push("processTypeLabel", "processTypeCode");
    });

    // Keep only columns that exist will be filtered in TableMessage.
    return [...groupCols, ...metrics];
  };

  const detectFollowUpTransform = (text) => {
    const s = String(text || "").trim();
    if (!s) return null;
    const lc = s.toLowerCase();

    const looksLikeFollowUp = /(dựa\s*vào\s*kết\s*quả|tu\s*kết\s*quả|from\s*the\s*(above|previous)\s*result)/i.test(lc);
    const mentionsIgnoreOrder = /(bỏ\s*qua\s*số\s*lệnh|bo\s*qua\s*so\s*lenh|ignore\s*(order|orders)|remove\s*(order|orders))/i.test(lc);
    const mentionsGroupBy = /(theo\s+|group\s*by|by\s+)/i.test(lc);

    if (!looksLikeFollowUp && !mentionsIgnoreOrder) return null;

    if (mentionsIgnoreOrder) {
      return { kind: "ignoreOrder", raw: s };
    }

    if (mentionsGroupBy) {
      const groupBy = parseGroupByFromText(lc);
      return { kind: "aggregate", groupBy, raw: s };
    }

    return null;
  };

  // Lấy API key: ưu tiên Vite env; nếu trống thì lấy từ localStorage (user nhập 1 lần)
  const getApiKey = () => {
    return DEFAULT_KEY || localStorage.getItem("SUN_API_KEY") || "";
  };

  const ensureApiKey = async () => {
    let key = getApiKey();
    if (!key) {
      key = window.prompt("Nhập API key (do DTHAUS cấp):")?.trim() || "";
      if (key) localStorage.setItem("SUN_API_KEY", key);
    }
    return key;
  };

  const parseChartSpecFromText = (text) => {
    const raw = String(text || "");
    const s = raw.toLowerCase();

    // We only support grouping choice for now (month / line / status).
    // Priority is based on first occurrence in text.
    const candidates = [
      {
        group: "month",
        patterns: [/theo\s*tháng/i, /by\s*month/i, /monthly/i, /month\b/i, /tháng\b/i],
      },
      {
        group: "line",
        patterns: [/theo\s*line/i, /by\s*line/i, /line\b/i, /dây\s*chuyền/i, /day\s*chuyen/i],
      },
      {
        group: "model",
        patterns: [/theo\s*model/i, /by\s*model/i, /model\b/i, /mã\s*model/i, /ma\s*model/i, /mã\s*hàng/i, /ma\s*hang/i],
      },
      {
        group: "status",
        patterns: [/theo\s*trạng\s*thái/i, /theo\s*trang\s*thai/i, /by\s*status/i, /status\b/i, /trạng\s*thái/i, /trang\s*thai/i],
      },
    ];

    const firstIndex = (patterns) => {
      let best = Number.POSITIVE_INFINITY;
      patterns.forEach((re) => {
        const m = s.match(re);
        if (m && typeof m.index === "number") best = Math.min(best, m.index);
      });
      return best;
    };

    let best = null;
    candidates.forEach((c) => {
      const idx = firstIndex(c.patterns);
      if (Number.isFinite(idx) && idx < (best?.idx ?? Number.POSITIVE_INFINITY)) {
        best = { idx, group: c.group };
      }
    });

    if (!best) return null;
    return { group: best.group };
  };

  const normalizeAnalyzeResponseToMessages = (userText, payload, currentLocale) => {
    const out = [];
    const decision = payload?.decision || {};
    const rows = payload?.planner_result?.data;
    const hasRows = Array.isArray(rows) && rows.length > 0;
    const chatText = payload?.chat_text;

    const wantsTable = /\b(table|bảng)\b/i.test(userText || "");
    const wantsChart = /\b(chart|graph|plot|đồ\s*thị|do\s*thi)\b/i.test(userText || "");

    const viz = String(decision?.viz || "").toLowerCase();
    const decisionSuggestsChart = viz.includes("chart") || viz.includes("bar") || viz.includes("line");

    // If backend returned a chat response (no MES), render it directly.
    if (typeof chatText === "string" && chatText.trim()) {
      out.push({
        sender: "ai",
        type: "text",
        locale: currentLocale,
        text: chatText.trim(),
      });
      if (!hasRows) return out;
    }

    // Always start with a short assistant text so the UI remains “chat-first”.
    if (hasRows) {
      const count = payload?.planner_result?.count ?? rows.length;
      const isVi = String(currentLocale || "en").toLowerCase().startsWith("vi");
      // Avoid mixed-language output like: "Fetched ... for dữ liệu".
      const target = isVi ? (decision?.target ? String(decision.target) : "dữ liệu") : "data";
      out.push({
        sender: "ai",
        type: "text",
        locale: currentLocale,
        text: t("ui.fetchedRows", currentLocale, { count, target }),
      });
    } else {
      out.push({
        sender: "ai",
        type: "text",
        locale: currentLocale,
        text: payload?.error
          ? t("ui.cannotFetchData", currentLocale, { error: String(payload.error) })
          : t("ui.noData", currentLocale),
      });
    }

    if (!hasRows) return out;

    // Render preference: explicit user request > decision.viz > fallback table
    const preferred = wantsTable ? "table" : (wantsChart || decisionSuggestsChart) ? "chart" : "table";

    const chartSpec = preferred === "chart" ? parseChartSpecFromText(userText) : null;

    if (preferred === "chart") {
      out.push({ sender: "ai", type: "chart", locale: currentLocale, rows, decision, chartSpec });
    } else {
      out.push({ sender: "ai", type: "table", locale: currentLocale, rows, decision });
    }

    return out;
  };

  const detectRenderIntent = (text) => {
    const t = String(text || "").trim();
    if (!t) return null;
    const wantsChart = /\b(chart|graph|plot|đồ\s*thị|do\s*thi|ve\s*chart|vẽ\s*chart|vẽ\s*đồ\s*thị|ve\s*do\s*thi)\b/i.test(t);
    const wantsTable = /\b(table|bảng|bang|hiện\s*bảng|show\s*table)\b/i.test(t);
    if (!wantsChart && !wantsTable) return null;

    // If it's clearly a data query, let backend handle it.
    // NOTE: render-commands may contain "theo ..." (e.g. "vẽ chart theo tháng"),
    // so we only treat it as a query when it includes fetching/analysis verbs.
    const looksLikeQuery = /(thống\s*kê|report|tìm|search|lấy|liệt\s*kê|trong\s+|bao\s*nhiêu|sản\s*lượng|yield|defect)/i.test(t);
    const looksLikeRender = /(vẽ|ve|hiện|hien|show|render|draw|plot)/i.test(t);
    if (looksLikeQuery && !looksLikeRender) return null;

    return {
      type: wantsChart ? "chart" : "table",
      chartSpec: wantsChart ? parseChartSpecFromText(t) : null,
    };
  };

  const findLastDataset = (msgs) => {
    for (let i = (msgs || []).length - 1; i >= 0; i -= 1) {
      const m = msgs[i];
      if (m && Array.isArray(m.rows) && m.rows.length > 0) {
        return { rows: m.rows, decision: m.decision || {} };
      }
    }
    return null;
  };

  const isChartableLineDataset = (rows) => {
    if (!Array.isArray(rows) || rows.length === 0) return false;
    // We render TopLinesChart which expects a grouping key (line/month/status) and numeric qty fields.
    return rows.some(
      (r) =>
        (r?.lineName || r?.lineId || r?.lineCode || r?.month || r?.productionStatusLabel || r?.productionStatusCode || r?.modelCode || r?.modelName) &&
        (r?.totalPlanQty !== undefined || r?.totalActualQty !== undefined || r?.planQty !== undefined || r?.actualQty !== undefined)
    );
  };

  const findLastChartableDataset = (msgs) => {
    for (let i = (msgs || []).length - 1; i >= 0; i -= 1) {
      const m = msgs[i];
      if (m && Array.isArray(m.rows) && isChartableLineDataset(m.rows)) {
        return { rows: m.rows, decision: m.decision || {} };
      }
    }
    return null;
  };

  const detectHideColumnTransform = (text) => {
    const s = String(text || "").trim();
    if (!s) return null;
    const lc = s.toLowerCase();
    const isHide = /(bỏ\s*cột|bo\s*cot|ẩn\s*cột|an\s*cot|hide\s*column|remove\s*column)/i.test(lc);
    if (!isHide) return null;

    const cols = [];
    const has = (re) => re.test(lc);

    if (has(/line\s*id|lineid|mã\s*dây\s*chuyền\s*id/i)) cols.push("lineId");
    if (has(/line\s*code|linecode|mã\s*dây\s*chuyền(?!\s*id)/i)) cols.push("lineCode");
    if (has(/order\b|orders\b|số\s*lệnh|so\s*lenh/i)) cols.push("orderCount", "orderNo", "poNo", "productionOrderNo");
    if (has(/model\s*code|mã\s*model|ma\s*model/i)) cols.push("modelCode");
    if (has(/model\s*name|tên\s*model|ten\s*model/i)) cols.push("modelName");

    // Process / operation (công đoạn)
    // - "Mã công đoạn" maps to code fields
    // - "Công đoạn" maps to label fields
    if (has(/mã\s*công\s*đoạn|ma\s*cong\s*doan|process\s*code/i)) cols.push("processTypeCode", "processTypes");
    if (has(/công\s*đoạn|cong\s*doan|process\s*type|process\b/i) && !has(/mã\s*công\s*đoạn|ma\s*cong\s*doan|process\s*code/i)) {
      cols.push("processTypeLabel", "processTypeLabels");
    }

    // If we can't map, do nothing (avoid accidental hiding)
    if (cols.length === 0) return null;
    return { kind: "hideColumns", columns: Array.from(new Set(cols)) };
  };

  const detectSortTransform = (text) => {
    const s = String(text || "").trim();
    if (!s) return null;
    const lc = s.toLowerCase();
    const isSort = /(order\s*by|sort\s*by|xếp\s*theo|sap\s*xep\s*theo|sắp\s*xếp\s*theo)/i.test(lc);
    if (!isSort) return null;

    const dir = /(asc|ascending|tăng\s*dần|tang\s*dan)/i.test(lc) ? "asc" : /(desc|descending|giảm\s*dần|giam\s*dan)/i.test(lc) ? "desc" : "desc";

    const field =
      /(line\s*code|linecode|mã\s*dây\s*chuyền\b|ma\s*day\s*chuyen\b)/i.test(lc)
        ? "lineCode"
        : /(line\s*name|tên\s*dây\s*chuyền\b|ten\s*day\s*chuyen\b)/i.test(lc)
          ? "lineName"
          : /\bline\b/i.test(lc)
            ? "lineCode"
            : /(model\s*code|modelcode|mã\s*model\b|ma\s*model\b)/i.test(lc)
              ? "modelCode"
              : /(model\s*name|tên\s*model\b|ten\s*model\b)/i.test(lc)
                ? "modelName"
                : /\bmodel\b/i.test(lc)
                  ? "modelCode"
                  : /(month|tháng|thang)/i.test(lc)
                    ? "month"
                    : /(status|trạng\s*thái|trang\s*thai)/i.test(lc)
                      ? "productionStatusLabel"
                      : /(actual|thực\s*tế|thuc\s*te)/i.test(lc)
                        ? "totalActualQty"
                        : /(plan|planned|kế\s*hoạch|ke\s*hoach)/i.test(lc)
                          ? "totalPlanQty"
                          : /(defect|lỗi|loi)/i.test(lc)
                            ? "totalDefectQty"
                            : /(tact|takt)/i.test(lc)
                              ? "avgTactTime"
                              : null;

    if (!field) return null;
    return { kind: "sort", field, direction: dir };
  };

  const sendMessage = async (text) => {
      // If a request is in flight, don't allow sending another one.
      // User can cancel via the Send button (loading state).
      if (loading) return;
    const nextLocale = detectLocaleFromText(text);
    setLocale(nextLocale);
    const userMsg = { sender: "user", type: "text", locale: nextLocale, text };
    setMessages((prev) => [...prev, userMsg]);

    // If we are waiting for factory selection, treat this message as the selection.
    if (pendingFactory?.originalText) {
      const selected = detectFactoryCodes(text);
      if (!selected || selected.length === 0) {
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: nextLocale.startsWith("vi")
              ? "Bạn vui lòng nhập mã nhà máy (ví dụ: FAC01 hoặc FAC01, DJVN1)."
              : "Please provide factory code(s) (e.g., FAC01 or FAC01, DJVN1).",
          },
        ]);
        return;
      }
      setFactoryCodes(selected);
      const originalText = pendingFactory.originalText;
      const originalLocale = pendingFactory.locale || nextLocale;
      setPendingFactory(null);
      try {
        await sendToBackend(originalText, originalLocale, selected);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          { sender: "ai", type: "text", locale: originalLocale, text: t("ui.apiError", originalLocale, { error: String(err) }) },
        ]);
      } finally {
        setLoading(false);
      }
      return;
    }

    // Handle confirmation replies for pending follow-up.
    if (pendingFollowUp?.kind === "confirmHideGroupBy") {
      const lc = String(text || "").trim().toLowerCase();
      const chooseRefresh = /^(1|làm\s*mới|lam\s*moi|refresh|yes|y|ok)$/i.test(lc);
      const chooseHideOnly = /^(2|ẩn|an|hide|no|n)$/i.test(lc);

      const payload = pendingFollowUp;
      setPendingFollowUp(null);

      const isVi = String(payload?.locale || nextLocale || "en").toLowerCase().startsWith("vi");

      if (chooseHideOnly) {
        const dataset = findLastDataset(messages);
        const lastTable = findLastTableMessage(messages);
        if (!dataset || !lastTable) {
          setMessages((prev) => [
            ...prev,
            { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
          ]);
          return;
        }

        const baseHidden = Array.isArray(lastTable.hiddenColumns) ? lastTable.hiddenColumns.map(String) : [];
        const cols = (payload.columns || []).map(String);
        const nextHidden = Array.from(new Set([...baseHidden, ...cols]));

        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: t("ui.confirmHideGroupByHideOnlyAck", nextLocale),
          },
          {
            sender: "ai",
            type: "table",
            locale: nextLocale,
            rows: dataset.rows,
            decision: dataset.decision,
            hiddenColumns: nextHidden,
            groupBy: lastTable.groupBy || lastTable.decision?.group_by || null,
          },
        ]);
        return;
      }

      if (chooseRefresh) {
        const original = payload.originalQueryText || lastDataQuery?.text;
        const factoryForRefresh = payload.factoryCodes || lastDataQuery?.factoryCodes || factoryCodes;
        const currentDims = Array.isArray(payload.currentDims) ? payload.currentDims : [];
        const affectedDims = Array.isArray(payload.affectedDims) ? payload.affectedDims : [];
        const nextDims = currentDims.filter((d) => !affectedDims.map((x) => String(x).toLowerCase()).includes(String(d).toLowerCase()));

        if (!original) {
          setMessages((prev) => [
            ...prev,
            {
              sender: "ai",
              type: "text",
              locale: nextLocale,
              text: t("ui.confirmHideGroupByNoOriginal", nextLocale),
            },
          ]);
          return;
        }

        const affectedPhrase = dimsToPhrase(affectedDims, nextLocale);
        const nextPhrase = dimsToPhrase(nextDims, nextLocale);

        const refreshText = nextDims.length
          ? `${original}\n\n${isVi ? `Làm mới dữ liệu và tổng hợp theo ${nextPhrase}. Không tổng hợp theo ${affectedPhrase}.` : `Refresh and group by ${nextPhrase}. Do not group by ${affectedPhrase}.`}`
          : `${original}\n\n${isVi ? `Làm mới dữ liệu và KHÔNG group by ${affectedPhrase}.` : `Refresh and do NOT group by ${affectedPhrase}.`}`;

        try {
          await sendToBackend(refreshText, nextLocale, factoryForRefresh);
        } catch (err) {
          setMessages((prev) => [
            ...prev,
            { sender: "ai", type: "text", locale: nextLocale, text: t("ui.apiError", nextLocale, { error: String(err) }) },
          ]);
        } finally {
          setLoading(false);
        }
        return;
      }

      // Unknown reply -> ask again
      setPendingFollowUp(payload);
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "text",
          locale: nextLocale,
          text: t("ui.confirmHideGroupByAskAgain", nextLocale),
        },
      ]);
      return;
    }

    if (pendingFollowUp?.kind === "ignoreOrder") {
      const lc = String(text || "").toLowerCase();
      const chooseHide = /(1|ẩn|an|hide)/i.test(lc);
      const chooseAgg = /(2|tổng\s*hợp|tong\s*hop|aggregate|summary)/i.test(lc);

      const dataset = findLastDataset(messages);
      setPendingFollowUp(null);

      if (!dataset) {
        setMessages((prev) => [
          ...prev,
          { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
        ]);
        return;
      }

      if (chooseHide) {
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "table",
            locale: nextLocale,
            rows: dataset.rows,
            decision: dataset.decision,
            hiddenColumns: ["orderCount", "orderNo", "orderId", "planId", "poNo", "poId", "productionOrderNo", "productionOrderId", "pk"],
          },
        ]);
        return;
      }

      if (chooseAgg) {
        // If user didn't specify dims, ask for group-by.
        setPendingFollowUp({ kind: "askGroupBy" });
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: nextLocale.startsWith("vi")
              ? "Bạn muốn tổng hợp theo gì? Ví dụ: ‘theo tháng và line’ hoặc ‘theo model’."
              : "Which grouping do you want? Example: 'by month and line' or 'by model'.",
          },
        ]);
        return;
      }

      // Unknown reply -> ask again
      setPendingFollowUp({ kind: "ignoreOrder" });
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "text",
          locale: nextLocale,
          text: nextLocale.startsWith("vi")
            ? "Mình chưa rõ ý bạn. Bạn chọn: (1) Ẩn cột số lệnh, hay (2) Tổng hợp lại (aggregate)?"
            : "I didn't catch that. Choose: (1) hide order column, or (2) aggregate (summary)?",
        },
      ]);
      return;
    }

    if (pendingFollowUp?.kind === "askGroupBy") {
      const groupBy = parseGroupByFromText(text);
      const dataset = findLastDataset(messages);
      setPendingFollowUp(null);

      if (!dataset) {
        setMessages((prev) => [
          ...prev,
          { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
        ]);
        return;
      }

      if (!groupBy || groupBy.length === 0) {
        setPendingFollowUp({ kind: "askGroupBy" });
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: nextLocale.startsWith("vi")
              ? "Bạn hãy nói rõ group-by (vd: theo tháng và line / theo model / theo trạng thái)."
              : "Please specify a group-by (e.g. by month and line / by model / by status).",
          },
        ]);
        return;
      }

      const nextRows = aggregateRows(dataset.rows, groupBy);
      const visibleColumns = parseMetricSelection(text, groupBy);
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "table",
          locale: nextLocale,
          rows: nextRows,
          decision: dataset.decision,
          visibleColumns,
          groupBy,
        },
      ]);
      return;
    }

    // Client-side render commands like: "vẽ chart cho mình" based on last dataset.
    const renderIntent = detectRenderIntent(text);
    if (renderIntent) {
      const dataset = renderIntent.type === "chart" ? findLastChartableDataset(messages) : findLastDataset(messages);
      if (!dataset) {
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: renderIntent.type === "chart" ? t("ui.noChartableDataset", nextLocale) : t("ui.noLastDataset", nextLocale),
          },
        ]);
        return;
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "text",
          locale: nextLocale,
          text: renderIntent.type === "chart" ? t("ui.renderChartFromLast", nextLocale) : t("ui.renderTableFromLast", nextLocale),
        },
        {
          sender: "ai",
          type: renderIntent.type,
          locale: nextLocale,
          rows: dataset.rows,
          decision: dataset.decision,
          chartSpec: renderIntent.chartSpec,
        },
      ]);
      return;
    }

    // Follow-up column visibility commands (hide/show) based on last dataset.
    // If the message is also a data request, let backend fetch data first and
    // apply inline transform after we get the result.
    const colTransform = detectColumnVisibilityTransform(text);
    if (colTransform && !looksLikeDataRequest(text)) {
      const dataset = findLastDataset(messages);
      if (!dataset) {
        setMessages((prev) => [
          ...prev,
          { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
        ]);
        return;
      }

      const lastTable = findLastTableMessage(messages);
      const baseHidden = Array.isArray(lastTable?.hiddenColumns) ? lastTable.hiddenColumns.map(String) : [];
      const cols = (colTransform.columns || []).map(String);
      const nextHidden =
        colTransform.kind === "showColumns" ? baseHidden.filter((c) => !cols.includes(String(c))) : Array.from(new Set([...baseHidden, ...cols]));

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "table",
          locale: nextLocale,
          rows: dataset.rows,
          decision: dataset.decision,
          hiddenColumns: nextHidden,
        },
      ]);
      return;
    }

    // Follow-up sort (e.g., "order by actual desc") based on last dataset
    const sortTransform = detectSortTransform(text);
    if (sortTransform) {
      const dataset = findLastDataset(messages);
      if (!dataset) {
        setMessages((prev) => [
          ...prev,
          { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
        ]);
        return;
      }

      const rowsCopy = Array.isArray(dataset.rows) ? [...dataset.rows] : [];
      const reverse = sortTransform.direction !== "asc";

      const normalizeForCompare = (v) => {
        if (v === null || v === undefined) return { kind: "missing", value: null };
        if (typeof v === "number" && Number.isFinite(v)) return { kind: "number", value: v };
        const n = Number(v);
        if (Number.isFinite(n) && String(v).trim() !== "") return { kind: "number", value: n };
        return { kind: "string", value: String(v) };
      };

      rowsCopy.sort((a, b) => {
        const va = normalizeForCompare(a?.[sortTransform.field]);
        const vb = normalizeForCompare(b?.[sortTransform.field]);

        // Missing values always last
        if (va.kind === "missing" && vb.kind === "missing") return 0;
        if (va.kind === "missing") return 1;
        if (vb.kind === "missing") return -1;

        // Prefer numeric compare when both numeric
        if (va.kind === "number" && vb.kind === "number") {
          if (va.value < vb.value) return reverse ? 1 : -1;
          if (va.value > vb.value) return reverse ? -1 : 1;
          return 0;
        }

        // Fallback to string compare
        const sa = String(va.value);
        const sb = String(vb.value);
        const cmp = sa.localeCompare(sb);
        return reverse ? -cmp : cmp;
      });

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "table",
          locale: nextLocale,
          rows: rowsCopy,
          decision: dataset.decision,
        },
      ]);
      return;
    }

    // Follow-up transforms based on last dataset
    const followUp = detectFollowUpTransform(text);
    if (followUp) {
      const dataset = findLastDataset(messages);
      if (!dataset) {
        setMessages((prev) => [
          ...prev,
          { sender: "ai", type: "text", locale: nextLocale, text: t("ui.noLastDataset", nextLocale) },
        ]);
        return;
      }

      if (followUp.kind === "ignoreOrder") {
        setPendingFollowUp({ kind: "ignoreOrder" });
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "text",
            locale: nextLocale,
            text: nextLocale.startsWith("vi")
              ? "Bạn muốn: (1) Ẩn cột số lệnh, hay (2) Tổng hợp lại (aggregate) không theo số lệnh?"
              : "Do you want: (1) hide the order column, or (2) aggregate (summary) without order?",
          },
        ]);
        return;
      }

      if (followUp.kind === "aggregate") {
        const groupBy = followUp.groupBy || [];
        if (groupBy.length === 0) {
          setPendingFollowUp({ kind: "askGroupBy" });
          setMessages((prev) => [
            ...prev,
            {
              sender: "ai",
              type: "text",
              locale: nextLocale,
              text: nextLocale.startsWith("vi")
                ? "Bạn muốn tổng hợp theo gì? Ví dụ: ‘theo tháng và line’ hoặc ‘theo model’."
                : "Which grouping do you want? Example: 'by month and line' or 'by model'.",
            },
          ]);
          return;
        }
        const nextRows = aggregateRows(dataset.rows, groupBy);
        const visibleColumns = parseMetricSelection(text, groupBy);
        setMessages((prev) => [
          ...prev,
          {
            sender: "ai",
            type: "table",
            locale: nextLocale,
            rows: nextRows,
            decision: dataset.decision,
            visibleColumns,
            groupBy,
          },
        ]);
        return;
      }
    }

    const inlineFactoryCodes = detectFactoryCodes(text);
    if (inlineFactoryCodes.length) setFactoryCodes(inlineFactoryCodes);
    const ctxFactoryCodes = inlineFactoryCodes.length ? inlineFactoryCodes : factoryCodes;

    // Require factory context only when the message looks like a data request.
    if (looksLikeDataRequest(text) && (!ctxFactoryCodes || ctxFactoryCodes.length === 0)) {
      setPendingFactory({ originalText: text, locale: nextLocale });
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          type: "text",
          locale: nextLocale,
          text: nextLocale.startsWith("vi")
            ? "Bạn đang hỏi dữ liệu của nhà máy nào? (ví dụ: FAC01 hoặc FAC01, DJVN1)"
            : "Which factory is this for? (e.g., FAC01 or FAC01, DJVN1)",
        },
      ]);
      return;
    }

    try {
      await sendToBackend(text, nextLocale, ctxFactoryCodes);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", type: "text", locale: nextLocale, text: t("ui.apiError", nextLocale, { error: String(err) }) },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="header-inner">
          <span className="logo-emoji">🤖</span>
          <span className="app-title">DTHAUS AI Assistant</span>
        </div>
      </header>
      <main className="app-main">
        <section className="chat-shell">
          <ChatWindow messages={messages} isLoading={loading} locale={locale} />
          <ChatInput onSend={sendMessage} isLoading={loading} onCancel={() => {
            try {
              inFlightAbortRef.current?.abort?.();
            } catch {
              // ignore
            }
            inFlightAbortRef.current = null;
            setLoading(false);
            setMessages((prev) => [
              ...prev,
              { sender: "ai", type: "text", locale, text: t("ui.requestCancelled", locale) },
            ]);
          }} locale={locale} />
        </section>
      </main>
    </div>
  );
}

export default App;
