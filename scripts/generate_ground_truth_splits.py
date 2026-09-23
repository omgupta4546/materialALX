import csv
import json
import random
import string
import os
import glob
import uuid

SEED = 777
random.seed(SEED)

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

print("Loading templates and rules...")
templates = {}
for file in glob.glob('data/templates/*.json'):
    t = load_json(file)
    templates[t['category']] = t

rules_data = load_json('data/reference/critical_rules.json')
rules = rules_data['rules']

synonyms_data = load_json('data/reference/synonyms.json')
synonym_map = {s['expansion']: s['term'] for s in synonyms_data['synonyms'] if not s['is_ambiguous']}

materials_csv = 'data/synthetic/source_materials.csv'

# Load source materials
print("Loading source materials...")
with open(materials_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    source_fields = reader.fieldnames
    source_materials = list(reader)

materials_by_cat = {}
for m in source_materials:
    materials_by_cat.setdefault(m['category'], []).append(m)

pairs = []
new_materials = []

def perturb_desc(desc):
    if random.random() < 0.5:
        for full, abbr in synonym_map.items():
            desc = desc.replace(full, abbr)
    if random.random() < 0.5:
        words = desc.split()
        random.shuffle(words)
        desc = " ".join(words)
    return desc

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

# 6 classes
class_counts = {
    'EXACT_DUPLICATE': 834,
    'NEAR_DUPLICATE': 833,
    'FUNCTIONALLY_EQUIVALENT': 833,
    'RELATED': 834,
    'NOT_EQUIVALENT': 833,
    'REQUIRES_ENGINEERING_REVIEW': 833
}

print("Generating 5000 pairs...")

for label, count in class_counts.items():
    for _ in range(count):
        cat = random.choice(list(templates.keys()))
        
        if label == 'REQUIRES_ENGINEERING_REVIEW':
            cat = 'CAT-BRG'
            
        if not materials_by_cat.get(cat):
            cat = random.choice(list(materials_by_cat.keys()))
            
        mat_A = random.choice(materials_by_cat[cat])
        mat_B = mat_A.copy()
        
        mat_B['material_code'] = f"{mat_A['cpse_code']}-B-{str(uuid.uuid4())[:8].upper()}"
        
        reason = ""
        critical_conflict = "NONE"
        t = templates.get(cat, list(templates.values())[0])
        
        if label == 'EXACT_DUPLICATE':
            mat_B['description'] = perturb_desc(mat_A['description'])
            reason = "Identical MPN/Attributes, perturbed description"
            
        elif label == 'NEAR_DUPLICATE':
            mat_B['description'] = perturb_desc(mat_A['description'])
            reason = "Identical MPN, perturbed desc, dropped minor field"
            
        elif label == 'FUNCTIONALLY_EQUIVALENT':
            mfgs = t.get('manufacturers', ['M1', 'M2'])
            mfg_B = random.choice([m for m in mfgs if m != mat_A['manufacturer']] + [str(mat_A['manufacturer'])+"_ALT"])
            mat_B['manufacturer'] = mfg_B
            mat_B['manufacturer_part_number'] = str(mat_A['manufacturer_part_number']) + "-EQ"
            mat_B['description'] = str(mat_A['description']).replace(str(mat_A['manufacturer']), mfg_B)
            mat_B['description'] = perturb_desc(mat_B['description'])
            reason = "Different Manufacturer/MPN, identical critical attributes"
            
        elif label == 'RELATED':
            mat_B['manufacturer_part_number'] = str(mat_A['manufacturer_part_number']) + "-SIZEB"
            mat_B['description'] = str(mat_A['description']) + " LARGER"
            reason = "Same category/mfg, different size/specs"
            
        elif label == 'NOT_EQUIVALENT':
            if random.random() < 0.5:
                cat_rules = [r for r in rules if r['category'] == cat and r['severity'] == 'CRITICAL']
                if cat_rules:
                    r = random.choice(cat_rules)
                    k = r['attribute']
                    if k in mat_B:
                        mat_B[k] = "CONFLICT"
                        critical_conflict = k
                mat_B['description'] = str(mat_A['description']) + " [CONFLICT]"
                reason = "Same category, critical attribute conflict"
            else:
                cat_B = random.choice([c for c in templates.keys() if c != cat])
                t_B = templates[cat_B]
                # clear old attributes to avoid taxonomy violations
                for attr in t.get('attributes', []):
                    mat_B.pop(attr['name'], None)
                mat_B['category'] = cat_B
                mat_B['subcategory'] = t_B['name']
                mat_B['description'] = f"{t_B['name']} DIFFERENT CAT {str(mat_A['description'])[:10]}"
                mat_B['manufacturer'] = random.choice(t_B.get('manufacturers', ['Gen']))
                mat_B['manufacturer_part_number'] = generate_mpn(t_B)
                reason = "Completely different category"
                critical_conflict = "CATEGORY_MISMATCH"
                
        elif label == 'REQUIRES_ENGINEERING_REVIEW':
            cat_rules = [r for r in rules if r['category'] == cat and r['severity'] == 'CONDITIONALLY_CRITICAL']
            if cat_rules:
                r = random.choice(cat_rules)
                k = r['attribute']
                if k in mat_B:
                    mat_B[k] = "REVIEW_VAL"
                    critical_conflict = k + " (Conditional)"
            mat_B['description'] = str(mat_A['description']) + " [REVIEW]"
            reason = "Mismatched conditionally critical attribute"

        new_materials.append(mat_B)
        
        pairs.append({
            'material_a': mat_A['material_code'],
            'material_b': mat_B['material_code'],
            'ground_truth': label,
            'reason': reason,
            'critical_conflict': critical_conflict,
            'category': cat
        })

print(f"Appending {len(new_materials)} new paired materials to {materials_csv}...")
with open(materials_csv, 'a', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=source_fields)
    writer.writerows(new_materials)

print("Shuffling pairs and splitting 70/15/15...")
random.shuffle(pairs)

total = len(pairs)
train_split = int(total * 0.70)
val_split = int(total * 0.15)

train_pairs = pairs[:train_split]
val_pairs = pairs[train_split:train_split+val_split]
test_pairs = pairs[train_split+val_split:]

pair_fields = ['material_a', 'material_b', 'ground_truth', 'reason', 'critical_conflict', 'category']

def write_pairs(filename, data):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=pair_fields)
        w.writeheader()
        w.writerows(data)
    print(f"Wrote {len(data)} rows to {filename}")

write_pairs('data/synthetic/match_ground_truth_train.csv', train_pairs)
write_pairs('data/synthetic/match_ground_truth_val.csv', val_pairs)
write_pairs('data/synthetic/match_ground_truth_test.csv', test_pairs)

print("Ground truth dataset generation successfully completed!")
