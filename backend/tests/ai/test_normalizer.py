import pytest
from app.ai.modules.normalizer import NormalizerModule, NormalizerInput

def test_normalization_casing_and_whitespace():
    raw = "   ball    bearing   "
    module = NormalizerModule()
    assert module.process(NormalizerInput(raw_text=raw)).normalized_text == "BALL BEARING"

def test_normalization_punctuation():
    raw = "PUMP, CENTRIFUGAL; 10GPM_SS"
    module = NormalizerModule()
    assert module.process(NormalizerInput(raw_text=raw)).normalized_text == "PUMP CENTRIFUGAL 10GPM STAINLESS STEEL"

def test_normalization_abbreviations():
    module = NormalizerModule()
    cases = [
        ("BRG", "BEARING"),
        ("BRNG", "BEARING"),
        ("DIA", "DIAMETER"),
        ("DIA.", "DIAMETER"),
        ("SS", "STAINLESS STEEL"),
        ("CS", "CARBON STEEL"),
        ("GALV", "GALVANIZED"),
        ("GALV.", "GALVANIZED"),
    ]
    for abbrev, expected in cases:
        assert module.process(NormalizerInput(raw_text=abbrev)).normalized_text == expected

def test_normalization_engineering_notation():
    module = NormalizerModule()
    raw1 = "PIPE 1/2\" CS"
    assert module.process(NormalizerInput(raw_text=raw1)).normalized_text == "PIPE 1/2 IN CARBON STEEL"
    
    raw2 = "VALVE 2'' SS"
    assert module.process(NormalizerInput(raw_text=raw2)).normalized_text == "VALVE 2 IN STAINLESS STEEL"
    
    raw3 = "SHAFT 5MM"
    assert module.process(NormalizerInput(raw_text=raw3)).normalized_text == "SHAFT 5 MM"

def test_normalization_does_not_expand_ambiguous():
    module = NormalizerModule()
    raw = "NO IN STOCK"
    assert module.process(NormalizerInput(raw_text=raw)).normalized_text == "NO IN STOCK"

def test_normalization_mixed_real_world():
    module = NormalizerModule()
    raw = " brg, ball; 1/2\" dia. ss_galv "
    expected = "BEARING BALL 1/2 IN DIAMETER STAINLESS STEEL GALVANIZED"
    assert module.process(NormalizerInput(raw_text=raw)).normalized_text == expected

# Note: The database persistence test remains, but we test the NormalizationService 
# which might still use the old TextNormalizer depending on if we migrated the service.
# For now we'll keep the AI module tests decoupled from the DB service test.

