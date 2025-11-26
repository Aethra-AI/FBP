# -*- coding: utf-8 -*-
"""
Sistema de Categorización Inteligente de Contenido
Clasifica contenido en categorías específicas para evitar mezclas entre nichos
"""

import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from database import db_manager
from ai_services import ai_service

# Definición de categorías y sus características
CONTENT_CATEGORIES = {
    "EMPLEOS": {
        "id": 1,
        "name": "Empleos",
        "description": "Ofertas laborales, vacantes, reclutamiento, búsqueda de personal",
        "keywords": [
            "trabajo", "empleo", "vacante", "contratar", "cv", "curriculum",
            "entrevista", "reclutamiento", "oferta laboral", "postular",
            "aplicar", "solicitud", "personal", "recursos humanos", "talento",
            "experiencia laboral", "salario", "beneficios", "jornada",
            "puesto", "candidato", "profesional", "carrera", "oportunidad laboral"
        ],
        "color": "#4CAF50",
        "icon": "💼"
    },
    "SERVICIOS": {
        "id": 2,
        "name": "Servicios",
        "description": "Servicios profesionales, consultorías, asesorías",
        "keywords": [
            "servicio", "asesoría", "consultoría", "profesional", "especialista",
            "experto", "atención", "soporte", "ayuda", "asistencia",
            "mantenimiento", "reparación", "instalación", "diseño",
            "desarrollo", "gestión", "administración", "capacitación",
            "curso", "entrenamiento", "taller", "solución", "personalizado"
        ],
        "color": "#2196F3",
        "icon": "🔧"
    },
    "VENTAS": {
        "id": 3,
        "name": "Ventas/Productos",
        "description": "Venta de productos, ofertas comerciales, promociones",
        "keywords": [
            "venta", "compra", "producto", "artículo", "precio", "oferta",
            "descuento", "promoción", "rebaja", "liquidación", "stock",
            "disponible", "nuevo", "lanzamiento", "calidad", "garantía",
            "envío", "entrega", "pedido", "tienda", "comercio",
            "negocio", "mercado", "cliente", "comprador"
        ],
        "color": "#FF9800",
        "icon": "🛒"
    }
}

