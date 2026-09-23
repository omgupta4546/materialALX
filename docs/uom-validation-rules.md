# Unit of Measure (UOM) Validation Rules

This document outlines the validation and conversion rules for processing Unit of Measure (UOM) data ingested from diverse CPSE legacy systems.

The master reference JSON is located in `data/reference/uom_master.json`.

## 1. Dimensional Constraint Rule
**Rule**: Conversions are strictly isolated to units within the same `dimension`.
- **Valid**: `LENGTH` to `LENGTH` (e.g., IN → MM)
- **Invalid**: `MASS` to `LENGTH` (e.g., KG → MM)
- **Action**: Any attempt to convert across dimensions throws a `CrossDimensionalConversionException`.

## 2. Alias Normalization Rule
**Rule**: Incoming UOM strings must be aggressively normalized to canonical codes before any processing.
- **Action**: Convert strings to uppercase and strip trailing/leading whitespace. Check against the `aliases` arrays in `uom_master.json`.
- **Example**: If a source system provides "Pcs", "pcs.", or "NOS", the system automatically normalizes this to the canonical count unit `EACH`.

## 3. Mathematical Conversion Rule
**Rule**: To convert Unit A to Unit B within the same dimension, route through the canonical base unit to prevent cascading precision loss.

**Formula**:
1. Convert Source to Canonical: `Canonical_Value = Source_Value * Multiplier_A`
2. Convert Canonical to Target: `Target_Value = Canonical_Value / Multiplier_B`

**Examples**:
- **IN → MM**
  - Canonical Unit: `MM`
  - `1 IN = 25.4 MM` (Multiplier: 25.4)
  - Formula: `1 * 25.4 = 25.4 MM`
  
- **MT → KG**
  - Canonical Unit: `KG`
  - `1 MT = 1000 KG` (Multiplier: 1000)
  - Formula: `1 * 1000 = 1000 KG`

- **HP → KW**
  - Canonical Unit: `KW`
  - `1 HP = 0.7457 KW` (Multiplier: 0.7457)
  - Formula: `1 * 0.7457 = 0.7457 KW`

## 4. Unknown Unit Rule
**Rule**: If a UOM is not present in the master reference or alias lists.
- **Action**: Do not attempt to guess or map the unit algorithmically. The material record must be flagged with `UOM_UNRECOGNIZED` and routed to a human data steward for engineering review or for the UOM to be added to the master reference.
