"""
Tests for the 6-dimension Procurement Signal Scoring module.
"""
import pytest
from datetime import date

from app.intelligence.procurement_signal_score import (
    calculate_procurement_signal_score,
    _infer_recipient_type,
)


# ─── Hard filters ────────────────────────────────────────────────────────

class TestHardFilters:
    """Grants that should immediately score 0 / noise."""

    def test_other_transfer_payment_is_noise(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Other transfer payment",
        )
        assert score == 0
        assert cat == "noise"
        assert any("hard_filter:agreement_type" in r for r in reasons)

    def test_individual_recipient_is_noise(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            recipient_type="individual",
        )
        assert score == 0
        assert cat == "noise"
        assert any("hard_filter:recipient_type" in r for r in reasons)

    def test_scholarship_keyword_is_noise(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            description="PhD Research Scholarship for advanced quantum computing",
            amount_cad=85000,
        )
        assert score == 0
        assert cat == "noise"
        assert any("hard_filter:keyword:scholarship" in r for r in reasons)

    def test_fellowship_keyword_is_noise(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            description="Post-doctoral fellowship in marine biology",
            amount_cad=50000,
        )
        assert score == 0
        assert cat == "noise"
        assert any("hard_filter:keyword:fellowship" in r for r in reasons)

    def test_assessed_contribution_is_noise(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            description="Canada's annual assessed contribution to ESA",
            amount_cad=18000000,
        )
        assert score == 0
        assert cat == "noise"

    def test_individual_inferred_from_name(self):
        """A short person-like name with no org indicator should be flagged."""
        score, reasons, cat, _ = calculate_procurement_signal_score(
            recipient_name="Dr. Sarah Chen",
            amount_cad=43000,
        )
        assert score == 0
        assert cat == "noise"


# ─── High signal grants ─────────────────────────────────────────────────

class TestHighSignal:
    """Grants that should score >= 60 (high)."""

    def test_port_authority_construction_grant(self):
        """FedNor → Port Authority → $2M construction."""
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_name="Peninsula Harbour Port Authority",
            recipient_type="port_authority",
            amount_cad=2_000_000,
            program_name="Northern Ontario Development Program",
            description="Construction and capital improvements to port terminal facility",
            start_date=date(2026, 1, 1),
            end_date=date(2028, 6, 1),
        )
        assert cat == "high"
        assert score >= 60

    def test_municipality_infrastructure(self):
        """Contribution to a municipality for digital infrastructure."""
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_name="City of Ottawa",
            recipient_type="municipal_government",
            amount_cad=5_000_000,
            description="Digital infrastructure modernization for city services",
            start_date=date(2025, 4, 1),
            end_date=date(2027, 3, 31),
        )
        assert cat == "high"
        assert score >= 60

    def test_crown_corp_it_modernization(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_type="crown_corporation",
            amount_cad=3_000_000,
            description="IT system modernization and software platform development",
            start_date=date(2025, 1, 1),
            end_date=date(2027, 12, 31),
        )
        assert cat == "high"
        assert score >= 60


# ─── Medium signal grants ───────────────────────────────────────────────

class TestMediumSignal:
    """Grants that should score 40-59 (medium)."""

    def test_private_company_irap(self):
        """NRC IRAP grant to a for-profit developing technology."""
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_type="private_company",
            amount_cad=95_000,
            program_name="Industrial Research Assistance Program (IRAP)",
            description="Developing next-generation electrolysis processing technology",
        )
        assert cat in ("medium", "high")
        assert score >= 40

    def test_university_infrastructure_not_research(self):
        """University receiving expansion/modernization grant."""
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_name="NOSM University",
            recipient_type="university",
            amount_cad=2_000_000,
            description="Expansion and modernization of community-based sites",
            start_date=date(2026, 1, 1),
            end_date=date(2028, 6, 1),
        )
        # University + contribution + expansion/modernization + large amount
        assert cat in ("medium", "high")
        assert score >= 40


