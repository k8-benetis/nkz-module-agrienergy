"""
AgriEnergy Orchestrator Backend - API Routes

Example CRUD routes demonstrating SDK/platform patterns.
Replace with your module's actual functionality.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from pydantic import BaseModel, Field
from app.middleware import TokenPayload, get_current_user, get_tenant_id, require_roles
from app.models import SimulationRequest, SimulationResponse
from app.engines.pv_engine import PVEngine, PVSpec
from app.engines.shadow_engine import ShadowEngine
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AgriEnergy Orchestrator"])


from app.models.ngsi import NGSILDSubscriptionPayload
from app.services.ngsi_client import ContextBrokerClient
from app.services.intelligence_client import IntelligenceClient
from app.engines.algorithm_engine import AlgorithmEngine
from app.engines.pv_engine import PVEngine, PVSpec
from app.engines.shadow_engine import ShadowEngine
import asyncio
from datetime import datetime

@router.post("/notify", status_code=status.HTTP_200_OK)
async def process_ngsild_notification(
    payload: NGSILDSubscriptionPayload,
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Webhook para recibir notificaciones (suscripciones) de Orion-LD.
    Se dispara cuando cambian entidades observadas como WeatherObserved o AgriEnergyTracker.
    """
    logger.info(f"Received NGSI-LD notification for subscription {payload.subscriptionId}")
    
    ngsi_client = ContextBrokerClient()
    intelligence_client = IntelligenceClient()
    shadow_engine = ShadowEngine()
    
    for entity in payload.data:
        entity_id = entity.get("id")
        entity_type = entity.get("type", "")
        
        logger.info(f"Processing entity {entity_id} of type {entity_type}")
        
        # 1. Extraer clima del evento si es WeatherObserved (idealmente usaríamos el evento para extraer valores)
        ghi = 800.0  # Placeholder si el evento no lo trae directamente
        dni = 600.0
        dhi = 200.0
        if entity_type == "WeatherObserved":
            if "illuminance" in entity:
                ghi = float(entity["illuminance"].get("value", ghi))
            elif "solarRadiation" in entity:
                 ghi = float(entity["solarRadiation"].get("value", ghi))
                 
            # Buscamos los trackers afectados y recalculamos (Lazo cerrado Reactivo)
            trackers = await ngsi_client.get_entities_by_type(tenant_id, "AgriEnergyTracker")
        elif entity_type == "AgriEnergyTracker":
            trackers = [entity] # El propio entity es el tracker
        else:
            continue
            
        # 2. Bucle de Evaluación
        for tracker in trackers:
            tracker_id = tracker.get("id")
            parcel_id = tracker.get("refAgriParcel", {}).get("object", "urn:ngsi-ld:AgriParcel:Default")
            
            # Parametría del panel (valores por defecto seguros si falta config)
            p_width = float(tracker.get("width", {}).get("value", 2.0))
            p_length = float(tracker.get("length", {}).get("value", 4.0))
            p_cap = float(tracker.get("capacityW", {}).get("value", 500.0))
            p_tilt = float(tracker.get("tilt", {}).get("value", 0.0))
            p_azimuth = float(tracker.get("azimuth", {}).get("value", 180.0))
            lat = float(tracker.get("location", {}).get("value", {}).get("coordinates", [43.0, -2.0])[1])
            lon = float(tracker.get("location", {}).get("value", {}).get("coordinates", [43.0, -2.0])[0])
            
            # 3. Algorithm Engine: Evaluar JSON Logic si lo hay
            context = {
                "weather": {"ghi": ghi, "dni": dni},
                "tracker": {"tilt": p_tilt, "azimuth": p_azimuth}
            }
            active_algo = tracker.get("activeAlgorithm", {}).get("value", AlgorithmEngine.default_algorithm())
            new_target_tilt = AlgorithmEngine.evaluate_rule(active_algo, context)
            
            if new_target_tilt is None:
                new_target_tilt = p_tilt # Mantener actual si no hay decisión
            
            # 4. Digital Twin Simulation: ¿Cuál será la radiación y sombra si aplico esto?
            # Evaluamos la posición solar actual real (vía PV Engine location)
            pv_engine = PVEngine(lat, lon)
            sim_time = datetime.utcnow()
            spec = PVSpec(tilt=new_target_tilt, azimuth=p_azimuth, capacity_w=p_cap, module_area_m2=p_width*p_length)
            
            pv_res = pv_engine.calculate_expected_power(sim_time, spec, ghi, dni, dhi)
            
            shadow_res = shadow_engine.calculate_shadow_polygon(
                panel_width=p_width, panel_length=p_length,
                panel_tilt=new_target_tilt, panel_azimuth=p_azimuth,
                solar_elevation=pv_res["solar_elevation"],
                solar_azimuth=pv_res["solar_azimuth"]
            )
            
            # 5. Biological Handshake (Llamar a NKZ-Intelligence)
            stress_index = await intelligence_client.evaluate_hydric_stress(
                tenant_id=tenant_id,
                parcel_id=parcel_id,
                shadow_polygon=shadow_res["polygon"],
                current_soil_moisture=0.3 # default baseline
            )
            
            logger.info(f"Tracker {tracker_id}: Simulated Target Tilt={new_target_tilt}º -> Shadow={shadow_res['area_m2']:.2f}m2 -> Stress={stress_index:.2f}")
            
            # 6. Actualizar Context Broker con la orden
            await ngsi_client.update_entity_attribute(tenant_id, tracker_id, "targetTilt", new_target_tilt)
            
    return {"status": "processed", "entities": len(payload.data)}


# =============================================================================
# Admin Routes (Role-Protected)
# =============================================================================

@router.get("/admin/stats")
async def get_stats(
    user: TokenPayload = Depends(require_roles("TenantAdmin", "PlatformAdmin")),
):
    """
    Get module statistics.
    
    Requires TenantAdmin or PlatformAdmin role.
    """
    total_tenants = len(_data_store)
    total_items = sum(len(store) for store in _data_store.values())
    
    return {
        "total_tenants": total_tenants,
        "total_items": total_items,
        "user": user.email,
    }
