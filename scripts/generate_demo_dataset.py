import csv
import json
import random
import string
import os
import glob
import uuid

SEED = 999
random.seed(SEED)

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

print("Loading templates and rules...")
templates = {}
for file in glob.glob('data/templates/*.json'):
    t = load_json(file)
    templates[t['category']] = t

synonyms_data = load_json('data/reference/synonyms.json')
synonym_map = {s['expansion']: s['term'] for s in synonyms_data['synonyms'] if not s['is_ambiguous']}

materials = []
ground_truth = []
procurement = []

def perturb_desc(desc):
    if random.random() < 0.5:
        for full, abbr in synonym_map.items():
            desc = desc.replace(full, abbr)
    if random.random() < 0.5:
        words = desc.split()
        random.shuffle(words)
        desc = " ".join(words)
    return desc

def get_base_dict(cpse, category, subcat, mfg, mpn, desc):
    return {
        'cpse_code': cpse,
        'material_code': f"{cpse}-DEMO-{str(uuid.uuid4())[:6].upper()}",
        'description': desc,
        'uom': 'EACH',
        'category': category,
        'subcategory': subcat,
        'manufacturer': mfg,
        'manufacturer_part_number': mpn,
        'material_grade': '', 'size': '', 'pressure_class': '', 'voltage': '',
        'power': '', 'frequency': '', 'diameter': '', 'schedule': '',
        'seal_type': '', 'body_material': '', 'trim_material': '', 'end_connection': ''
    }

def add_proc(mat_code, cpse, qty, price, date_str):
    procurement.append({
        'procurement_id': f"PR-{str(uuid.uuid4())[:8].upper()}",
        'cpse_code': cpse,
        'material_code': mat_code,
        'supplier': f"Supplier_{random.choice('ABCDE')}",
        'quantity': qty,
        'unit_price': price,
        'total_spend': round(qty * price, 2),
        'uom': 'EACH',
        'procurement_date': date_str,
        'plant': f"PLANT-{random.randint(1,5)}"
    })

# STORYLINE 1: The High-Similarity Dangerous Conflict (Valve)
v1 = get_base_dict('NTPC', 'CAT-VLV', 'Gate Valve', 'KITZ', 'GT-150-SS', 'GATE VALVE 6IN WCB TRIM SS316 CLASS 150 FLANGED')
v1['pressure_class'] = '150#'
v1['size'] = '6 inch'
v1['body_material'] = 'WCB'

v2 = get_base_dict('NTPC', 'CAT-VLV', 'Gate Valve', 'KITZ', 'GT-300-SS', 'GATE VALVE 6IN WCB TRIM SS316 CLASS 300 FLANGED')
v2['pressure_class'] = '300#'
v2['size'] = '6 inch'
v2['body_material'] = 'WCB'

materials.extend([v1, v2])
ground_truth.append({
    'material_a': v1['material_code'], 'material_b': v2['material_code'],
    'ground_truth': 'NOT_EQUIVALENT', 'reason': 'Critical pressure class conflict',
    'critical_conflict': 'pressure_class', 'category': 'CAT-VLV'
})
add_proc(v1['material_code'], 'NTPC', 5, 1200.00, '2025-01-15')
add_proc(v2['material_code'], 'NTPC', 2, 2500.00, '2025-02-10')

# STORYLINE 2: Aggregation Opportunity (Multiple CPSEs EXACT_DUPLICATE)
skf_mfg = "SKF"
skf_mpn = "6205-2RS"
skf_desc = "SKF DEEP GROOVE BALL BEARING 6205-2RS 25MM X 52MM X 15MM"

b1 = get_base_dict('ONGC', 'CAT-BRG', 'Ball Bearing', skf_mfg, skf_mpn, skf_desc)
b1['seal_type'] = '2RS'
b2 = get_base_dict('SAIL', 'CAT-BRG', 'Ball Bearing', skf_mfg, skf_mpn, "BRG BALL DEEP GROOVE 6205-2RS SKF")
b2['seal_type'] = '2RS'
b3 = get_base_dict('IOCL', 'CAT-BRG', 'Ball Bearing', skf_mfg, skf_mpn, "6205-2RS BEARING SKF")
b3['seal_type'] = '2RS'

materials.extend([b1, b2, b3])
ground_truth.append({'material_a': b1['material_code'], 'material_b': b2['material_code'], 'ground_truth': 'EXACT_DUPLICATE', 'reason': 'Same MPN/MFG', 'critical_conflict': 'NONE', 'category': 'CAT-BRG'})
ground_truth.append({'material_a': b1['material_code'], 'material_b': b3['material_code'], 'ground_truth': 'EXACT_DUPLICATE', 'reason': 'Same MPN/MFG', 'critical_conflict': 'NONE', 'category': 'CAT-BRG'})

