import pandas as pd
import streamlit as st

from shared import configure_page, research_notice, safe_get, source_caption

configure_page("Fundamentals & Events", "📰")

instruments = safe_get("/api/v1/instruments", default=[])
if not instruments:
    st.stop()
symbol = st.selectbox("Instrument", [item["symbol"] for item in instruments])
research = safe_get(f"/api/v1/research/{symbol}", default={})

fundamentals, news, earnings, actions = st.tabs(
    ["Fundamentals", "News", "Earnings", "Corporate actions"]
)
with fundamentals:
    component = research.get("fundamentals", {})
    if component.get("available"):
        st.metric("Fundamental score", f"{component.get('score')}/100")
        st.dataframe(
            pd.DataFrame(component.get("data", {}).items(), columns=["Metric", "Value"]),
            use_container_width=True,
            hide_index=True,
        )
        source_caption(component.get("provider", "unknown"), component.get("retrieved_at"))
    else:
        st.info("Fundamental data is not available for this instrument.")
with news:
    component = research.get("news", {})
    items = component.get("data", []) if component.get("available") else []
    if items:
        for item in items[:25]:
            headline = item.get("headline", "Untitled")
            url = item.get("url")
            st.markdown(f"**[{headline}]({url})**" if url else f"**{headline}**")
            st.caption(
                f"{item.get('source', 'Unknown source')} · Published timestamp: "
                f"{item.get('datetime', 'Not available')}"
            )
            if item.get("summary"):
                st.write(item["summary"])
            st.divider()
        source_caption(component.get("provider", "unknown"), component.get("retrieved_at"))
    else:
        st.info("No company news is stored.")
with earnings:
    component = research.get("earnings", {})
    events = component.get("data", []) if component.get("available") else []
    if events:
        st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
        source_caption(component.get("provider", "unknown"), component.get("retrieved_at"))
    else:
        st.info("No earnings events are stored.")
with actions:
    for title, key in (("Dividends", "dividends"), ("Stock splits", "splits")):
        st.subheader(title)
        component = research.get(key, {})
        events = component.get("data", []) if component.get("available") else []
        if events:
            st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
            source_caption(component.get("provider", "unknown"), component.get("retrieved_at"))
        else:
            st.info(f"{title} are unavailable on the configured provider plan.")

research_notice()
