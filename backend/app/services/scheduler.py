import asyncio
import logging
from datetime import datetime
from typing import List

from app.services.ngsi_client import ContextBrokerClient
from app.engines.pv_engine import PVEngine, PVSpec
from app.engines.shadow_engine import ShadowEngine

logger = logging.getLogger(__name__)

class SimulationScheduler:
    """
    Control de Lazo Cerrado (Closed-loop)
    Ejecuta simulaciones en background periódicamente (ej. cada 5 min).
    Revisa los Trackers fotovoltaicos, lee la meteo, calcula el ángulo óptimo (o sombra ideal) 
    y envía comandos via NGSI-LD al array.
    """
    def __init__(self, check_interval_sec: int = 300):
        self.interval = check_interval_sec
        self.is_running = False
        self._task = None
        self.ngsi_client = ContextBrokerClient()
        self.shadow_engine = ShadowEngine()

    async def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"SimulationLoop started. Interval: {self.interval}s")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            
    async def _loop(self):
        while self.is_running:
            try:
                await self.execute_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SimulationLoop: {e}")
            
            await asyncio.sleep(self.interval)

    async def execute_loop(self):
        logger.info("Running scheduled AgriEnergy loop...")
        
        # En NKZ real se debería obtener la lista de tenants suscritos al módulo
        # tenant_ids = await get_active_tenants("agrienergy")
        # Por simplicidad de este esqueleto iteraremos como concepto
        tenant_ids = ["tenant-sandbox"] 
        
        for tenant in tenant_ids:
            # 1. Leer trackers
            trackers = await self.ngsi_client.get_entities_by_type(tenant, "AgriEnergyTracker")
            if not trackers:
                continue
                
            # 2. Leer meteorología actual de la parcela o del worker global
            meteo = await self.ngsi_client.get_entities_by_type(tenant, "WeatherObserved")
            # Extraer GHI, DNI, DHI (mockup safe access)
            ghi = meteo[0].get("ghi", {}).get("value", 0) if meteo else 0
            dni = meteo[0].get("dni", {}).get("value", 0) if meteo else 0
            dhi = meteo[0].get("dhi", {}).get("value", 0) if meteo else 0
            
            # Si es de noche no se mueve a menos que sea a safe_position
            if ghi < 10:
                continue
                
            for tracker in trackers:
                try:
                    # Parse tracker config
                    t_id = tracker.get("id")
                    lat = tracker.get("location", {}).get("value", {}).get("coordinates", [0, 0])[1]
                    lon = tracker.get("location", {}).get("value", {}).get("coordinates", [0, 0])[0]
                    
                    capacity_w = tracker.get("capacity_w", {}).get("value", 1000)
                    panel_w = tracker.get("panel_width", {}).get("value", 2.0)
                    panel_l = tracker.get("panel_length", {}).get("value", 4.0)
                    
                    # Motor FV 
                    pv_engine = PVEngine(lat=lat, lon=lon)
                    
                    # TODO: Lógica de Optimización. 
                    # Buscar qué inclinación (tilt) minimiza el estrés hídrico (Handshake) y maximiza GHI.
                    # Aquí proponemos un target_tilt ideal para máxima GHI en el momento
                    # y lo enviamos al dispositivo.
                    target_tilt = 30.0 # Angulo fijo por defecto
                    
                    # Actualizar objetivo del tracker en NGSI-LD. El modulo `connectivity` lo tomará para MQTt
                    await self.ngsi_client.update_entity_attribute(tenant, t_id, "targetTilt", target_tilt)
                    
                    logger.info(f"TargetTilt for {t_id} updated to {target_tilt}°")
                except Exception as e:
                    logger.error(f"Error processing tracker {tracker.get('id')}: {e}")

# Global scheduler instance
scheduler = SimulationScheduler(check_interval_sec=120)  # Cada 2 minutos (estado SOTA para followers)
