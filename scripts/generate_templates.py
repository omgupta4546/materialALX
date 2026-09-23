import json
import os

templates = {
    "bearing": {
        "category": "CAT-BRG",
        "name": "Bearing",
        "attributes": [
            {"name": "bore", "valid_units": ["mm", "inch"], "value_range": {"min": 3, "max": 1500}},
            {"name": "outer_diameter", "valid_units": ["mm", "inch"], "value_range": {"min": 10, "max": 2000}},
            {"name": "width", "valid_units": ["mm", "inch"], "value_range": {"min": 4, "max": 500}},
            {"name": "seal_type", "valid_values": ["Open", "Z", "ZZ", "RS", "2RS", "NR"]}
        ],
        "manufacturers": ["SKF", "FAG", "Timken", "NSK", "NTN"],
        "part_number_structure": "[SeriesCode][BoreCode][Suffix(Seals/Clearance)] (e.g. 6204-2RS1/C3)"
    },
    "valve": {
        "category": "CAT-VLV",
        "name": "Valve",
        "attributes": [
            {"name": "size", "valid_units": ["inch", "mm"], "value_range": {"min": 0.25, "max": 72}},
            {"name": "pressure_class", "valid_values": ["150#", "300#", "600#", "900#", "1500#", "2500#", "PN16", "PN40"]},
            {"name": "body_material", "valid_values": ["WCB", "LCC", "CF8M", "A105", "Ductile Iron", "Bronze"]},
            {"name": "end_connection", "valid_values": ["Flanged", "Threaded", "Socket Weld", "Butt Weld", "Wafer", "Lug"]}
        ],
        "manufacturers": ["Emerson", "Flowserve", "Velan", "Crane", "KITZ"],
        "part_number_structure": "[Size]-[Class]-[Type]-[BodyMat]-[TrimMat]-[Ends]"
    },
    "motor": {
        "category": "CAT-MTR",
        "name": "Motor",
        "attributes": [
            {"name": "power", "valid_units": ["kW", "HP"], "value_range": {"min": 0.1, "max": 10000}},
            {"name": "voltage", "valid_units": ["V", "KV"], "value_range": {"min": 110, "max": 11000}},
            {"name": "frequency", "valid_units": ["HZ"], "valid_values": [50, 60]},
            {"name": "rpm", "valid_units": ["RPM"], "valid_values": [750, 1000, 1500, 3000, 900, 1200, 1800, 3600]},
            {"name": "enclosure", "valid_values": ["TEFC", "ODP", "TENV", "Explosion Proof"]}
        ],
        "manufacturers": ["Siemens", "ABB", "WEG", "Crompton Greaves", "Baldor"],
        "part_number_structure": "[FrameSize]-[Poles]-[Power]-[VoltageCode]-[Enclosure]"
    },
    "pipe": {
        "category": "CAT-PIP",
        "name": "Pipe",
        "attributes": [
            {"name": "diameter", "valid_units": ["inch", "mm"], "value_range": {"min": 0.5, "max": 120}},
            {"name": "schedule", "valid_values": ["SCH10", "SCH40", "SCH80", "SCH160", "STD", "XS", "XXS"]},
            {"name": "material_grade", "valid_values": ["API 5L X52", "ASTM A106 Gr B", "ASTM A312 TP316L", "ASTM A333 Gr 6"]},
            {"name": "length", "valid_units": ["M", "FT"], "value_range": {"min": 6, "max": 12}}
        ],
        "manufacturers": ["Tenaris", "Jindal SAW", "ArcelorMittal", "Nippon Steel", "Vallourec"],
        "part_number_structure": "[Type]-[Size]-[Schedule]-[Material]-[Length]"
    },
    "pump": {
        "category": "CAT-PMP",
        "name": "Pump",
        "attributes": [
            {"name": "flow_rate", "valid_units": ["m3/h", "GPM"], "value_range": {"min": 1, "max": 20000}},
            {"name": "head", "valid_units": ["M", "FT"], "value_range": {"min": 5, "max": 3000}},
            {"name": "power", "valid_units": ["KW", "HP"], "value_range": {"min": 0.5, "max": 5000}}
        ],
        "manufacturers": ["KSB", "Flowserve", "Sulzer", "Grundfos", "ITT Goulds"],
        "part_number_structure": "[ModelFamily]-[Size]-[ImpellerDia]-[MaterialCode]"
    },
    "flange": {
        "category": "CAT-FLG",
        "name": "Flange",
        "attributes": [
            {"name": "size", "valid_units": ["inch", "mm"], "value_range": {"min": 0.5, "max": 72}},
            {"name": "pressure_class", "valid_values": ["150#", "300#", "600#", "900#", "1500#", "2500#"]},
            {"name": "flange_type", "valid_values": ["Weld Neck", "Slip-On", "Blind", "Socket Weld", "Threaded", "Lap Joint"]},
            {"name": "facing", "valid_values": ["Raised Face (RF)", "Flat Face (FF)", "Ring Type Joint (RTJ)"]}
        ],
        "manufacturers": ["Ulma", "Melesi", "Galperti", "CHW Forge"],
        "part_number_structure": "[Size]-[Class]-[Type]-[Facing]-[Material]"
    },
    "gasket": {
        "category": "CAT-GSK",
        "name": "Gasket",
        "attributes": [
            {"name": "size", "valid_units": ["inch", "mm"], "value_range": {"min": 0.5, "max": 72}},
            {"name": "pressure_class", "valid_values": ["150#", "300#", "600#", "900#", "1500#", "2500#"]},
            {"name": "gasket_type", "valid_values": ["Spiral Wound", "CNAF", "PTFE", "RTJ", "Corrugated Metal"]},
            {"name": "material", "valid_values": ["Graphite/SS316", "PTFE", "Soft Iron", "SS304"]}
        ],
        "manufacturers": ["Flexitallic", "Garlock", "Klinger", "Lamons"],
        "part_number_structure": "[Type]-[Size]-[Class]-[WindingMat]-[FillerMat]-[RingMat]"
    },
    "fastener": {
        "category": "CAT-FST",
        "name": "Fastener",
        "attributes": [
            {"name": "diameter", "valid_units": ["mm", "inch"], "value_range": {"min": 2, "max": 100}},
            {"name": "length", "valid_units": ["mm", "inch"], "value_range": {"min": 5, "max": 500}},
            {"name": "grade", "valid_values": ["8.8", "10.9", "12.9", "A2-70", "A4-80", "B7", "L7"]},
            {"name": "thread_type", "valid_values": ["Metric Coarse", "Metric Fine", "UNC", "UNF"]}
        ],
        "manufacturers": ["Hilti", "Würth", "Bossard", "Kamax"],
        "part_number_structure": "[Type]-[Dia]x[Length]-[Grade]-[Finish]"
    },
    "cable": {
        "category": "CAT-CBL",
        "name": "Cable",
        "attributes": [
            {"name": "cores", "valid_units": ["EACH"], "value_range": {"min": 1, "max": 100}},
            {"name": "cross_section", "valid_units": ["mm2", "AWG"], "value_range": {"min": 0.5, "max": 1000}},
            {"name": "voltage_grade", "valid_values": ["1.1KV", "3.3KV", "11KV", "33KV", "66KV"]},
            {"name": "insulation", "valid_values": ["PVC", "XLPE", "EPR", "Rubber"]}
        ],
        "manufacturers": ["Prysmian", "Nexans", "Polycab", "LAPP", "Havells"],
        "part_number_structure": "[Cores]C x [Size] sqmm [Insulation]/[Sheath] [Voltage]"
    },
    "electrical_component": {
        "category": "CAT-ELC",
        "name": "Electrical Component",
        "attributes": [
            {"name": "current_rating", "valid_units": ["A", "KA"], "value_range": {"min": 0.1, "max": 6300}},
            {"name": "voltage_rating", "valid_units": ["V", "KV"], "value_range": {"min": 12, "max": 800000}},
            {"name": "poles", "valid_values": ["1P", "2P", "3P", "4P"]},
            {"name": "breaking_capacity", "valid_units": ["KA"], "value_range": {"min": 10, "max": 150}}
        ],
        "manufacturers": ["Schneider Electric", "ABB", "Siemens", "Eaton"],
        "part_number_structure": "[Family]-[Rating]-[Poles]-[Curve/Type]"
    },
    "instrumentation": {
        "category": "CAT-INS",
        "name": "Instrumentation",
        "attributes": [
            {"name": "measurement_range", "valid_units": ["BAR", "PSI", "degC", "degF"], "value_range": {"min": -200, "max": 10000}},
            {"name": "output_signal", "valid_values": ["4-20mA", "HART", "Profibus", "Modbus", "0-10V"]},
            {"name": "process_connection", "valid_values": ["1/2 NPT", "1/4 NPT", "Flanged 2 inch", "Sanitary"]},
            {"name": "accuracy", "valid_values": ["0.1%", "0.25%", "0.5%", "1.0%"]}
        ],
        "manufacturers": ["Rosemount", "Endress+Hauser", "Yokogawa", "WIKA", "Honeywell"],
        "part_number_structure": "[ModelCode]-[RangeCode]-[OutputCode]-[ConnectionCode]-[Options]"
    },
    "ppe": {
        "category": "CAT-PPE",
        "name": "PPE",
        "attributes": [
            {"name": "size", "valid_values": ["S", "M", "L", "XL", "XXL", "7", "8", "9", "10", "11"]},
            {"name": "material", "valid_values": ["Nitrile", "Leather", "Kevlar", "Polycarbonate", "HDPE"]},
            {"name": "certification", "valid_values": ["CE", "ANSI", "EN 388", "EN 397"]},
            {"name": "color", "valid_values": ["Yellow", "White", "Blue", "Red", "Hi-Vis"]}
        ],
        "manufacturers": ["3M", "Honeywell", "MSA Safety", "Ansell", "DuPont"],
        "part_number_structure": "[ProductFamily]-[Model]-[Size]-[Color]"
    },
    "lubricant": {
        "category": "CAT-LUB",
        "name": "Lubricant",
        "attributes": [
            {"name": "viscosity_grade", "valid_values": ["ISO VG 32", "ISO VG 46", "ISO VG 68", "ISO VG 220", "SAE 10W-40"]},
            {"name": "base_oil", "valid_values": ["Mineral", "Synthetic (PAO)", "PAG", "Ester", "Silicone"]},
            {"name": "nlgi_grade", "valid_values": ["NLGI 0", "NLGI 1", "NLGI 2", "NLGI 3"]},
            {"name": "container_size", "valid_units": ["L", "KG"], "value_range": {"min": 1, "max": 1000}}
        ],
        "manufacturers": ["Shell", "Mobil", "Castrol", "TotalEnergies", "Klüber"],
        "part_number_structure": "[BrandName] [ProductLine] [Viscosity/NLGI] - [ContainerSize]"
    }
}

os.makedirs('data/templates', exist_ok=True)
for key, data in templates.items():
    with open(f"data/templates/{key}.json", "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)

print("Generated all 13 industrial material templates successfully in data/templates/")
