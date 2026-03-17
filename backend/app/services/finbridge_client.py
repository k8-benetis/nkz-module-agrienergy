import httpx
import logging
from typing import Dict, Any, List
from datetime import datetime
from app.config import get_settings

logger = logging.getLogger(__name__)

class FinBridgeEmitter:
    """
    Cliente para emitir eventos de liquidación y agregación energética a N8N / Odoo
    (Comunidades Energéticas).
    """

    def __init__(self):
        self.settings = get_settings()
        self.webhook_url = (
            getattr(self.settings, "agrienergy_n8n_webhook_url", None) or ""
        ).strip() or "http://n8n-webhook-service:5678/webhook/agrienergy-aggregation"

    async def emit_daily_aggregation(self, tenant_id: str, tracker_id: str, generation_wh: float, consumption_wh: float = 0.0):
        """
        Emite el balance MWh y el estrés diario del panel.
        Este evento asienta en las cuentas analíticas en el módulo Odoo.
        """
        
        payload = {
            "tenant_id": tenant_id,
            "tracker_id": tracker_id,
            "date": datetime.utcnow().date().isoformat(),
            "generation_wh": generation_wh,
            "consumption_wh": consumption_wh,
            "surplus_wh": generation_wh - consumption_wh,
            "module": "agrienergy"
        }
        
        try:
             async with httpx.AsyncClient(timeout=10.0) as client:
                 res = await client.post(
                     self.webhook_url,
                     json=payload
                 )
                 if res.status_code >= 400:
                    logger.warning(f"Failed to post aggregation. Code: {res.status_code}")
                 else:
                    logger.debug(f"Emitted financial aggregation for {tracker_id}: {generation_wh}Wh")

        except Exception as e:
            logger.error(f"Error emitting aggregation event to bridge: {e}")
