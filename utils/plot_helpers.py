"""
utils/plot_helpers.py — Reusable Plotly chart factory functions
Ruang Statistika v4.0
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats


BLUE   = "#185FA5"
NAVY   = "#0c2340"
GREEN  = "#3B6D11"
RED    = "#A32D2D"
RED2   = "#E24B4A"


def plotly_qq(data: pd.Series, title: str) -> go.Figure:
    """Q-Q Plot normal."""
    qq = stats.probplot(data.dropna(), dist="norm")
    x_line = np.array([qq[0][0][0], qq[0][0][-1]])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=qq[0][0], y=qq[0][1], mode="markers", name="Data",
        marker=dict(color=BLUE, size=5)
    ))
    fig.add_trace(go.Scatter(
        x=x_line, y=qq[1][0] * x_line + qq[1][1],
        mode="lines", name="Normal", line=dict(color=RED2, width=2)
    ))
    fig.update_layout(title=title, template="plotly_white", height=350,
                      margin=dict(l=30, r=30, t=50, b=30))
    return fig


def plotly_histogram(s: pd.Series, col_name: str) -> go.Figure:
    fig = go.Figure(go.Histogram(x=s, nbinsx=20, marker_color=BLUE, opacity=0.75))
    fig.update_layout(
        title=f"Distribusi: {col_name}", template="plotly_white", height=320,
        xaxis_title=col_name, yaxis_title="Frekuensi",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def plotly_validity_bar(val_df: pd.DataFrame, r_tab: float) -> go.Figure:
    colors = ["#3B6D11" if "Valid ✓" in s else "#A32D2D" for s in val_df["Status"]]
    fig = go.Figure(go.Bar(
        x=val_df["Butir"], y=val_df["r-hitung"],
        marker_color=colors,
        text=val_df["Status"], textposition="outside",
    ))
    fig.add_hline(y=r_tab, line_dash="dash", line_color=RED2,
                  annotation_text=f"r-tabel = {r_tab}")
    fig.update_layout(
        title="r-hitung vs r-tabel per Butir",
        yaxis_title="r-hitung", xaxis_title="Butir",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=50, b=30)
    )
    return fig


def plotly_cronbach_gauge(alpha_val: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=alpha_val,
        gauge={
            "axis": {"range": [0, 1]},
            "bar": {"color": BLUE},
            "steps": [
                {"range": [0, 0.6], "color": "#fcebeb"},
                {"range": [0.6, 0.7], "color": "#faeeda"},
                {"range": [0.7, 0.8], "color": "#eaf3de"},
                {"range": [0.8, 0.9], "color": "#c0dd97"},
                {"range": [0.9, 1.0], "color": "#639922"},
            ],
            "threshold": {"line": {"color": RED, "width": 3}, "value": 0.7},
        },
        title={"text": "Cronbach's Alpha"},
    ))
    fig.update_layout(height=250, template="plotly_white",
                      margin=dict(l=20, r=20, t=30, b=10))
    return fig


def plotly_heatmap(corr: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.columns,
        colorscale="Blues",
        text=np.round(corr.values, 3),
        texttemplate="%{text}", textfont={"size": 10},
        zmin=-1, zmax=1,
        colorbar={"title": "r"},
    ))
    fig.update_layout(
        title="Heatmap Korelasi Pearson",
        template="plotly_white", height=480,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    return fig


def plotly_scatter(df: pd.DataFrame, var_x: str, var_y: str,
                   r_val: float, p_val: float) -> go.Figure:
    fig = px.scatter(
        df, x=var_x, y=var_y, trendline="ols",
        title=f"Scatter: {var_x} vs {var_y} | r = {r_val:.3f}, p = {p_val:.4f}",
        template="plotly_white",
    )
    fig.update_layout(height=380, margin=dict(l=30, r=30, t=50, b=30))
    return fig


def plotly_vif_bar(vif_df: pd.DataFrame) -> go.Figure:
    colors = [RED if v > 10 else BLUE for v in vif_df["VIF"]]
    fig = go.Figure(go.Bar(
        x=vif_df["Variabel"], y=vif_df["VIF"],
        marker_color=colors,
        text=vif_df["VIF"].round(2), textposition="outside"
    ))
    fig.add_hline(y=10, line_dash="dash", line_color=RED2,
                  annotation_text="Threshold VIF = 10")
    fig.update_layout(
        title="VIF per Variabel Independen",
        xaxis_title="Variabel", yaxis_title="VIF",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=50, b=30)
    )
    return fig


def plotly_residual_scatter(y_pred: np.ndarray, resid: np.ndarray,
                             dep_var: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=y_pred, y=resid, mode="markers",
        marker=dict(color=BLUE, size=6, opacity=0.7), name="Residual"
    ))
    fig.add_hline(y=0, line_dash="dash", line_color=RED2)
    fig.update_layout(
        title=f"Residual vs Fitted: {dep_var}",
        xaxis_title="Fitted Values", yaxis_title="Residual",
        template="plotly_white", height=380,
        margin=dict(l=30, r=30, t=50, b=30)
    )
    return fig


def mediasi_path_svg(x_name: str, m_name: str, y_name: str,
                     a: float, b: float, c: float, cp: float, ind: float) -> str:
    """Render SVG diagram path mediasi."""
    xn = x_name[:10]
    mn = m_name[:10]
    yn = y_name[:10]
    return f"""
    <svg viewBox="0 0 680 240" xmlns="http://www.w3.org/2000/svg"
         style="width:100%;max-width:680px;background:#f7faff;border-radius:12px;padding:10px;">
      <rect x="20" y="90" width="120" height="50" rx="10" fill="{BLUE}" />
      <text x="80" y="118" text-anchor="middle" fill="white" font-size="15" font-weight="bold">{xn}</text>
      <rect x="280" y="20" width="120" height="50" rx="10" fill="{GREEN}" />
      <text x="340" y="48" text-anchor="middle" fill="white" font-size="15" font-weight="bold">{mn}</text>
      <rect x="540" y="90" width="120" height="50" rx="10" fill="{RED}" />
      <text x="600" y="118" text-anchor="middle" fill="white" font-size="15" font-weight="bold">{yn}</text>
      <line x1="140" y1="95" x2="280" y2="55" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr)" />
      <text x="200" y="62" text-anchor="middle" fill="{GREEN}" font-size="13" font-weight="600">a = {a}</text>
      <line x1="400" y1="55" x2="540" y2="95" stroke="{GREEN}" stroke-width="2.5" marker-end="url(#arr)" />
      <text x="487" y="62" text-anchor="middle" fill="{GREEN}" font-size="13" font-weight="600">b = {b}</text>
      <line x1="140" y1="115" x2="540" y2="115" stroke="{BLUE}" stroke-width="2"
            stroke-dasharray="6,4" marker-end="url(#arr2)" />
      <text x="340" y="138" text-anchor="middle" fill="{BLUE}" font-size="12">c' = {cp} (langsung)</text>
      <text x="340" y="180" text-anchor="middle" fill="#6b21a8" font-size="13" font-weight="600">
        Indirect = a×b = {ind}  |  Total c = {c}
      </text>
      <defs>
        <marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="{GREEN}" />
        </marker>
        <marker id="arr2" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="{BLUE}" />
        </marker>
      </defs>
    </svg>
    """