class ContentCategorizer:
    """
    Clasificador inteligente de contenido usando IA y análisis de palabras clave
    """
    
    def __init__(self):
        self.categories = CONTENT_CATEGORIES
        
    def analyze_content(self, text: str, manual_category: Optional[str] = None) -> Dict:
        """
        Analiza un texto y determina su categoría con score de confianza
        
        Args:
            text: Contenido a analizar
            manual_category: Categoría manual si el usuario la especifica
            
        Returns:
            {
                "category": str,
                "confidence": float (0-1),
                "keywords_found": List[str],
                "suggested_tags": List[str]
            }
        """
        if not text or len(text.strip()) < 10:
            return {
                "category": "GENERAL",
                "confidence": 0.0,
                "keywords_found": [],
                "suggested_tags": []
            }
        
        # Si el usuario especificó categoría, usar esa con confianza alta
        if manual_category and manual_category in self.categories:
            return {
                "category": manual_category,
                "confidence": 1.0,
                "keywords_found": [],
                "suggested_tags": self._extract_tags_with_ai(text, manual_category)
            }
        
        # Análisis por keywords primero (rápido)
        keyword_result = self._analyze_by_keywords(text)
        
        # Si hay alta confianza (>0.7), usar ese resultado
        if keyword_result["confidence"] > 0.7:
            keyword_result["suggested_tags"] = self._extract_tags_with_ai(
                text, 
                keyword_result["category"]
            )
            return keyword_result
        
        # Si no hay alta confianza, usar IA para clasificación más precisa
        ai_result = self._analyze_with_ai(text)
        
        # Combinar resultados (dar más peso a IA si keyword score es bajo)
        if ai_result["confidence"] > keyword_result["confidence"]:
            return ai_result
        
        return keyword_result
    
    def _analyze_by_keywords(self, text: str) -> Dict:
        """
        Análisis rápido por conteo de keywords
        """
        text_lower = text.lower()
        scores = {}
        keywords_found = {}
        
        for category_name, category_data in self.categories.items():
            score = 0
            found_keywords = []
            
            for keyword in category_data["keywords"]:
                if keyword.lower() in text_lower:
                    # Dar más peso a keywords más específicas (más largas)
                    weight = len(keyword.split())
                    score += weight
                    found_keywords.append(keyword)
            
            scores[category_name] = score
            keywords_found[category_name] = found_keywords
        
        if not scores or max(scores.values()) == 0:
            return {
                "category": "GENERAL",
                "confidence": 0.0,
                "keywords_found": []
            }
        
        # Categoría con mayor score
        best_category = max(scores, key=scores.get)
        max_score = scores[best_category]
        
        # Calcular confianza (normalizada)
        total_keywords = len(self.categories[best_category]["keywords"])
        confidence = min(max_score / (total_keywords * 0.3), 1.0)
        
        return {
            "category": best_category,
            "confidence": confidence,
            "keywords_found": keywords_found[best_category]
        }
    
    def _analyze_with_ai(self, text: str) -> Dict:
        """
        Clasificación usando IA de OpenAI
        """
        try:
            # Crear prompt estructurado
            categories_str = "\n".join([
                f"- {name}: {data['description']}"
                for name, data in self.categories.items()
            ])
            
            prompt = f"""
Eres un experto en clasificación de contenido para marketing en Facebook.

CATEGORÍAS DISPONIBLES:
{categories_str}

TEXTO A CLASIFICAR:
"{text}"

INSTRUCCIONES:
1. Analiza el texto y determina a cuál categoría pertenece
2. Asigna un score de confianza (0.0 a 1.0)
3. Extrae 3-5 etiquetas específicas relevantes

RESPONDE SOLO EN ESTE FORMATO JSON:
{{
    "category": "EMPLEOS|SERVICIOS|VENTAS",
    "confidence": 0.95,
    "tags": ["etiqueta1", "etiqueta2", "etiqueta3"]
}}
"""
            
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "category": result.get("category", "GENERAL"),
                "confidence": float(result.get("confidence", 0.5)),
                "keywords_found": [],
                "suggested_tags": result.get("tags", [])
            }
            
        except Exception as e:
            print(f"Error en clasificación con IA: {e}")
            return {
                "category": "GENERAL",
                "confidence": 0.3,
                "keywords_found": [],
                "suggested_tags": []
            }
    
    def _extract_tags_with_ai(self, text: str, category: str) -> List[str]:
        """
        Extrae etiquetas específicas usando IA
        """
        try:
            category_info = self.categories.get(category, {})
            
            prompt = f"""
Extrae 3-5 etiquetas específicas para este contenido de {category_info.get('name', category)}.

TEXTO:
"{text}"

Responde SOLO con las etiquetas separadas por comas, en minúsculas.
Ejemplo: oferta laboral,ingeniero,experiencia requerida
"""
            
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            tags_str = response.choices[0].message.content.strip()
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            return tags[:5]  # Máximo 5 etiquetas
            
        except Exception as e:
            print(f"Error extrayendo etiquetas: {e}")
            return []
    
    def categorize_existing_content(self) -> Dict:
        """
        Categoriza todo el contenido existente en la base de datos
        """
        # Obtener todos los textos
        texts = db_manager.fetch_all("SELECT id, content, ai_tags FROM texts")
        
        categorized = {
            "success": [],
            "errors": [],
            "stats": {
                "EMPLEOS": 0,
                "SERVICIOS": 0,
                "VENTAS": 0,
                "GENERAL": 0
            }
        }
        
        for text in texts:
            try:
                result = self.analyze_content(text["content"])
                
                # Combinar etiquetas existentes con nuevas sugeridas
                existing_tags = text.get("ai_tags", "") or ""
                new_tags = result.get("suggested_tags", [])
                
                # Crear etiquetas jerárquicas: categoria:tag1,categoria:tag2
                hierarchical_tags = [
                    f"{result['category'].lower()}:{tag}"
                    for tag in new_tags
                ]
                
                # Agregar categoría principal
                all_tags = [result['category'].lower()] + hierarchical_tags
                
                if existing_tags:
                    all_tags.append(existing_tags)
                
                final_tags = ",".join(all_tags)
                
                # Actualizar en base de datos
                db_manager.execute_query(
                    "UPDATE texts SET ai_tags = ? WHERE id = ?",
                    (final_tags, text["id"])
                )
                
                categorized["success"].append({
                    "id": text["id"],
                    "category": result["category"],
                    "confidence": result["confidence"]
                })
                
                categorized["stats"][result["category"]] += 1
                
            except Exception as e:
                categorized["errors"].append({
                    "id": text["id"],
                    "error": str(e)
                })
        
        return categorized
    
    def get_category_info(self, category_name: str) -> Optional[Dict]:
        """
        Obtiene información de una categoría
        """
        return self.categories.get(category_name.upper())
    
    def get_all_categories(self) -> Dict:
        """
        Retorna todas las categorías disponibles
        """
        return self.categories
    
    def validate_content_coherence(
        self, 
        text_content: str, 
        image_tags: str
    ) -> Dict:
        """
        Valida que el texto y la imagen sean coherentes (misma categoría)
        
        Returns:
            {
                "coherent": bool,
                "text_category": str,
                "image_category": str,
                "confidence": float,
                "message": str
            }
        """
        # Analizar categoría del texto
        text_analysis = self.analyze_content(text_content)
        text_category = text_analysis["category"]
        
        # Determinar categoría de la imagen por sus tags
        image_category = self._determine_category_from_tags(image_tags)
        
        # Verificar coherencia
        coherent = text_category == image_category
        
        message = ""
        if coherent:
            message = f"✅ Contenido coherente: ambos son de {text_category}"
        else:
            message = f"⚠️ Incoherencia detectada: texto es {text_category} pero imagen es {image_category}"
        
        return {
            "coherent": coherent,
            "text_category": text_category,
            "image_category": image_category,
            "confidence": text_analysis["confidence"],
            "message": message
        }
    
    def _determine_category_from_tags(self, tags: str) -> str:
        """
        Determina la categoría de una imagen basándose en sus tags
        """
        if not tags:
            return "GENERAL"
        
        tags_lower = tags.lower()
        
        # Contar coincidencias con keywords de cada categoría
        scores = {}
        for category_name, category_data in self.categories.items():
            score = sum(
                1 for keyword in category_data["keywords"]
                if keyword.lower() in tags_lower
            )
            scores[category_name] = score
        
        if not scores or max(scores.values()) == 0:
            return "GENERAL"
        
        return max(scores, key=scores.get)


# Instancia global
content_categorizer = ContentCategorizer()
