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
    
    class Config:
        extra = "ignore"  # Ignore extra fields


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


class DecisionPlan(BaseModel):
    decision: Optional[str] = None  # Buy | Hold | Avoid
    confidence: Optional[float | str] = None  # Allow both float and string values
    entry_timing: Optional[str] = None
    position_size: Optional[str | float | dict] = None  # Allow string, float, or dict values
    dca_plan: Optional[str] = None
    risk_controls: Dict[str, str] = {}
    rationale: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignore extra fields


class AnalysisBundle(BaseModel):
    input: TickerInfo
    profile: InputProfile
    fundamentals: FundamentalsReport
    technical: TechnicalReport
    news: NewsReport
    sector_macro: SectorMacroReport
    decision: DecisionPlan


# --- Multi-agent extensions inspired by TradingAgents ---

class SentimentReport(BaseModel):
    score: float = Field(description="Overall sentiment score in [-1.0, 1.0]")
    drivers: List[str] = []
    summary: str = ""
    
    class Config:
        extra = "ignore"  # Ignore extra fields


class ResearchDebateReport(BaseModel):
    bull_points: List[str] = []
    bear_points: List[str] = []
    consensus: str = ""
    
    class Config:
        extra = "ignore"  # Ignore extra fields


class RiskAssessment(BaseModel):
    overall_risk: str = Field(description="low|medium|high")
    issues: List[str] = []
    constraints: Dict[str, str] = {}
    veto: bool = False
    
    class Config:
        extra = "ignore"  # Ignore extra fields


class FundManagerDecision(BaseModel):
    approved: bool
    notes: str = ""
    adjustments: Dict[str, str] = {}


# Optional fields in bundle for extended pipeline outputs
class ExtendedAnalysisBundle(AnalysisBundle):
    sentiment: Optional[SentimentReport] = None
    research: Optional[ResearchDebateReport] = None
    risk: Optional[RiskAssessment] = None
    approval: Optional[FundManagerDecision] = None


# --- Trader agents and ensemble ---

class TraderSignal(BaseModel):
    risk_profile: str = Field(description="conservative|moderate|aggressive")
    action: str = Field(description="Buy|Hold|Avoid")
    confidence: float = 0.0
    entry_timing: Optional[str] = None
    position_size: Optional[str | float] = None  # Allow both string and float values
    rationale: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignore extra fields


class TraderEnsemble(BaseModel):
    signals: List[TraderSignal]
    consensus_action: str
    consensus_confidence: float
    notes: Optional[str] = None


# --- Backtesting ---

class Trade(BaseModel):
    date: str
    symbol: str
    side: str  # buy|sell
    price: float
    size: float  # fraction of equity


class BacktestResult(BaseModel):
    symbol: str
    start: str
    end: str
    strategy: str
    cumulative_return_pct: float
    annual_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    num_trades: int
    trades: List[Trade] = []
