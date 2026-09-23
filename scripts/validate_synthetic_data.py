import csv
import json
import os
import glob
import re

def print_header(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

print_header("Loading References")

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

uom_data = load_json('data/reference/uom_master.json')
valid_uoms = set()
for dim_name, dim_info in uom_data['dimensions'].items():
    valid_uoms.add(dim_info['canonical_unit'])
    for unit in dim_info.get('units', []):
        valid_uoms.add(unit['code'])
        valid_uoms.update(unit.get('aliases', []))
valid_uoms.add('EACH')
valid_uoms.add('Unknown')

classifications = load_json('data/reference/classification.json')
valid_categories = {c['id'] for c in classifications['categories']}

templates = {}
for f in glob.glob('data/templates/*.json'):
    t = load_json(f)
    templates[t['category']] = t

rules_data = load_json('data/reference/critical_rules.json')
critical_rules = rules_data['rules']

print("References loaded successfully.")

# Phase 1: Source Materials
print_header("Phase 1: Material Master Validation")
materials_file = 'data/synthetic/source_materials.csv'

errors = []
master_ids = set()
master_dict = {}

def extract_number(val_str):
    if not isinstance(val_str, str): return None
    # match first number
    m = re.search(r'-?\d+(\.\d+)?', val_str)
    if m:
        return float(m.group())
    return None

if not os.path.exists(materials_file):
    errors.append("source_materials.csv not found")
else:
    with open(materials_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            mid = row.get('material_code')
            master_ids.add(mid)
            master_dict.setdefault(mid, []).append(row)
            
            # 1. Required fields
            if not row.get('cpse_code'): errors.append(f"Row {i}: Missing cpse_code")
            if not row.get('material_code'): errors.append(f"Row {i}: Missing material_code")
            if not row.get('description'): errors.append(f"Row {i}: Missing description")
            if not row.get('category'): errors.append(f"Row {i}: Missing category")
            
            # 2. Valid UOM
            uom = row.get('uom', '')
            if uom and uom not in valid_uoms:
                errors.append(f"Row {i}: Invalid UOM '{uom}'")
                
            # 3. Valid taxonomy
            cat = row.get('category')
            if cat and cat not in valid_categories and cat not in templates:
                errors.append(f"Row {i}: Invalid category '{cat}'")
                
            # Attribute checking
            if cat in templates:
                t = templates[cat]
                # 4, 5. Attribute ranges
                for attr in t.get('attributes', []):
                    name = attr['name']
                    val = row.get(name)
                    # Exclude purposely injected conflict values from mathematical checking
                    if val and val not in ["Unknown", "CONFLICT", "REVIEW_VAL", "CONFLICTING_VAL"] and "CONFLICT" not in val:
                        num = extract_number(val)
                        if num is not None and 'value_range' in attr:
                            min_v = attr['value_range']['min']
                            max_v = attr['value_range']['max']
                            if not (min_v <= num <= max_v):
                                errors.append(f"Row {i} ({mid}): {name} value {num} out of range [{min_v}, {max_v}]")
                                
                # 7. Logical technical combinations
                if cat != 'CAT-PIP' and row.get('schedule'):
                    errors.append(f"Row {i}: Category {cat} should not have 'schedule'")
                if cat != 'CAT-BRG' and row.get('seal_type'):
                    errors.append(f"Row {i}: Category {cat} should not have 'seal_type'")

print(f"Material Master check complete. {len(master_ids)} records checked.")
if len(errors) > 0:
    print(f"Errors found: {len(errors)}")
    for e in errors[:10]: print(e)

# Phase 2: Procurement Records
print_header("Phase 2: Procurement Validation")
proc_file = 'data/synthetic/procurement_records.csv'
proc_errors = []

if not os.path.exists(proc_file):
    proc_errors.append("procurement_records.csv not found")
else:
    with open(proc_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            try:
                qty = float(row.get('quantity', 0))
                price = float(row.get('unit_price', 0))
                spend = float(row.get('total_spend', 0))
                
                # 8. Procurement arithmetic
                if qty <= 0: proc_errors.append(f"Row {i}: Quantity <= 0")
                if price < 0: proc_errors.append(f"Row {i}: Unit price < 0")
                
                expected_spend = round(qty * price, 2)
                if abs(spend - expected_spend) > 0.05:
                    proc_errors.append(f"Row {i}: Spend arithmetic error. {qty} * {price} != {spend}")
                    
                # Foreign key
                if row.get('material_code') not in master_ids:
                    proc_errors.append(f"Row {i}: material_code {row.get('material_code')} not found in master")
            except ValueError:
                proc_errors.append(f"Row {i}: Invalid numeric value in procurement math")

print(f"Procurement check complete. Errors: {len(proc_errors)}")
if len(proc_errors) > 0:
    for e in proc_errors[:10]: print(e)

# Phase 3: Ground Truth
print_header("Phase 3: Ground-Truth Consistency")
gt_errors = []

for split in ['train', 'val', 'test']:
    gt_file = f'data/synthetic/match_ground_truth_{split}.csv'
    if not os.path.exists(gt_file):
        continue
    with open(gt_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            ma = row.get('material_a')
            mb = row.get('material_b')
            label = row.get('ground_truth')
            
            if ma not in master_ids: gt_errors.append(f"{split} Row {i}: material_a {ma} missing")
            if mb not in master_ids: gt_errors.append(f"{split} Row {i}: material_b {mb} missing")
            
            if ma in master_ids and mb in master_ids:
                recs_A = master_dict[ma]
                recs_B = master_dict[mb]
                
                # 10. Duplicate relationships
                if label == 'EXACT_DUPLICATE':
                    match_found = False
                    for rA in recs_A:
                        for rB in recs_B:
                            if str(rA.get('manufacturer', '')) == str(rB.get('manufacturer', '')) and \
                               str(rA.get('manufacturer_part_number', '')) == str(rB.get('manufacturer_part_number', '')):
                                match_found = True
                                break
                    if not match_found:
                        gt_errors.append(f"{split} Row {i}: EXACT_DUPLICATE has mismatched manufacturers/MPN")

print(f"Ground Truth check complete. Errors: {len(gt_errors)}")
if len(gt_errors) > 0:
    for e in gt_errors[:10]: print(e)

print_header("Final Validation Report")
total_errors = len(errors) + len(proc_errors) + len(gt_errors)

if total_errors == 0:
    print("ALL TESTS PASSED: Synthetic data is highly consistent, logically sound, and mathematically verified.")
    with open("data/synthetic/validation_report.txt", "w") as f:
        f.write("STATUS: PASSED\nChecked: Required fields, UOM, Taxonomy, Numeric Ranges, Math Arithmetic, FK Relationships.\nTotal Errors: 0\n")
    exit(0)
else:
    print(f"VALIDATION FAILED with {total_errors} total errors.")
    with open("data/synthetic/validation_report.txt", "w") as f:
        f.write(f"STATUS: FAILED\nTotal Errors: {total_errors}\n")
    exit(1)
