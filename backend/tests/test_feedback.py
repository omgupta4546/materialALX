"""
tests/test_feedback.py

Unit tests for feedback schema validation and analytics helper logic.
Integration tests (DB) require a live Postgres instance.
"""
import pytest
from pydantic import ValidationError
from app.schemas.feedback import (
    FeedbackEventCreate,
    FeedbackSummary,
    VALID_EVENT_TYPES,
)
from app.api.endpoints.feedback import _is_disagreement, _score_to_band


# ──────────────────────────────────────────────────────────────────────────────
# Schema validation
# ──────────────────────────────────────────────────────────────────────────────

class TestFeedbackEventCreate:

    def _base(self, **kwargs):
        defaults = dict(
            match_id="match-abc",
            event_type="APPROVED",
            ai_match_type="FUNCTIONALLY_EQUIVALENT",
            ai_final_score=0.88,
            ai_recommendation="REQUIRES_REVIEW",
        )
        defaults.update(kwargs)
        return FeedbackEventCreate(**defaults)

    def test_approved_event_valid(self):
        e = self._base(event_type="APPROVED")
        assert e.event_type == "APPROVED"

    def test_rejected_event_valid(self):
        e = self._base(event_type="REJECTED", reason="Wrong material")
        assert e.reason == "Wrong material"

    def test_engineering_review_valid(self):
        e = self._base(event_type="ENGINEERING_REVIEW")
        assert e.event_type == "ENGINEERING_REVIEW"

    def test_attribute_corrected_requires_corrections(self):
        with pytest.raises(ValidationError, match="corrected_attributes must be provided"):
            self._base(event_type="ATTRIBUTE_CORRECTED", corrected_attributes=None)

    def test_attribute_corrected_with_data_valid(self):
        e = self._base(
            event_type="ATTRIBUTE_CORRECTED",
            corrected_attributes={"pressure_class": "150#", "size": "2 inch"},
        )
        assert "pressure_class" in e.corrected_attributes

    def test_invalid_event_type_rejected(self):
        with pytest.raises(ValidationError, match="event_type must be one of"):
            self._base(event_type="MAYBE")

    def test_requires_match_id_or_target_id(self):
        with pytest.raises(ValidationError, match="Either match_id or target_id must be provided"):
            FeedbackEventCreate(
                match_id=None,
                target_id=None,
                event_type="APPROVED",
            )

    def test_target_id_fallback_accepted(self):
        e = FeedbackEventCreate(
            match_id=None,
            target_id="some-target-id",
            event_type="REJECTED",
        )
        assert e.target_id == "some-target-id"

    @pytest.mark.parametrize("et", list(VALID_EVENT_TYPES - {"ATTRIBUTE_CORRECTED"}))
    def test_all_non_correction_event_types(self, et):
        e = self._base(event_type=et)
        assert e.event_type == et


# ──────────────────────────────────────────────────────────────────────────────
# Disagreement logic
# ──────────────────────────────────────────────────────────────────────────────

class TestDisagreementLogic:

    def test_approved_when_ai_required_review_is_disagreement(self):
        assert _is_disagreement("APPROVED", "REQUIRES_REVIEW") is True

    def test_approved_when_ai_approved_is_not_disagreement(self):
        assert _is_disagreement("APPROVED", "APPROVE") is False

    def test_rejected_when_ai_approved_is_disagreement(self):
        assert _is_disagreement("REJECTED", "APPROVE") is True

    def test_rejected_when_ai_required_review_not_disagreement(self):
        assert _is_disagreement("REJECTED", "REQUIRES_REVIEW") is False

    def test_engineering_review_when_ai_approved_is_disagreement(self):
        assert _is_disagreement("ENGINEERING_REVIEW", "APPROVE") is True

    def test_no_ai_recommendation_never_disagreement(self):
        assert _is_disagreement("APPROVED", None) is False
        assert _is_disagreement("REJECTED", None) is False

    def test_attribute_corrected_not_classified_as_disagreement_without_ai_rec(self):
        assert _is_disagreement("ATTRIBUTE_CORRECTED", None) is False


# ──────────────────────────────────────────────────────────────────────────────
# Score banding
# ──────────────────────────────────────────────────────────────────────────────

class TestScoreBanding:

    @pytest.mark.parametrize("score,expected_band", [
        (0.98, "0.95–1.0"),
        (0.95, "0.95–1.0"),
        (0.90, "0.85–0.95"),
        (0.85, "0.85–0.95"),
        (0.70, "0.65–0.85"),
        (0.65, "0.65–0.85"),
        (0.55, "0.50–0.65"),
        (0.50, "0.50–0.65"),
        (0.30, "below–0.50"),
        (None, "unknown"),
    ])
    def test_score_bands(self, score, expected_band):
        assert _score_to_band(score) == expected_band


# ──────────────────────────────────────────────────────────────────────────────
# FeedbackSummary construction
# ──────────────────────────────────────────────────────────────────────────────

class TestFeedbackSummary:

    def test_disagreement_rate_calculation(self):
        s = FeedbackSummary(
            total_events=100,
            approved=60,
            rejected=20,
            engineering_review=10,
            attribute_corrected=10,
            disagreement_count=15,
            disagreement_rate=0.15,
        )
        assert s.disagreement_rate == 0.15

    def test_zero_total_handled(self):
        s = FeedbackSummary(
            total_events=0,
            approved=0,
            rejected=0,
            engineering_review=0,
            attribute_corrected=0,
            disagreement_count=0,
            disagreement_rate=0.0,
        )
        assert s.disagreement_rate == 0.0
