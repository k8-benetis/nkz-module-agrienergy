import pvlib
import pandas as pd
import numpy as np
from datetime import datetime
from pydantic import BaseModel

class PVSpec(BaseModel):
    tilt: float
    azimuth: float
    capacity_w: float
    module_area_m2: float

class PVEngine:
    """
    Motor fotovoltaico basado en pvlib-python.
    Calcula irradiancia y rendimiento teórico.
    """
    def __init__(self, lat: float, lon: float, alt: float = 0):
        self.location = pvlib.location.Location(lat, lon, altitude=alt)
        
    def calculate_expected_power(self, time: datetime, spec: PVSpec, ghi: float, dni: float, dhi: float) -> dict:
        """
        Calcula la potencia esperada (Pexpected) y la irradiancia en el plano de array (POA).
        """
        # Convertir tiempo a DatetimeIndex
        times = pd.DatetimeIndex([time])
        
        # Posición solar exacta
        solar_position = self.location.get_solarposition(times)
        
        # Irradiancia en el plano inclinado del panel (POA)
        poa_irrad = pvlib.irradiance.get_total_irradiance(
            surface_tilt=spec.tilt,
            surface_azimuth=spec.azimuth,
            solar_zenith=solar_position['zenith'],
            solar_azimuth=solar_position['azimuth'],
            dni=dni,
            ghi=ghi,
            dhi=dhi
        )
        
        poa_global = poa_irrad['poa_global'].iloc[0]
        
        # Estimación muy básica de potencia: (Irradiancia / 1000) * Capacidad
        # Asumiendo STC (1000 W/m2)
        power_w = (poa_global / 1000.0) * spec.capacity_w if poa_global > 0 else 0.0
        
        return {
            "solar_elevation": solar_position['elevation'].iloc[0],
            "solar_azimuth": solar_position['azimuth'].iloc[0],
            "poa_global": poa_global,
            "expected_power_w": power_w
        }
