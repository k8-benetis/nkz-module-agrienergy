import httpx
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class IntelligenceClient:
    """
    Cliente API interno para invocar endpoints del módulo `NKZ-Intelligence`
    (o `NKZ-BioOrchestrator`) y resolver la evaluación biológica y estrés hídrico.
    """
    
    def __init__(self):
        # En k8s local: http://intelligence-backend:8000
        # Gateway: http://api-gateway:8080/api/intelligence
        self.base_url = "http://api-gateway:8080/api/intelligence"
        
    async def evaluate_hydric_stress(self, tenant_id: str, parcel_id: str, shadow_polygon: List[tuple], current_soil_moisture: float) -> float:
        """
        Ejecuta el Handshake Biológico. Interroga al módulo de inteligencia biológica
        para conocer el estrés hídrico proyectado en base a la sombra que generará
        el panel en la coordenada indicada de la parcela agrícola.
        """
        headers = {
            "Fiware-Service": tenant_id
        }
        
        payload = {
            "parcel_id": parcel_id,
            "soil_moisture": current_soil_moisture,
            "shadow_projection": shadow_polygon
        }
        
        try:
             async with httpx.AsyncClient(timeout=15.0) as client:
                 res = await client.post(
                     f"{self.base_url}/evaluate-stress",
                     json=payload,
                     headers=headers
                 )
                 
                 if res.status_code == 200:
                     return res.json().get("stress_index", 0.0)
                 return 0.0 # Valor conservador en caso de error
                 
        except Exception as e:
            logger.error(f"Biological Handshake failed for {parcel_id}: {e}")
            return 0.0
