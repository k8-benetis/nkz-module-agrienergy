import numpy as np
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate, scale

class ShadowEngine:
    """
    Motor de geometría vectorial 2.5D.
    Proyecta las sombras de los paneles sobre un terreno inclinado.
    """
    
    @staticmethod
    def _rotation_matrix_z(angle_deg):
        theta = np.radians(angle_deg)
        c, s = np.cos(theta), np.sin(theta)
        return np.array([
            [c, -s, 0],
            [s, c, 0],
            [0, 0, 1]
        ])

    @staticmethod
    def _rotation_matrix_x(angle_deg):
        theta = np.radians(angle_deg)
        c, s = np.cos(theta), np.sin(theta)
        return np.array([
            [1, 0, 0],
            [0, c, -s],
            [0, s, c]
        ])

    def calculate_shadow_polygon(self, 
                                 panel_width: float, 
                                 panel_length: float, 
                                 panel_tilt: float, 
                                 panel_azimuth: float, 
                                 solar_elevation: float, 
                                 solar_azimuth: float,
                                 terrain_slope: float = 0.0,
                                 terrain_aspect: float = 180.0) -> dict:
        """
        Calcula el polígono de sombra proyectado en un plano 2.5D.
        Devuelve el área y las coordenadas relativas.
        """
        if solar_elevation <= 0:
            return {"area_m2": 0.0, "polygon": []}
            
        # 1. Definir panel como rectángulo horizontal centrado en el origen (Z=1m de altura base por ejemplo)
        # Asumimos eje de rotación en el centro
        w2 = panel_width / 2
        l2 = panel_length / 2
        
        # Vértices locales (X, Y, Z)
        vertices = np.array([
            [-w2, -l2, 0],
            [w2, -l2, 0],
            [w2, l2, 0],
            [-w2, l2, 0]
        ])
        
        # 2. Rotación del panel (Tilt en X, Azimuth en Z)
        # Asumiendo Azimuth 0 = Norte, 90 = Este (estándar). 
        # Cuidado con las convenciones: pvlib suele usar Norte=0. 
        # Aquí rotamos Y hacia abajo (inclinación) y luego rotamos en el plano XY
        R_tilt = self._rotation_matrix_x(panel_tilt)
        # Ajuste de azimut (180 es Sur en pvlib)
        R_az = self._rotation_matrix_z(180 - panel_azimuth) 
        
        vertices_rotated = (R_az @ (R_tilt @ vertices.T)).T
        
        # Añadir altura base al poste geométrico para proyección
        vertices_rotated[:, 2] += 2.0 # Poste de 2m de altura

        # 3. Vector solar
        el_rad = np.radians(solar_elevation)
        az_rad = np.radians(180 - solar_azimuth) # Invertir para vector incidente
        
        sz = np.sin(el_rad)
        sy = np.cos(el_rad) * np.cos(az_rad)
        sx = np.cos(el_rad) * np.sin(az_rad)
        
        sun_vector = np.array([sx, sy, sz])
        
        # 4. Proyección sobre terreno 2.5D
        # Si el terreno tiene pendiente, el vector normal Z no es (0,0,1)
        # Normal del terreno:
        slope_rad = np.radians(terrain_slope)
        aspect_rad = np.radians(180 - terrain_aspect)
        
        nx = np.sin(slope_rad) * np.sin(aspect_rad)
        ny = np.sin(slope_rad) * np.cos(aspect_rad)
        nz = np.cos(slope_rad)
        terrain_normal = np.array([nx, ny, nz])
        
        # Proyección de cada vértice al plano del terreno por el vector solar
        projected = []
        for v in vertices_rotated:
            # t = (N·P - N·V) / (N·S) donde P=(0,0,0) (origen del plano topográfico local)
            dot_ns = np.dot(terrain_normal, sun_vector)
            if dot_ns >= 0:
                continue # El panel está debajo del terreno (imposible) o el sol no incide sobre el terreno
                
            t = -np.dot(terrain_normal, v) / dot_ns
            p_proj = v + t * sun_vector
            projected.append(p_proj[:2]) # 2D en el plano topográfico

        if len(projected) < 3:
             return {"area_m2": 0.0, "polygon": []}
             
        # Crear polígono 2D plano (Shapely)
        poly = Polygon(projected).convex_hull
        
        return {
            "area_m2": poly.area,
            "polygon": list(poly.exterior.coords)
        }
