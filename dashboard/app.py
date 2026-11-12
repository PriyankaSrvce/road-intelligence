"""UrbanRoadAI – Interactive Streamlit Dashboard.

Visualises road condition data, defect distributions, risk predictions
and maintenance priorities from the SQLite demo database.

SIMULATED DATA NOTICE: All demo data is synthetic (data_source='simulated').
A visible badge appears on every page that displays simulated data.

Run from repo root:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="UrbanRoadAI Dashboard",
    page_icon="🛣️",
    layout="wide",
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "roads_demo.db"

BAND_COLORS = {
    "good": "#2ecc71",
    "fair": "#f1c40f",
    "poor": "#e67e22",
    "very_poor": "#e74c3c",
}

BAND_LABELS = {
    "good": "Good (0–25)",
    "fair": "Fair (26–50)",
    "poor": "Poor (51–75)",
    "very_poor": "Very Poor (76–100)",
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def get_conn():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql: str, params=()) -> pd.DataFrame:
    conn = get_conn()
    if conn is None:
        return pd.DataFrame()
    return pd.read_sql_query(sql, conn, params=params)


def scalar(sql: str, params=()):
    conn = get_conn()
    if conn is None:
        return 0
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else 0


def has_simulated_data() -> bool:
    """Return True if any row in condition_history is simulated."""
    conn = get_conn()
    if conn is None:
        return False
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM condition_history WHERE data_source='simulated'"
        ).fetchone()[0]
        return n > 0
    except Exception:
        return False


def show_simulated_badge():
    """Render the SIMULATED DEMO DATA warning banner."""
    st.warning(
        "⚠️ **SIMULATED DEMO DATA** — All condition scores, detections and risk values "
        "shown here are synthetically generated (`data_source='simulated'`). "
        "They do **not** represent real road measurements.",
        icon="🔬",
    )


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.title("🛣️ UrbanRoadAI")
st.sidebar.markdown("AI-Powered Road Condition Monitoring")
st.sidebar.markdown("**SDG 11 — Sustainable Cities**")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Overview",
        "🗺️ Map View",
        "🔍 Segment Detail",
        "🔬 Defect Analysis",
        "📈 Survey Comparison",
        "🔧 Maintenance Priority",
    ],
)

st.sidebar.markdown("---")

# Show simulated badge in sidebar if any simulated data exists
if has_simulated_data():
    st.sidebar.error("🔬 SIMULATED DATA MODE")

st.sidebar.caption(
    "⚠️ Scores reflect **visible surface defects** only. "
    "This is not a structural pavement assessment."
)

# ---------------------------------------------------------------------------
# Guard: no database
# ---------------------------------------------------------------------------

if get_conn() is None:
    st.error(
        f"**Database not found** at `{DB_PATH}`.\n\n"
        "Seed the demo database first:\n```bash\n"
        "source .venv/bin/activate\n"
        "python -m src.db.seed_demo\n```"
    )
    st.stop()


# ===================================================================
# PAGE: Overview
# ===================================================================

if page == "📊 Overview":
    st.title("📊 System Overview")

    if has_simulated_data():
        show_simulated_badge()

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Road Segments", scalar("SELECT COUNT(*) FROM road_segments"))
    c2.metric("Surveys", scalar("SELECT COUNT(*) FROM surveys"))
    c3.metric("Images Analysed", scalar("SELECT COUNT(*) FROM images"))
    c4.metric("Detections", scalar("SELECT COUNT(*) FROM damage_detections"))

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Condition Band Distribution")
        bands = query(
            """SELECT band, COUNT(*) as count
               FROM condition_history
               WHERE id IN (
                   SELECT MAX(id) FROM condition_history GROUP BY segment_id
               )"""
        )
        if not bands.empty:
            bands["label"] = bands["band"].map(BAND_LABELS)
            fig = px.pie(
                bands,
                values="count",
                names="label",
                color="band",
                color_discrete_map=BAND_COLORS,
                title="Latest Condition Band — All Segments",
            )
            fig.update_traces(textinfo="label+percent+value")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No condition data yet.")

    with col_right:
        st.subheader("Defect Class Distribution")
        classes = query(
            """SELECT dc.class_name, COUNT(*) as count
               FROM damage_detections dd
               JOIN damage_classes dc ON dd.class_id = dc.class_id
               GROUP BY dc.class_name ORDER BY count DESC"""
        )
        if not classes.empty:
            fig = px.bar(
                classes,
                x="class_name",
                y="count",
                color="class_name",
                title="Detected Defects by Class (All Surveys)",
                labels={"class_name": "Defect Class", "count": "Count"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No detections yet.")

    # Score evolution across surveys
    st.subheader("📈 All Segments — Condition Score Trend")
    trend = query(
        """SELECT ch.segment_id, rs.road_name, ch.survey_date, ch.score, ch.band
           FROM condition_history ch
           JOIN road_segments rs ON ch.segment_id = rs.segment_id
           ORDER BY ch.segment_id, ch.survey_date"""
    )
    if not trend.empty:
        fig = px.line(
            trend,
            x="survey_date",
            y="score",
            color="segment_id",
            hover_data=["road_name", "band"],
            markers=True,
            title="Condition Score Over Time — All Segments",
            labels={"survey_date": "Survey Date", "score": "Condition Score (0–100)"},
        )
        fig.add_hline(y=25, line_dash="dot", line_color="#2ecc71",
                      annotation_text="Good/Fair")
        fig.add_hline(y=50, line_dash="dot", line_color="#f1c40f",
                      annotation_text="Fair/Poor")
        fig.add_hline(y=75, line_dash="dot", line_color="#e67e22",
                      annotation_text="Poor/Very Poor")
        fig.update_layout(yaxis=dict(range=[0, 105]), height=420)
        st.plotly_chart(fig, use_container_width=True)

    # Top risk segments
    st.subheader("🔴 Highest Risk Segments")
    risk_df = query(
        """SELECT p.segment_id, r.road_name, r.road_type,
                  ROUND(p.risk_prob, 3) as risk_prob,
                  p.horizon_days, p.model_version, p.data_source
           FROM predictions p
           JOIN road_segments r ON p.segment_id = r.segment_id
           ORDER BY p.risk_prob DESC LIMIT 10"""
    )
    if not risk_df.empty:
        st.dataframe(risk_df, use_container_width=True, hide_index=True)


# ===================================================================
# PAGE: Map View
# ===================================================================

elif page == "🗺️ Map View":
    st.title("🗺️ Geospatial Map View")

    if has_simulated_data():
        show_simulated_badge()

    segments = query(
        """SELECT rs.segment_id, rs.road_name, rs.road_type, rs.length_m, rs.geom_wkt,
                  ch.score, ch.band
           FROM road_segments rs
           LEFT JOIN (
               SELECT segment_id, score, band,
                      ROW_NUMBER() OVER (PARTITION BY segment_id ORDER BY survey_date DESC) as rn
               FROM condition_history
           ) ch ON rs.segment_id = ch.segment_id AND ch.rn = 1"""
    )

    if segments.empty:
        st.info("No segment data available.")
    else:
        map_data = []
        for _, row in segments.iterrows():
            wkt = row.get("geom_wkt", "")
            if wkt and "LINESTRING" in str(wkt).upper():
                try:
                    coords_str = str(wkt).split("(")[1].split(")")[0]
                    pairs = [p.strip().split() for p in coords_str.split(",")]
                    lats = [float(p[1]) for p in pairs]
                    lons = [float(p[0]) for p in pairs]
                    clat = sum(lats) / len(lats)
                    clon = sum(lons) / len(lons)
                    band = row.get("band", "good") or "good"
                    map_data.append({
                        "lat": clat,
                        "lon": clon,
                        "segment_id": row["segment_id"],
                        "road_name": row["road_name"],
                        "band": band,
                        "score": round(float(row.get("score") or 0), 1),
                    })
                except (IndexError, ValueError):
                    pass

        if map_data:
            map_df = pd.DataFrame(map_data)

            # Ensure GPS coordinates are numeric
            map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
            map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")

            # Remove records with invalid coordinates
            map_df = map_df.dropna(subset=["lat", "lon"])

            if not map_df.empty:

                # Debug information
                st.write("Map data preview:")
                st.dataframe(
                    map_df[["segment_id", "lat", "lon", "band"]].head(10)
                )
                st.write("Total map points:", len(map_df))

                # Calculate centre using actual GPS coordinates
                center_lat = map_df["lat"].mean()
                center_lon = map_df["lon"].mean()

                # Generate interactive road condition map
                fig = px.scatter_map(
                    map_df,
                    lat="lat",
                    lon="lon",
                    color="band",
                    color_discrete_map=BAND_COLORS,
                    hover_name="road_name",
                    hover_data={
                        "segment_id": True,
                        "score": True,
                        "band": True,
                        "lat": False,
                        "lon": False
                    },
                    zoom=15,
                    center={
                        "lat": center_lat,
                        "lon": center_lon
                    },
                    map_style="open-street-map",
                    title="Road Segments by Latest Condition Band"
                )

                # Improve marker visibility
                fig.update_traces(
                    marker=dict(
                        size=16,
                        opacity=1
                    )
                )

                fig.update_layout(
                    height=560,
                    margin=dict(l=0, r=0, t=40, b=0)
                )

                st.plotly_chart(fig, use_container_width=True)

                # Segment Summary Table
                st.subheader("Segment Summary Table")

                disp = segments[
                    ["segment_id", "road_name", "road_type",
                     "length_m", "score", "band"]
                ].copy()

                disp.columns = [
                    "Segment ID", "Road Name", "Type",
                    "Length (m)", "Latest Score", "Band"
                ]

                st.dataframe(
                    disp,
                    use_container_width=True,
                    hide_index=True
                )

            else:
                st.warning("No valid GPS coordinates available.")
        else:
            st.info("No road segment map data available.")



# ===================================================================
# PAGE: Segment Detail
# ===================================================================

elif page == "🔍 Segment Detail":
    st.title("🔍 Segment Detail View")

    if has_simulated_data():
        show_simulated_badge()

    seg_list = query(
        "SELECT segment_id, road_name FROM road_segments ORDER BY segment_id"
    )
    if seg_list.empty:
        st.info("No segments in database.")
    else:
        options = [
            f"{r['segment_id']} — {r['road_name']}"
            for _, r in seg_list.iterrows()
        ]
        selected = st.selectbox("Select Segment", options)
        seg_id = selected.split(" — ")[0]

        seg_info = query(
            "SELECT * FROM road_segments WHERE segment_id = ?", (seg_id,)
        )
        if not seg_info.empty:
            si = seg_info.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Road Name", si["road_name"])
            c2.metric("Road Type", si["road_type"])
            c3.metric("Length", f"{si['length_m']:.0f} m")
            c4.metric("Data Source", si.get("data_source", "unknown"))

        st.markdown("---")
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("📈 Condition History")
            history = query(
                """SELECT survey_date, score, band, n_defects, defect_density
                   FROM condition_history WHERE segment_id = ?
                   ORDER BY survey_date""",
                (seg_id,),
            )
            if not history.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history["survey_date"],
                    y=history["score"],
                    mode="lines+markers",
                    name="Condition Score",
                    line=dict(color="#3498db", width=3),
                    marker=dict(size=12),
                ))
                fig.add_hline(y=25, line_dash="dot", line_color="#2ecc71",
                              annotation_text="Good/Fair")
                fig.add_hline(y=50, line_dash="dot", line_color="#f1c40f",
                              annotation_text="Fair/Poor")
                fig.add_hline(y=75, line_dash="dot", line_color="#e67e22",
                              annotation_text="Poor/Very Poor")
                fig.update_layout(
                    title="Condition Score per Survey",
                    xaxis_title="Survey Date",
                    yaxis_title="Score (0–100)",
                    yaxis=dict(range=[0, 105]),
                    height=380,
                )
                st.plotly_chart(fig, use_container_width=True)

                # Band color column
                history["band_colour"] = history["band"].map(BAND_COLORS)
                st.dataframe(
                    history[["survey_date", "score", "band",
                              "n_defects", "defect_density"]],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No condition history for this segment.")

        with col_r:
            st.subheader("🔬 Defects on This Segment")
            defects = query(
                """SELECT dc.class_name, COUNT(*) as count
                   FROM damage_detections dd
                   JOIN images i ON dd.image_id = i.image_id
                   JOIN damage_classes dc ON dd.class_id = dc.class_id
                   WHERE i.segment_id = ?
                   GROUP BY dc.class_name""",
                (seg_id,),
            )
            if not defects.empty:
                fig = px.bar(
                    defects,
                    x="class_name",
                    y="count",
                    color="class_name",
                    title="Defect Classes on Segment (All Surveys)",
                    labels={"class_name": "Class", "count": "Count"},
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No detections on this segment.")

        st.subheader("⚠️ Risk Prediction")
        risk = query(
            """SELECT risk_prob, horizon_days, model_version, made_at, data_source
               FROM predictions WHERE segment_id = ?
               ORDER BY made_at DESC LIMIT 1""",
            (seg_id,),
        )
        if not risk.empty:
            r = risk.iloc[0]
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Risk Probability", f"{r['risk_prob']*100:.1f}%")
            rc2.metric("Horizon", f"{r['horizon_days']} days")
            rc3.metric("Model", r["model_version"])
            if r.get("data_source") == "simulated":
                st.caption("🔬 SIMULATED — Experimental rule-based prediction only.")
            else:
                st.caption("⚠️ Experimental rule-based prediction. Not a validated forecast.")


# ===================================================================
# PAGE: Defect Analysis
# ===================================================================

elif page == "🔬 Defect Analysis":
    st.title("🔬 Defect Analysis")

    if has_simulated_data():
        show_simulated_badge()

    all_dets = query(
        """SELECT dd.*, dc.class_name
           FROM damage_detections dd
           JOIN damage_classes dc ON dd.class_id = dc.class_id"""
    )

    if all_dets.empty:
        st.info("No detections in the database.")
    else:
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Class Distribution")
            class_dist = all_dets.groupby("class_name").size().reset_index(name="count")
            fig = px.pie(
                class_dist,
                values="count",
                names="class_name",
                title="Detection Count by Defect Class",
            )
            fig.update_traces(textinfo="label+percent+value")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Confidence Distribution")
            fig = px.histogram(
                all_dets,
                x="confidence",
                nbins=20,
                color="class_name",
                title="Detection Confidence by Class",
                labels={"confidence": "Confidence Score", "count": "Frequency"},
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)

        c3, c4 = st.columns(2)

        with c3:
            st.subheader("Severity Distribution")
            sev_dist = all_dets.groupby("severity").size().reset_index(name="count")
            sev_colors = {"low": "#2ecc71", "moderate": "#f1c40f", "high": "#e74c3c"}
            fig = px.bar(
                sev_dist,
                x="severity",
                y="count",
                color="severity",
                color_discrete_map=sev_colors,
                title="Detections by Severity",
                labels={"severity": "Severity", "count": "Count"},
                category_orders={"severity": ["low", "moderate", "high"]},
            )
            st.plotly_chart(fig, use_container_width=True)

        with c4:
            st.subheader("Bounding-Box Area Ratio")
            fig = px.histogram(
                all_dets,
                x="area_ratio",
                nbins=25,
                color="class_name",
                title="Area Ratio Distribution (box area ÷ image area)",
                labels={"area_ratio": "Area Ratio", "count": "Frequency"},
                barmode="stack",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 All Detections")
        st.dataframe(
            all_dets[["image_id", "class_name", "confidence", "severity",
                       "area_ratio", "model_version", "data_source"]]
            .sort_values("confidence", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# ===================================================================
# PAGE: Survey Comparison
# ===================================================================

elif page == "📈 Survey Comparison":
    st.title("📈 Survey Comparison")

    if has_simulated_data():
        show_simulated_badge()

    surveys = query(
        "SELECT survey_id, survey_date, notes FROM surveys ORDER BY survey_date"
    )
    if len(surveys) < 2:
        st.info("Need at least 2 surveys for comparison.")
    else:
        labels = surveys.apply(
            lambda r: f"{r['survey_id']} — {r['survey_date']}", axis=1
        )
        c1, c2 = st.columns(2)
        with c1:
            s1_label = st.selectbox("Survey 1 (Earlier)", labels, index=0)
        with c2:
            s2_label = st.selectbox(
                "Survey 2 (Later)", labels,
                index=min(len(surveys) - 1, 2)
            )

        s1_id = int(s1_label.split(" — ")[0])
        s2_id = int(s2_label.split(" — ")[0])

        if s1_id == s2_id:
            st.warning("Select two different surveys.")
        else:
            ch1 = query(
                """SELECT ch.segment_id, r.road_name,
                          ch.score as score_1, ch.band as band_1,
                          ch.n_defects as defects_1
                   FROM condition_history ch
                   JOIN road_segments r ON ch.segment_id = r.segment_id
                   WHERE ch.survey_id = ?""",
                (s1_id,),
            )
            ch2 = query(
                """SELECT ch.segment_id,
                          ch.score as score_2, ch.band as band_2,
                          ch.n_defects as defects_2
                   FROM condition_history ch WHERE ch.survey_id = ?""",
                (s2_id,),
            )

            if ch1.empty or ch2.empty:
                st.warning("One survey has no condition history data.")
            else:
                merged = ch1.merge(ch2, on="segment_id", how="outer")
                merged["score_1"] = merged["score_1"].fillna(0).round(1)
                merged["score_2"] = merged["score_2"].fillna(0).round(1)
                merged["score_change"] = (merged["score_2"] - merged["score_1"]).round(1)
                merged["trend"] = merged["score_change"].apply(
                    lambda x: "⬆️ Worsened" if x > 2
                    else ("⬇️ Improved" if x < -2 else "➡️ Stable")
                )

                st.subheader("Segment Condition Changes")
                st.dataframe(
                    merged[["segment_id", "road_name", "score_1", "band_1",
                             "score_2", "band_2", "score_change", "trend"]],
                    use_container_width=True,
                    hide_index=True,
                )

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name=f"Survey {s1_id} ({s1_label.split(' — ')[1]})",
                    x=merged["segment_id"],
                    y=merged["score_1"],
                    marker_color="#3498db",
                ))
                fig.add_trace(go.Bar(
                    name=f"Survey {s2_id} ({s2_label.split(' — ')[1]})",
                    x=merged["segment_id"],
                    y=merged["score_2"],
                    marker_color="#e74c3c",
                ))
                fig.update_layout(
                    barmode="group",
                    title="Condition Score Comparison",
                    xaxis_title="Segment",
                    yaxis_title="Condition Score (0–100)",
                    yaxis=dict(range=[0, 105]),
                )
                st.plotly_chart(fig, use_container_width=True)


# ===================================================================
# PAGE: Maintenance Priority
# ===================================================================

elif page == "🔧 Maintenance Priority":
    st.title("🔧 Maintenance Prioritization")

    if has_simulated_data():
        show_simulated_badge()

    st.info(
        "Segments ranked by **risk probability** (experimental rule-based model, "
        "`model_version=rule_v1`). Higher risk = higher priority for maintenance."
    )

    priority = query(
        """SELECT p.segment_id, r.road_name, r.road_type, r.length_m,
                  ROUND(ch.score, 1) as latest_score, ch.band as latest_band,
                  ROUND(p.risk_prob, 3) as risk_prob,
                  p.horizon_days, p.data_source
           FROM predictions p
           JOIN road_segments r ON p.segment_id = r.segment_id
           LEFT JOIN (
               SELECT segment_id, score, band,
                      ROW_NUMBER() OVER
                        (PARTITION BY segment_id ORDER BY survey_date DESC) as rn
               FROM condition_history
           ) ch ON p.segment_id = ch.segment_id AND ch.rn = 1
           ORDER BY p.risk_prob DESC"""
    )

    if priority.empty:
        st.info("No prediction data. Run `python -m src.db.seed_demo` first.")
    else:
        priority.insert(0, "Rank", range(1, len(priority) + 1))

        def _risk_color(val):
            if val >= 0.7:
                return "background-color: #e74c3c; color: white"
            elif val >= 0.4:
                return "background-color: #f39c12; color: black"
            return "background-color: #2ecc71; color: black"

        st.dataframe(
            priority.style.map(_risk_color, subset=["risk_prob"]),
            use_container_width=True,
            hide_index=True,
        )

        fig = px.bar(
            priority.sort_values("risk_prob", ascending=True),
            x="risk_prob",
            y="road_name",
            orientation="h",
            color="risk_prob",
            color_continuous_scale=["#2ecc71", "#f1c40f", "#e74c3c"],
            title="Risk Probability by Segment (Highest = Highest Priority)",
            labels={"risk_prob": "Risk Probability (0–1)", "road_name": "Road Segment"},
        )
        fig.update_layout(height=max(300, len(priority) * 55))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.caption(
        "⚠️ **Scientific Disclaimer:** Condition scores are based on visible surface "
        "defects detected by a YOLO model. Bounding-box area ≠ actual damaged area. "
        "This system cannot independently determine structural pavement health, "
        "subgrade strength, or material composition. Risk predictions are experimental "
        "(rule-based `rule_v1`) and must not be cited as validated forecasts."
    )
