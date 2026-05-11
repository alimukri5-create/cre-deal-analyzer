#!/usr/bin/env python3
"""CRE Deal Analyzer - Market Comp Engine (Streamlit Cloud compatible)"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class MarketComp:
    location: str
    property_type: str
    comparable_rent_psf: Optional[float] = None
    vacancy_rate: Optional[float] = None
    market_trend: Optional[str] = None
    nearby_supply_sqft: Optional[float] = None
    demand_indicators: List[str] = None
    
    def __post_init__(self):
        if self.demand_indicators is None:
            self.demand_indicators = []


class MarketCompEngine:
    def __init__(self, location: str, property_type: str, sq_ft: Optional[float] = None):
        self.location = location
        self.property_type = property_type
        self.sq_ft = sq_ft
        self.comp = MarketComp(location=location, property_type=property_type)
        
    def research(self) -> Dict[str, Any]:
        self._search_market_data()
        self._assess_demand_indicators()
        return {
            "market_data": asdict(self.comp),
            "market_score": self.get_market_score(),
        }
    
    def _search_market_data(self):
        query = f"{self.location} {self.property_type} rent per sq ft vacancy rate 2024 2025"
        result = self._web_search(query)
        self._parse_market_data(result)
        
        comp_query = f"{self.location} {self.property_type} available to let vacant space 2025"
        comp_result = self._web_search(comp_query)
        self._parse_competitive_supply(comp_result)
    
    def _web_search(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=5):
                    results.append(f"{r['title']}: {r['body']}")
                return "\n\n".join(results) if results else ""
        except Exception:
            return ""
    
    def _parse_competitive_supply(self, text: str):
        if not text:
            return
        supply_mentions = len(re.findall(r'available|to let|vacant|for rent', text, re.IGNORECASE))
        if supply_mentions > 3:
            self.comp.demand_indicators.append(f"Competitive supply detected ({supply_mentions} listings nearby)")
        elif supply_mentions == 0:
            self.comp.demand_indicators.append("Limited competitive supply in immediate area")
    
    def _parse_market_data(self, text: str):
        rent_patterns = [
            r'£(\d{2,3})[-\s]*£?(\d{2,3})\s*per\s*sq\s*ft',
            r'£(\d{2,3})\s*per\s*sq\s*ft',
            r'£(\d{2,3})\s*psf',
            r'(\d{2,3})\s*pounds?\s*per\s*sq\s*ft',
        ]
        rents_found = []
        for pattern in rent_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if isinstance(m, tuple):
                    for val in m:
                        if val and val.isdigit():
                            rents_found.append(int(val))
                elif m.isdigit():
                    rents_found.append(int(m))
        
        if rents_found:
            self.comp.comparable_rent_psf = sum(rents_found) / len(rents_found)
        
        vac_patterns = [
            r'vacancy\s*rate.*? (\d{1,2}\.?\d?)%',
            r'vacancy\s*rate.*? (\d{1,2})\s*percent',
            r'vacancies?\s*at\s*(\d{1,2})%',
        ]
        for pattern in vac_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    self.comp.vacancy_rate = float(match.group(1))
                    break
                except (IndexError, ValueError):
                    pass
        
        text_lower = text.lower()
        if any(w in text_lower for w in ['rising', 'upward', 'increasing', 'strong', 'recovering', 'growth']):
            self.comp.market_trend = "rising"
        elif any(w in text_lower for w in ['falling', 'declining', 'decreasing', 'weak', 'struggling']):
            self.comp.market_trend = "falling"
        else:
            self.comp.market_trend = "stable"
    
    def _assess_demand_indicators(self):
        query = f"{self.location} office demand major employers economy 2024 2025"
        result = self._web_search(query)
        
        indicators = []
        if re.search(r'university|uni|campus', result, re.IGNORECASE):
            uni_match = re.search(r'([A-Z][a-zA-Z\s]+University)', result)
            if uni_match:
                indicators.append(f"University presence: {uni_match.group(1)}")
        
        employer_patterns = [
            r'([A-Z][a-zA-Z\s]+)\s*headquarters',
            r'([A-Z][a-zA-Z\s]+)\s*HQ',
            r'([A-Z][a-zA-Z\s]+)\s*employs?\s+\d+',
        ]
        for pattern in employer_patterns:
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                employer = match.group(1).strip()
                if len(employer) > 3 and len(employer) < 40:
                    indicators.append(f"Major employer: {employer}")
                    break
        
        if re.search(r'railway|train station|motorway|M\d+|M1|M6|transport', result, re.IGNORECASE):
            indicators.append("Transport connectivity (rail/motorway)")
        
        sectors = re.findall(r'((?:logistics|tech|finance|pharma|manufacturing|digital)\s+sector)', result, re.IGNORECASE)
        if sectors:
            indicators.append(f"Key sector: {sectors[0]}")
        
        if not indicators:
            indicators.append("Location demand data - review manually")
        
        self.comp.demand_indicators = indicators[:4]
    
    def get_market_score(self) -> Dict[str, Any]:
        score = 5
        
        if self.comp.vacancy_rate:
            if self.comp.vacancy_rate < 8:
                score += 2
            elif self.comp.vacancy_rate > 15:
                score -= 2
        
        if self.comp.market_trend == "rising":
            score += 1
        elif self.comp.market_trend == "falling":
            score -= 1
        
        if len(self.comp.demand_indicators) > 3:
            score += 1
        
        return {
            "market_score": max(1, min(10, score)),
            "vacancy_rate": self.comp.vacancy_rate,
            "market_trend": self.comp.market_trend,
            "comparable_rent_psf": self.comp.comparable_rent_psf,
        }


def research_market(location: str, property_type: str, sq_ft: Optional[float] = None) -> Dict[str, Any]:
    engine = MarketCompEngine(location, property_type, sq_ft)
    return engine.research()
