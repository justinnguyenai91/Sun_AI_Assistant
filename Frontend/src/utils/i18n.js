import uiEn from "../i18n/ui.en.json";
import uiVi from "../i18n/ui.vi.json";
import termsEn from "../i18n/terms.en.json";
import termsVi from "../i18n/terms.vi.json";

const BUNDLES = {
  en: {
    ui: uiEn,
    terms: termsEn,
  },
  vi: {
    ui: uiVi,
    terms: termsVi,
  },
};

function normalizeLocale(locale) {
  const lc = String(locale || "en").toLowerCase();
  if (lc.startsWith("vi")) return "vi";
  return "en";
}

function interpolate(template, vars) {
  return String(template).replace(/\{(\w+)\}/g, (_, name) => {
    const v = vars?.[name];
    return v === undefined || v === null ? `{${name}}` : String(v);
  });
}

/**
 * Simple dictionary helper.
 *
 * Usage:
 * - t("ui.fetchedRows", locale, { count: 10, target: "production" })
 * - t("charts.plannedQty", locale)
 */
export function t(key, locale = "en", vars = {}) {
  const lang = normalizeLocale(locale);

  const raw = String(key || "");
  const match = raw.match(/^(?<ns>[^.]+)\.(?<k>.+)$/);
  const ns = match?.groups?.ns || "ui";
  const k = match?.groups?.k || raw;

  const dict = BUNDLES?.[lang]?.[ns] || {};
  const fallbackDict = BUNDLES?.en?.[ns] || {};

  const template = dict?.[k] ?? fallbackDict?.[k] ?? k;
  return interpolate(template, vars);
}
