import os
import csv
from collections import defaultdict
from baseline_matcher import BaselineMatcher

def load_source_materials(csv_path: str) -> dict:
    materials = {}
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return materials
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Reconstruct a rich text representation for matching
            # E.g. "DESCRIPTION MANUFACTURER MPN"
            desc = row.get('description', '')
            mfg = row.get('manufacturer', '')
            mpn = row.get('manufacturer_part_number', '')
            
            text_blocks = [desc]
            if mfg: text_blocks.append(mfg)
            if mpn: text_blocks.append(mpn)
            
            materials[row['material_code']] = " ".join(text_blocks)
            
    return materials

def evaluate():
    source_csv = 'data/synthetic/source_materials.csv'
    ground_truth_csv = 'data/synthetic/match_ground_truth_test.csv'
    
    if not os.path.exists(ground_truth_csv):
        print(f"Error: Could not find {ground_truth_csv}")
        return
        
    print(f"Loading source materials from {source_csv}...")
    materials_dict = load_source_materials(source_csv)
    print(f"Loaded {len(materials_dict)} materials.")
    
    matcher = BaselineMatcher(match_threshold=0.75)
    
    # Ground truth classes that denote a "positive" match
    POSITIVE_CLASSES = {'EXACT_DUPLICATE', 'NEAR_DUPLICATE', 'FUNCTIONALLY_EQUIVALENT'}
    
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    
    processed_count = 0
    missing_material_count = 0

    print("Evaluating baseline matcher against ground truth...")
    with open(ground_truth_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat_a_code = row['material_a']
            mat_b_code = row['material_b']
            
            text_a = materials_dict.get(mat_a_code)
            text_b = materials_dict.get(mat_b_code)
            
            if not text_a or not text_b:
                missing_material_count += 1
                continue
                
            pred = matcher.predict(text_a, text_b)
            is_predicted_match = pred['is_match']
            
            actual_label = row['ground_truth']
            is_actual_match = actual_label in POSITIVE_CLASSES
            
            if is_predicted_match and is_actual_match:
                true_positives += 1
            elif is_predicted_match and not is_actual_match:
                false_positives += 1
            elif not is_predicted_match and is_actual_match:
                false_negatives += 1
            else:
                true_negatives += 1
                
            processed_count += 1

    print(f"\n--- Evaluation Complete ---")
    print(f"Pairs processed: {processed_count}")
    if missing_material_count > 0:
        print(f"Warning: {missing_material_count} pairs skipped due to missing source material references.")
        
    print("\nConfusion Matrix:")
    print(f"True Positives (TP):  {true_positives}")
    print(f"False Positives (FP): {false_positives}")
    print(f"True Negatives (TN):  {true_negatives}")
    print(f"False Negatives (FN): {false_negatives}")
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print("\nMetrics:")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1_score:.4f}")

if __name__ == "__main__":
    evaluate()
