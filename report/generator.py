import os
import json
from datetime import datetime


class ReportGenerator:
    """
    Generate a clean, professional HTML report with charts, stats, and PNG map thumbnails.
    """

    INDEX_INFO = {
        "NDVI": {
            "name": "Normalized Difference Vegetation Index",
            "short": "Vegetation Health",
            "desc": "Range: -1 to +1. Above 0.5 = healthy vegetation, below 0.2 = stress or bare soil.",
            "color": "#2d7a2d",
            "gradient": "linear-gradient(135deg, #1a4a1a, #2d7a2d)",
            "icon": "🌿",
            "ranges": [
                ( 0.8,  1.0, "Excellent",       "#006400"),
                ( 0.6,  0.8, "Good",            "#32CD32"),
                ( 0.4,  0.6, "Moderate",        "#FFD700"),
                ( 0.2,  0.4, "Poor",            "#FF8C00"),
                (-1.0,  0.2, "Critical / Bare", "#DC143C"),
            ]
        },
        "NDWI": {
            "name": "Normalized Difference Water Index",
            "short": "Water Content",
            "desc": "Range: -1 to +1. Positive = water presence, negative = dry conditions.",
            "color": "#1a6eb5",
            "gradient": "linear-gradient(135deg, #0d3b6e, #1a6eb5)",
            "icon": "💧",
            "ranges": [
                ( 0.3,  1.0, "High Water Content",  "#0000CD"),
                ( 0.0,  0.3, "Adequate Moisture",   "#4169E1"),
                (-0.3,  0.0, "Mild Water Stress",   "#FFA500"),
                (-1.0, -0.3, "Severe Water Stress", "#DC143C"),
            ]
        },
        "EVI": {
            "name": "Enhanced Vegetation Index",
            "short": "Enhanced Vegetation",
            "desc": "Improved version of NDVI — reduces atmospheric and soil background effects.",
            "color": "#4a7c59",
            "gradient": "linear-gradient(135deg, #2a4a35, #4a7c59)",
            "icon": "🌱",
            "ranges": [
                ( 0.6,  1.0, "Very Dense Cover", "#006400"),
                ( 0.4,  0.6, "Dense Cover",      "#32CD32"),
                ( 0.2,  0.4, "Moderate Cover",   "#FFD700"),
                ( 0.0,  0.2, "Sparse Cover",     "#FF8C00"),
                (-1.0,  0.0, "No Vegetation",    "#DC143C"),
            ]
        },
    }

    def __init__(self, results):
        self.results = results
        home = os.path.expanduser("~")
        reports_dir = os.path.join(home, "FarmWatcher_Reports")
        os.makedirs(reports_dir, exist_ok=True)
        timestamp = results["generated_at"].replace(":", "-").replace(" ", "_")
        self.report_path = os.path.join(
            reports_dir,
            f"report_{timestamp}.html"
        )

    def generate(self):
        html = self._build_html()
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(html)
        return self.report_path

    def _build_html(self):
        r = self.results
        dates = sorted(r["indices"].keys())
        charts_data = self._build_charts_data(dates)
        png_b64 = r.get("png_b64", {})

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FarmWatcher — Crop Health Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #f4f6f4;
    color: #1a2e1a;
  }}
  .header {{
    background: linear-gradient(135deg, #0d2e0d 0%, #1a5c1a 50%, #2d7a2d 100%);
    color: white;
    padding: 48px 32px 40px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at center, rgba(255,255,255,0.05) 0%, transparent 60%);
  }}
  .header-logo {{ font-size: 3rem; margin-bottom: 8px; display: block; }}
  .header h1 {{ font-size: 2.2rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 6px; }}
  .header-sub {{ opacity: 0.75; font-size: 1rem; margin-bottom: 28px; }}
  .meta-pills {{ display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; }}
  .meta-pill {{
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    backdrop-filter: blur(4px);
    padding: 7px 18px;
    border-radius: 999px;
    font-size: 0.82rem;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .container {{ max-width: 1140px; margin: 0 auto; padding: 40px 20px 60px; }}
  .section-header {{ display: flex; align-items: center; gap: 10px; margin: 44px 0 20px; }}
  .section-header .bar {{ width: 4px; height: 24px; background: #2d7a2d; border-radius: 2px; }}
  .section-header h2 {{ font-size: 1.25rem; font-weight: 700; color: #0d2e0d; }}
  .summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
  }}
  .summary-card {{
    background: white;
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
    border: 1px solid rgba(0,0,0,0.05);
  }}
  .summary-card .s-icon {{ font-size: 1.8rem; margin-bottom: 8px; display: block; }}
  .summary-card .s-value {{ font-size: 1.9rem; font-weight: 800; margin-bottom: 4px; line-height: 1; }}
  .summary-card .s-label {{ color: #666; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; }}
  .cards-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
    gap: 20px;
  }}
  .index-card {{
    background: white;
    border-radius: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
    border: 1px solid rgba(0,0,0,0.05);
    overflow: hidden;
  }}
  .card-header {{
    padding: 20px 22px;
    color: white;
    display: flex;
    align-items: center;
    gap: 14px;
  }}
  .card-header .ch-icon {{ font-size: 2rem; flex-shrink: 0; }}
  .card-header .ch-title {{ font-size: 1.1rem; font-weight: 700; }}
  .card-header .ch-sub {{ font-size: 0.78rem; opacity: 0.8; margin-top: 2px; }}
  .card-header .ch-date {{
    margin-left: auto;
    background: rgba(0,0,0,0.18);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.75rem;
    white-space: nowrap;
  }}
  .card-body {{ padding: 20px 22px; }}
  .card-desc {{ color: #777; font-size: 0.82rem; margin-bottom: 16px; line-height: 1.5; }}
  .card-map {{
    width: 100%;
    border-radius: 10px;
    margin-bottom: 16px;
    image-rendering: pixelated;
    border: 1px solid #eee;
  }}
  .health-section {{ margin-bottom: 18px; }}
  .health-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
  .health-status {{ font-size: 0.85rem; font-weight: 600; }}
  .health-value {{ font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px; }}
  .health-bar {{ height: 10px; background: #eee; border-radius: 999px; overflow: hidden; }}
  .health-fill {{ height: 100%; border-radius: 999px; transition: width 1.2s cubic-bezier(0.4, 0, 0.2, 1); }}
  .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 4px; }}
  .stat-item {{ background: #f8faf8; border-radius: 10px; padding: 10px 14px; }}
  .stat-item .si-label {{ font-size: 0.72rem; color: #888; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px; }}
  .stat-item .si-value {{ font-size: 1rem; font-weight: 700; color: #1a2e1a; }}
  .chart-card {{
    background: white;
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
    border: 1px solid rgba(0,0,0,0.05);
  }}
  .chart-card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }}
  .chart-icon {{ font-size: 1.4rem; }}
  .chart-title {{ font-size: 1rem; font-weight: 700; color: #0d2e0d; }}
  .chart-subtitle {{ font-size: 0.78rem; color: #888; margin-top: 1px; }}
  .range-legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
  .range-pill {{
    display: flex;
    align-items: center;
    gap: 6px;
    background: #f8faf8;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    color: #555;
  }}
  .range-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
  .footer {{
    text-align: center;
    padding: 32px;
    color: #aaa;
    font-size: 0.78rem;
    border-top: 1px solid #e8ece8;
    margin-top: 20px;
  }}
  .footer strong {{ color: #2d7a2d; }}
  .map-label {{
    font-size: 0.72rem;
    color: #aaa;
    text-align: center;
    margin-top: -10px;
    margin-bottom: 14px;
    letter-spacing: 0.3px;
  }}
</style>
</head>
<body>

<div class="header">
  <span class="header-logo">🌾</span>
  <h1>FarmWatcher</h1>
  <p class="header-sub">Crop Health Monitoring Report</p>
  <div class="meta-pills">
    <div class="meta-pill">🏡 {r['farm_name']}</div>
    <div class="meta-pill">📅 {r['date_start']} → {r['date_end']}</div>
    <div class="meta-pill">🛰️ Sentinel-2 · Copernicus</div>
    <div class="meta-pill">🕐 {r['generated_at']}</div>
  </div>
</div>

<div class="container">

  <div class="section-header">
    <div class="bar"></div>
    <h2>Overview</h2>
  </div>
  <div class="summary-grid">
    {self._build_summary(dates)}
  </div>

  <div class="section-header">
    <div class="bar"></div>
    <h2>Latest Indices — {dates[-1] if dates else 'N/A'}</h2>
  </div>
  <div class="cards-grid">
    {self._build_index_cards(dates, png_b64)}
  </div>

  <div class="section-header">
    <div class="bar"></div>
    <h2>Time Series</h2>
  </div>
  {self._build_chart_containers()}

</div>

<div class="footer">
  Generated by <strong>FarmWatcher</strong> Plugin for QGIS &nbsp;·&nbsp;
  Data: Copernicus Sentinel-2 (free) &nbsp;·&nbsp;
  {r['generated_at']}
</div>

<script>
const chartsData = {charts_data};

Object.entries(chartsData).forEach(([indexName, data]) => {{
  const ctx = document.getElementById('chart_' + indexName);
  if (!ctx || !data.dates.length) return;

  new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: data.dates,
      datasets: [{{
        label: indexName,
        data: data.means,
        borderColor: data.color,
        backgroundColor: data.color + '18',
        borderWidth: 2.5,
        tension: 0.4,
        fill: true,
        pointBackgroundColor: data.color,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 9,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a2e1a',
          padding: 12,
          cornerRadius: 10,
          callbacks: {{
            label: ctx => ' ' + indexName + ': ' + ctx.parsed.y.toFixed(4)
          }}
        }}
      }},
      scales: {{
        y: {{
          min: -1, max: 1,
          grid: {{ color: '#f0f4f0' }},
          ticks: {{ color: '#888', font: {{ size: 11 }} }}
        }},
        x: {{
          grid: {{ color: '#f0f4f0' }},
          ticks: {{ color: '#888', font: {{ size: 11 }} }}
        }}
      }}
    }}
  }});
}});
</script>

</body>
</html>"""

    def _build_summary(self, dates):
        if not dates:
            return ""
        last_date = dates[-1]
        html = ""

        html += f"""
        <div class="summary-card">
          <span class="s-icon">🛰️</span>
          <div class="s-value" style="color:#2d7a2d">{len(dates)}</div>
          <div class="s-label">Sentinel-2 Scenes</div>
        </div>"""

        html += f"""
        <div class="summary-card">
          <span class="s-icon">📅</span>
          <div class="s-value" style="color:#1a6eb5;font-size:1rem;padding-top:6px">
            {self.results['date_start']}<br>
            <span style="font-size:0.75rem;color:#aaa">to</span><br>
            {self.results['date_end']}
          </div>
          <div class="s-label">Analysis Period</div>
        </div>"""

        if last_date in self.results["indices"] and "NDVI" in self.results["indices"][last_date]:
            mean = self.results["indices"][last_date]["NDVI"]["stats"]["mean"]
            status, color = self._get_ndvi_status(mean)
            html += f"""
            <div class="summary-card">
              <span class="s-icon">🌿</span>
              <div class="s-value" style="color:{color}">{mean:.3f}</div>
              <div class="s-label">Latest NDVI — {status}</div>
            </div>"""

        if last_date in self.results["indices"] and "NDWI" in self.results["indices"][last_date]:
            mean = self.results["indices"][last_date]["NDWI"]["stats"]["mean"]
            status, color = self._get_ndwi_status(mean)
            html += f"""
            <div class="summary-card">
              <span class="s-icon">💧</span>
              <div class="s-value" style="color:{color}">{mean:.3f}</div>
              <div class="s-label">Latest NDWI — {status}</div>
            </div>"""

        return html

    def _build_index_cards(self, dates, png_b64):
        if not dates:
            return "<p style='color:#888'>No data available.</p>"
        last_date = dates[-1]
        html = ""

        for index_name, info in self.INDEX_INFO.items():
            if last_date not in self.results["indices"]:
                continue
            if index_name not in self.results["indices"][last_date]:
                continue

            stats = self.results["indices"][last_date][index_name]["stats"]
            mean = stats["mean"]
            pct = max(0, min(100, int((mean + 1) / 2 * 100)))
            status_label, status_color = self._get_status(index_name, mean)

            # PNG thumbnail embedded as base64
            map_html = ""
            if index_name in png_b64:
                b64 = png_b64[index_name]
                map_html = f"""
                <img
                  class="card-map"
                  src="data:image/png;base64,{b64}"
                  alt="{index_name} map"
                  title="{index_name} — {last_date}"
                />
                <p class="map-label">Spatial distribution — {last_date}</p>"""

            legend_html = ""
            for low, high, label, color in info["ranges"]:
                legend_html += f"""
                <div class="range-pill">
                  <div class="range-dot" style="background:{color}"></div>
                  {label}
                </div>"""

            html += f"""
            <div class="index-card">
              <div class="card-header" style="background:{info['gradient']}">
                <span class="ch-icon">{info['icon']}</span>
                <div>
                  <div class="ch-title">{index_name}</div>
                  <div class="ch-sub">{info['short']}</div>
                </div>
                <div class="ch-date">{last_date}</div>
              </div>
              <div class="card-body">
                <p class="card-desc">{info['desc']}</p>

                {map_html}

                <div class="health-section">
                  <div class="health-top">
                    <span class="health-status" style="color:{status_color}">{status_label}</span>
                    <span class="health-value" style="color:{info['color']}">{mean:.4f}</span>
                  </div>
                  <div class="health-bar">
                    <div class="health-fill" style="width:{pct}%;background:{info['color']}"></div>
                  </div>
                </div>

                <div class="stats-grid">
                  <div class="stat-item">
                    <div class="si-label">Mean</div>
                    <div class="si-value">{stats['mean']:.4f}</div>
                  </div>
                  <div class="stat-item">
                    <div class="si-label">Std Dev</div>
                    <div class="si-value">{stats['std']:.4f}</div>
                  </div>
                  <div class="stat-item">
                    <div class="si-label">Min</div>
                    <div class="si-value">{stats['min']:.4f}</div>
                  </div>
                  <div class="stat-item">
                    <div class="si-label">Max</div>
                    <div class="si-value">{stats['max']:.4f}</div>
                  </div>
                </div>

                <div class="range-legend">{legend_html}</div>
              </div>
            </div>"""

        return html

    def _build_chart_containers(self):
        html = ""
        for index_name, info in self.INDEX_INFO.items():
            html += f"""
            <div class="chart-card">
              <div class="chart-card-header">
                <span class="chart-icon">{info['icon']}</span>
                <div>
                  <div class="chart-title">{index_name} — {info['name']}</div>
                  <div class="chart-subtitle">Mean value over time</div>
                </div>
              </div>
              <div style="
                text-align: center;
                padding: 40px 20px;
                color: #aaa;
                background: #f8faf8;
                border-radius: 10px;
                border: 1px dashed #ddd;
              ">
                <div style="font-size: 2rem; margin-bottom: 12px;">📈</div>
                <div style="font-weight: 600; color: #888; margin-bottom: 6px;">
                  Time Series — Coming in Next Update
                </div>
                <div style="font-size: 0.82rem; color: #bbb;">
                  Multi-date analysis will be available in FarmWatcher v0.2
                </div>
              </div>
            </div>"""
        return html

    def _build_charts_data(self, dates):
        data = {}
        for index_name, info in self.INDEX_INFO.items():
            means, valid_dates = [], []
            for d in dates:
                if d in self.results["indices"] and index_name in self.results["indices"][d]:
                    means.append(self.results["indices"][d][index_name]["stats"]["mean"])
                    valid_dates.append(d)
            data[index_name] = {
                "dates": valid_dates,
                "means": means,
                "color": info["color"],
            }
        return json.dumps(data, ensure_ascii=False)

    def _get_status(self, index_name, value):
        for low, high, label, color in self.INDEX_INFO[index_name]["ranges"]:
            if low <= value <= high:
                return label, color
        return "Unknown", "#999"

    def _get_ndvi_status(self, value):
        if value >= 0.6: return "Excellent", "#2d7a2d"
        if value >= 0.4: return "Good",      "#32CD32"
        if value >= 0.2: return "Moderate",  "#FF8C00"
        return "Critical", "#DC143C"

    def _get_ndwi_status(self, value):
        if value >= 0.3:  return "High",     "#0000CD"
        if value >= 0.0:  return "Adequate", "#4169E1"
        if value >= -0.3: return "Mild",     "#FFA500"
        return "Severe", "#DC143C"