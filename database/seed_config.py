from pydantic import BaseModel

class SeedConfig(BaseModel):
    reference_dir: str = "data/reference"
    synthetic_dir: str = "data/synthetic"
    demo_dir: str = "data/demo"

    cpse_file: str = "cpse.json"
    classification_file: str = "classification.json"
    uom_file: str = "uom_master.json"
    synonym_file: str = "synonyms.json"
    critical_rules_file: str = "critical_rules.json"
    attribute_definitions_dir: str = "data/templates"

    def get_ref_path(self, filename: str) -> str:
        return f"{self.reference_dir}/{filename}"

    def get_data_path(self, filename: str, is_demo: bool) -> str:
        base = self.demo_dir if is_demo else self.synthetic_dir
        return f"{base}/{filename}"
