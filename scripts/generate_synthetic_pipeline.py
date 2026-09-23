import json
import os
import random
import csv
import string
import glob
import uuid
from datetime import datetime, timedelta

# Configuration
SEED = 42
TOTAL_RECORDS = 10000
DUPLICATE_RATIO = 0.15
NEAR_DUP_RATIO = 0.10
CONFLICT_RATIO = 0.05
FUNC_EQUIV_RATIO = 0.05
RELATED_RATIO = 0.05
# The rest will be base records (no specific GT pair, just background volume)

random.seed(SEED)

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load references
cpse_data = load_json('data/reference/cpse.json')
cpses = [c['cpse_code'] for c in cpse_data['organizations']]

synonyms_data = load_json('data/reference/synonyms.json')
synonym_map = {s['expansion']: s['term'] for s in synonyms_data['synonyms'] if not s['is_ambiguous']}

rules_data = load_json('data/reference/critical_rules.json')
rules = rules_data['rules']

templates = {}
for file in glob.glob('data/templates/*.json'):
    t = load_json(file)
    templates[t['category']] = t

FIELDNAMES_MAT = [
    'cpse_code', 'material_code', 'description', 'uom', 'category', 'subcategory',
    'manufacturer', 'manufacturer_part_number', 'material_grade', 'size',
    'pressure_class', 'voltage', 'power', 'frequency', 'diameter', 'schedule',
    'seal_type', 'body_material', 'trim_material', 'end_connection', 'plant'
]

FIELDNAMES_PROC = [
    'procurement_id', 'cpse_code', 'material_code', 'supplier', 'quantity',
    'unit_price', 'total_spend', 'uom', 'procurement_date', 'plant'
]

FIELDNAMES_GT = [
    'pair_id', 'source_template_category', 'true_label',
    'record_A_mat_code', 'record_B_mat_code', 'reason'
]

def get_random_date(start_year=2020):
    start = datetime(start_year, 1, 1)
    end = datetime.now()
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def generate_mpn(template):
    part_structure = template.get('part_number_structure', '')
    if part_structure:
        mpn = part_structure
        while '[' in mpn and ']' in mpn:
            start = mpn.find('[')
            end = mpn.find(']')
            mpn = mpn[:start] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) + mpn[end+1:]
        return mpn
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_attrs(template):
    attrs = {}
    for attr in template['attributes']:
        name = attr['name']
        if 'valid_values' in attr:
            val = random.choice(attr['valid_values'])
        elif 'value_range' in attr:
            min_val = attr['value_range']['min']
            max_val = attr['value_range']['max']
            if isinstance(min_val, int) and isinstance(max_val, int):
                val = random.randint(min_val, max_val)
            else:
                val = round(random.uniform(min_val, max_val), 2)
        else:
            val = "Unknown"
            
        unit = random.choice(attr.get('valid_units', [""]))
        if unit:
            attrs[name] = f"{val} {unit}".strip()
        else:
            attrs[name] = str(val)
    return attrs

def build_desc(template, attrs, mfg, mpn):
    desc_parts = ["[SYN]", template['name'].upper(), mfg.upper(), mpn]
    desc_parts.extend(attrs.values())
    return " ".join([str(p).upper() for p in desc_parts if p])

def perturb_desc(desc):
    # Word Order
    if random.random() < 0.2:
        words = desc.split()
        if len(words) > 3:
            # shuffle a few words in the middle to avoid losing SYN or core name
            mid = words[2:]
            random.shuffle(mid)
            desc = " ".join(words[:2] + mid)
            
    # Abbreviations
    if random.random() < 0.3:
        for full, abbr in synonym_map.items():
            desc = desc.replace(full, abbr)
            
    # UOM variations
    if random.random() < 0.2:
        desc = desc.replace("inch", random.choice(["IN", "\"", "in."]))
        desc = desc.replace("mm", random.choice(["MM", "m.m."]))
        
    # Spelling error
    if random.random() < 0.1 and len(desc) > 10:
        idx = random.randint(5, len(desc) - 1)
        if desc[idx].isalpha():
            desc = desc[:idx] + random.choice(string.ascii_uppercase) + desc[idx+1:]
            
    return desc

