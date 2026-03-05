from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AgriParcelSpec(BaseModel):
    id: str
    slope: float = Field(default=0.0, description="Pendiente media en grados")
    aspect: float = Field(default=180.0, description="Orientación en grados (180=Sur)")

class TrackerSpec(BaseModel):
    id: str
    panel_width: float
    panel_length: float
    capacity_w: float
    min_tilt: float = -60.0
    max_tilt: float = 60.0
    lat: float
    lon: float
    parent_parcel_id: str

class TelemetryInput(BaseModel):
    timestamp: str
    ghi: float
    dni: float
    dhi: float
    actual_tilt: float
    actual_azimuth: float

class SimulationRequest(BaseModel):
    tracker: TrackerSpec
    parcel: AgriParcelSpec
    telemetry: TelemetryInput
    target_tilt: float 

class SimulationResponse(BaseModel):
    expected_power_w: float
    shadow_area_m2: float
    shadow_polygon_2d: List[tuple]
