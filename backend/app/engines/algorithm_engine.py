from typing import Dict, Any, Optional
import logging
from json_logic import jsonLogic

logger = logging.getLogger(__name__)

class AlgorithmEngine:
    """
    Motor de Evaluación de Algoritmos Autónomo.
    Permite inyectar reglas en formato JSON Logic para controlar dinámicamente el Tracker.
    """
    
    @staticmethod
    def evaluate_rule(logic: Dict[str, Any], context: Dict[str, Any]) -> Optional[float]:
        """
        Evalúa una regla JSON-Logic dado un contexto de variables (telemetría + biología).
        Retorna el `targetTilt` resultante si la lógica devuelve un número, 
        de lo contrario retorna None.
        """
        try:
            result = jsonLogic(logic, context)
            if isinstance(result, (int, float)) and not isinstance(result, bool):
                 return float(result)
            elif result is None or isinstance(result, bool):
                 logger.debug(f"JSON Logic computed {result}, not applying targetTilt offset")
                 return None
            return float(result)
        except Exception as e:
            logger.error(f"Failed to evaluate JSON Logic rule: {e}")
            return None
        
    @staticmethod
    def default_algorithm() -> Dict[str, Any]:
        """
        Ejemplo de la regla por defecto para maximizar el tracker:
        Si GHI > 10, poner Tilt = 0 (horizontal), sino -60 (standby)
        """
        return {
            "if": [
                {">": [{"var": "weather.ghi"}, 10]},
                0,    # Tilt = 0
                -60   # Tilt = -60
            ]
        }