def generate_base_record(template_cat=None):
    if not template_cat:
        template_cat = random.choice(list(templates.keys()))
    t = templates[template_cat]
    
    cpse = random.choice(cpses)
    mfg = random.choice(t.get('manufacturers', ["Generic"]))
    mpn = generate_mpn(t)
    attrs = generate_attrs(t)
    
    record = {f: "" for f in FIELDNAMES_MAT}
    record['cpse_code'] = cpse
    record['category'] = t['category']
    record['subcategory'] = t['name']
    
    for k, v in attrs.items():
        if k in record:
            record[k] = v
            
    record['manufacturer'] = mfg
    record['manufacturer_part_number'] = mpn
    record['material_code'] = f"{cpse}-SYN-{random.randint(100000, 999999)}"
    record['description'] = build_desc(t, attrs, mfg, mpn)
    record['uom'] = "EACH"
    record['plant'] = f"PLANT-{random.randint(1, 5)}"
    
    return record, t, attrs

source_materials = []
ground_truth = []
procurement_records = []

num_exact = int(TOTAL_RECORDS * DUPLICATE_RATIO)
num_near = int(TOTAL_RECORDS * NEAR_DUP_RATIO)
num_conflict = int(TOTAL_RECORDS * CONFLICT_RATIO)
num_func = int(TOTAL_RECORDS * FUNC_EQUIV_RATIO)
num_related = int(TOTAL_RECORDS * RELATED_RATIO)
num_base = TOTAL_RECORDS - (num_exact + num_near + num_conflict + num_func + num_related)

print(f"Generating {TOTAL_RECORDS} total materials...")

# 1. Base Records (No specific pairs tracked for GT)
for _ in range(num_base):
    rec, _, _ = generate_base_record()
    rec['description'] = perturb_desc(rec['description'])
    source_materials.append(rec)

# 2. EXACT_DUPLICATE
for _ in range(num_exact):
    rec_A, t, _ = generate_base_record()
    rec_B = rec_A.copy()
    rec_B['material_code'] = f"{random.choice(cpses)}-SYN-{random.randint(100000, 999999)}"
    rec_B['cpse_code'] = rec_B['material_code'].split('-')[0]
    rec_B['plant'] = f"PLANT-{random.randint(1, 5)}"
    rec_B['description'] = perturb_desc(rec_B['description'])
    
    source_materials.extend([rec_A, rec_B])
    ground_truth.append({
        'pair_id': str(uuid.uuid4()),
        'source_template_category': t['category'],
        'true_label': 'EXACT_DUPLICATE',
        'record_A_mat_code': rec_A['material_code'],
        'record_B_mat_code': rec_B['material_code'],
        'reason': 'Identical MPN and specs'
    })

# 3. NEAR_DUPLICATE
for _ in range(num_near):
    rec_A, t, attrs = generate_base_record()
    rec_B = rec_A.copy()
    rec_B['material_code'] = f"{random.choice(cpses)}-SYN-{random.randint(100000, 999999)}"
    rec_B['cpse_code'] = rec_B['material_code'].split('-')[0]
    
    # Drop an attribute
    if attrs:
        k = random.choice(list(attrs.keys()))
        if k in rec_B:
            rec_B[k] = ""
            
    rec_B['description'] = perturb_desc(build_desc(t, {k:v for k,v in attrs.items() if rec_B.get(k)}, rec_B['manufacturer'], rec_B['manufacturer_part_number']))
    
    source_materials.extend([rec_A, rec_B])
    ground_truth.append({
        'pair_id': str(uuid.uuid4()),
        'source_template_category': t['category'],
        'true_label': 'NEAR_DUPLICATE',
        'record_A_mat_code': rec_A['material_code'],
        'record_B_mat_code': rec_B['material_code'],
        'reason': 'Missing text attribute but same MPN'
    })

# 4. FUNCTIONALLY_EQUIVALENT
for _ in range(num_func):
    rec_A, t, attrs = generate_base_record()
    rec_B = rec_A.copy()
    rec_B['material_code'] = f"{random.choice(cpses)}-SYN-{random.randint(100000, 999999)}"
    rec_B['cpse_code'] = rec_B['material_code'].split('-')[0]
    
    mfgs = t.get('manufacturers', ['GenMfgA', 'GenMfgB'])
    rec_B['manufacturer'] = random.choice([m for m in mfgs if m != rec_A['manufacturer']]) if len(mfgs)>1 else rec_A['manufacturer']+"_ALT"
    rec_B['manufacturer_part_number'] = generate_mpn(t)
    
    rec_B['description'] = perturb_desc(build_desc(t, attrs, rec_B['manufacturer'], rec_B['manufacturer_part_number']))
    
    source_materials.extend([rec_A, rec_B])
    ground_truth.append({
        'pair_id': str(uuid.uuid4()),
        'source_template_category': t['category'],
        'true_label': 'FUNCTIONALLY_EQUIVALENT',
        'record_A_mat_code': rec_A['material_code'],
        'record_B_mat_code': rec_B['material_code'],
        'reason': 'Different manufacturer, identical core specs'
    })

