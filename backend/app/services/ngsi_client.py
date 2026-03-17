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

    async def get_entity(self, tenant_id: str, entity_id: str) -> Dict[str, Any] | None:
        """Fetch a single entity by id. Returns None if not found or on error."""
        import urllib.parse
        headers = {"Fiware-Service": tenant_id}
        try:
            encoded_id = urllib.parse.quote(entity_id, safe="")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/{encoded_id}",
                    headers=headers,
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching entity {entity_id}: {e}")
            return None

    async def update_entity_attribute(self, tenant_id: str, entity_id: str, attr_name: str, value: Any) -> bool:
        headers = {
            "Fiware-Service": tenant_id,
            "Content-Type": "application/json",
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

    async def create_entity(self, tenant_id: str, entity: dict) -> bool:
        """
        Create an NGSI-LD entity in Orion (POST /ngsi-ld/v1/entities).
        Requires context_broker_url to be set. Returns True on 201/200.
        """
        base = (self.settings.context_broker_url or "").rstrip("/")
        if not base:
            logger.warning("context_broker_url not set; cannot create entity")
            return False
        url = f"{base}/entities"
        headers = {
            "Content-Type": "application/ld+json",
            "Fiware-Service": tenant_id,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=entity, headers=headers)
                if response.status_code in (200, 201):
                    return True
                logger.error(
                    "Create entity failed: %s %s",
                    response.status_code,
                    response.text[:200],
                )
                return False
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return False
