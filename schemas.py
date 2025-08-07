from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class InputProfile(BaseModel):
    risk_level: str = Field(description="low|medium|high")
    horizon_years: float = Field(description="Target holding horizon in years")


class TickerInfo(BaseModel):
    name: str
    exchange: Optional[str] = None
    symbol: str
    yf_symbol: str


class FundamentalsReport(BaseModel):
    metrics: Dict[str, float] = {}
    pros: List[str] = []
    cons: List[str] = []
    score: float = 0.0
    notes: Optional[str] = None


class TechnicalReport(BaseModel):
    metrics: Dict[str, float] = {}
    trend: str = "unknown"
    pros: List[str] = []
    cons: List[str] = []


class NewsItem(BaseModel):
    title: str
    url: str
    published_at: Optional[str] = None
    source: Optional[str] = None
    snippet: Optional[str] = None


class NewsReport(BaseModel):
    items: List[NewsItem]
    summary: str


class SectorMacroReport(BaseModel):
    summary: str


class AlternativeCandidate(BaseModel):
    ticker: Optional[TickerInfo] = None
    name: str
    reason: str


class AlternativesReport(BaseModel):
    candidates: List[AlternativeCandidate]


class DecisionPlan(BaseModel):
    decision: Optional[str] = None  # Buy | Hold | Avoid
    confidence: Optional[float] = None
    entry_timing: Optional[str] = None
    position_size: Optional[str] = None  # conservative|moderate|aggressive + % guidance, or % string
    dca_plan: Optional[str] = None
    risk_controls: Dict[str, str] = {}
    rationale: Optional[str] = None


class AnalysisBundle(BaseModel):
    input: TickerInfo
    profile: InputProfile
    fundamentals: FundamentalsReport
    technical: TechnicalReport
    news: NewsReport
    sector_macro: SectorMacroReport
    alternatives: AlternativesReport
    decision: DecisionPlan
