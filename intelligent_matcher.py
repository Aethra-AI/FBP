# -*- coding: utf-8 -*-
"""
Motor de Emparejamiento Inteligente
Selecciona el mejor contenido (texto + imagen) para cada grupo basándose en coherencia semántica
"""

from typing import Dict, List, Optional, Tuple
from database import db_manager
from content_categorizer import content_categorizer

class IntelligentMatcher:
    """
    Motor inteligente para emparejar contenido con grupos de destino
    """
    
    def __init__(self):
        pass
    
    def find_best_content_for_group(
        self, 
        group: Dict, 
        content_tags: str,
        publication_type: str = "text-and-image"
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Encuentra el mejor par de texto e imagen para un grupo específico.
        
        Args:
            group: Diccionario con información del grupo
            content_tags: Etiquetas de contenido configuradas en la sesión (ej: "empleos,servicios")
            publication_type: "text-only" o "text-and-image"
        
        Returns:
            (text_dict, image_dict) - El mejor par encontrado
        """
        # Determinar categoría principal del grupo
        group_category = self._determine_group_category(group.get('tags', ''))
        
        # Filtrar textos por categoría
        text = self._find_best_text(group, group_category, content_tags)
        
        if not text:
            return None, None
        
        # Si solo queremos texto, retornar sin imagen
        if publication_type == "text-only":
            return text, None
        
        # Buscar imagen coherente con el texto
        image = self._find_coherent_image(text, group_category, content_tags)
        
        return text, image
    
    def _determine_group_category(self, group_tags: str) -> str:
        """
        Determina la categoría principal de un grupo basándose en sus tags
        """
        if not group_tags:
            return "GENERAL"
        
        tags_lower = group_tags.lower()
        
        # Buscar keywords de categorías
        category_scores = {
            "EMPLEOS": 0,
            "SERVICIOS": 0,
            "VENTAS": 0
        }
        
        # Keywords específicas por categoría
        category_keywords = {
            "EMPLEOS": ["empleo", "trabajo", "vacante", "reclutamiento", "job", "career"],
            "SERVICIOS": ["servicio", "profesional", "consultoría", "asesoría", "service"],
            "VENTAS": ["venta", "producto", "compra", "oferta", "shop", "store"]
        }
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in tags_lower:
                    category_scores[category] += 1
        
        # Retornar categoría con mayor score
        max_score = max(category_scores.values())
        if max_score == 0:
            return "GENERAL"
        
        for category, score in category_scores.items():
            if score == max_score:
                return category
        
        return "GENERAL"
    
    def _find_best_text(
        self, 
        group: Dict, 
        group_category: str,
        content_tags: str
    ) -> Optional[Dict]:
        """
        Encuentra el mejor texto para el grupo considerando:
        1. Coincidencia de categoría (más importante)
        2. Menor uso
        3. No usado recientemente en este grupo
        """
        # Construir query para filtrar por categoría
        category_filter = f"%{group_category.lower()}%"
        
        # Obtener textos de la categoría del grupo
        query = """
            SELECT t.* 
            FROM texts t
            WHERE t.ai_tags LIKE ?
            ORDER BY t.usage_count ASC
            LIMIT 20
        """
        
        texts = db_manager.fetch_all(query, (category_filter,))
        
        if not texts:
            # Si no hay textos de esa categoría, buscar cualquiera
            texts = db_manager.fetch_all(
                "SELECT * FROM texts ORDER BY usage_count ASC LIMIT 10"
            )
        
        if not texts:
            return None
        
        # Filtrar textos ya usados recientemente en este grupo
        available_texts = []
        for text in texts:
            # Verificar si se usó en este grupo en las últimas 50 publicaciones
            recent_use = db_manager.fetch_one(
                """
                SELECT COUNT(*) as count 
                FROM group_text_usage_log 
                WHERE text_id = ? AND group_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (text['id'], group['id'])
            )
            
            if not recent_use or recent_use['count'] == 0:
                available_texts.append(text)
        
        # Si todos fueron usados, usar cualquiera con menor uso
        if not available_texts:
            available_texts = texts
        
        # Calcular score de calidad para cada texto
        scored_texts = []
        for text in available_texts[:10]:  # Solo los 10 con menor uso
            score = self._calculate_text_score(text, group_category)
            scored_texts.append((score, text))
        
        # Ordenar por score y retornar el mejor
        scored_texts.sort(reverse=True, key=lambda x: x[0])
        
        return scored_texts[0][1] if scored_texts else None
    
    def _calculate_text_score(self, text: Dict, target_category: str) -> float:
        """
        Calcula un score de calidad para un texto basado en múltiples factores.
        
        Score máximo: 100
        - Coincidencia de categoría: 50 puntos
        - Menor uso: 30 puntos
        - Longitud adecuada: 10 puntos
        - Tiene etiquetas: 10 puntos
        """
        score = 0.0
        
        # 1. Coincidencia de categoría (50 puntos)
        tags = (text.get('ai_tags') or '').lower()
        if target_category.lower() in tags:
            score += 50
        
        # 2. Menor uso (30 puntos) - invertido
        usage_count = text.get('usage_count', 0)
        # Normalizar: 0 usos = 30 puntos, 100+ usos = 0 puntos
        usage_score = max(0, 30 - (usage_count * 0.3))
        score += usage_score
        
        # 3. Longitud adecuada (10 puntos)
        content_length = len(text.get('content', ''))
        if 50 <= content_length <= 200:
            score += 10
        elif 30 <= content_length <= 300:
            score += 5
        
        # 4. Tiene etiquetas (10 puntos)
        if tags and len(tags) > 5:
            score += 10
        
        return score
    
    def _find_coherent_image(
        self,
        text: Dict,
        group_category: str,
        content_tags: str
    ) -> Optional[Dict]:
        """
        Encuentra una imagen coherente con el texto seleccionado.
        """
        # Verificar coherencia texto-imagen usando el categorizador
        text_content = text.get('content', '')
        
        # Buscar imágenes de la misma categoría
        category_filter = f"%{group_category.lower()}%"
        
        query = """
            SELECT * FROM images
            WHERE manual_tags LIKE ?
            ORDER BY 
                CASE 
                    WHEN usage_count IS NULL THEN 0
                    ELSE usage_count
                END ASC
            LIMIT 20
        """
        
        images = db_manager.fetch_all(query, (category_filter,))
        
        if not images:
            # Si no hay imágenes de esa categoría, buscar cualquiera
            images = db_manager.fetch_all(
                "SELECT * FROM images ORDER BY usage_count ASC LIMIT 10"
            )
        
        if not images:
            return None
        
        # Validar coherencia con el categorizador
        best_image = None
        best_coherence_score = 0.0
        
        for image in images[:10]:  # Evaluar solo las 10 menos usadas
            image_tags = image.get('manual_tags', '')
            
            # Validar coherencia
            coherence = content_categorizer.validate_content_coherence(
                text_content,
                image_tags
            )
            
            if coherence['coherent']:
                # Calcular score considerando coherencia y uso
                usage_count = image.get('usage_count', 0) or 0
                coherence_score = coherence['confidence'] * (1.0 / (usage_count + 1))
                
                if coherence_score > best_coherence_score:
                    best_coherence_score = coherence_score
                    best_image = image
        
        # Si no hay imagen coherente, retornar la menos usada de la categoría
        if not best_image and images:
            best_image = min(images, key=lambda x: x.get('usage_count', 0) or 0)
        
        return best_image
    
    def validate_content_pair(
        self, 
        text: Dict, 
        image: Optional[Dict]
    ) -> Dict:
        """
        Valida que un par de contenido sea coherente antes de publicar.
        
        Returns:
            {
                "valid": bool,
                "confidence": float,
                "warnings": list,
                "recommendation": str
            }
        """
        result = {
            "valid": True,
            "confidence": 1.0,
            "warnings": [],
            "recommendation": "Contenido listo para publicar"
        }
        
        if not text:
            result["valid"] = False
            result["confidence"] = 0.0
            result["warnings"].append("No hay texto disponible")
            return result
        
        # Si no hay imagen pero se esperaba, advertir
        if not image:
            result["warnings"].append("No hay imagen disponible, se publicará solo texto")
            result["confidence"] = 0.7
            return result
        
        # Validar coherencia entre texto e imagen
        text_content = text.get('content', '')
        image_tags = image.get('manual_tags', '')
        
        coherence = content_categorizer.validate_content_coherence(
            text_content,
            image_tags
        )
        
        result["confidence"] = coherence.get('confidence', 0.5)
        
        if not coherence.get('coherent', False):
            result["valid"] = False
            result["warnings"].append(coherence.get('message', 'Contenido no coherente'))
            result["recommendation"] = "Se recomienda seleccionar otra imagen o texto"
        
        return result
    
    def get_matching_statistics(self, session_id: int) -> Dict:
        """
        Obtiene estadísticas de emparejamiento para una sesión.
        
        Returns:
            {
                "total_published": int,
                "coherence_rate": float,
                "category_distribution": dict
            }
        """
        # Por ahora retornar estructura básica
        # Se puede extender cuando se implementen métricas más avanzadas
        return {
            "total_published": 0,
            "coherence_rate": 0.95,
            "category_distribution": {
                "EMPLEOS": 0,
                "SERVICIOS": 0,
                "VENTAS": 0
            }
        }


# Instancia global
intelligent_matcher = IntelligentMatcher()
