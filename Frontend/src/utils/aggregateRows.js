function toMonthString(value) {
  if (!value) return null;
  const s = String(value);

  // Accept YYYY-MM directly
  if (/^\d{4}-\d{2}$/.test(s)) return s;

  // ISO date or date-time
  const d = new Date(s);
  if (!Number.isNaN(d.getTime())) {
    const y = d.getUTCFullYear();
    const m = d.getUTCMonth() + 1;
    return `${y.toString().padStart(4, "0")}-${m.toString().padStart(2, "0")}`;
  }

  // YYYY-MM-DD
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}`;

  return null;
}

function extractLine(row) {
  if (!row || typeof row !== "object") return { lineCode: null, lineId: null, lineName: null };
  const lineName = row.lineName || row.line_name || row?.line?.name || null;
  const lineCode = row.lineCode || row.line_code || row?.line?.parentCode?.code || row?.line?.code || row?.line?.pk?.code || null;
  const lineId = row.lineId || row.line_id || row?.line?.pk?.id || row?.line?.id || null;
  return { lineCode, lineId, lineName };
}

function extractStatus(row) {
  if (!row || typeof row !== "object") return { productionStatusCode: null, productionStatusLabel: null };
  const code = row.productionStatusCode || row?.prodStatus?.code || row?.prodStatusCode || null;
  const label = row.productionStatusLabel || row?.prodStatus?.name || row?.prodStatusLabel || null;
  return { productionStatusCode: code, productionStatusLabel: label };
}

function extractModel(row) {
  if (!row || typeof row !== "object") return { modelCode: null, modelName: null };

  // Aggregated result shape
  if (row.modelCode || row.modelName) {
    return { modelCode: row.modelCode || null, modelName: row.modelName || null };
  }

  const modelObj = row.modelId || row.model || null;
  if (modelObj && typeof modelObj === "object") {
    const parent = modelObj.parentCode;
    if (parent && typeof parent === "object") {
      return { modelCode: parent.code || null, modelName: parent.name || parent.description || null };
    }
    return {
      modelCode: modelObj.code || modelObj.modelCode || null,
      modelName: modelObj.name || modelObj.modelName || modelObj.description || null,
    };
  }

  return { modelCode: row.modelCode || null, modelName: row.modelName || null };
}

function extractMonth(row) {
  if (!row || typeof row !== "object") return null;
  return (
    row.month ||
    toMonthString(row.planDate) ||
    toMonthString(row.plan_date) ||
    toMonthString(row.startTime) ||
    toMonthString(row.planStartDate) ||
    toMonthString(row.date) ||
    null
  );
}

function extractDate(row) {
  if (!row || typeof row !== "object") return null;
  const raw =
    row.date ||
    row.planDate ||
    row.plan_date ||
    row.planStartDate ||
    row.planStartTime ||
    row.startTime ||
    row.planStart ||
    null;
  if (!raw) return null;
  const s = String(raw);
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const d = new Date(s);
  if (!Number.isNaN(d.getTime())) {
    const y = d.getUTCFullYear();
    const m = d.getUTCMonth() + 1;
    const day = d.getUTCDate();
    return `${y.toString().padStart(4, "0")}-${m.toString().padStart(2, "0")}-${day.toString().padStart(2, "0")}`;
  }
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  return null;
}

function extractYear(row) {
  const d = extractDate(row);
  if (!d) return null;
  const y = Number(d.slice(0, 4));
  return Number.isFinite(y) ? y : null;
}

function extractQuarter(row) {
  const d = extractDate(row);
  if (!d) return null;
  const y = d.slice(0, 4);
  const m = Number(d.slice(5, 7));
  if (!Number.isFinite(m) || m < 1 || m > 12) return null;
  const q = Math.floor((m - 1) / 3) + 1;
  return `${y}-Q${q}`;
}

function extractWeek(row) {
  // ISO week (UTC) => YYYY-Www
  const d = extractDate(row);
  if (!d) return null;
  const dt = new Date(`${d}T00:00:00Z`);
  if (Number.isNaN(dt.getTime())) return null;
  // ISO week algorithm
  const tmp = new Date(Date.UTC(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate()));
  const dayNum = tmp.getUTCDay() || 7;
  tmp.setUTCDate(tmp.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((tmp - yearStart) / 86400000 + 1) / 7);
  const isoYear = tmp.getUTCFullYear();
  return `${isoYear.toString().padStart(4, "0")}-W${weekNo.toString().padStart(2, "0")}`;
}

function extractProcessType(row) {
  if (!row || typeof row !== "object") return { processTypeCode: null, processTypeLabel: null };
  const code = row.processTypeCode || row?.process?.code || null;
  const label = row.processTypeLabel || row?.process?.name || row?.process?.displayName || null;
  return { processTypeCode: code, processTypeLabel: label };
}

function asNumber(v) {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
}

export function aggregateRows(rows, groupBy = []) {
  if (!Array.isArray(rows) || rows.length === 0) return [];
  const dims = Array.isArray(groupBy) ? groupBy.filter(Boolean) : [];
  if (dims.length === 0) return rows;

  const acc = new Map();

  rows.forEach((row) => {
    const group = {};
    const keyParts = [];

    dims.forEach((dim) => {
      if (dim === "date") {
        const date = extractDate(row);
        group.date = date;
        keyParts.push(date || "__unknown__");
      } else if (dim === "week") {
        const week = extractWeek(row);
        group.week = week;
        keyParts.push(week || "__unknown__");
      } else if (dim === "quarter") {
        const quarter = extractQuarter(row);
        group.quarter = quarter;
        keyParts.push(quarter || "__unknown__");
      } else if (dim === "year") {
        const year = extractYear(row);
        group.year = year;
        keyParts.push(year ?? "__unknown__");
      } else if (dim === "month") {
        const month = extractMonth(row);
        group.month = month;
        keyParts.push(month || "__unknown__");
      } else if (dim === "line") {
        const { lineCode, lineId, lineName } = extractLine(row);
        group.lineCode = lineCode;
        group.lineId = lineId;
        group.lineName = lineName;
        keyParts.push(lineCode ?? lineId ?? lineName ?? "__unknown__");
      } else if (dim === "model") {
        const { modelCode, modelName } = extractModel(row);
        group.modelCode = modelCode;
        group.modelName = modelName;
        keyParts.push(modelCode ?? modelName ?? "__unknown__");
      } else if (dim === "status") {
        const { productionStatusCode, productionStatusLabel } = extractStatus(row);
        group.productionStatusCode = productionStatusCode;
        group.productionStatusLabel = productionStatusLabel;
        keyParts.push(productionStatusCode ?? productionStatusLabel ?? "__unknown__");
      } else if (dim === "processType") {
        const { processTypeCode, processTypeLabel } = extractProcessType(row);
        group.processTypeCode = processTypeCode;
        group.processTypeLabel = processTypeLabel;
        keyParts.push(processTypeCode ?? processTypeLabel ?? "__unknown__");
      }
    });

    const k = JSON.stringify(keyParts);
    if (!acc.has(k)) {
      acc.set(k, {
        ...group,
        __count: 0,
        totalPlanQty: 0,
        totalActualQty: 0,
        totalDefectQty: 0,
        __sumTact: 0,
        __hasTact: false,
      });
    }

    const out = acc.get(k);
    out.__count += 1;

    out.totalPlanQty += asNumber(row.totalPlanQty ?? row.planQty);
    out.totalActualQty += asNumber(row.totalActualQty ?? row.actualQty);
    out.totalDefectQty += asNumber(row.totalDefectQty ?? row.defectQty);

    if (row.tactTime !== undefined && row.tactTime !== null) {
      out.__sumTact += asNumber(row.tactTime);
      out.__hasTact = true;
    }
  });

  return Array.from(acc.values()).map((v) => {
    const count = v.__count || 0;
    const avgTactTime = v.__hasTact && count ? v.__sumTact / count : v.avgTactTime;

    const { __count, __sumTact, __hasTact, ...rest } = v;
    return {
      ...rest,
      avgTactTime: avgTactTime ?? null,
    };
  });
}
