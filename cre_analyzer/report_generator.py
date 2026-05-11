#!/usr/bin/env python3
"""
CRE Deal Analyzer - Report Generator
Produces markdown reports with verdict.
"""

import json
from typing import Dict, Any
from datetime import datetime


class ReportGenerator:
    """Generates markdown deal evaluation reports."""
    
    def __init__(self, metrics: Dict, tenant: Dict, market: Dict, risk: Dict, satellite: Dict = None, scraped_comps: Dict = None):
        self.metrics = metrics
        self.tenant = tenant
        self.market = market
        self.risk = risk
        self.satellite = satellite or {}
        self.scraped_comps = scraped_comps or {}
        
    def generate(self) -> str:
        """Generate full markdown report."""
        lines = []
        
        # Header
        lines.append(f"# CRE Deal Evaluation Report")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        verdict = self.risk.get("verdict", "UNKNOWN")
        score = self.risk.get("total_score", 0)
        lines.append(f"### Verdict: **{verdict}** (Score: {score}/100)")
        lines.append("")
        
        # Property Overview
        lines.append("## Property Overview")
        lines.append("")
        lines.append(self._property_table())
        lines.append("")
        
        # Financial Metrics
        lines.append("## Financial Metrics")
        lines.append("")
        lines.append(self._financial_table())
        lines.append("")
        
        # Tenant Analysis
        lines.append("## Tenant Analysis")
        lines.append("")
        lines.append(self._tenant_section())
        lines.append("")
        
        # Market Context
        lines.append("## Market Context")
        lines.append("")
        lines.append(self._market_section())
        lines.append("")
        
        # Satellite Analysis
        if self.satellite:
            lines.append("## Satellite Imagery Analysis")
            lines.append("")
            lines.append(self._satellite_section())
            lines.append("")
        
        # Scraped Comparables
        if self.scraped_comps and self.scraped_comps.get('listings'):
            lines.append("## Scraped Market Comparables")
            lines.append("")
            lines.append(self._scraped_section())
            lines.append("")
        
        # Risk Breakdown
        lines.append("## Risk Assessment")
        lines.append("")
        lines.append(self._risk_section())
        lines.append("")
        
        # Strengths & Warnings
        lines.append("## Deal Strengths")
        lines.append("")
        for s in self.risk.get("strengths", []):
            lines.append(f"- {s}")
        lines.append("")
        
        lines.append("## Warnings")
        lines.append("")
        for w in self.risk.get("warnings", []):
            lines.append(f"- ⚠️ {w}")
        lines.append("")
        
        # Recommendation
        lines.append("## Recommendation")
        lines.append("")
        lines.append(self._recommendation())
        lines.append("")
        
        return "\n".join(lines)
    
    def _property_table(self) -> str:
        m = self.metrics
        rows = [
            f"| Property | {m.get('property_name', 'N/A')} |",
            f"| Location | {m.get('location', 'N/A')} |",
            f"| Type | {m.get('property_type', 'N/A')} |",
            f"| Size | {m.get('sq_ft', 'N/A'):,.0f} sq ft |" if m.get('sq_ft') else "| Size | N/A |",
            f"| Year Built | {m.get('year_built', 'N/A')} |",
            f"| EPC Rating | {m.get('epc_rating', 'N/A')} |",
            f"| Tenure | {m.get('tenure', 'N/A')} |",
            f"| Site Area | {m.get('site_area_acres', 'N/A')} acres |" if m.get('site_area_acres') else "| Site Area | N/A |",
            f"| Parking | {m.get('car_parking_spaces', 'N/A')} spaces ({m.get('parking_ratio', 'N/A')}) |" if m.get('car_parking_spaces') else "| Parking | N/A |",
        ]
        return "\n".join(rows)
    
    def _financial_table(self) -> str:
        m = self.metrics
        rows = [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Asking Price | £{m.get('asking_price', 0):,.0f} |" if m.get('asking_price') else "| Asking Price | N/A |",
            f"| Price / sq ft | £{m.get('price_psf', 0):.2f} |" if m.get('price_psf') else "| Price / sq ft | N/A |",
            f"| Annual Rent | £{m.get('annual_rent', 0):,.0f} |" if m.get('annual_rent') else "| Annual Rent | N/A |",
            f"| Rent / sq ft | £{m.get('rent_psf', 0):.2f} |" if m.get('rent_psf') else "| Rent / sq ft | N/A |",
            f"| Net Initial Yield | {m.get('net_initial_yield', 0):.2f}% |" if m.get('net_initial_yield') else "| Net Initial Yield | N/A |",
            f"| Reversionary Yield | {m.get('reversionary_yield', 0):.2f}% |" if m.get('reversionary_yield') else "| Reversionary Yield | N/A |",
            f"| ERV / sq ft | £{m.get('erv_psf', 0):.2f} |" if m.get('erv_psf') else "| ERV / sq ft | N/A |",
            f"| Lease Term | {m.get('lease_term_years', 'N/A')} years |",
        ]
        return "\n".join(rows)
    
    def _tenant_section(self) -> str:
        t = self.tenant
        lines = [
            f"**Tenant:** {t.get('name', 'N/A')}",
            "",
            f"- **Credit Rating:** {t.get('credit_rating', 'N/A')}",
            f"- **D\u0026B Rating:** {t.get('dnb_rating', 'N/A')}",
            f"- **Financial Health Score:** {t.get('financial_health_score', 'N/A')}/10",
            f"- **Parent Company:** {t.get('parent_company', 'N/A')}",
            f"- **Store Count:** {t.get('store_count', 'N/A')}",
            f"- **Employees:** {t.get('employee_count', 'N/A')}",
            f"- **Status:** {t.get('public_private', 'N/A')}",
            "",
            "**Recent News:**",
        ]
        for news in t.get('recent_news', [])[:5]:
            lines.append(f"- {news}")
        return "\n".join(lines)
    
    def _market_section(self) -> str:
        m = self.market
        md = m.get("market_data", {})
        ms = m.get("market_score", {})
        lines = [
            f"**Location:** {md.get('location', 'N/A')}",
            f"**Property Type:** {md.get('property_type', 'N/A')}",
            "",
            f"- **Market Trend:** {ms.get('market_trend', 'N/A')}",
            f"- **Vacancy Rate:** {ms.get('vacancy_rate', 'N/A')}%",
            f"- **Comparable Rent:** £{ms.get('comparable_rent_psf', 'N/A'):.2f}/sq ft" if ms.get('comparable_rent_psf') else "- **Comparable Rent:** N/A",
            f"- **Market Score:** {ms.get('market_score', 'N/A')}/10",
            "",
            "**Demand Indicators:**",
        ]
        for ind in md.get('demand_indicators', []):
            lines.append(f"- {ind}")
        return "\n".join(lines)
    
    def _satellite_section(self) -> str:
        s = self.satellite
        lines = [
            f"**Property:** {s.get('property_address', 'N/A')}",
            f"**Lat/Lng:** {s.get('lat', 'N/A')}, {s.get('lng', 'N/A')}",
            "",
            f"- **Parking Lot Status:** {s.get('parking_lot_status', 'N/A')}",
            f"- **Estimated Occupancy:** {s.get('estimated_occupancy_pct', 'N/A')}%" if s.get('estimated_occupancy_pct') else "- **Estimated Occupancy:** N/A",
            f"- **Building Condition:** {s.get('building_condition_estimate', 'N/A')}",
            "",
            "**Activity Indicators:**",
        ]
        for ind in s.get('activity_indicators', []):
            lines.append(f"- {ind}")
        return "\n".join(lines)
    
    def _scraped_section(self) -> str:
        sc = self.scraped_comps
        lines = [
            f"**Source:** Rightmove / Zoopla scrape",
            f"**Listings found:** {sc.get('supply_count', 0)}",
            f"**Avg comparable rent:** £{sc.get('comparable_rent_psf', 'N/A'):.2f}/sq ft" if sc.get('comparable_rent_psf') else "**Avg comparable rent:** N/A",
            "",
            "**Sample Listings:**",
        ]
        for listing in sc.get('listings', [])[:5]:
            rent = listing.get('rent_psf') or listing.get('rent_total')
            lines.append(f"- {listing.get('source', 'N/A')}: {listing.get('address', 'N/A')} - £{rent}/sq ft" if listing.get('rent_psf') else f"- {listing.get('source', 'N/A')}: {listing.get('address', 'N/A')} - £{rent}/annum")
        
        if sc.get('vacancy_indicators'):
            lines.append("")
            lines.append("**Market Signals:**")
            for ind in sc.get('vacancy_indicators', []):
                lines.append(f"- {ind}")
        return "\n".join(lines)
    
    def _risk_section(self) -> str:
        b = self.risk.get("breakdown", {})
        lines = [
            "| Risk Category | Score / 20 |",
            "|---------------|------------|",
            f"| Tenant Risk | {b.get('tenant_risk', 0)} |",
            f"| Lease Risk | {b.get('lease_risk', 0)} |",
            f"| Market Risk | {b.get('market_risk', 0)} |",
            f"| Property Risk | {b.get('property_risk', 0)} |",
            f"| Financial Risk | {b.get('financial_risk', 0)} |",
            "",
            f"**Total Score: {self.risk.get('total_score', 0)} / 100**",
        ]
        return "\n".join(lines)
    
    def _recommendation(self) -> str:
        verdict = self.risk.get("verdict", "UNKNOWN")
        warnings = self.risk.get("warnings", [])
        strengths = self.risk.get("strengths", [])
        
        if verdict == "GOOD DEAL":
            return (
                "This deal presents attractive risk-adjusted returns with a strong tenant, "
                "solid lease structure, and positive reversionary potential. "
                "Recommended for acquisition subject to standard due diligence."
            )
        elif verdict == "CONDITIONAL":
            rec = (
                "This deal has merit but carries identifiable risks that require mitigation. "
            )
            if warnings:
                rec += f"Key conditions: address {len(warnings)} identified warning(s). "
            rec += "Proceed with enhanced due diligence and risk mitigation strategy."
            return rec
        else:
            return (
                "This deal carries significant risks that outweigh the potential returns. "
                "Multiple warning factors identified. Not recommended unless material "
                "price reduction or structural improvements are secured."
            )


def generate_report(metrics: Dict, tenant: Dict, market: Dict, risk: Dict, satellite: Dict = None, scraped_comps: Dict = None) -> str:
    """Main entry point: generate markdown report."""
    gen = ReportGenerator(metrics, tenant, market, risk, satellite, scraped_comps)
    return gen.generate()


if __name__ == "__main__":
    import sys
    # Can accept JSON file path
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
        report = generate_report(data["metrics"], data["tenant"], data["market"], data["risk"])
    else:
        print("Usage: python report_generator.py <analysis_json>")
        sys.exit(1)
    print(report)
