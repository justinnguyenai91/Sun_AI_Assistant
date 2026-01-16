// Minimal copy of backend lookup mappings for client-side label resolution
const PROD_STATUS = {
  "D019001": "PLANNED",
  "D019002": "IN_PROGRESS",
  "D019003": "COMPLETED",
  "D019006": "CANCELLED",
  "D019007": "ON_HOLD",
};

const PROCESS_TYPE = {
  "D014004": "MOTOR",
  "D014002": "ROTOR",
  "D014001": "STATOR",
  "D014003": "CASE",
};

export function mapProdStatus(codes) {
  if (!codes) return [];
  return (Array.isArray(codes) ? codes : String(codes).split(/[,\s]+/)).map(c => PROD_STATUS[c] || c);
}

export function mapProcessType(codes) {
  if (!codes) return [];
  return (Array.isArray(codes) ? codes : String(codes).split(/[,\s]+/)).map(c => PROCESS_TYPE[c] || c);
}

export default { mapProdStatus, mapProcessType };
