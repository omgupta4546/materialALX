# Attribute Dictionary

This document defines the core technical attributes associated with specific material categories in the National Material Intelligence & Harmonization Platform.

The machine-readable version of this dictionary is stored in `data/reference/attribute_dictionary.json`.

## Schema Definition

Each attribute is defined with the following properties:
- **Name**: The internal, machine-readable key (e.g., `bearing_type`).
- **Display Name**: The human-readable label used in the UI (e.g., `Bearing Type`).
- **Data Type**: The expected format of the value (`string`, `number`, `boolean`).
- **Unit**: The standardized unit of measurement (`mm`, `kW`, `inch`, `V`, `Hz`, `rpm`, `m3/h`, `m`, or `null` if not applicable).
- **Mandatory**: Whether the attribute is required for a complete material record (`true`/`false`).
- **Critical**: Whether the attribute is essential for determining functional equivalence or duplicate detection (`true`/`false`).
- **Applicable Categories**: An array of category IDs (from `classification.json`) that this attribute applies to (e.g., `["CAT-BRG"]`).

## Category-Specific Attributes

### 1. Bearings (`CAT-BRG`)
- `bearing_type` (String) [Critical, Mandatory]
- `series` (String) [Critical]
- `bore` (Number, mm) [Critical, Mandatory]
- `outer_diameter` (Number, mm) [Critical, Mandatory]
- `width` (Number, mm) [Critical, Mandatory]
- `seal_type` (String)
- `material` (String)
- `manufacturer` (String) [Critical, Mandatory]
- `mpn` (String) [Critical, Mandatory]

### 2. Valves (`CAT-VLV`)
- `valve_type` (String) [Critical, Mandatory]
- `size` (Number, inch) [Critical, Mandatory]
- `pressure_class` (String) [Critical, Mandatory]
- `body_material` (String) [Critical, Mandatory]
- `trim_material` (String) [Critical]
- `end_connection` (String) [Critical, Mandatory]
- `rating` (String)
- `manufacturer` (String) [Critical, Mandatory]
- `mpn` (String) [Critical, Mandatory]

### 3. Motors (`CAT-MTR`)
- `motor_type` (String) [Critical, Mandatory]
- `power` (Number, kW) [Critical, Mandatory]
- `voltage` (Number, V) [Critical, Mandatory]
- `frequency` (Number, Hz) [Critical, Mandatory]
- `phase` (Number) [Critical, Mandatory]
- `rpm` (Number, rpm) [Critical, Mandatory]
- `efficiency` (String)
- `enclosure` (String)
- `manufacturer` (String) [Critical, Mandatory]
- `mpn` (String) [Critical, Mandatory]

### 4. Pipes (`CAT-PIP`)
- `pipe_type` (String) [Critical, Mandatory]
- `diameter` (Number, inch) [Critical, Mandatory]
- `wall_thickness` (Number, mm) [Critical]
- `schedule` (String) [Critical, Mandatory]
- `material_grade` (String) [Critical, Mandatory]
- `length` (Number, m)
- `manufacturer` (String) [Critical, Mandatory]

### 5. Pumps (`CAT-PMP`)
- `pump_type` (String) [Critical, Mandatory]
- `flow_rate` (Number, m3/h) [Critical, Mandatory]
- `head` (Number, m) [Critical, Mandatory]
- `power` (Number, kW) [Critical, Mandatory]
- `voltage` (Number, V) [Critical, Mandatory]
- `material` (String)

## Cross-Category Attributes
Some attributes are defined universally and applied to multiple categories:
- `manufacturer`
- `mpn` (Manufacturer Part Number)
- `power` (e.g., Motors and Pumps)
- `voltage` (e.g., Motors and Pumps)
- `material` (e.g., Bearings, Pumps)
