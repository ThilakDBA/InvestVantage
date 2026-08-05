import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.shared import SCORE_WEIGHTS, configure_page, research_notice, safe_get, score_label

configure_page("Signals", "🧭")

signals = safe_get("/api/v1/signals", default=[])
if not signals:
    st.info("Generate a research signal from Instrument Research to populate this page.")
    research_notice()
    st.stop()

summary = pd.DataFrame(signals)
st.dataframe(
    summary[
        [
            "symbol",
            "recommendation",
            "confidence_score",
            "risk_score",
            "data_completeness",
            "generated_at",
            "status",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

selected_index = st.selectbox(
    "Inspect signal",
    range(len(signals)),
    format_func=lambda index: (
        f"{signals[index]['symbol']} · {signals[index]['recommendation']} · "
        f"{signals[index]['generated_at']}"
    ),
)
signal = signals[selected_index]
recommendation, confidence, risk, completeness = st.columns(4)
recommendation.metric("Recommendation", signal["recommendation"])
confidence.metric("Confidence", f"{signal['confidence_score']}/100")
risk.metric("Risk", f"{signal['risk_score']}/100")
completeness.metric("Data completeness", f"{signal['data_completeness']}%")

component_fields = {
    "Technical": "technical_score",
    "Fundamentals": "fundamental_score",
    "News": "news_score",
    "Market regime": "market_regime_score",
    "Sector strength": "sector_strength_score",
    "Portfolio suitability": "portfolio_score",
}
components = []
for name, field in component_fields.items():
    score = signal.get(field)
    weight = SCORE_WEIGHTS[name]
    components.append(
        {
            "Component": name,
            "Score": score,
            "Weight": f"{weight:.0%}",
            "Contribution": round(score * weight, 1) if score is not None else None,
            "Interpretation": score_label(score),
        }
    )
component_frame = pd.DataFrame(components)
left, right = st.columns([1.2, 1])
with left:
    st.dataframe(component_frame, use_container_width=True, hide_index=True)
with right:
    available = component_frame.dropna(subset=["Contribution"])
    st.plotly_chart(
        px.bar(
            available,
            x="Contribution",
            y="Component",
            orientation="h",
            color="Interpretation",
            title="Weighted score contribution",
        ),
        use_container_width=True,
    )

st.info(signal["explanation"])
positive, negative = st.columns(2)
with positive:
    st.subheader("Positive factors")
    for factor in signal.get("positive_factors") or ["No positive factor recorded"]:
        st.success(factor)
with negative:
    st.subheader("Risks and missing information")
    for factor in signal.get("negative_factors") or ["No negative factor recorded"]:
        st.warning(factor)
    missing = component_frame[component_frame["Score"].isna()]["Component"].tolist()
    if missing:
        st.warning(f"Missing components: {', '.join(missing)}")

st.subheader("Research references")
reference_left, reference_middle, reference_right = st.columns(3)
reference_left.metric("Entry reference", f"${signal['entry_price']:,.2f}")
stop_reference = f"${signal['stop_price']:,.2f}" if signal["stop_price"] else "—"
reference_middle.metric("Stop reference", stop_reference)
reference_right.metric(
    "Target reference", f"${signal['target_price']:,.2f}" if signal["target_price"] else "—"
)
with st.expander("Invalidation conditions"):
    for condition in signal.get("invalidation_conditions", []):
        st.write(f"• {condition}")
st.caption(
    "Confidence measures agreement and indicator coverage; it is not the probability of profit."
)
research_notice()
