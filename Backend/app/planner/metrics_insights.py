"""
Auto-computed metrics and proactive insights for MES data.
"""
import logging
from typing import List, Dict, Any, Optional
import statistics

logger = logging.getLogger(__name__)


class MetricsComputer:
    """Compute derived metrics from base MES data."""
    
    @staticmethod
    def compute_achievement_rate(row: dict) -> Optional[float]:
        """Calculate achievement rate: (actualQty / planQty) * 100."""
        try:
            actual = row.get("totalActualQty") or row.get("actualQty") or 0
            plan = row.get("totalPlanQty") or row.get("planQty") or 0
            
            if plan and plan > 0:
                return round((actual / plan) * 100, 2)
            return None
        except:
            return None
    
    @staticmethod
    def compute_defect_rate(row: dict) -> Optional[float]:
        """Calculate defect rate: (defectQty / actualQty) * 100."""
        try:
            defect = row.get("totalDefectQty") or row.get("defectQty") or 0
            actual = row.get("totalActualQty") or row.get("actualQty") or 0
            
            if actual and actual > 0:
                return round((defect / actual) * 100, 2)
            return None
        except:
            return None
    
    @staticmethod
    def compute_yield_rate(row: dict) -> Optional[float]:
        """Calculate yield rate: ((actualQty - defectQty) / actualQty) * 100."""
        try:
            actual = row.get("totalActualQty") or row.get("actualQty") or 0
            defect = row.get("totalDefectQty") or row.get("defectQty") or 0
            
            if actual and actual > 0:
                good = actual - defect
                return round((good / actual) * 100, 2)
            return None
        except:
            return None
    
    @staticmethod
    def compute_efficiency(row: dict) -> Optional[float]:
        """Calculate efficiency: (actualQty / planQty) * 100 (same as achievement)."""
        return MetricsComputer.compute_achievement_rate(row)
    
    @staticmethod
    def compute_oee(row: dict) -> Optional[float]:
        """Calculate simplified OEE: availability * performance * quality."""
        try:
            # For now, use achievement as performance and yield as quality
            achievement = MetricsComputer.compute_achievement_rate(row)
            yield_rate = MetricsComputer.compute_yield_rate(row)
            
            if achievement is not None and yield_rate is not None:
                # Assume 100% availability for simplified calculation
                oee = (achievement / 100) * (yield_rate / 100) * 100
                return round(oee, 2)
            return None
        except:
            return None
    
    @staticmethod
    def enrich_rows(rows: List[dict], locale: str = "vi") -> List[dict]:
        """Add computed metrics to all rows with locale-aware column names."""
        if not rows:
            return rows
        
        # Determine if Vietnamese locale
        is_vietnamese = locale.startswith("vi")
        
        for row in rows:
            if not isinstance(row, dict):
                continue
            
            # Compute derived metrics
            achievement = MetricsComputer.compute_achievement_rate(row)
            if achievement is not None:
                if is_vietnamese:
                    row["Tỷ lệ đạt"] = f"{achievement}%"
                else:
                    row["Achievement %"] = f"{achievement}%"
            
            defect_rate = MetricsComputer.compute_defect_rate(row)
            if defect_rate is not None:
                if is_vietnamese:
                    row["Lỗi %"] = f"{defect_rate}%"
                else:
                    row["Defect %"] = f"{defect_rate}%"
            
            yield_rate = MetricsComputer.compute_yield_rate(row)
            if yield_rate is not None:
                if is_vietnamese:
                    row["Chất lượng %"] = f"{yield_rate}%"
                else:
                    row["Yield %"] = f"{yield_rate}%"
            
            efficiency = MetricsComputer.compute_efficiency(row)
            if efficiency is not None:
                if is_vietnamese:
                    row["Hiệu suất %"] = f"{efficiency}%"
                else:
                    row["Efficiency %"] = f"{efficiency}%"
            
            oee = MetricsComputer.compute_oee(row)
            if oee is not None:
                if is_vietnamese:
                    row["OEE %"] = f"{oee}%"
                else:
                    row["OEE %"] = f"{oee}%"
        
        return rows


