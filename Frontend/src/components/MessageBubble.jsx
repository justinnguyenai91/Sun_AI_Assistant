// Frontend/src/components/MessageBubble.jsx
import React, { useMemo } from "react";
import TopLinesChart from "./TopLinesChart.jsx";
import ExportButton from "./ExportButton.jsx";
import CollapsibleTable from "./CollapsibleTable.jsx";
import { DEFAULT_COLUMN_ORDER, getColumnTitle } from "../utils/columnI18n.js";
import { getMetricColorClass, detectMetricType } from "../utils/tableHelpers.js";
import { IconTrash } from "./Icons.jsx";

function isRecord(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function TableMessage({ rows, locale, hiddenColumns, visibleColumns, groupBy }) {
  const columns = useMemo(() => {
    const keys = new Set();
    (rows || []).forEach((r) => Object.keys(r || {}).forEach((k) => keys.add(k)));
    const hide = new Set((hiddenColumns || []).map(String));
    // If backend provides both, prefer showing lineCode (not PK-like lineId)
    if (keys.has("lineCode") && keys.has("lineId") && !(Array.isArray(visibleColumns) && visibleColumns.includes("lineId"))) {
      hide.add("lineId");
    }

    const metricKeys = new Set([
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
      "orderCount",
    ]);

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
      dims.forEach((d) => {
        const dim = String(d || "").toLowerCase();
        if (dim === "factory" || dim === "factorycode") add("factoryCode");
        if (dim === "date") add("date");
        else if (dim === "shift") add("shift");
        else if (dim === "week") add("week");
        else if (dim === "quarter") add("quarter");
        else if (dim === "year") add("year");
        else if (dim === "month") add("month");
        else if (dim === "line") add("lineCode", "lineName", "lineId");
        else if (dim === "model") add("modelCode", "modelName");
        else if (dim === "prodstatus" || dim === "status") add("productionStatusLabel", "productionStatusCode", "productionStatusLabels", "productionStatusCodes");
        else if (dim === "processtype" || dim === "process") add("processTypeLabel", "processTypeCode");
      });
      return out;
    };

    const dims = normalizeGroupBy(groupBy);

    // We allow hiding group-by keys after user confirmation (handled in App.jsx).

    const groupPreferred = dims.length
      ? groupColsFromDims(dims)
      : [
          "factoryCode",
          "shift",
          "month",
          "lineCode",
          "lineName",
          "lineId",
          "modelCode",
          "modelName",
          "productionStatusLabel",
          "productionStatusCode",
          "productionStatusLabels",
          "productionStatusCodes",
        ];

    // Always prefer factory/shift/date on the far left if present.
    ["factoryCode", "shift", "date"].forEach((k) => {
      if (keys.has(k) && !hide.has(k) && !groupPreferred.includes(k)) groupPreferred.unshift(k);
    });

    if (Array.isArray(visibleColumns) && visibleColumns.length > 0) {
      const vis = visibleColumns.map(String);
      return vis.filter((k) => keys.has(k) && !hide.has(k));
    }

    const all = Array.from(keys).filter((k) => !hide.has(k));

    const ordered = [];

    // 1) Group-by-ish columns on the left
    groupPreferred.forEach((k) => {
      if (keys.has(k) && !hide.has(k) && !ordered.includes(k)) ordered.push(k);
    });

    // 2) Non-metric middle columns
    all
      .filter((k) => !ordered.includes(k) && !metricKeys.has(k))
      .sort((a, b) => String(a).localeCompare(String(b)))
      .forEach((k) => ordered.push(k));

    // 3) Metrics on the right (stable order)
    DEFAULT_COLUMN_ORDER.forEach((k) => {
      if (keys.has(k) && !hide.has(k) && !ordered.includes(k) && metricKeys.has(k)) ordered.push(k);
    });
    all
      .filter((k) => !ordered.includes(k) && metricKeys.has(k))
      .sort((a, b) => String(a).localeCompare(String(b)))
      .forEach((k) => ordered.push(k));

    return ordered;
  }, [rows, hiddenColumns, visibleColumns, groupBy]);

  const groupHideWarning = useMemo(() => {
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

    const dims = normalizeGroupBy(groupBy);
    if (!dims.length) return null;

    const requested = new Set((hiddenColumns || []).map(String));
    if (!requested.size) return null;

    const protectedCols = new Set();
    dims.forEach((d) => {
      const dim = String(d || "").toLowerCase();
      if (dim === "date") protectedCols.add("date");
      else if (dim === "week") protectedCols.add("week");
      else if (dim === "quarter") protectedCols.add("quarter");
      else if (dim === "year") protectedCols.add("year");
      else if (dim === "month") protectedCols.add("month");
      else if (dim === "line") {
        protectedCols.add("lineCode");
        protectedCols.add("lineName");
      } else if (dim === "model") {
        protectedCols.add("modelCode");
        protectedCols.add("modelName");
      } else if (dim === "prodstatus" || dim === "status") {
        protectedCols.add("productionStatusLabel");
        protectedCols.add("productionStatusCode");
      } else if (dim === "processtype" || dim === "process") {
        protectedCols.add("processTypeLabel");
        protectedCols.add("processTypeCode");
      }
    });

    const blocked = Array.from(requested).filter((c) => protectedCols.has(c));
    if (!blocked.length) return null;

    const titles = blocked.map((k) => getColumnTitle(k, locale)).join(", ");
    const isVi = String(locale || "en").toLowerCase().startsWith("vi");
    return isVi
      ? `Lưu ý: bạn đã ẩn cột thuộc group by (${titles}) nên có thể gây hiểu nhầm khi đọc bảng.`
      : `Note: you've hidden group-by key columns (${titles}), which may be misleading.`;
  }, [hiddenColumns, groupBy, locale]);

  if (!Array.isArray(rows) || rows.length === 0) {
    return <div className="muted">No data</div>;
  }

  const formatShiftValue = (value) => {
    if (value === null || value === undefined) return value;
    const s = String(value).trim();
    if (!s) return value;
    // Common MES shift codes: D001001, D001002 ... => take trailing digits as shift number
    const m = s.match(/(\d{1,3})$/);
    if (!m) return value;
    const n = parseInt(m[1], 10);
    if (!Number.isFinite(n) || n <= 0) return value;
    const isVi = String(locale || "en").toLowerCase().startsWith("vi");
    return isVi ? `Ca ${n}` : `Shift ${n}`;
  };

  const fmt = (v) => {
    if (v === null || v === undefined) return "-";
    if (typeof v === "number") return v.toLocaleString();

    // Keep arrays readable but avoid flooding the table when items are objects.
    if (Array.isArray(v)) {
      const allPrimitive = v.every((x) => x === null || ["string", "number", "boolean"].includes(typeof x));
      if (allPrimitive) return v.join(", ");
      const json = JSON.stringify(v, null, 2) || "";
      const clipped = json.length > 2000 ? `${json.slice(0, 2000)}\n…` : json;
      return <pre className="cell-pre">{clipped}</pre>;
    }

    if (isRecord(v)) {
      const json = JSON.stringify(v, null, 2) || "";
      const clipped = json.length > 2500 ? `${json.slice(0, 2500)}\n…` : json;
      return <pre className="cell-pre">{clipped}</pre>;
    }

    const s = String(v);
    if (s.length > 500) return <pre className="cell-pre">{`${s.slice(0, 500)}…`}</pre>;
    return s;
  };

  const fmtCell = (col, v) => {
    if (String(col) === "shift") return fmt(formatShiftValue(v));
    
    // Check if this is a metric column and apply color coding
    const metricColumns = [
      'oee', 'quality', 'performance', 'availability',
      'totalActualQty', 'totalPlanQty', 'totalDefectQty',
      'defectRate', 'yield', 'defect_ppm', 'avgTactTime'
    ];
    
    const isMetric = metricColumns.some(m => 
      String(col).toLowerCase().includes(m.toLowerCase())
    );
    
    if (isMetric && typeof v === 'number') {
      const metricType = detectMetricType(String(col));
      const colorClass = getMetricColorClass(v, metricType);
      const formattedValue = v.toLocaleString();
      
      return (
        <span className={colorClass}>
          {formattedValue}
          {String(col).toLowerCase().includes('rate') && '%'}
        </span>
      );
    }
    
    return fmt(v);
  };

  const getTableTitle = () => {
    if (groupBy && Array.isArray(groupBy) && groupBy.length > 0) {
      const dims = groupBy.join(', ');
      return locale === 'vi' 
        ? `Dữ liệu theo ${dims}` 
        : `Data by ${dims}`;
    }
    return locale === 'vi' ? 'Bảng dữ liệu' : 'Data Table';
  };

  return (
    <div className="message-table">
      {groupHideWarning && <div className="muted" style={{ marginBottom: 8 }}>{groupHideWarning}</div>}
      
      {/* Export buttons */}
      <ExportButton data={rows} filename="mes_data" locale={locale} />
      
      <CollapsibleTable title={getTableTitle()} rows={rows} columns={columns}>
        <table className="result-table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c}>{getColumnTitle(c, locale)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, idx) => (
            <tr key={idx}>
              {columns.map((c) => (
                <td key={c}>{fmtCell(c, r?.[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      </CollapsibleTable>
    </div>
  );
}

function ChartMessage({ rows, decision, locale, chartSpec }) {
  const viz = String(decision?.viz || "").toLowerCase();
  const canUseTopLines = Array.isArray(rows) && rows.length > 0;

  const normalizedRows = React.useMemo(() => {
    if (!Array.isArray(rows) || rows.length === 0) return [];
    const group = chartSpec?.group;
    if (!group || group === "line") return rows;

    const toKey = (r) => {
      if (group === "month") return r?.month;
      if (group === "status") return r?.productionStatusLabel || r?.productionStatusCode;
      if (group === "model") return r?.modelCode || r?.modelName;
      return null;
    };

    // TopLinesChart aggregates by lineName/lineId.
    // We map the selected grouping value into a synthetic lineName.
    return rows
      .map((r) => {
        const key = toKey(r);
        if (!key) return r;
        return { ...r, lineName: String(key) };
      })
      .filter((r) => r?.lineName || r?.lineId);
  }, [rows, chartSpec]);

  // If the message type is already "chart", render chart whenever we can.
  // Don't depend on decision.viz because render-commands may not carry it.
  const hasNumeric = normalizedRows.some(
    (r) => r?.totalPlanQty !== undefined || r?.totalActualQty !== undefined || r?.planQty !== undefined || r?.actualQty !== undefined
  );

  if (canUseTopLines && hasNumeric) {
    return (
      <div className="message-chart">
        <TopLinesChart rows={normalizedRows} locale={locale} />
      </div>
    );
  }

  const msg = String(locale || "en").toLowerCase().startsWith("vi")
    ? "Không thể vẽ chart cho dữ liệu này. Hãy yêu cầu thống kê theo line (vd: ‘thống kê sản lượng 3 tháng theo line’)."
    : "Cannot render a chart for this dataset. Ask for a report grouped by line (e.g., 'production report by line for last 3 months').";

  return <div className="muted">{msg}</div>;
}

export default function MessageBubble({ message, onDelete }) {
  const sender = message?.sender || "ai";
  const type = message?.type || "text";
  const senderLc = String(sender || "").toLowerCase();
  const isUser = senderLc === "user" || senderLc === "human" || senderLc === "me";
  const locale = message?.locale || "en";

  const wide = !isUser && (type === "chart" || type === "table");

  return (
    <div className={`message-row ${isUser ? "right" : "left"}`}>
      {/* Avatar cho AI */}
      {!isUser && (
        <div className="message-avatar">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="24" height="24" rx="6" fill="url(#avatar-gradient)"/>
            <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 5C13.66 5 15 6.34 15 8C15 9.66 13.66 11 12 11C10.34 11 9 9.66 9 8C9 6.34 10.34 5 12 5ZM12 19.2C9.5 19.2 7.29 17.92 6 15.98C6.03 13.99 10 12.9 12 12.9C13.99 12.9 17.97 13.99 18 15.98C16.71 17.92 14.5 19.2 12 19.2Z" fill="white"/>
            <defs>
              <linearGradient id="avatar-gradient" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1"/>
                <stop offset="1" stopColor="#8b5cf6"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
      )}
      
      <div className="message-content">
        <div className={`message-bubble ${isUser ? "user" : "ai"}${wide ? " wide" : ""}`}>
          {type === "table" ? (
            <TableMessage
              rows={message?.rows || []}
              locale={locale}
              hiddenColumns={message?.hiddenColumns || []}
              visibleColumns={message?.visibleColumns || null}
              groupBy={message?.groupBy || message?.decision?.group_by || null}
            />
          ) : type === "chart" ? (
            <ChartMessage rows={message?.rows || []} decision={message?.decision || {}} locale={locale} chartSpec={message?.chartSpec || null} />
          ) : (
            <div className="message-text">{message?.text || message?.content || ""}</div>
          )}
        </div>

        {typeof onDelete === "function" && (
          <div className="message-actions">
            <button
              className="message-action-btn"
              type="button"
              onClick={onDelete}
              title={String(locale || "en").toLowerCase().startsWith("vi") ? "Xóa tin nhắn" : "Delete message"}
              aria-label={String(locale || "en").toLowerCase().startsWith("vi") ? "Xóa tin nhắn" : "Delete message"}
            >
              <IconTrash size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
