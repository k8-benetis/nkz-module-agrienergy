import httpx
import logging
from typing import Dict, Any, List
from app.config import get_settings

logger = logging.getLogger(__name__)

class ContextBrokerClient:
    """
    Cliente para interactuar con FIWARE Orion-LD (Context Broker).
    """
    def __init__(self):
        self.settings = get_settings()
        # En la arquitectura NKZ, el entity-manager o el api-gateway expone las rutas.
        # Directo a Orion suele ser http://orion-ld:1026/ngsi-ld/v1
        # Por seguridad y multitenancy usamos el entity-manager interno.
        self.base_url = "http://entity-manager-service:5000/api/entities"

    async def get_entities_by_type(self, tenant_id: str, entity_type: str) -> List[Dict[str, Any]]:
        headers = {
            "Fiware-Service": tenant_id
        }
        try:
            # Query the manager
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}?type={entity_type}",
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching entities from Orion-LD: {e}")
            return []

    async def update_entity_attribute(self, tenant_id: str, entity_id: str, attr_name: str, value: Any) -> bool:
        headers = {
            "Fiware-Service": tenant_id,
            "Content-Type": "application/json"
            # Importante: Como se definió en CLAUDE.md, application/json requiere el Link header en FIWARE
            # o bien pasarlo por el entity-manager que ya solventa eso. Asumiendo entity-manager.
        }
        
        payload = {
            attr_name: {
                "type": "Property",
                "value": value
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # NGSI-LD partial attribute update format
                response = await client.post(
                    f"{self.base_url}/{entity_id}/attrs",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error updating entity {entity_id}: {e}")
            return False
