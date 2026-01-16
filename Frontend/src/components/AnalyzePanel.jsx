import { useState, useMemo } from "react";
import TopLinesChart from "./TopLinesChart";
import { mapProdStatus, mapProcessType } from "../utils/lookup";

export default function AnalyzePanel({ baseUrl, getApiKey }) {
  const [query, setQuery] = useState("Hay thống kê sản lượng 1 năm qua theo line");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [flexible, setFlexible] = useState(false);
  const [chatMode, setChatMode] = useState(false);
  const [chartMode, setChartMode] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [retrySeconds, setRetrySeconds] = useState(0);
  const maxRetries = 3;
  const baseDelaySec = 30;

  const columns = useMemo(() => {
    const preferred = [
      'lineName','lineId','model','orderCount','totalPlanQty','totalActualQty','totalDefectQty','avgTactTime','yield','defectRate','productionStatusCodes','productionStatusLabels','processTypes','processTypeLabels'
    ];
    if (!flexible) return ['lineName','orderCount','totalPlanQty','totalActualQty','totalDefectQty','avgTactTime','productionStatusCodes','processTypes'];
    const keys = new Set();
    rows.forEach(r => Object.keys(r || {}).forEach(k => keys.add(k)));
    const remaining = [...keys].filter(k => !preferred.includes(k));
    const cols = preferred.filter(c => keys.has(c)).concat(remaining).slice(0, 40);
    return cols;
  }, [rows, flexible]);

  const colTitles = {
    lineName: "Line Name",
    lineId: "Line ID",
    model: "Model",
    orderCount: "Orders",
    totalPlanQty: "Total Plan Qty",
    totalActualQty: "Total Actual Qty",
    totalDefectQty: "Total Defect Qty",
    avgTactTime: "Avg Tact",
    yield: "Yield",
    defectRate: "Defect Rate",
    productionStatusCodes: "Production Status",
    productionStatusLabels: "Production Status",
    productionStatusCount: "Status Count",
    processTypes: "Process Type",
    processTypeLabels: "Process Type",
    processTypeCount: "Process Count",
  };

  const fmt = (v) => {
    if (v === null || v === undefined) return "-";
    if (typeof v === "number") return v.toLocaleString();
    return String(v);
  };

  const renderCell = (r, col) => {
    // prefer label fields if present
    if (col === "productionStatusCodes" || col === "productionStatusLabels") {
      // prefer server-provided labels; otherwise map codes locally
      const labels = r.productionStatusLabels || r.productionStatusCodes || [];
      const arr = Array.isArray(labels) ? labels : String(labels || "").split(/[,\s]+/).filter(Boolean);
      const mapped = mapProdStatus(arr);
      return mapped.length ? mapped.join(", ") : "-";
    }
    if (col === "processTypes" || col === "processTypeLabels") {
      const labels = r.processTypeLabels || r.processTypes || [];
      const arr = Array.isArray(labels) ? labels : String(labels || "").split(/[,\s]+/).filter(Boolean);
      const mapped = mapProcessType(arr);
      return mapped.length ? mapped.join(", ") : "-";
    }
    // numeric formatting
    if (["totalPlanQty","totalActualQty","totalDefectQty","orderCount","productionStatusCount","processTypeCount"].includes(col)) {
      const val = r[col] ?? r[col.replace(/Count$/,'Count')];
      return fmt(Number(val));
    }
    if (col === "avgTactTime") return fmt(Number(r[col] ?? r.avgTactTime));
    // default
    const val = r[col];
    if (Array.isArray(val)) return val.join(", ");
    return val === undefined || val === null ? "-" : String(val);
  };

  const summarizeRow = (r) => {
    const line = r.lineName || r.lineId || "(unknown)";
    const plan = (r.totalPlanQty !== undefined) ? Number(r.totalPlanQty).toLocaleString() : "-";
    const actual = (r.totalActualQty !== undefined) ? Number(r.totalActualQty).toLocaleString() : "-";
    const defect = (r.totalDefectQty !== undefined) ? Number(r.totalDefectQty).toLocaleString() : "-";
    const tact = r.avgTactTime ? Number(r.avgTactTime).toFixed(2) : "-";
    const statuses = (r.productionStatusLabels || r.productionStatusCodes || []).slice(0,5).join(", ") || "-";
    return `Line ${line}: Planned ${plan}; Actual ${actual}; Defects ${defect}; Avg tact ${tact}; Statuses: ${statuses}`;
  };

  const runAnalyze = async (attempt = 0) => {
    // attempt: 0..maxRetries
    setLoading(true);
    setError(null);
    if (attempt === 0) setRows([]);
    try {
      const apiKey = await getApiKey();
      if (!apiKey) throw new Error("Missing API key");

      const resp = await fetch(`${baseUrl}/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ input: query }),
      });

      if (resp.status === 429) {
        // rate limited: parse retry message and schedule retry with exponential backoff
        const text = await resp.text();
        const delay = baseDelaySec * Math.pow(2, attempt); // exponential backoff
        setError(`Error: HTTP 429: ${text}`);
        if (attempt < maxRetries) {
          setRetrying(true);
          setRetrySeconds(delay);
          // countdown
          const interval = setInterval(() => {
            setRetrySeconds((s) => {
              if (s <= 1) {
                clearInterval(interval);
                setRetrying(false);
                // attempt again
                runAnalyze(attempt + 1);
                return 0;
              }
              return s - 1;
            });
          }, 1000);
        }
        return;
      }

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
      }

      const data = await resp.json();
      const result = (data.planner_result && data.planner_result.data) || [];
      setRows(result);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="analyze-panel">
      <div className="analyze-header">
        <input
          className="analyze-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="btn-primary" onClick={runAnalyze} disabled={loading}>
          {loading ? "Running..." : "Analyze"}
        </button>
      </div>

      {error && <div className="analyze-error">{error}</div>}

      <div className="analyze-controls">
        <label style={{ marginRight: 12 }}>
          <input type="checkbox" checked={flexible} onChange={(e) => setFlexible(e.target.checked)} /> Flexible columns
        </label>
        <label style={{ marginRight: 12 }}>
          <input type="checkbox" checked={chartMode} onChange={(e) => setChartMode(e.target.checked)} /> Chart
        </label>
        <label>
          <input type="checkbox" checked={chatMode} onChange={(e) => setChatMode(e.target.checked)} /> Chat mode
        </label>
      </div>

      <div className="analyze-results">
        {chartMode ? (
          <TopLinesChart rows={rows} />
        ) : chatMode ? (
          <div className="chat-like">
            {rows.length === 0 && <div className="muted">No messages. Click Analyze to run.</div>}
            {rows.map((r, idx) => (
              <div key={idx} className="chat-row">
                <pre>{JSON.stringify(r, null, 2)}</pre>
              </div>
            ))}
          </div>
        ) : (
          <table className="result-table">
            <thead>
              <tr>
                {/** if flexible, infer columns else show defaults **/}
                {columns.map((c) => (
                  <th key={c}>{colTitles[c] || c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="muted">No data. Click Analyze to run.</td>
                </tr>
              )}
              {rows.map((r, idx) => (
                <tr key={idx}>
                  {columns.map((col, i) => (
                    <td key={i}>{renderCell(r, col)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
