#!/usr/bin/env python3
"""
CRE Deal Analyzer - PDF Ingestion Module
Extracts structured deal metrics from investment memorandum PDFs.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import pdfplumber


class PDFIngestor:
    """Extracts CRE deal data from PDF investment memorandums."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.raw_text = ""
        self.pages_text = []
        
    def extract_all_text(self) -> str:
        """Extract text from all pages."""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    self.pages_text.append(text)
        self.raw_text = "\n\n".join(self.pages_text)
        return self.raw_text
    
    def extract_metrics(self) -> Dict[str, Any]:
        """Extract key financial and property metrics."""
        if not self.raw_text:
            self.extract_all_text()
            
        metrics = {
            "property_name": self._extract_property_name(),
            "location": self._extract_location(),
            "asking_price": self._extract_price(),
            "sq_ft": self._extract_sq_ft(),
            "annual_rent": self._extract_annual_rent(),
            "rent_psf": self._extract_rent_psf(),
            "tenant_name": self._extract_tenant(),
            "lease_term_years": self._extract_lease_term(),
            "yield": self._extract_yield(),
            "rent_review_date": self._extract_rent_review(),
            "rent_post_review": self._extract_post_review_rent(),
            "car_parking_spaces": self._extract_parking(),
            "parking_ratio": self._extract_parking_ratio(),
            "epc_rating": self._extract_epc(),
            "site_area_acres": self._extract_site_area(),
            "tenure": self._extract_tenure(),
            "property_type": self._extract_property_type(),
            "year_built": self._extract_year_built(),
            "tenant_dnb_rating": self._extract_dnb_rating(),
            "erv_psf": self._extract_erv(),
        }
        
        # Compute derived metrics
        metrics = self._compute_derived(metrics)
        
        return metrics
    
    def _extract_property_name(self) -> Optional[str]:
        patterns = [
            r"([A-Z][a-zA-Z\s]+Business\s+Park)",
            r"([A-Z][a-zA-Z\s]+Office)",
            r"([A-Z][a-zA-Z\s]+Building)",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_location(self) -> Optional[str]:
        # Look for "Nottingham | NG11 6NZ" pattern
        match = re.search(r"([A-Za-z\s]+)\s*\|\s*([A-Z]{1,2}\d{1,2}\s*\d?[A-Z]{2})", self.raw_text)
        if match:
            return f"{match.group(1).strip()}, {match.group(2)}"
        
        # Look for city mentions near postcode
        match = re.search(r"([A-Z][a-z]+)\s+is a major city", self.raw_text)
        if match:
            city = match.group(1)
            postcodes = re.findall(r"[A-Z]{1,2}\d{1,2}\s*\d?[A-Z]{2}", self.raw_text)
            if postcodes:
                return f"{city}, {postcodes[0]}"
        return None
    
    def _extract_price(self) -> Optional[float]:
        patterns = [
            r"offers? in excess of\s*£?([\d,.]+)",
            r"£([\d,.]+)\s*million",
            r"£([\d,.]+)(?:\s|$)",
            r"price[d]?\s*[:;]?\s*£?([\d,.]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(",", "").replace(".", "")
                # Handle cases like "6.25" meaning 6.25 million
                if "million" in match.group(0).lower():
                    return float(price_str) * 1_000_000 if len(price_str) < 4 else float(price_str)
                price = float(price_str)
                return price if price > 1_000_000 else price * 1_000_000
        return None
    
    def _extract_sq_ft(self) -> Optional[float]:
        patterns = [
            r"(?:extends to|extends?|totals?|comprises?|approximately)\s+([\d,.]+)\s*sq\s*ft",
            r"([\d,.]+)\s*sq\s*ft\s*\(",
            r"([\d,.]{3,})\s*sq\s*ft",
            r"([\d,.]+)\s*sqft",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                val = float(match.group(1).replace(",", ""))
                if val > 1000:  # Must be reasonable building size
                    return val
        return None
    
    def _extract_annual_rent(self) -> Optional[float]:
        # Use specific patterns that avoid matching £11.06 psf
        patterns = [
            r"producing an annual rent.*?£([\d,]+)",
            r"annual rent.*?£([\d,]+)",
            r"rent of\s*£?([\d,]+)\s*per\s*annum",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                val_str = match.group(1).replace(",", "")
                if val_str.replace(".", "").isdigit():
                    return float(val_str)
        # Fallback: per annum figures
        matches = re.findall(r"£([\d,]+)\s*per\s*annum", self.raw_text, re.IGNORECASE)
        for m in matches:
            val_str = m.replace(",", "")
            if val_str.replace(".", "").isdigit():
                val = float(val_str)
                if 100000 < val < 10000000:
                    return val
        return None
    
    def _extract_rent_psf(self) -> Optional[float]:
        patterns = [
            r"£([\d.]+)\s*per\s*sq\s*ft",
            r"£([\d.]+)\s*psf",
            r"\(([£$]?)([\d.]+)\s*per\s*sq\s*ft\)",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace("£", "").replace("$", ""))
        return None
    
    def _extract_tenant(self) -> Optional[str]:
        patterns = [
            r"Fully let to\s+([A-Z][A-Za-z\s\(\)]+?)(?:,|\.)",
            r"let to\s+([A-Z][A-Za-z\s\(\)]+?)(?:,|\.|producing)",
            r"tenant[:;]?\s*([A-Z][A-Za-z\s\(\)]+?)(?:,|\.|\n)",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                tenant = match.group(1).strip()
                if len(tenant) > 3:
                    return tenant
        return None
    
    def _extract_lease_term(self) -> Optional[float]:
        patterns = [
            r"Unexpired term of\s*(\d+(?:\.\d+)?)\s*years?",
            r"(\d+(?:\.\d+)?)\s*years?\s*unexpired",
            r"lease.*?(\d+)\s*years?",
            r"term of\s*(\d+)\s*years?",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_yield(self) -> Optional[float]:
        patterns = [
            r"([\d.]+)%\s*net initial yield",
            r"NIY\s*[:;]?\s*([\d.]+)%",
            r"yield.*?(\d+\.?\d*)%",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_rent_review(self) -> Optional[str]:
        patterns = [
            r"fixed uplift in\s+(January\s+\d{4})",
            r"rent review.*?(\d{4})",
            r"uplift in\s+([A-Za-z]+\s+\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_post_review_rent(self) -> Optional[float]:
        patterns = [
            r"uplift.*to\s*£?([\d,.]+)\s*per\s*annum",
            r"to\s*£?([\d,.]+)\s*per\s*annum",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return None
    
    def _extract_parking(self) -> Optional[int]:
        patterns = [
            r"(\d+)\s*car parking spaces",
            r"(\d+)\s*parking spaces",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def _extract_parking_ratio(self) -> Optional[str]:
        match = re.search(r"ratio of\s*(1:\d+\s*(?:sq\s*ft)?)", self.raw_text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_epc(self) -> Optional[str]:
        match = re.search(r"EPC\s*([A-G])", self.raw_text)
        if match:
            return match.group(1)
        return None
    
    def _extract_site_area(self) -> Optional[float]:
        match = re.search(r"Site area of\s*([\d.]+)\s*acres", self.raw_text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_tenure(self) -> Optional[str]:
        if re.search(r"Freehold", self.raw_text):
            return "Freehold"
        if re.search(r"Leasehold", self.raw_text):
            return "Leasehold"
        return None
    
    def _extract_property_type(self) -> Optional[str]:
        if re.search(r"HQ\s*office", self.raw_text, re.IGNORECASE):
            return "HQ Office"
        if re.search(r"office building", self.raw_text, re.IGNORECASE):
            return "Office"
        if re.search(r"industrial", self.raw_text, re.IGNORECASE):
            return "Industrial"
        if re.search(r"retail", self.raw_text, re.IGNORECASE):
            return "Retail"
        return "Office"  # Default
    
    def _extract_year_built(self) -> Optional[int]:
        match = re.search(r"constructed in\s*(\d{4})", self.raw_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        match = re.search(r"built in\s*(\d{4})", self.raw_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_dnb_rating(self) -> Optional[str]:
        # Match D&B with various ampersand encodings, newlines, and whitespace
        patterns = [
            r"D\s*&\s*B\s+rating.*?of\s+([\w\d]+)",
            r"D&B\s+rating.*?of\s+([\w\d]+)",
            r"D\u0026B\s+rating.*?of\s+([\w\d]+)",
            r"D\u0026amp;B\s+rating.*?of\s+([\w\d]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, self.raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        return None
    
    def _extract_erv(self) -> Optional[float]:
        match = re.search(r"ERV of\s*£?([\d.]+)", self.raw_text)
        if match:
            return float(match.group(1))
        return None
    
    def _compute_derived(self, metrics: Dict) -> Dict:
        """Compute derived metrics from extracted data."""
        if metrics.get("annual_rent") and metrics.get("asking_price"):
            metrics["net_initial_yield"] = (metrics["annual_rent"] / metrics["asking_price"]) * 100
        
        if metrics.get("asking_price") and metrics.get("sq_ft"):
            metrics["price_psf"] = metrics["asking_price"] / metrics["sq_ft"]
        
        if metrics.get("annual_rent") and metrics.get("sq_ft"):
            metrics["rent_psf"] = metrics["annual_rent"] / metrics["sq_ft"]
        
        if metrics.get("rent_post_review") and metrics.get("asking_price"):
            metrics["reversionary_yield"] = (metrics["rent_post_review"] / metrics["asking_price"]) * 100
        
        if metrics.get("sq_ft") and metrics.get("car_parking_spaces"):
            ratio = metrics["sq_ft"] / metrics["car_parking_spaces"]
            metrics["parking_ratio_computed"] = f"1:{int(ratio)}"
        
        return metrics
    
    def to_json(self) -> str:
        return json.dumps(self.extract_metrics(), indent=2)
    
    def get_raw_text_preview(self, max_chars: int = 3000) -> str:
        if not self.raw_text:
            self.extract_all_text()
        return self.raw_text[:max_chars]


def ingest_pdf(pdf_path: str) -> Dict[str, Any]:
    """Main entry point: ingest a PDF and return structured metrics."""
    ingestor = PDFIngestor(pdf_path)
    return ingestor.extract_metrics()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_ingestor.py <pdf_path>")
        sys.exit(1)
    
    result = ingest_pdf(sys.argv[1])
    print(json.dumps(result, indent=2))
