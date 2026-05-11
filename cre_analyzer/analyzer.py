#!/usr/bin/env python3
"""
CRE Deal Analyzer - Main Orchestrator
End-to-end pipeline: PDF -> Metrics -> Tenant Research -> Market Comps -> Risk Score -> Report
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

from cre_analyzer.pdf_ingestor import ingest_pdf
from cre_analyzer.tenant_research import research_tenant
from cre_analyzer.market_comp import research_market
from cre_analyzer.satellite_analyzer import analyze_property_satellite
from cre_analyzer.risk_scorer import score_deal
from cre_analyzer.report_generator import generate_report


class CREAnalyzer:
    """End-to-end CRE deal analysis pipeline."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.metrics = {}
        self.tenant = {}
        self.market = {}
        self.risk = {}
        self.report = ""
        
    def analyze(self) -> Dict[str, Any]:
        """Run full analysis pipeline."""
        print("=" * 60)
        print("CRE DEAL ANALYZER")
        print("=" * 60)
        
        # Step 1: Ingest PDF
        print("\n[1/5] Extracting deal metrics from PDF...")
        self.metrics = ingest_pdf(self.pdf_path)
        print(f"  → Price: £{self.metrics.get('asking_price', 0):,.0f}")
        print(f"  → Size: {self.metrics.get('sq_ft', 0):,.0f} sq ft")
        print(f"  → Tenant: {self.metrics.get('tenant_name', 'N/A')}")
        print(f"  → Rent: £{self.metrics.get('annual_rent', 0):,.0f}/year")
        
        # Step 2: Research tenant
        print("\n[2/5] Researching tenant...")
        tenant_name = self.metrics.get("tenant_name", "Unknown")
        dnb = self.metrics.get("tenant_dnb_rating")
        self.tenant = research_tenant(tenant_name, dnb)
        print(f"  → Credit: {self.tenant.get('credit_rating', 'N/A')}")
        print(f"  → Health Score: {self.tenant.get('financial_health_score', 'N/A')}/10")
        
        # Step 3: Market comps (includes portal scraping + live search + VOA)
        print("\n[3/5] Researching market comparables...")
        location = self.metrics.get("location", "Unknown")
        ptype = self.metrics.get("property_type", "Office")
        sqft = self.metrics.get("sq_ft")
        market_result = research_market(location, ptype, sqft)
        
        # Satellite imagery analysis
        print("  → [3a] Analyzing satellite imagery...")
        prop_name = (self.metrics.get("property_name") or "").replace("\n", " ").strip()
        address = f"{prop_name}, {location}" if prop_name else location
        self.satellite = analyze_property_satellite(address)
        print(f"    Satellite view: {(self.satellite.get('image_path') or 'N/A')[:60]}...")
        print(f"    Parking status: {self.satellite.get('parking_lot_status') or 'N/A'} ({self.satellite.get('estimated_car_count')} cars)")
        
        # Scraped comparables already included in market_result
        self.scraped_comps = market_result.get('scraped_comps', {})
        avg_rent = self.scraped_comps.get('comparable_rent_psf')
        supply = self.scraped_comps.get('supply_count', 0)
        voa = self.scraped_comps.get('voa_rateable_value')
        print(f"    Avg comparable rent: £{avg_rent:.2f}/sq ft" if avg_rent else "    Avg comparable rent: N/A")
        print(f"    Supply count: {supply} listings")
        if voa:
            print(f"    VOA rateable value: £{voa:,.0f}")
        
        self.market = market_result.get("market_score", {})
        print(f"  → Market Trend: {self.market.get('market_trend', 'N/A')}")
        print(f"  → Market Score: {self.market.get('market_score', 'N/A')}/10")
        
        # Step 4: Risk scoring
        print("\n[4/5] Scoring deal risks...")
        self.risk = score_deal(self.metrics, self.tenant, self.market)
        print(f"  → Total Score: {self.risk.get('total_score', 0)}/100")
        print(f"  → Verdict: {self.risk.get('verdict', 'N/A')}")
        
        # Step 5: Generate report
        print("\n[5/5] Generating report...")
        self.report = generate_report(self.metrics, self.tenant, market_result, self.risk, getattr(self, 'satellite', None), getattr(self, 'scraped_comps', None))
        
        # Save outputs
        self._save_outputs()
        
        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        
        return {
            "metrics": self.metrics,
            "tenant": self.tenant,
            "market": market_result,
            "risk": self.risk,
            "report": self.report,
        }
    
    def _save_outputs(self):
        """Save analysis outputs to workspace."""
        base = Path("/tmp/cre-results")
        base.mkdir(parents=True, exist_ok=True)
        
        # Save JSON
        json_path = base / "analysis.json"
        with open(json_path, 'w') as f:
            json.dump({
                "metrics": self.metrics,
                "tenant": self.tenant,
                "market": self.market,
                "satellite": getattr(self, 'satellite', {}),
                "scraped_comps": getattr(self, 'scraped_comps', {}),
                "risk": self.risk,
            }, f, indent=2, default=str)
        
        # Save report
        report_path = base / "report.md"
        with open(report_path, 'w') as f:
            f.write(self.report)
        
        print(f"  → Saved to {base}/")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    analyzer = CREAnalyzer(pdf_path)
    result = analyzer.analyze()
    
    # Print verdict
    print(f"\n🏛️  VERDICT: {result['risk']['verdict']}")
    print(f"📊 Score: {result['risk']['total_score']}/100")
    if result.get('satellite'):
        print(f"🛰️  Satellite: {result['satellite'].get('image_path', 'N/A')[:60]}...")
    if result.get('scraped_comps'):
        avg = result['scraped_comps'].get('avg_rent_psf')
        if avg:
            print(f"📈 Scraped avg rent: £{avg:.2f}/sq ft")
        voa = result['scraped_comps'].get('voa_rateable_value')
        if voa:
            print(f"🏛️  VOA rateable value: £{voa:,.0f}")
    print(f"📄 Report saved to: cre-analyzer/output/report.md")


if __name__ == "__main__":
    main()
