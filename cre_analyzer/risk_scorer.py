#!/usr/bin/env python3
"""
CRE Deal Analyzer - Risk Scoring Engine
Scores deal risks and outputs verdict.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class RiskScore:
    total_score: int  # 0-100, higher = better deal
    tenant_risk: int  # 0-20
    lease_risk: int  # 0-20
    market_risk: int  # 0-20
    property_risk: int  # 0-20
    financial_risk: int  # 0-20
    verdict: str  # GOOD DEAL / BAD DEAL / CONDITIONAL
    reasoning: List[str]
    warnings: List[str]
    strengths: List[str]


class RiskScorer:
    """Scores CRE deal risks and produces verdict."""
    
    VERDICT_THRESHOLDS = {
        "GOOD DEAL": 70,
        "CONDITIONAL": 50,
        "BAD DEAL": 0,
    }
    
    def __init__(self, metrics: Dict[str, Any], tenant_profile: Dict[str, Any], market_data: Dict[str, Any]):
        self.metrics = metrics
        self.tenant = tenant_profile
        self.market = market_data
        self.scores = {}
        self.reasoning = []
        self.warnings = []
        self.strengths = []
        
    def score(self) -> RiskScore:
        """Run full risk scoring and return verdict."""
        self._score_tenant_risk()
        self._score_lease_risk()
        self._score_market_risk()
        self._score_property_risk()
        self._score_financial_risk()
        
        total = sum(self.scores.values())
        
        # Determine verdict
        if total >= self.VERDICT_THRESHOLDS["GOOD DEAL"]:
            verdict = "GOOD DEAL"
        elif total >= self.VERDICT_THRESHOLDS["CONDITIONAL"]:
            verdict = "CONDITIONAL"
        else:
            verdict = "BAD DEAL"
        
        return RiskScore(
            total_score=total,
            tenant_risk=self.scores["tenant"],
            lease_risk=self.scores["lease"],
            market_risk=self.scores["market"],
            property_risk=self.scores["property"],
            financial_risk=self.scores["financial"],
            verdict=verdict,
            reasoning=self.reasoning,
            warnings=self.warnings,
            strengths=self.strengths,
        )
    
    def _score_tenant_risk(self):
        """Score tenant creditworthiness (0-20)."""
        score = 10  # Baseline
        
        # D&B rating: first digit = size, letter = risk
        dnb = self.tenant.get("dnb_rating")
        if dnb and len(dnb) >= 2:
            letter = dnb[1]
            if letter in 'Aa':
                score += 5
                self.strengths.append(f"D&B rating {dnb} - minimal risk (A grade)")
            elif letter in 'Bb':
                score += 4
                self.strengths.append(f"D&B rating {dnb} - low risk (B grade)")
            elif letter in 'Cc':
                score += 2
            elif letter in 'DdEeFfGgHh':
                score -= 3
                self.warnings.append(f"D&B rating {dnb} indicates elevated credit risk")
            elif letter in 'Nn':
                score -= 5
                self.warnings.append(f"D&B rating {dnb} - company out of business risk")
        
        # Financial health score
        health = self.tenant.get("financial_health_score")
        if health:
            if health >= 8:
                score += 3
            elif health <= 4:
                score -= 3
                self.warnings.append("Tenant financial health is weak")
        
        # Parent company backing
        parent = self.tenant.get("parent_company")
        if parent:
            score += 2
            self.strengths.append(f"Backed by parent company: {parent}")
        
        # Single tenant concentration
        single = self.tenant.get("single_tenant_risk")
        if single:
            score -= 2
            self.warnings.append("Small tenant with limited store footprint")
        
        self.scores["tenant"] = max(0, min(20, score))
    
    def _score_lease_risk(self):
        """Score lease structure risk (0-20)."""
        score = 10
        
        # Lease term length
        term = self.metrics.get("lease_term_years")
        if term:
            if term >= 10:
                score += 4
                self.strengths.append(f"Long lease term ({term} years) provides income certainty")
            elif term >= 7:
                score += 2
            elif term >= 5:
                score += 0
            else:
                score -= 4
                self.warnings.append(f"Short lease term ({term} years) - re-leasing risk imminent")
        
        # Rent review structure
        review_date = self.metrics.get("rent_review_date")
        post_review = self.metrics.get("rent_post_review")
        current_rent = self.metrics.get("annual_rent")
        
        if review_date and post_review and current_rent:
            uplift_pct = ((post_review - current_rent) / current_rent) * 100
            if uplift_pct > 10:
                score += 2
                self.strengths.append(f"Fixed uplift to {review_date} provides {uplift_pct:.1f}% rent growth")
            elif uplift_pct < 0:
                score -= 2
                self.warnings.append("Rent review is downward - negative reversion")
        
        # Single tenant
        # (Already scored in tenant risk, but worth noting)
        if self.tenant.get("single_tenant_risk") is None:
            score += 1
            self.strengths.append("Single tenant - simple lease structure, no multi-tenant conflicts")
        
        self.scores["lease"] = max(0, min(20, score))
    
    def _score_market_risk(self):
        """Score market/location risk (0-20)."""
        score = 10
        
        # Market trend
        trend = self.market.get("market_trend")
        if trend == "rising":
            score += 3
            self.strengths.append("Market rents trending upward")
        elif trend == "falling":
            score -= 3
            self.warnings.append("Market rents declining - re-leasing risk")
        
        # Vacancy rate
        vac = self.market.get("vacancy_rate")
        if vac:
            if vac < 8:
                score += 3
                self.strengths.append(f"Low vacancy market ({vac}%) - strong demand")
            elif vac > 15:
                score -= 3
                self.warnings.append(f"High vacancy market ({vac}%) - weak demand if tenant leaves")
        
        # Comparable rent vs deal rent
        comp_rent = self.market.get("comparable_rent_psf")
        deal_rent = self.metrics.get("rent_psf")
        if comp_rent and deal_rent:
            if deal_rent < comp_rent * 0.8:
                score += 2
                self.strengths.append(f"Rent {deal_rent:.2f}/sq ft below market {comp_rent:.2f}/sq ft - reversion upside")
            elif deal_rent > comp_rent * 1.1:
                score -= 2
                self.warnings.append(f"Rent {deal_rent:.2f}/sq ft above market {comp_rent:.2f}/sq ft - over-rented risk")
        
        self.scores["market"] = max(0, min(20, score))
    
    def _score_property_risk(self):
        """Score property-specific risk (0-20)."""
        score = 10
        
        # Property age
        year_built = self.metrics.get("year_built")
        if year_built:
            age = 2025 - year_built
            if age < 10:
                score += 3
                self.strengths.append("Modern building - low capex risk")
            elif age < 25:
                score += 1
            elif age > 40:
                score -= 3
                self.warnings.append(f"Building is {age} years old - increasing maintenance risk")
        
        # EPC rating
        epc = self.metrics.get("epc_rating")
        if epc:
            epc_scores = {"A": 3, "B": 2, "C": 1, "D": 0, "E": -1, "F": -2, "G": -3}
            score += epc_scores.get(epc, 0)
            if epc in "AB":
                self.strengths.append(f"EPC {epc} rating - energy efficient, future-proof")
            elif epc in "EFG":
                self.warnings.append(f"EPC {epc} rating - potential MEES compliance costs")
        
        # Parking ratio
        parking = self.metrics.get("car_parking_spaces")
        sqft = self.metrics.get("sq_ft")
        if parking and sqft:
            ratio = sqft / parking
            if ratio < 150:
                score += 1
                self.strengths.append("Good parking ratio for suburban office")
            elif ratio > 300:
                score -= 1
                self.warnings.append("Low parking ratio may limit tenant appeal")
        
        # Freehold vs leasehold
        tenure = self.metrics.get("tenure")
        if tenure == "Freehold":
            score += 2
            self.strengths.append("Freehold ownership - no ground rent or lease expiry risk")
        elif tenure == "Leasehold":
            score -= 1
            self.warnings.append("Leasehold - review ground rent and expiry terms")
        
        self.scores["property"] = max(0, min(20, score))
    
    def _score_financial_risk(self):
        """Score financial metrics (0-20)."""
        score = 10
        
        # Yield vs market
        niy = self.metrics.get("net_initial_yield")
        if niy:
            if niy >= 9:
                score += 3
                self.strengths.append(f"Strong {niy:.1f}% net initial yield - well above risk-free rate")
            elif niy >= 7:
                score += 1
            elif niy < 5:
                score -= 3
                self.warnings.append(f"Low {niy:.1f}% yield - limited income buffer for risks")
        
        # Reversionary yield
        rev_yield = self.metrics.get("reversionary_yield")
        if rev_yield and niy:
            spread = rev_yield - niy
            if spread > 1.0:
                score += 2
                self.strengths.append(f"{spread:.1f}% reversionary yield spread - built-in upside")
        
        # Price per sq ft
        price_psf = self.metrics.get("price_psf")
        comp_rent = self.market.get("comparable_rent_psf")
        if price_psf and comp_rent:
            implied_yield = (self.metrics.get("annual_rent", 0) / self.metrics.get("sq_ft", 1)) / price_psf * 100
            if implied_yield > 8:
                score += 1
        
        # ERV vs passing rent
        erv = self.metrics.get("erv_psf")
        deal_rent = self.metrics.get("rent_psf")
        if erv and deal_rent:
            if erv > deal_rent * 1.2:
                score += 2
                self.strengths.append(f"ERV £{erv:.2f}/sq ft vs passing £{deal_rent:.2f}/sq ft - significant reversion potential")
            elif erv < deal_rent:
                score -= 2
                self.warnings.append("ERV below passing rent - over-rented, negative reversion risk")
        
        self.scores["financial"] = max(0, min(20, score))


def score_deal(metrics: Dict, tenant: Dict, market: Dict) -> Dict:
    """Main entry point: score a deal and return verdict."""
    scorer = RiskScorer(metrics, tenant, market)
    result = scorer.score()
    return {
        "total_score": result.total_score,
        "max_score": 100,
        "verdict": result.verdict,
        "breakdown": {
            "tenant_risk": result.tenant_risk,
            "lease_risk": result.lease_risk,
            "market_risk": result.market_risk,
            "property_risk": result.property_risk,
            "financial_risk": result.financial_risk,
        },
        "reasoning": result.reasoning,
        "warnings": result.warnings,
        "strengths": result.strengths,
    }


if __name__ == "__main__":
    # Test with mock data
    metrics = {
        "annual_rent": 632812,
        "rent_psf": 11.06,
        "sq_ft": 57227,
        "lease_term_years": 9,
        "net_initial_yield": 10.1,
        "reversionary_yield": 11.4,
        "price_psf": 109.2,
        "erv_psf": 19.5,
        "year_built": 1993,
        "epc_rating": "B",
        "car_parking_spaces": 305,
        "tenure": "Freehold",
    }
    tenant = {
        "dnb_rating": "5A2",
        "financial_health_score": 8,
        "parent_company": "EssilorLuxottica",
        "single_tenant_risk": False,
    }
    market = {
        "market_trend": "stable",
        "vacancy_rate": 12,
        "comparable_rent_psf": 14.0,
    }
    result = score_deal(metrics, tenant, market)
    print(json.dumps(result, indent=2))