# 5. NOT_EQUIVALENT / CONFLICTING
for _ in range(num_conflict):
    rec_A, t, attrs = generate_base_record()
    rec_B = rec_A.copy()
    rec_B['material_code'] = f"{random.choice(cpses)}-SYN-{random.randint(100000, 999999)}"
    rec_B['cpse_code'] = rec_B['material_code'].split('-')[0]
    
    # Intentionally cause a conflict in a critical rule
    cat_rules = [r for r in rules if r['category'] == t['category'] and r['severity'] == 'CRITICAL']
    if cat_rules:
        rule = random.choice(cat_rules)
        attr = rule['attribute']
        if attr in rec_B:
            rec_B[attr] = "CONFLICTING_VAL"
    else:
        # Fallback if no critical rule, just change MPN radically
        rec_B['manufacturer_part_number'] += "-INCOMPAT"
        
    rec_B['description'] = perturb_desc(build_desc(t, {k:v for k,v in attrs.items() if rec_B.get(k)}, rec_B['manufacturer'], rec_B['manufacturer_part_number']))
    
    source_materials.extend([rec_A, rec_B])
    ground_truth.append({
        'pair_id': str(uuid.uuid4()),
        'source_template_category': t['category'],
        'true_label': 'NOT_EQUIVALENT',
        'record_A_mat_code': rec_A['material_code'],
        'record_B_mat_code': rec_B['material_code'],
        'reason': 'Critical rule violation or total mismatch'
    })
    
# 6. RELATED
for _ in range(num_related):
    rec_A, t, attrs = generate_base_record()
    rec_B = rec_A.copy()
    rec_B['material_code'] = f"{random.choice(cpses)}-SYN-{random.randint(100000, 999999)}"
    rec_B['cpse_code'] = rec_B['material_code'].split('-')[0]
    
    if attrs:
        k = random.choice(list(attrs.keys()))
        if k in rec_B:
            rec_B[k] = str(rec_B[k]) + "-DIFF"
            
    rec_B['manufacturer_part_number'] += "-X"
    rec_B['description'] = build_desc(t, {k:v for k,v in attrs.items() if rec_B.get(k)}, rec_B['manufacturer'], rec_B['manufacturer_part_number'])
    
    source_materials.extend([rec_A, rec_B])
    ground_truth.append({
        'pair_id': str(uuid.uuid4()),
        'source_template_category': t['category'],
        'true_label': 'RELATED',
        'record_A_mat_code': rec_A['material_code'],
        'record_B_mat_code': rec_B['material_code'],
        'reason': 'Similar item, different subclass'
    })

print(f"Total Materials Generated: {len(source_materials)}")
print(f"Total Ground Truth Pairs: {len(ground_truth)}")

# Procurement Generation
print("Generating procurement records...")
synthetic_suppliers = [f"SYNTHETIC_SUPPLIER_{chr(65+i)}{chr(65+j)}" for i in range(26) for j in range(2)]

for mat in source_materials:
    # 50% chance a material has procurement history
    if random.random() < 0.5:
        num_events = random.randint(1, 3)
        base_price = round(random.uniform(5.0, 5000.0), 2)
        
        for _ in range(num_events):
            qty = random.randint(1, 100)
            unit_price = round(base_price * random.uniform(0.9, 1.1), 2)
            
            procurement_records.append({
                'procurement_id': f"PROC-SYN-{str(uuid.uuid4())[:8].upper()}",
                'cpse_code': mat['cpse_code'],
                'material_code': mat['material_code'],
                'supplier': random.choice(synthetic_suppliers),
                'quantity': qty,
                'unit_price': unit_price,
                'total_spend': round(qty * unit_price, 2),
                'uom': mat['uom'],
                'procurement_date': get_random_date().strftime('%Y-%m-%d'),
                'plant': mat['plant']
            })

print(f"Total Procurement Records Generated: {len(procurement_records)}")

# Write Outputs
os.makedirs('data/synthetic', exist_ok=True)

with open('data/synthetic/source_materials.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES_MAT)
    writer.writeheader()
    writer.writerows(source_materials)

with open('data/synthetic/ground_truth_matches.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES_GT)
    writer.writeheader()
    writer.writerows(ground_truth)

with open('data/synthetic/procurement_records.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES_PROC)
    writer.writeheader()
    writer.writerows(procurement_records)

print("Unified pipeline completed successfully.")