add_proc(b1['material_code'], 'ONGC', 100, 45.00, '2025-03-01')
add_proc(b2['material_code'], 'SAIL', 500, 15.00, '2025-03-15')
add_proc(b3['material_code'], 'IOCL', 50, 65.00, '2025-03-20')

# STORYLINE 3: Missing Critical Attributes (Pipe missing schedule)
p1 = get_base_dict('NTPC', 'CAT-PIP', 'Carbon Steel Pipe', 'Jindal', 'PIP-CS-10', 'CARBON STEEL PIPE SEAMLESS 10 INCH LENGTH 6M')
p1['diameter'] = '10 inch'
p1['length'] = '6 M'
# intentionally omitted schedule
materials.append(p1)
add_proc(p1['material_code'], 'NTPC', 20, 800.00, '2025-04-01')

# STORYLINE 4: Functional Equivalents (Motors)
m1 = get_base_dict('BHEL', 'CAT-MTR', 'AC Motor', 'Siemens', '1LA7090-4AA10', 'AC MOTOR 1.5KW 415V 50HZ 1500RPM TEFC SIEMENS')
m1['power'] = '1.5 KW'
m1['voltage'] = '415 V'
m1['frequency'] = '50 HZ'

m2 = get_base_dict('BHEL', 'CAT-MTR', 'AC Motor', 'ABB', 'M2QA090L4A', 'MOTOR AC 1.5KW 415V 50HZ 1500RPM IP55 ABB')
m2['power'] = '1.5 KW'
m2['voltage'] = '415 V'
m2['frequency'] = '50 HZ'

materials.extend([m1, m2])
ground_truth.append({
    'material_a': m1['material_code'], 'material_b': m2['material_code'],
    'ground_truth': 'FUNCTIONALLY_EQUIVALENT', 'reason': 'Different MFG, identical core specs',
    'critical_conflict': 'NONE', 'category': 'CAT-MTR'
})
add_proc(m1['material_code'], 'BHEL', 5, 4500.00, '2025-05-01')
add_proc(m2['material_code'], 'BHEL', 3, 4400.00, '2025-05-15')

# STORYLINE 5: Near Duplicate
f1 = get_base_dict('SAIL', 'CAT-FST', 'Bolts', 'Bossard', 'HX-M10-50', 'HEX BOLT M10 X 50MM SS304 CLASS 8.8')
f1['size'] = 'M10'
f2 = get_base_dict('SAIL', 'CAT-FST', 'Bolts', 'Bossard', 'HX-M10-50', 'BOLT HEX M10 50MM SS304') 
f2['size'] = 'M10'
materials.extend([f1, f2])
ground_truth.append({
    'material_a': f1['material_code'], 'material_b': f2['material_code'],
    'ground_truth': 'NEAR_DUPLICATE', 'reason': 'Identical MPN, dropped text field',
    'critical_conflict': 'NONE', 'category': 'CAT-FST'
})
add_proc(f1['material_code'], 'SAIL', 1000, 1.20, '2025-06-01')
add_proc(f2['material_code'], 'SAIL', 500, 1.25, '2025-06-15')

# PADDING
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

cpses = ['NTPC', 'ONGC', 'SAIL', 'IOCL', 'BHEL']
while len(materials) < 400:
    cat = random.choice(list(templates.keys()))
    t = templates[cat]
    mfg = random.choice(t.get('manufacturers', ['GenMfg']))
    mpn = generate_mpn(t)
    attrs = generate_attrs(t)
    
    parts = [t['name'].upper(), mfg.upper(), mpn]
    parts.extend(attrs.values())
    desc = " ".join([str(p).upper() for p in parts if p])
    
    cpse = random.choice(cpses)
    mat = get_base_dict(cpse, cat, t['name'], mfg, mpn, desc)
    for k, v in attrs.items():
        if k in mat:
            mat[k] = v
        
    materials.append(mat)
    
    if random.random() < 0.8:
        add_proc(mat['material_code'], cpse, random.randint(1, 100), round(random.uniform(10, 5000), 2), f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}")

os.makedirs('data/demo', exist_ok=True)

mat_fields = list(materials[0].keys())
all_keys = set()
for m in materials:
    all_keys.update(m.keys())
extra_keys = sorted(list(all_keys - set(mat_fields)))
mat_fields.extend(extra_keys)
with open('data/demo/demo_materials.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=mat_fields)
    writer.writeheader()
    writer.writerows(materials)

gt_fields = list(ground_truth[0].keys())
with open('data/demo/demo_ground_truth.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=gt_fields)
    writer.writeheader()
    writer.writerows(ground_truth)

pr_fields = list(procurement[0].keys())
with open('data/demo/demo_procurement.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=pr_fields)
    writer.writeheader()
    writer.writerows(procurement)

print(f"Demo dataset generation successfully completed!")
print(f"Materials: {len(materials)}")
print(f"Ground Truth Pairs: {len(ground_truth)}")
print(f"Procurement Records: {len(procurement)}")
