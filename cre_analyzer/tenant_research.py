#!/usr/bin/env python3
"""CRE Deal Analyzer - Tenant Research (Streamlit Cloud compatible)"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class TenantProfile:
    name: str
    parent_company: Optional[str] = None
    sector: Optional[str] = None
    store_count: Optional[int] = None
    employee_count: Optional[str] = None
    annual_revenue: Optional[str] = None
    credit_rating: Optional[str] = None
    dnb_rating: Optional[str] = None
    years_in_operation: Optional[int] = None
    public_private: Optional[str] = None
    recent_news: List[str] = None
    financial_health_score: Optional[int] = None
    
    def __post_init__(self):
        if self.recent_news is None:
            self.recent_news = []


class TenantResearcher:
    DNB_SIZE_BONUS = {
        "1": -1, "2": -1, "3": 0, "4": 0,
        "5": 2, "6": 3, "7": 3, "8": 3,
    }
    
    def __init__(self, tenant_name: str, dnb_rating: Optional[str] = None):
        self.tenant_name = tenant_name
        self.dnb_rating = dnb_rating
        self.profile = TenantProfile(name=tenant_name, dnb_rating=dnb_rating)
        
    def research(self) -> TenantProfile:
        self._search_company_info()
        self._search_financial_news()
        self._assess_financial_health()
        return self.profile
    
    def _search_company_info(self):
        queries = [
            f"{self.tenant_name} number of stores UK 2024 2025",
            f"{self.tenant_name} parent company owner",
            f"{self.tenant_name} employees headcount",
        ]
        all_text = []
        for query in queries:
            result = self._web_search(query)
            if result:
                all_text.append(result)
        combined = "\n\n".join(all_text)
        self._parse_company_info(combined)
        lines = [l.strip() for l in combined.split('\n') if l.strip() and len(l.strip()) > 30]
        self.profile.recent_news.extend(lines[:5])
    
    def _search_financial_news(self):
        queries = [
            f"{self.tenant_name} financial results 2024 2025",
            f"{self.tenant_name} store closures expansion",
            f"{self.tenant_name} parent company revenue",
        ]
        for query in queries:
            result = self._web_search(query)
            if result:
                lines = [l.strip() for l in result.split('\n') if l.strip() and len(l.strip()) > 20]
                self.profile.recent_news.extend(lines[:3])
    
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
    
    def _parse_company_info(self, text: str):
        store_patterns = [
            r'(\d{2,4})\s+stores',
            r'(\d{2,4})\s+retail\s+outlets',
            r'operates\s+(\d{2,4})\s+stores',
            r'has\s+(\d{2,4})\s+stores',
            r'(\d{2,4})\s+opticians?',
            r'(\d{2,4})\s+branches',
        ]
        for pattern in store_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = int(match.group(1))
                if 50 < val < 2000:
                    self.profile.store_count = val
                    break
        
        emp_patterns = [
            r'(\d{1,2},?\d{3})\s+employees',
            r'(\d{1,2},?\d{3})\s+staff',
            r'(\d{1,2},?\d{3})\s+people',
            r'employs?\s+(\d{1,2},?\d{3})',
        ]
        for pattern in emp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.profile.employee_count = match.group(1).replace(',', '')
                break
        
        parent_patterns = [
            r'(?:parent|owned\s+by|acquired\s+by|part\s+of|subsidiary\s+of)\s+(?:the\s+)?([A-Z][A-Za-z\s&]+?)(?:\.|\n|,|$)',
            r'([A-Z][a-zA-Z\s]+)\s+acquired\s+(?:the\s+)?company',
            r'now\s+(?:owned\s+by|part\s+of)\s+([A-Z][A-Za-z\s&]+?)(?:\.|\n|,|$)',
        ]
        for pattern in parent_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parent = match.group(1).strip()
                if len(parent) > 3 and len(parent) < 40 and 'store' not in parent.lower():
                    self.profile.parent_company = parent
                    break
        
        rev_match = re.search(r'(?:revenue|turnover)\s+of\s+£?([\d,.]+)\s*million', text, re.IGNORECASE)
        if rev_match:
            self.profile.annual_revenue = f"£{rev_match.group(1)}M"
        
        rev_match2 = re.search(r'(?:revenue|turnover)\s+of\s+£?([\d,.]+)\s*billion', text, re.IGNORECASE)
        if rev_match2:
            self.profile.annual_revenue = f"£{rev_match2.group(1)}B"
        
        if re.search(r'plc|public limited|listed on|stock exchange|shares|ticker', text.lower()):
            self.profile.public_private = "Public"
        elif re.search(r'private|subsidiary|privately', text.lower()):
            self.profile.public_private = "Private (Subsidiary)"
    
    def _assess_financial_health(self):
        score = 5
        
        if self.dnb_rating and len(self.dnb_rating) >= 2:
            number = self.dnb_rating[0]
            letter = self.dnb_rating[1]
            
            if letter in 'Aa':
                score += 3
            elif letter in 'Bb':
                score += 2
            elif letter in 'Cc':
                score += 0
            elif letter in 'DdEeFfGgHh':
                score -= 3
            elif letter in 'Nn':
                score -= 5
            
            if number and number in self.DNB_SIZE_BONUS:
                score += self.DNB_SIZE_BONUS[number]
        
        if self.profile.parent_company:
            major_parents = ['essilorluxottica', 'grandvision', 'luxottica', 'essilor']
            if any(p in self.profile.parent_company.lower() for p in major_parents):
                score += 2
        
        if self.profile.store_count:
            if self.profile.store_count > 500:
                score += 1
            elif self.profile.store_count < 10:
                score -= 2
        
        self.profile.financial_health_score = max(1, min(10, score))
        
        if score >= 8:
            self.profile.credit_rating = "Excellent"
        elif score >= 6:
            self.profile.credit_rating = "Good"
        elif score >= 4:
            self.profile.credit_rating = "Fair"
        else:
            self.profile.credit_rating = "Poor"
    
    def get_risk_contribution(self) -> Dict[str, Any]:
        return {
            "tenant_name": self.profile.name,
            "financial_health_score": self.profile.financial_health_score,
            "credit_rating": self.profile.credit_rating,
            "dnb_rating": self.profile.dnb_rating,
            "parent_company": self.profile.parent_company,
            "public_private": self.profile.public_private,
            "store_count": self.profile.store_count,
            "single_tenant_risk": self.profile.store_count < 50 if self.profile.store_count else None,
        }


def research_tenant(tenant_name: str, dnb_rating: Optional[str] = None) -> Dict[str, Any]:
    researcher = TenantResearcher(tenant_name, dnb_rating)
    profile = researcher.research()
    return asdict(profile)
