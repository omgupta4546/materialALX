# Critical Attribute Rules

This document outlines the reasoning behind the Critical Attribute Rules engine for the National Material Intelligence & Harmonization Platform. The machine-readable version is located in `data/reference/critical_rules.json`.

## Purpose
The Hybrid Matching Engine utilizes embeddings and textual similarities to retrieve candidate matches for materials. However, certain physical and electrical properties are **fundamentally incompatible** if they do not match exactly. The Critical Rules Engine acts as a safety layer to prevent the AI from automatically merging materials that look textually similar but are technically incompatible.

## Schema Definition
Each rule is defined by:
- **`category`**: The target material category (e.g., `CAT-VLV`).
- **`attribute`**: The target attribute key (e.g., `pressure_class`).
- **`severity`**: 
  - `CRITICAL`: An exact match or verified conversion is strictly required.
  - `CONDITIONALLY_CRITICAL`: A mismatch might be acceptable depending on the operating environment (e.g., open vs. shielded bearings).
- **`conflict_behavior`**:
  - `PREVENT_MATCH`: The system will explicitly reject merging these materials, changing the match type to `NOT_EQUIVALENT`.
  - `REQUIRE_ENGINEERING_APPROVAL`: The system will flag the match as `REQUIRES_ENGINEERING_REVIEW`, demanding a human domain expert's sign-off before proceeding.
- **`automatic_match_allowed`**: A boolean strictly controlling whether the AI can auto-approve a match if a mismatch is detected (always `false` for critical attributes).

## Category Reasoning

### Valves (`CAT-VLV`)
- **`size`, `end_connection`**: Dimensional mismatch physically prevents installation.
- **`pressure_class`, `body_material`**: Metallurgical and rating mismatches can result in catastrophic failure under operational pressure and temperature. A 150# valve can never safely replace a 300# valve.

### Motors (`CAT-MTR`)
- **`power`, `voltage`, `frequency`**: Mismatching these electrical properties will destroy the motor, trip breakers, or fail to provide adequate torque for the driven equipment. They are universally incompatible if mismatched.

### Pipes (`CAT-PIP`)
- **`diameter`, `schedule` (Wall Thickness)**: Required for flow calculations and burst pressure integrity.
- **`material_grade`**: Directly impacts chemical compatibility and corrosion resistance.

### Bearings (`CAT-BRG`)
- **`series`, `bore`, `outer_diameter`, `width` (Dimensions)**: Physical dimensions must be identical. A bearing that does not fit the shaft or housing is useless.
- **`seal_type` (Conditionally Critical)**: A shielded bearing (ZZ) might be used in place of an open bearing in some contexts, but a rubber-sealed (2RS) bearing might cause overheating in high-speed applications. Therefore, mismatches trigger `REQUIRE_ENGINEERING_APPROVAL` rather than a hard block.
