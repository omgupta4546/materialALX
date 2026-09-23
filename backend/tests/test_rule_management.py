"""
tests/test_rule_management.py

Unit tests for:
  - CriticalRule schema validation guards
  - GlobalMatchingConfig weight validation
  - Weight-sum constraint enforcement
  - Severity / behavior enum guards
"""
import pytest
from pydantic import ValidationError
from app.schemas.rule_management import (
    CriticalRuleCreate,
    CriticalRuleUpdate,
    GlobalMatchingConfigCreate,
)


# ──────────────────────────────────────────────────────────────────────────────
# CriticalRule schema tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCriticalRuleCreate:

    def test_valid_rule(self):
        r = CriticalRuleCreate(
            classification_code="VALVE",
            attribute="pressure_class",
            severity="CRITICAL",
            conflict_behavior="BLOCK_EQUIVALENCE",
        )
        assert r.classification_code == "VALVE"
        assert r.attribute == "pressure_class"

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError, match="severity must be one of"):
            CriticalRuleCreate(
                classification_code="VALVE",
                attribute="pressure_class",
                severity="EXTREME",   # invalid
            )

    def test_invalid_behavior_rejected(self):
        with pytest.raises(ValidationError, match="conflict_behavior must be one of"):
            CriticalRuleCreate(
                classification_code="MOTOR",
                attribute="voltage",
                conflict_behavior="AUTO_APPROVE",  # invalid
            )

    @pytest.mark.parametrize("severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    def test_all_valid_severities(self, severity):
        r = CriticalRuleCreate(
            classification_code="PIPE",
            attribute="diameter",
            severity=severity,
        )
        assert r.severity == severity

    @pytest.mark.parametrize("behavior", ["BLOCK_EQUIVALENCE", "REQUIRE_REVIEW", "FLAG_ONLY"])
    def test_all_valid_behaviors(self, behavior):
        r = CriticalRuleCreate(
            classification_code="BEARING",
            attribute="bore",
            conflict_behavior=behavior,
        )
        assert r.conflict_behavior == behavior


class TestCriticalRuleUpdate:

    def test_partial_update_only_severity(self):
        u = CriticalRuleUpdate(severity="HIGH")
        assert u.severity == "HIGH"
        assert u.conflict_behavior is None

    def test_update_invalid_severity_rejected(self):
        with pytest.raises(ValidationError, match="severity must be one of"):
            CriticalRuleUpdate(severity="SUPER_CRITICAL")


# ──────────────────────────────────────────────────────────────────────────────
# GlobalMatchingConfig schema tests
# ──────────────────────────────────────────────────────────────────────────────

VALID_CONFIG = dict(
    weight_semantic=0.30,
    weight_attribute=0.40,
    weight_manufacturer=0.10,
    weight_mpn=0.20,
)

class TestGlobalMatchingConfigCreate:

    def test_valid_config_accepted(self):
        c = GlobalMatchingConfigCreate(**VALID_CONFIG)
        assert c.auto_approve_enabled is False
        assert c.auto_approve_max_risk_level == "LOW"

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValidationError, match="Weights must sum to 1.0"):
            GlobalMatchingConfigCreate(
                weight_semantic=0.50,   # intentionally breaks total
                weight_attribute=0.40,
                weight_manufacturer=0.10,
                weight_mpn=0.20,
            )

    def test_weight_sum_tolerance_passes(self):
        """Weights summing to 0.999 should pass the 0.01 tolerance."""
        c = GlobalMatchingConfigCreate(
            weight_semantic=0.299,
            weight_attribute=0.40,
            weight_manufacturer=0.101,
            weight_mpn=0.20,
        )
        assert c is not None

    def test_invalid_risk_level_rejected(self):
        with pytest.raises(ValidationError, match="auto_approve_max_risk_level must be one of"):
            GlobalMatchingConfigCreate(
                **VALID_CONFIG,
                auto_approve_max_risk_level="EXTREME",
            )

    @pytest.mark.parametrize("level", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    def test_all_valid_risk_levels(self, level):
        c = GlobalMatchingConfigCreate(**VALID_CONFIG, auto_approve_max_risk_level=level)
        assert c.auto_approve_max_risk_level == level

    def test_auto_approve_defaults_disabled(self):
        c = GlobalMatchingConfigCreate(**VALID_CONFIG)
        assert c.auto_approve_enabled is False

    def test_auto_approve_can_be_enabled(self):
        c = GlobalMatchingConfigCreate(
            **VALID_CONFIG,
            auto_approve_enabled=True,
            auto_approve_threshold=0.97,
            auto_approve_max_risk_level="LOW",
        )
        assert c.auto_approve_enabled is True
        assert c.auto_approve_threshold == 0.97

    def test_default_risk_categories_populated(self):
        c = GlobalMatchingConfigCreate(**VALID_CONFIG)
        assert "VALVE" in c.high_risk_categories
        assert "MOTOR" in c.high_risk_categories
        assert "PIPE" in c.medium_risk_categories

    def test_penalty_values_must_be_negative(self):
        with pytest.raises(ValidationError):
            GlobalMatchingConfigCreate(
                **VALID_CONFIG,
                penalty_missing_attribute=0.10,   # must be <= 0
            )
