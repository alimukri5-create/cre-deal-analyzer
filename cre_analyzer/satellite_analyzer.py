#!/usr/bin/env python3
"""
CRE Deal Analyzer - Satellite Imagery Module
Analyzes property via satellite imagery for occupancy indicators.
Uses ESRI World Imagery (free, no API key) + OpenCV car detection.
"""

import re
import math
import base64
import io
import requests
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, List
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from PIL import Image


@dataclass
class SatelliteAnalysis:
    property_address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    image_path: Optional[str] = None
    parking_lot_status: Optional[str] = None  # full / moderate / empty / unknown
    estimated_occupancy_pct: Optional[float] = None
    estimated_car_count: Optional[int] = None
    building_condition_estimate: Optional[str] = None
    activity_indicators: list = None
    
    def __post_init__(self):
        if self.activity_indicators is None:
            self.activity_indicators = []


class SatelliteAnalyzer:
    """Analyzes property satellite imagery for occupancy and activity signals."""
    
    # ESRI World Imagery — free satellite tiles, no API key
    ESRI_TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    # OpenStreetMap as fallback (not satellite but useful)
    OSM_TILE_URL = "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"
    # Bing Maps static (requires key, but we leave URL for user)
    BING_URL = "https://www.bing.com/maps?cp={lat}~{lng}&lvl=19&style=a"
    
    def __init__(self, address: str, lat: Optional[float] = None, lng: Optional[float] = None,
                 output_dir: Optional[str] = None):
        self.raw_address = address
        self.address = self._clean_address(address)
        self.lat = lat
        self.lng = lng
        self.output_dir = Path(output_dir) if output_dir else Path("/tmp/cre-results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analysis = SatelliteAnalysis(property_address=self.address, lat=lat, lng=lng)
        
    def _clean_address(self, addr: str) -> str:
        """Aggressively clean address for geocoding."""
        # Normalize all whitespace (tabs, newlines, multiple spaces)
        addr = re.sub(r'\s+', ' ', addr).strip()
        # Strip common prefixes that break geocoding
        addr = re.sub(r'^(HQ|Headquarters|Unit\s+\d+|Building\s+\d+|Block\s+\d+|Office\s+|Suite\s+\d+)\s*,?\s*', '', addr, flags=re.IGNORECASE)
        addr = re.sub(r'^HQ\s+', '', addr, flags=re.IGNORECASE)
        # Remove extraneous lines inside address
        addr = addr.replace("|", ", ")
        # Clean up double commas
        addr = re.sub(r',\s*,', ',', addr)
        addr = re.sub(r',\s*$', '', addr)
        return addr.strip()
    
    def analyze(self) -> SatelliteAnalysis:
        """Run satellite analysis pipeline."""
        if not self.lat or not self.lng:
            self._geocode_address()
        
        if self.lat and self.lng:
            self._fetch_satellite_image()
            self._assess_parking_lot()
            self._assess_building_condition()
        else:
            self.analysis.parking_lot_status = "unknown"
            self.analysis.activity_indicators.append("Could not geocode address - manual review needed")
        
        return self.analysis
    
    def _geocode_address(self):
        """Geocode address to lat/lng using Nominatim (OpenStreetMap, free)."""
        try:
            clean_addr = self.address
            
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": clean_addr,
                "format": "json",
                "limit": 1,
                "addressdetails": 0,
            }
            headers = {
                "User-Agent": "CRE-Analyzer/1.0",
                "Accept": "application/json",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                if data:
                    self.lat = float(data[0]["lat"])
                    self.lng = float(data[0]["lon"])
                    self.analysis.lat = self.lat
                    self.analysis.lng = self.lng
                    self.analysis.activity_indicators.append(f"Geocoded to {self.lat:.6f}, {self.lng:.6f}")
                    return
            
            # Fallback 1: try with just postcode
            postcode_match = re.search(r'([A-Z]{1,2}\d{1,2}\s*\d?[A-Z]{2})', clean_addr)
            if postcode_match:
                params["q"] = postcode_match.group(1) + ", UK"
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    if data:
                        self.lat = float(data[0]["lat"])
                        self.lng = float(data[0]["lon"])
                        self.analysis.lat = self.lat
                        self.analysis.lng = self.lng
                        self.analysis.activity_indicators.append(f"Geocoded via postcode to {self.lat:.6f}, {self.lng:.6f}")
                        return
            
            # Fallback 2: try city only
            city_match = re.search(r'([A-Za-z\s]+?),?\s*[A-Z]{1,2}\d', clean_addr)
            if city_match:
                city = city_match.group(1).strip().rstrip(',')
                params["q"] = city + ", UK"
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    if data:
                        self.lat = float(data[0]["lat"])
                        self.lng = float(data[0]["lon"])
                        self.analysis.lat = self.lat
                        self.analysis.lng = self.lng
                        self.analysis.activity_indicators.append(f"Geocoded via city to {self.lat:.6f}, {self.lng:.6f} (low accuracy)")
                        return
                        
            self.analysis.activity_indicators.append("Geocoding returned no results - manual address verification needed")
            
        except Exception as e:
            self.analysis.activity_indicators.append(f"Geocoding error: {e}")
    
    # ------------------------------------------------------------------
    # Tile math for slippy maps
    # ------------------------------------------------------------------
    @staticmethod
    def _deg2num(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
        """Convert lat/lng to tile x,y at given zoom."""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return xtile, ytile
    
    @staticmethod
    def _num2deg(xtile: int, ytile: int, zoom: int) -> Tuple[float, float]:
        """Convert tile x,y to lat/lng of NW corner."""
        n = 2.0 ** zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg
    
    def _fetch_tile(self, x: int, y: int, zoom: int, source: str = "esri") -> Optional[Image.Image]:
        """Fetch a single map tile."""
        if source == "esri":
            url = self.ESRI_TILE_URL.format(z=zoom, x=x, y=y)
        else:
            url = self.OSM_TILE_URL.format(z=zoom, x=x, y=y)
        
        try:
            resp = requests.get(url, headers={"User-Agent": "CRE-Analyzer/1.0"}, timeout=15)
            if resp.status_code == 200:
                return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except Exception:
            pass
        return None
    
    def _fetch_satellite_image(self):
        """Fetch satellite image from ESRI World Imagery tiles."""
        if not self.lat or not self.lng:
            return
        
        zoom = 18  # Good balance: ~0.6m/px, building + parking visible
        cx, cy = self._deg2num(self.lat, self.lng, zoom)
        
        # Fetch 3x3 grid centered on property
        tiles = []
        for dy in [-1, 0, 1]:
            row = []
            for dx in [-1, 0, 1]:
                tile = self._fetch_tile(cx + dx, cy + dy, zoom, source="esri")
                if tile is None:
                    # Fallback to OSM
                    tile = self._fetch_tile(cx + dx, cy + dy, zoom, source="osm")
                row.append(tile)
            tiles.append(row)
        
        # Check if we got any tiles
        if all(t is None for row in tiles for t in row):
            # All tile fetches failed — provide browser URLs
            self.analysis.image_path = self.BING_URL.format(lat=self.lat, lng=self.lng)
            self.analysis.activity_indicators.append(
                f"Tile fetch failed — use Bing/ESRI viewer: {self.analysis.image_path}"
            )
            return
        
        # Determine tile size from first valid tile
        valid_tile = next(t for row in tiles for t in row if t is not None)
        tw, th = valid_tile.size
        
        # Stitch tiles into composite image
        composite = Image.new("RGB", (tw * 3, th * 3), color=(128, 128, 128))
        for ri, row in enumerate(tiles):
            for ci, tile in enumerate(row):
                if tile:
                    composite.paste(tile, (ci * tw, ri * th))
        
        # Save to disk
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', self.address)[:40]
        img_path = self.output_dir / f"satellite_{safe_name}_{zoom}.jpg"
        composite.save(img_path, "JPEG", quality=90)
        self.analysis.image_path = str(img_path)
        self.analysis.activity_indicators.append(
            f"Satellite image saved: {img_path} ({composite.size[0]}x{composite.size[1]} px)"
        )
    
    # ------------------------------------------------------------------
    # Parking lot analysis via OpenCV
    # ------------------------------------------------------------------
    def _assess_parking_lot(self):
        """Assess parking lot occupancy using OpenCV blob detection on satellite image."""
        img_path = self.analysis.image_path
        if not img_path or not Path(img_path).exists():
            self.analysis.parking_lot_status = "manual_review_required"
            self.analysis.activity_indicators.append(
                "Parking lot analysis requires satellite image — none available"
            )
            return
        
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                raise ValueError("Could not load satellite image")
            
            h, w = img.shape[:2]
            
            # Strategy 1: Look for dark blobs on gray asphalt background
            # Convert to HSV for better color separation
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Asphalt is typically low saturation, mid-value. Cars are darker.
            # Mask for asphalt-like areas: low saturation, mid brightness
            lower_asphalt = np.array([0, 0, 40])
            upper_asphalt = np.array([180, 60, 180])
            asphalt_mask = cv2.inRange(hsv, lower_asphalt, upper_asphalt)
            
            # Within asphalt, find dark spots (cars)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Use adaptive thresholding to find dark objects on lighter asphalt
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 25, 15
            )
            
            # Combine: only dark spots that are on asphalt-like areas
            combined = cv2.bitwise_and(thresh, asphalt_mask)
            
            # Morphological cleanup
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
            combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size — a car in satellite imagery at zoom 18
            # is roughly 15-80 pixels in area
            min_area = 80    # ~8x10 px
            max_area = 2500  # ~50x50 px
            valid_contours = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if min_area < area < max_area:
                    # Additional shape filter: cars are somewhat rectangular
                    x, y, cw, ch = cv2.boundingRect(cnt)
                    aspect = max(cw, ch) / max(min(cw, ch), 1)
                    if aspect < 4.0:  # Not too elongated
                        valid_contours.append(cnt)
            
            car_count = len(valid_contours)
            self.analysis.estimated_car_count = car_count
            
            # Categorize parking lot status
            # At zoom 18, a typical commercial property with 200-300 spaces
            # would show ~50-150 cars in the 3x3 tile view if full
            # We'll use relative buckets
            if car_count > 80:
                self.analysis.parking_lot_status = "full"
                self.analysis.estimated_occupancy_pct = 85
            elif car_count > 30:
                self.analysis.parking_lot_status = "moderate"
                self.analysis.estimated_occupancy_pct = 50
            elif car_count > 5:
                self.analysis.parking_lot_status = "low"
                self.analysis.estimated_occupancy_pct = 20
            else:
                self.analysis.parking_lot_status = "empty"
                self.analysis.estimated_occupancy_pct = 5
            
            self.analysis.activity_indicators.append(
                f"Parking lot CV analysis: ~{car_count} vehicles detected ({self.analysis.parking_lot_status})"
            )
            
            # Save annotated image for reference
            annotated = img.copy()
            cv2.drawContours(annotated, valid_contours, -1, (0, 255, 0), 2)
            ann_path = str(img_path).replace(".jpg", "_annotated.jpg")
            cv2.imwrite(ann_path, annotated)
            self.analysis.activity_indicators.append(f"Annotated satellite saved: {ann_path}")
            
        except Exception as e:
            self.analysis.parking_lot_status = "manual_review_required"
            self.analysis.activity_indicators.append(f"Parking lot CV analysis failed: {e}")
    
    def _assess_building_condition(self):
        """Assess building condition from satellite image heuristics."""
        img_path = self.analysis.image_path
        if not img_path or not Path(img_path).exists():
            self.analysis.building_condition_estimate = "manual_review_required"
            self.analysis.activity_indicators.append(
                "Building condition assessment requires satellite image"
            )
            return
        
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                raise ValueError("Could not load image")
            
            h, w = img.shape[:2]
            # Sample center region where building likely is
            cx, cy = w // 2, h // 2
            roi = img[cy - h//4:cy + h//4, cx - w//4:cx + w//4]
            
            # Compute roof color statistics
            hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            mean_v = np.mean(hsv_roi[:, :, 2])
            std_v = np.std(hsv_roi[:, :, 2])
            
            # Heuristics:
            # - Very bright roof = new/light colored materials (positive)
            # - Dark/variable roof = aging or patchwork (negative)
            # - Uniform color = well-maintained
            if mean_v > 170 and std_v < 40:
                condition = "good_roof_condition"
                self.analysis.activity_indicators.append(
                    "Building condition (satellite): Light, uniform roof — likely well-maintained"
                )
            elif mean_v < 80 or std_v > 60:
                condition = "poor_roof_condition"
                self.analysis.activity_indicators.append(
                    "Building condition (satellite): Dark or patchy roof — may need attention"
                )
            else:
                condition = "fair"
                self.analysis.activity_indicators.append(
                    "Building condition (satellite): Moderate appearance — no clear red flags"
                )
            
            self.analysis.building_condition_estimate = condition
            
        except Exception as e:
            self.analysis.building_condition_estimate = "manual_review_required"
            self.analysis.activity_indicators.append(f"Building condition analysis failed: {e}")
    
    def get_risk_contribution(self) -> Dict[str, Any]:
        """Return risk contribution for deal scoring."""
        score = 10  # Neutral
        
        if self.analysis.parking_lot_status == "full":
            score += 3
        elif self.analysis.parking_lot_status == "moderate":
            score += 1
        elif self.analysis.parking_lot_status == "low":
            score -= 1
        elif self.analysis.parking_lot_status == "empty":
            score -= 3
            self.analysis.activity_indicators.append("WARNING: Empty parking lot suggests low occupancy")
        
        if self.analysis.building_condition_estimate == "poor_roof_condition":
            score -= 2
        elif self.analysis.building_condition_estimate == "good_roof_condition":
            score += 1
        
        return {
            "satellite_score": max(0, min(20, score)),
            "parking_status": self.analysis.parking_lot_status,
            "occupancy_estimate": self.analysis.estimated_occupancy_pct,
            "estimated_car_count": self.analysis.estimated_car_count,
            "satellite_url": self.analysis.image_path,
        }


def analyze_property_satellite(address: str, lat: Optional[float] = None, lng: Optional[float] = None,
                                output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Main entry point: analyze property via satellite."""
    analyzer = SatelliteAnalyzer(address, lat, lng, output_dir)
    result = analyzer.analyze()
    return asdict(result)


if __name__ == "__main__":
    import sys
    address = sys.argv[1] if len(sys.argv) > 1 else "Ruddington Fields Business Park, Nottingham, NG11 6NZ"
    result = analyze_property_satellite(address)
    print(f"Satellite analysis for: {address}")
    print(f"Lat/Lng: {result.get('lat')}, {result.get('lng')}")
    print(f"Image: {result.get('image_path')}")
    print(f"Parking: {result.get('parking_lot_status')} ({result.get('estimated_car_count')} cars)")
