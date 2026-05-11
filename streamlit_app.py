import streamlit as st
import sys
import json
import shutil
import os
from pathlib import Path
from datetime import datetime
import time

st.set_page_config(
    page_title="CRE Deal Analyzer",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0a0a0f; }
    .stApp { background-color: #0a0a0f; }
    h1, h2, h3 { color: #e0e0e0 !important; }
    .stMarkdown { color: #e0e0e0; }
    .verdict-good {
        background: linear-gradient(135deg, #166534 0%, #22c55e 100%);
        color: white; padding: 1rem 2rem; border-radius: 12px;
        text-align: center; font-size: 1.5rem; font-weight: bold;
    }
    .verdict-caution {
        background: linear-gradient(135deg, #713f12 0%, #fbbf24 100%);
        color: white; padding: 1rem 2rem; border-radius: 12px;
        text-align: center; font-size: 1.5rem; font-weight: bold;
    }
    .verdict-pass {
        background: linear-gradient(135deg, #7f1d1d 0%, #f87171 100%);
        color: white; padding: 1rem 2rem; border-radius: 12px;
        text-align: center; font-size: 1.5rem; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.title("🏢 CRE Deal Analyzer")
    st.caption("Institutional-grade commercial real estate analysis")

    with st.sidebar:
        st.header("About")
        st.markdown("""
        **Pipeline:**
        1. 📄 PDF Extraction
        2. 👤 Tenant Research
        3. 📊 Market Comps
        4. 🛰️ Satellite Analysis
        5. ⚠️ Risk Scoring
        6. 📄 Report Generation
        """)
        st.divider()
        st.markdown("Powered by web search + ESRI satellite tiles")

    st.subheader("Upload Investment Memorandum")
    uploaded_file = st.file_uploader(
        "Drop your PDF deal memo here",
        type=['pdf'],
        help="Investment memorandum, offering memorandum, or lease abstract"
    )

    if uploaded_file is not None:
        temp_dir = Path("/tmp/cre-streamlit")
        temp_dir.mkdir(exist_ok=True)
        pdf_path = temp_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"

        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        st.divider()
        st.subheader("Analysis in Progress")

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            from cre_analyzer.pdf_ingestor import ingest_pdf
            from cre_analyzer.tenant_research import research_tenant
            from cre_analyzer.market_comp import research_market
            from cre_analyzer.satellite_analyzer import analyze_property_satellite
            from cre_analyzer.analyzer import CREAnalyzer

            status_text.text("Phase 1/6: Extracting PDF metrics...")
            progress_bar.progress(10)
            metrics = ingest_pdf(str(pdf_path))

            tenant_name = metrics.get('tenant', 'Unknown')
            location = metrics.get('location', 'Unknown')

            status_text.text("Phase 2/6: Researching tenant...")
            progress_bar.progress(30)
            tenant_data = research_tenant(tenant_name, '5A2')

            status_text.text("Phase 3/6: Gathering market comparables...")
            progress_bar.progress(50)
            market_result = research_market(location, metrics.get('property_type', 'office'))
            market_data = market_result.get('market_data', {})

            status_text.text("Phase 4/6: Analyzing satellite imagery...")
            progress_bar.progress(70)
            satellite = analyze_property_satellite(location)

            status_text.text("Phase 5/6: Running risk scoring...")
            progress_bar.progress(85)
            analyzer = CREAnalyzer(str(pdf_path))
            result = analyzer.analyze()

            status_text.text("Phase 6/6: Generating report...")
            progress_bar.progress(100)
            time.sleep(0.5)

            status_text.empty()
            progress_bar.empty()

            display_results(result, metrics, tenant_data, market_data, satellite, pdf_path)

        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")
            st.exception(e)


def display_results(result, metrics, tenant_data, market_data, satellite, pdf_path):
    st.divider()

    verdict = result.get('verdict', 'ANALYZED')
    score = result.get('total_score', 0)

    col1, col2 = st.columns([1, 2])

    with col1:
        verdict_class = "verdict-good" if "GOOD" in verdict else "verdict-caution" if "CAUTION" in verdict else "verdict-pass"
        st.markdown(f'<div class="{verdict_class}">{verdict}<br><span style="font-size:2rem">{score}/100</span></div>', unsafe_allow_html=True)

    with col2:
        st.subheader("Executive Summary")
        summary_text = result.get('summary', 'Analysis complete. Review metrics below.')
        st.write(summary_text)

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🏢 Property")
        st.metric("Location", metrics.get('location', 'N/A'))
        st.metric("Type", metrics.get('property_type', 'N/A'))
        st.metric("Size", f"{metrics.get('size_sqft', 0):,} sq ft" if metrics.get('size_sqft') else 'N/A')
        st.metric("Year Built", metrics.get('year_built', 'N/A'))

    with col2:
        st.subheader("💰 Financial")
        price = metrics.get('price')
        st.metric("Asking Price", f"£{price:,.0f}" if price else 'N/A')
        st.metric("Annual Rent", f"£{metrics.get('rent', 0):,.0f}" if metrics.get('rent') else 'N/A')
        st.metric("NIY", f"{metrics.get('niy', 'N/A')}%")
        st.metric("Price/sq ft", f"£{metrics.get('price_psf', 0):.2f}" if metrics.get('price_psf') else 'N/A')

    with col3:
        st.subheader("👤 Tenant")
        st.metric("Tenant", metrics.get('tenant', 'N/A'))
        st.metric("Stores", tenant_data.get('store_count', 'N/A'))
        st.metric("Parent", tenant_data.get('parent_company', 'N/A')[:20] if tenant_data.get('parent_company') else 'N/A')
        st.metric("Credit", tenant_data.get('credit_rating', 'N/A'))

    st.divider()

    st.subheader("📊 Market Comparables")

    comp_rent = market_data.get('comparable_rent_psf')
    passing_rent = metrics.get('rent_psf')

    if comp_rent and passing_rent:
        rent_gap = ((comp_rent - passing_rent) / passing_rent) * 100

        col1, col2, col3 = st.columns(3)
        col1.metric("Market Rent (psf)", f"£{comp_rent:.2f}")
        col2.metric("Passing Rent (psf)", f"£{passing_rent:.2f}")
        col3.metric("Gap to Market", f"{rent_gap:+.1f}%", delta_color="inverse" if rent_gap > 0 else "normal")

        if rent_gap > 20:
            st.warning(f"⚠️ Passing rent is {rent_gap:.0f}% BELOW market — potential value-add opportunity or lower-grade building")
        elif rent_gap < -10:
            st.error(f"🚨 Passing rent is {abs(rent_gap):.0f}% ABOVE market — reversion risk on lease expiry")
        else:
            st.success(f"✅ Rent aligned with market (within {abs(rent_gap):.0f}%)")

    indicators = market_data.get('demand_indicators', [])
    if indicators:
        with st.expander("Market Demand Indicators"):
            for ind in indicators[:5]:
                st.write(f"• {ind}")

    st.divider()

    st.subheader("🛰️ Satellite Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Property Location:**")
        st.write(f"Lat: {satellite.get('lat', 'N/A')}")
        st.write(f"Lng: {satellite.get('lng', 'N/A')}")
        st.write(f"**Parking:** {satellite.get('parking_lot_status', 'N/A')}")
        st.write(f"**Occupancy estimate:** {satellite.get('estimated_occupancy_pct', 'N/A')}")
        st.write(f"**Building condition:** {satellite.get('building_condition_estimate', 'N/A')}")

    with col2:
        satellite_path = satellite.get('image_path')
        output_dir = Path("/tmp/cre-results")
        if satellite_path and Path(satellite_path).exists():
            st.image(satellite_path, caption="Satellite view (ESRI World Imagery)")
        elif output_dir.exists():
            sat_files = list(output_dir.glob("satellite_*.jpg"))
            if sat_files:
                annotated = [f for f in sat_files if "annotated" in f.name]
                target = annotated[0] if annotated else sat_files[0]
                st.image(str(target), caption="Satellite view with analysis overlay")
            else:
                st.info("No satellite image available")
        else:
            st.info("No satellite image available")

    st.divider()

    st.subheader("⚠️ Risk Breakdown")

    risk_scores = result.get('risk_scores', {})

    if risk_scores:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Tenant Risk", f"{risk_scores.get('tenant_risk', 'N/A')}/10")
        with col2:
            st.metric("Market Risk", f"{risk_scores.get('market_risk', 'N/A')}/10")
        with col3:
            st.metric("Structural", f"{risk_scores.get('structural_risk', 'N/A')}/10")
        with col4:
            st.metric("Lease Risk", f"{risk_scores.get('lease_risk', 'N/A')}/10")

    st.divider()

    output_dir = Path("/tmp/cre-results")
    report_path = output_dir / "report.md"

    if report_path.exists():
        with open(report_path, 'r') as f:
            report_content = f.read()

        st.download_button(
            label="📄 Download Full Report (Markdown)",
            data=report_content,
            file_name=f"CRE_Analysis_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )

    with st.expander("🔧 Raw Analysis JSON"):
        st.json(result)


if __name__ == "__main__":
    main()
