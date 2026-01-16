import termsEn from "../i18n/terms.en.json";
import termsVi from "../i18n/terms.vi.json";
import glossaryVi from "../i18n/glossary.vi.json";

// Map raw JSON keys -> shared terminology keys.
// This keeps terminology in ONE place (terms.*.json) even if raw keys differ.
const KEY_TO_TERM = {
  factoryCode: "factoryCode",
  shift: "shift",
  date: "date",
  week: "week",
  quarter: "quarter",
  year: "year",
  month: "month",
  lineName: "lineName",
  lineId: "lineId",
  lineCode: "lineCode",
  model: "model",
  modelCode: "modelCode",
  modelName: "modelName",

  processTypeCode: "processTypeCode",
  processTypeLabel: "processType",

  orderCount: "orders",

  totalPlanQty: "plannedQty",
  totalActualQty: "actualQty",
  totalDefectQty: "defectQty",

  // New KPI engine keys
  plan_qty: "plannedQty",
  actual_production_qty: "actualQty",
  defect_count: "defectQty",
  defect_ppm: "defectPpm",

  avgTactTime: "avgTactTime",
  yield: "yield",
  defectRate: "defectRate",

  productionStatusCodes: "productionStatusCode",
  productionStatusLabels: "productionStatus",
  productionStatusCount: "statusCount",

  processTypes: "processTypeCode",
  processTypeLabels: "processType",
  processTypeCount: "processCount",
};

export function detectLocaleFromText(text) {
  const t = String(text || "");
  // Very small heuristic: Vietnamese diacritics or common particles
  const hasDiacritics = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(t);
  const looksVi = hasDiacritics || /(\b(thống\s*kê|sản\s*lượng|dây\s*chuyền|bảng|đồ\s*thị|vẽ)\b)/i.test(t);
  return looksVi ? "vi" : "en";
}

export function humanizeKeyToEnglishLabel(key) {
  if (!key) return "";
  const s = String(key)
    .replace(/_/g, " ")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function translateEnglishToVietnamese(englishLabel) {
  const tokens = String(englishLabel || "")
    .split(/\s+/)
    .filter(Boolean);
  if (tokens.length === 0) return "";

  const translated = tokens.map((w) => glossaryVi[w] || w);
  return translated.join(" ");
}

export function getColumnTitle(key, locale = "en") {
  const lc = String(locale || "en").toLowerCase();

  const rawKey = String(key || "").trim();

  // Heuristic: if backend (or user-followups) produce mixed VN/EN labels as keys,
  // map them back to canonical term keys so column headers stay fully localized.
  // Example: "Thực tế production qty" -> actualQty -> "Số lượng thực tế" (vi) / "Actual Qty" (en)
  const inferredTermKey = (() => {
    if (!rawKey) return null;
    const k = rawKey.toLowerCase();
    const hasProdQty = /production\s*qty|prod\s*qty|\bqty\b/.test(k);
    if (hasProdQty && /(thực\s*tế|thuc\s*te|\bactual\b)/.test(k)) return "actualQty";
    if (hasProdQty && /(kế\s*hoạch|ke\s*hoach|\bplan(ned)?\b)/.test(k)) return "plannedQty";
    if (/(ppm)/.test(k) && /(defect|lỗi|loi)/.test(k)) return "defectPpm";
    if (/(defect|lỗi|loi)/.test(k) && /(qty|count|số\s*lượng)/.test(k)) return "defectQty";
    if (/(ngày|\bdate\b)/.test(k)) return "date";
    if (/(ca|\bshift\b)/.test(k)) return "shift";
    return null;
  })();

  // 1) Key -> English label (central)
  const termKey = KEY_TO_TERM[rawKey] || inferredTermKey || rawKey;
  const englishLabel = termsEn[termKey] || humanizeKeyToEnglishLabel(key);

  // 2) Translate to target locale (currently vi/en; others fallback en)
  if (lc.startsWith("vi")) {
    // Prefer term->vi mapping (best quality)
    if (termsVi[termKey]) return termsVi[termKey];
    // Otherwise, attempt word-by-word glossary translation
    return translateEnglishToVietnamese(englishLabel);
  }

  return englishLabel;
}

export const DEFAULT_COLUMN_ORDER = [
  "factoryCode",
  "shift",
  "date",
  "lineCode",
  "lineName",
  "model",
  "orderCount",
  "totalPlanQty",
  "totalActualQty",
  "totalDefectQty",
  "plan_qty",
  "actual_production_qty",
  "defect_count",
  "defect_ppm",
  "avgTactTime",
  "yield",
  "defectRate",
  "productionStatusLabels",
  "productionStatusCodes",
  "processTypeLabels",
  "processTypes",
];
