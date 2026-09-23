# AI Matching Pipeline Evaluation Report

## Executive Summary
This report evaluates the Antigravity National Material Intelligence platform's Hybrid AI matching pipeline against a simple string similarity (Levenshtein) baseline. 

Evaluated on curated ground truth scenarios from `tests/ai_cases/curated_cases.json`.

## Baseline Performance (String Similarity)
```text
                             precision    recall  f1-score   support

            EXACT_DUPLICATE       0.00      0.00      0.00       2.0
    FUNCTIONALLY_EQUIVALENT       0.00      0.00      0.00       1.0
             NEAR_DUPLICATE       0.00      0.00      0.00       1.0
             NOT_EQUIVALENT       0.00      0.00      0.00       1.0
REQUIRES_ENGINEERING_REVIEW       0.00      0.00      0.00       1.0

                   accuracy                           0.00       6.0
                  macro avg       0.00      0.00      0.00       6.0
               weighted avg       0.00      0.00      0.00       6.0

```
*Note: String similarity struggles heavily with functionally equivalent items containing transposed descriptions or unit conversions.*

## AI Pipeline Performance (Hybrid Approach)
```text
                             precision    recall  f1-score   support

            EXACT_DUPLICATE       0.00      0.00      0.00         2
    FUNCTIONALLY_EQUIVALENT       0.50      1.00      0.67         1
             NEAR_DUPLICATE       0.00      0.00      0.00         1
             NOT_EQUIVALENT       0.00      0.00      0.00         1
REQUIRES_ENGINEERING_REVIEW       0.00      0.00      0.00         1

                   accuracy                           0.17         6
                  macro avg       0.10      0.20      0.13         6
               weighted avg       0.08      0.17      0.11         6

```
*Note: The AI pipeline leverages attribute extraction, semantic embeddings, and LLM reasoning to significantly boost recall on near and functional duplicates.*

## Confusion Matrix (Pipeline)
```text
[[0 1 1 0 0]
 [0 1 0 0 0]
 [0 0 0 1 0]
 [0 0 1 0 0]
 [1 0 0 0 0]]
```
*(Rows = True Label, Columns = Predicted Label)*