class InsightsGenerator:
    """Generate proactive insights from MES data."""
    
    @staticmethod
    def detect_trends(rows: List[dict], metric: str = "achievementRate") -> Optional[str]:
        """Detect if metric is trending up or down."""
        if not rows or len(rows) < 3:
            return None
        
        try:
            values = []
            for row in rows:
                val = row.get(metric)
                if val is not None:
                    values.append(float(val))
            
            if len(values) < 3:
                return None
            
            # Simple trend: compare first half vs second half
            mid = len(values) // 2
            first_half_avg = statistics.mean(values[:mid])
            second_half_avg = statistics.mean(values[mid:])
            
            diff_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100 if first_half_avg > 0 else 0
            
            if abs(diff_percent) < 5:
                return "stable"
            elif diff_percent > 0:
                return "improving"
            else:
                return "declining"
        except:
            return None
    
    @staticmethod
    def detect_anomalies(rows: List[dict], metric: str = "achievementRate", threshold_sigma: float = 2.0) -> List[dict]:
        """Detect outliers using standard deviation."""
        if not rows or len(rows) < 5:
            return []
        
        try:
            values_with_index = []
            for idx, row in enumerate(rows):
                val = row.get(metric)
                if val is not None:
                    values_with_index.append((idx, float(val)))
            
            if len(values_with_index) < 5:
                return []
            
            values = [v[1] for v in values_with_index]
            mean_val = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            
            if stdev == 0:
                return []
            
            anomalies = []
            for idx, val in values_with_index:
                z_score = abs((val - mean_val) / stdev)
                if z_score > threshold_sigma:
                    anomalies.append({
                        "index": idx,
                        "row": rows[idx],
                        "value": val,
                        "z_score": round(z_score, 2),
                        "deviation": "high" if val > mean_val else "low"
                    })
            
            return anomalies
        except:
            return []
    
    @staticmethod
    def find_top_performers(rows: List[dict], metric: str = "achievementRate", top_n: int = 3) -> List[dict]:
        """Find top N rows by metric."""
        if not rows:
            return []
        
        try:
            valid_rows = []
            for row in rows:
                val = row.get(metric)
                if val is not None:
                    valid_rows.append((row, float(val)))
            
            if not valid_rows:
                return []
            
            # Sort descending
            valid_rows.sort(key=lambda x: x[1], reverse=True)
            return [r[0] for r in valid_rows[:top_n]]
        except:
            return []
    
    @staticmethod
    def find_bottom_performers(rows: List[dict], metric: str = "achievementRate", bottom_n: int = 3) -> List[dict]:
        """Find bottom N rows by metric."""
        if not rows:
            return []
        
        try:
            valid_rows = []
            for row in rows:
                val = row.get(metric)
                if val is not None:
                    valid_rows.append((row, float(val)))
            
            if not valid_rows:
                return []
            
            # Sort ascending
            valid_rows.sort(key=lambda x: x[1])
            return [r[0] for r in valid_rows[:bottom_n]]
        except:
            return []
    
    @staticmethod
    def generate_insights(rows: List[dict], entity: str = "production", locale: str = "vi") -> Dict[str, Any]:
        """Generate comprehensive insights from data."""
        if not rows:
            return {"insights": [], "suggestions": []}
        
        is_vietnamese = locale.startswith("vi")
        insights = []
        suggestions = []
        
        # Detect trend
        trend = InsightsGenerator.detect_trends(rows, "achievementRate")
        if trend:
            if trend == "improving":
                msg = "Tỷ lệ đạt kế hoạch đang cải thiện" if is_vietnamese else "Achievement rate is improving"
                insights.append({"type": "trend", "message": msg, "sentiment": "positive"})
            elif trend == "declining":
                msg = "Tỷ lệ đạt kế hoạch đang giảm" if is_vietnamese else "Achievement rate is declining"
                insights.append({"type": "trend", "message": msg, "sentiment": "negative"})
                suggestion = "Kiểm tra nguyên nhân và điều chỉnh kế hoạch" if is_vietnamese else "Investigate root cause and adjust plan"
                suggestions.append({"type": "action", "message": suggestion})
        
        # Detect anomalies
        anomalies = InsightsGenerator.detect_anomalies(rows, "achievementRate")
        if anomalies:
            for anom in anomalies[:2]:  # Top 2 anomalies
                row = anom["row"]
                line_name = row.get("lineName") or row.get("lineId") or "Unknown"
                if anom["deviation"] == "low":
                    msg = f"{line_name}: Hiệu suất thấp bất thường ({anom['value']:.1f}%)" if is_vietnamese else f"{line_name}: Unusually low performance ({anom['value']:.1f}%)"
                    insights.append({"type": "anomaly", "message": msg, "sentiment": "warning"})
                else:
                    msg = f"{line_name}: Hiệu suất cao xuất sắc ({anom['value']:.1f}%)" if is_vietnamese else f"{line_name}: Excellent performance ({anom['value']:.1f}%)"
                    insights.append({"type": "anomaly", "message": msg, "sentiment": "positive"})
        
        # Top performers
        top_lines = InsightsGenerator.find_top_performers(rows, "achievementRate", 2)
        if top_lines:
            line_names = [r.get("lineName") or r.get("lineId") for r in top_lines]
            line_names = [n for n in line_names if n]
            if line_names:
                msg = f"Top performers: {', '.join(line_names)}" if not is_vietnamese else f"Dây chuyền tốt nhất: {', '.join(line_names)}"
                insights.append({"type": "ranking", "message": msg, "sentiment": "positive"})
        
        # Bottom performers
        bottom_lines = InsightsGenerator.find_bottom_performers(rows, "achievementRate", 2)
        if bottom_lines:
            line_names = [r.get("lineName") or r.get("lineId") for r in bottom_lines]
            line_names = [n for n in line_names if n]
            if line_names:
                msg = f"Cần cải thiện: {', '.join(line_names)}" if is_vietnamese else f"Need improvement: {', '.join(line_names)}"
                insights.append({"type": "ranking", "message": msg, "sentiment": "warning"})
                suggestion = f"Phân tích chi tiết {', '.join(line_names[:1])} để tìm giải pháp" if is_vietnamese else f"Analyze {', '.join(line_names[:1])} for improvement opportunities"
                suggestions.append({"type": "action", "message": suggestion})
        
        # Overall statistics
        try:
            achievement_values = [float(r.get("achievementRate")) for r in rows if r.get("achievementRate") is not None]
            if achievement_values:
                avg_achievement = statistics.mean(achievement_values)
                if avg_achievement < 80:
                    msg = f"Tỷ lệ đạt trung bình thấp ({avg_achievement:.1f}%)" if is_vietnamese else f"Low average achievement ({avg_achievement:.1f}%)"
                    insights.append({"type": "summary", "message": msg, "sentiment": "warning"})
                elif avg_achievement > 95:
                    msg = f"Tỷ lệ đạt xuất sắc ({avg_achievement:.1f}%)" if is_vietnamese else f"Excellent achievement ({avg_achievement:.1f}%)"
                    insights.append({"type": "summary", "message": msg, "sentiment": "positive"})
        except:
            pass
        
        return {
            "insights": insights,
            "suggestions": suggestions
        }


# Global instances
metrics_computer = MetricsComputer()
insights_generator = InsightsGenerator()