# ─── Low / noise signal grants ──────────────────────────────────────────

class TestLowOrNoise:
    """Grants that should score below 40."""

    def test_arts_cultural_grant(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Grant",
            recipient_type="nonprofit",
            amount_cad=150_000,
            description="Arts operating grant for cultural programming and heritage preservation",
        )
        # Negative keywords should pull this down
        assert cat in ("low", "noise")
        assert score < 40

    def test_nserc_research_training(self):
        """NSERC scholarship to an individual researcher."""
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Grant",
            recipient_type="individual",
            amount_cad=43_850,
            program_name="Research Training and Talent Development",
            description="Research training grant for graduate student",
        )
        assert cat == "noise"
        assert score == 0

    def test_small_grant_to_unknown(self):
        score, reasons, cat, _ = calculate_procurement_signal_score(
            agreement_type="Grant",
            amount_cad=5_000,
            description="Community youth employment programme",
        )
        assert cat in ("low", "noise")
        assert score < 40


# ─── Duration dimension ─────────────────────────────────────────────────

class TestDuration:
    def test_short_duration_penalty(self):
        """< 6 months should get a penalty."""
        score_short, _, _, dur = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_type="municipal_government",
            amount_cad=500_000,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),  # 3 months
        )
        score_long, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_type="municipal_government",
            amount_cad=500_000,
            start_date=date(2026, 1, 1),
            end_date=date(2028, 1, 1),  # 24 months
        )
        assert dur == 2  # ~3 months
        assert score_long > score_short

    def test_long_duration_bonus(self):
        _, _, _, dur = calculate_procurement_signal_score(
            start_date=date(2025, 1, 1),
            end_date=date(2027, 6, 1),
        )
        assert dur == 29


# ─── NAICS dimension ────────────────────────────────────────────────────

class TestNAICS:
    def test_construction_naics_boost(self):
        score_with, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            amount_cad=1_000_000,
            naics_code="237990",
        )
        score_without, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            amount_cad=1_000_000,
        )
        assert score_with > score_without

    def test_arts_naics_penalty(self):
        score_arts, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            amount_cad=100_000,
            naics_code="711120",
        )
        score_none, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            amount_cad=100_000,
        )
        assert score_arts < score_none

    def test_empty_naics_ignored(self):
        """Dash or empty NAICS should not affect score."""
        score_dash, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            amount_cad=100_000,
            naics_code="-",
        )
        score_none, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            amount_cad=100_000,
        )
        assert score_dash == score_none


# ─── Recipient type inference ────────────────────────────────────────────

class TestRecipientTypeInference:
    def test_infer_municipality(self):
        assert _infer_recipient_type("City of Ottawa") == "municipal_government"
        assert _infer_recipient_type("Municipality of Chatham-Kent") == "municipal_government"

    def test_infer_hospital(self):
        assert _infer_recipient_type("Toronto General Hospital") == "hospital_health"

    def test_infer_university(self):
        assert _infer_recipient_type("University of British Columbia") == "university"

    def test_infer_individual(self):
        assert _infer_recipient_type("Dr. Sarah Chen") == "individual"

    def test_no_inference_for_company(self):
        # A company name shouldn't be inferred as individual
        result = _infer_recipient_type("Noram Electrolysis Technologies Inc.")
        assert result != "individual"


# ─── Score clamping ──────────────────────────────────────────────────────

class TestScoreClamping:
    def test_score_never_exceeds_100(self):
        score, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Contribution",
            recipient_type="municipal_government",
            amount_cad=10_000_000,
            description="Construction of digital infrastructure modernization facility with equipment expansion",
            naics_code="237990",
            start_date=date(2025, 1, 1),
            end_date=date(2028, 12, 31),
        )
        assert score <= 100

    def test_score_never_below_zero(self):
        score, _, _, _ = calculate_procurement_signal_score(
            agreement_type="Grant",
            recipient_type="nonprofit",
            amount_cad=5_000,
            description="Arts cultural heritage language training research study",
        )
        assert score >= 0
