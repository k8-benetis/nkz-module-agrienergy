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
import asyncio

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
    
    for entity in payload.data:
        entity_id = entity.get("id")
        entity_type = entity.get("type")
        
        logger.info(f"Processing entity {entity_id} of type {entity_type}")
        
        if entity_type == "WeatherObserved":
            # Si cambia el clima, buscar todos los trackers de este tenant y evaluarlos
            # TODO: implementar lógica de busqueda de todos los trackers y actualizarlos
            pass
            
        elif entity_type == "AgriEnergyTracker":
            # Si cambia el estado interno del tracker, evaluar este en concreto
            # TODO: implementar lógica de cálculo individual
            pass
            
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
