# Domain Taxonomy for Industrial Materials

This document defines the initial domain taxonomy for the National Material Intelligence & Harmonization Platform. The taxonomy is designed to be extensible, allowing for deeper hierarchical nesting as more granular material variations are encountered.

## Taxonomy Structure

The taxonomy is represented as a tree hierarchy. Each category can contain an arbitrary number of nested subcategories.

The machine-readable version of this taxonomy is stored in `data/reference/classification.json`.

## Core Categories

Below is the initial tree representing the primary industrial categories and their common subcategories.

### 1. Bearings
- Ball Bearings
  - Deep Groove Ball Bearings
- Tapered Roller Bearings

### 2. Valves
- Gate Valve
- Globe Valve
- Ball Valve
- Butterfly Valve

### 3. Pumps
- Centrifugal Pump
- Positive Displacement Pump

### 4. Motors
- AC Motor
- DC Motor

### 5. Pipes
- Carbon Steel Pipe
- Stainless Steel Pipe

### 6. Flanges
- Weld Neck
- Slip-On
- Blind

### 7. Gaskets
- Spiral Wound
- Non-Metallic

### 8. Fasteners
- Bolts
- Nuts
- Washers
- Screws

### 9. Cables
- Power Cable
- Control Cable

### 10. Electrical Components
- Circuit Breaker
- Relay
- Switchgear

### 11. Instrumentation
- Pressure Transmitter
- Temperature Transmitter
- Flow Transmitter

### 12. PPE (Personal Protective Equipment)
- Helmets
- Gloves
- Safety Boots

### 13. Lubricants
- Industrial Oil
- Grease

## Extensibility Rules

1. **New Categories**: Top-level categories should only be added when a material clearly does not fall under existing classifications.
2. **Deep Nesting**: The JSON schema allows `subcategories` to contain their own `subcategories`. Use this for highly specific material variants (e.g., `Valves -> Ball Valve -> Trunnion Mounted Ball Valve`).
3. **IDs**: Each node must have a unique identifier (e.g., `CAT-VLV` or `SCAT-VLV-BA`) to ensure resilient database mappings even if the human-readable string is updated.
