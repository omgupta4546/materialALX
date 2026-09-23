import re
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Tuple
from app.ai.base import BaseAIModule

class ExtractedAttribute(BaseModel):
    attribute: str
    value: str
    unit: Optional[str] = None
    confidence: float
    source_span: Optional[Tuple[int, int]] = None
    method: str

class AttributeExtractorConfig(BaseModel):
    extraction_model: str = "mock-extractor-v1"
    confidence_threshold: float = 0.8
    enable_llm_fallback: bool = True

class AttributeExtractorInput(BaseModel):
    normalized_text: str
    category_context: Optional[str] = None

class AttributeExtractorOutput(BaseModel):
    attributes: List[ExtractedAttribute]
    version: str

class AttributeExtractorModule(BaseAIModule[AttributeExtractorInput, AttributeExtractorOutput, AttributeExtractorConfig]):
    @property
    def version(self) -> str:
        return "1.1.0"

    def get_default_config(self) -> AttributeExtractorConfig:
        return AttributeExtractorConfig()

    def process(self, input_data: AttributeExtractorInput) -> AttributeExtractorOutput:
        self.logger.info(f"Extracting attributes from: {input_data.normalized_text} [Category: {input_data.category_context}]")
        
        extracted: List[ExtractedAttribute] = []
        
        cat = input_data.category_context.upper() if input_data.category_context else ""
        
        # 1. Deterministic Extraction based on category or text keywords
        if "BEARING" in cat or "BRG" in input_data.normalized_text:
            extracted.extend(self._extract_bearing(input_data.normalized_text))
        elif "VALVE" in cat or "VALVE" in input_data.normalized_text:
            extracted.extend(self._extract_valve(input_data.normalized_text))
        elif "MOTOR" in cat or "MOTOR" in input_data.normalized_text:
            extracted.extend(self._extract_motor(input_data.normalized_text))
        elif "PIPE" in cat or "PIPE" in input_data.normalized_text:
            extracted.extend(self._extract_pipe(input_data.normalized_text))
                
        # 2. LLM Fallback (stubbed)
        # In a real scenario, we would check which expected attributes are missing
        # and prompt the LLM to extract only those.
        if self.config.enable_llm_fallback:
            llm_attrs = self._fallback_llm_extract(input_data.normalized_text, input_data.category_context, extracted)
            extracted.extend(llm_attrs)
            
        return AttributeExtractorOutput(
            attributes=extracted,
            version=self.version
        )
        
    def _create_attr(self, name: str, match: re.Match, unit: Optional[str] = None, val_idx: int = 1) -> ExtractedAttribute:
        return ExtractedAttribute(
            attribute=name,
            value=match.group(val_idx).strip(),
            unit=unit,
            confidence=0.95,
            source_span=match.span(),
            method="deterministic"
        )

    def _extract_bearing(self, text: str) -> List[ExtractedAttribute]:
        attrs = []
        # Series/Type e.g., 6205, 6309
        m_series = re.search(r'\b(6\d{3}|7\d{3}|NU\d{3}|NJ\d{3})\b', text)
        if m_series:
            attrs.append(self._create_attr("series", m_series))
            
        # Seal e.g., 2RS, ZZ
        m_seal = re.search(r'\b(2RS|ZZ|Z|RS1)\b', text)
        if m_seal:
            attrs.append(self._create_attr("seal", m_seal))
            
        # Dimensions: 25x52x15 MM or 25 X 52 X 15 MM
        m_dim = re.search(r'\b(\d+(?:\.\d+)?)\s*[X\*]\s*(\d+(?:\.\d+)?)\s*[X\*]\s*(\d+(?:\.\d+)?)\s*(MM|IN)?\b', text)
        if m_dim:
            unit = m_dim.group(4) if m_dim.group(4) else None
            attrs.append(ExtractedAttribute(
                attribute="bore", value=m_dim.group(1), unit=unit, confidence=0.9, source_span=m_dim.span(1), method="deterministic"
            ))
            attrs.append(ExtractedAttribute(
                attribute="outer_diameter", value=m_dim.group(2), unit=unit, confidence=0.9, source_span=m_dim.span(2), method="deterministic"
            ))
            attrs.append(ExtractedAttribute(
                attribute="width", value=m_dim.group(3), unit=unit, confidence=0.9, source_span=m_dim.span(3), method="deterministic"
            ))
            
        return attrs

    def _extract_valve(self, text: str) -> List[ExtractedAttribute]:
        attrs = []
        # Type
        m_type = re.search(r'\b(BALL|GATE|GLOBE|CHECK|BUTTERFLY)\b', text)
        if m_type:
            attrs.append(self._create_attr("type", m_type))
            
        # Size
        m_size = re.search(r'\b(\d+(?:\.\d+)?(?:/\d+)?)\s*(IN|MM)\b', text)
        if m_size:
            attrs.append(self._create_attr("size", m_size, unit=m_size.group(2)))
            
        # Pressure class
        m_class = re.search(r'\b(150#|300#|600#|PN16|PN40|CLASS\s*150|CLASS\s*300)(?:\b|\s|$)', text)
        if m_class:
            attrs.append(self._create_attr("pressure_class", m_class))
            
        # Material
        m_mat = re.search(r'\b(CS|SS|STAINLESS STEEL|CARBON STEEL|BRASS|BRONZE)\b', text)
        if m_mat:
            attrs.append(self._create_attr("body_material", m_mat))
            
        return attrs

    def _extract_motor(self, text: str) -> List[ExtractedAttribute]:
        attrs = []
        # Power
        m_power = re.search(r'\b(\d+(?:\.\d+)?)\s*(HP|KW)\b', text)
        if m_power:
            attrs.append(self._create_attr("power", m_power, unit=m_power.group(2)))
            
        # Voltage
        m_volt = re.search(r'\b(\d{3,4})\s*V(?:OLTS?)?\b', text)
        if m_volt:
            attrs.append(self._create_attr("voltage", m_volt, unit="V"))
            
        # Frequency
        m_freq = re.search(r'\b(50|60)\s*HZ\b', text)
        if m_freq:
            attrs.append(self._create_attr("frequency", m_freq, unit="HZ"))
            
        # Phase
        m_phase = re.search(r'\b(1|3)\s*(?:PH|PHASE)\b', text)
        if m_phase:
            attrs.append(self._create_attr("phase", m_phase))
            
        # RPM
        m_rpm = re.search(r'\b(\d{3,4})\s*RPM\b', text)
        if m_rpm:
            attrs.append(self._create_attr("rpm", m_rpm, unit="RPM"))
            
        # Enclosure
        m_enc = re.search(r'\b(TEFC|ODP|TENV)\b', text)
        if m_enc:
            attrs.append(self._create_attr("enclosure", m_enc))
            
        return attrs

    def _extract_pipe(self, text: str) -> List[ExtractedAttribute]:
        attrs = []
        # Diameter
        m_dia = re.search(r'\b(\d+(?:\.\d+)?(?:/\d+)?)\s*(IN|MM)\b', text)
        if m_dia:
            attrs.append(self._create_attr("diameter", m_dia, unit=m_dia.group(2)))
            
        # Schedule
        m_sch = re.search(r'\b(SCH\s*\d+|SCHEDULE\s*\d+)\b', text)
        if m_sch:
            attrs.append(self._create_attr("schedule", m_sch))
            
        # Material
        m_mat = re.search(r'\b(CS|SS|STAINLESS STEEL|CARBON STEEL|PVC|CPVC)\b', text)
        if m_mat:
            attrs.append(self._create_attr("material_grade", m_mat))
            
        return attrs

    def _fallback_llm_extract(self, text: str, category: Optional[str], existing_attrs: List[ExtractedAttribute]) -> List[ExtractedAttribute]:
        """
        Stub for LLM extraction fallback.
        In a real implementation, this would prompt the LLM to find attributes that were missed by regex.
        Never invents missing values.
        """
        # For now, return empty to signify no extra attributes found by the stub LLM.
        return []
