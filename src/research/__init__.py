"""Niche research tools for workbook planning."""

from src.research.niche_research_engine import (
    NicheResearchResult,
    analyze_niche,
    save_niche_research_result,
)
from src.research.opportunity_engine import OpportunityRanking, OpportunityScore, rank_opportunities, save_opportunity_scores

__all__ = [
    "NicheResearchResult",
    "OpportunityRanking",
    "OpportunityScore",
    "analyze_niche",
    "rank_opportunities",
    "save_niche_research_result",
    "save_opportunity_scores",
]
