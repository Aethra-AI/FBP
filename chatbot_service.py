# -*- coding: utf-8 -*-
"""
Chatbot Asistente Inteligente para Generación de Contenido
Especializado en crear textos para Facebook según categoría y contexto
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from ai_services import ai_service
from content_categorizer import content_categorizer, CONTENT_CATEGORIES
from database import db_manager

class ChatbotAssistant:
    """
    Asistente conversacional para ayudar al usuario a crear contenido de calidad
    """
    
    def __init__(self):
        self.conversation_history = []
        self.context = {
            "last_category": None,
            "last_example": None,
            "user_preferences": {}
        }
        
        # System prompt base para el chatbot
        self.system_prompt = """
Eres un asistente experto en marketing digital para Facebook, especializado en crear contenido efectivo para redes sociales.

Tu trabajo es ayudar al usuario a:
1. Generar textos atractivos para publicaciones de Facebook
2. Crear variaciones basadas en ejemplos proporcionados
3. Adaptar el tono y estilo según la categoría (EMPLEOS, SERVICIOS, VENTAS)
4. Sugerir mejoras para que el contenido sea más efectivo

CATEGORÍAS DE CONTENIDO:
- EMPLEOS: Ofertas laborales, vacantes, reclutamiento
- SERVICIOS: Servicios profesionales, consultorías, asesorías  
- VENTAS: Productos, ofertas comerciales, promociones

REGLAS IMPORTANTES:
- Siempre pregunta la categoría si no está clara
- Genera textos de 60-100 palabras
- Incluye emojis relevantes naturalmente
- Usa llamados a la acción efectivos
- Mantén un tono profesional pero cercano
- Si el usuario da un ejemplo, respeta su estructura y tono

Responde siempre de forma concisa y práctica.
"""
    
    def chat(self, user_message: str, category: Optional[str] = None) -> Dict:
        """
        Procesa un mensaje del usuario y genera respuesta contextual
        
        Args:
            user_message: Mensaje del usuario
            category: Categoría opcional para contextualizar
            
        Returns:
            {
                "response": str,
                "action": str,  # "generate", "optimize", "clarify", "info"
                "data": Dict,   # Datos adicionales según la acción
                "suggestions": List[str]  # Botones de acción rápida
            }
        """
        # Detectar intención del usuario
        intent = self._detect_intent(user_message, category)
        
        # Actualizar historial
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now()
        })
        
        # Procesar según intención
        if intent["type"] == "add_text":
            result = self._handle_add_text(user_message, category)
        elif intent["type"] == "generate_content":
            result = self._handle_generate_content(user_message, intent, category)
        elif intent["type"] == "create_variations":
            result = self._handle_create_variations(user_message, intent, category)
        elif intent["type"] == "optimize_content":
            result = self._handle_optimize_content(user_message, intent)
        elif intent["type"] == "get_ideas":
            result = self._handle_get_ideas(category)
        elif intent["type"] == "analyze_content":
            result = self._handle_analyze_content(category)
        else:
            result = self._handle_general_query(user_message)
        
        # Guardar respuesta en historial
        self.conversation_history.append({
            "role": "assistant",
            "content": result["response"],
            "timestamp": datetime.now()
        })
        
        # Guardar en base de datos
        self._save_conversation_to_db(user_message, result["response"], intent["type"])
        
        return result
    
    def _detect_intent(self, message: str, category: Optional[str]) -> Dict:
        """
        Detecta la intención del usuario basándose en el mensaje
        """
        message_lower = message.lower()
        
        # Patrones de intención
        if any(word in message_lower for word in ["añadir texto", "agregar texto", "guardar texto", "añadir al contenido", "guardar este texto"]):
            return {"type": "add_text", "category": category}
        
        if any(word in message_lower for word in ["generar", "crear", "necesito", "quiero un post", "post sobre"]):
            return {"type": "generate_content", "category": category}
        
        if any(word in message_lower for word in ["variaciones", "versiones", "similar a", "como este", "basado en"]):
            return {"type": "create_variations", "example": message}
        
        if any(word in message_lower for word in ["mejorar", "optimizar", "revisar", "qué opinas"]):
            return {"type": "optimize_content"}
        
        if any(word in message_lower for word in ["ideas", "sugerencias", "qué puedo publicar", "temas"]):
            return {"type": "get_ideas"}
        
        if any(word in message_lower for word in ["analizar", "estadísticas", "qué tengo", "distribución"]):
            return {"type": "analyze_content"}
        
        return {"type": "general_query"}
    
    def _handle_add_text(self, user_message: str, category: Optional[str]) -> Dict:
        """
        Guía al usuario para añadir un texto manualmente al contenido
        """
        # Extraer el texto del mensaje (todo después de palabras clave)
        message_lower = user_message.lower()
        text_to_add = None
        
        # Buscar patrones explícitos
        patterns = ["añadir texto:", "agregar texto:", "guardar texto:", "añadir al contenido:", "texto:"]
        for pattern in patterns:
            if pattern in message_lower:
                text_to_add = user_message.split(":", 1)[1].strip() if ":" in user_message else None
                break
        
        # Si no tiene palabras clave, usar todo el mensaje como texto
        if not text_to_add:
            text_to_add = user_message.strip()
        
        # Si no encontró texto específico o es muy corto, guiar al usuario
        if not text_to_add or len(text_to_add) < 10:
            return {
                "response": "¡Perfecto! Para añadir un texto al contenido, necesito que me lo proporciones. 📝\n\n**¿Cómo funciona?**\n\n1️⃣ Escribe o pega el texto que quieres añadir\n2️⃣ Yo lo analizaré y le generaré etiquetas automáticamente\n3️⃣ Se guardará en tu biblioteca de contenido\n\n✨ Solo escribe el texto en tu siguiente mensaje y yo me encargo del resto.",
                "action": "clarify",
                "data": {"awaiting_text": True},
                "suggestions": []
            }
        
        # Si el usuario proporcionó el texto, devolverlo para que el frontend llame a add_manual_text
        if not category:
            # Detectar categoría automáticamente
            analysis = content_categorizer.analyze_content(text_to_add)
            category = analysis["category"]
        
        category_info = CONTENT_CATEGORIES.get(category, {"name": "General", "icon": "📄"})
        
        return {
            "response": f"✅ Perfecto, añadiré este texto a tu contenido:\n\n**Texto:**\n{text_to_add}\n\n**Categoría detectada:** {category_info['icon']} {category_info['name']}\n\nGenerando etiquetas inteligentes... ⏳",
            "action": "add_text",
            "data": {
                "text_to_add": text_to_add,
                "category": category
            },
            "suggestions": []
        }
    
    def _handle_generate_content(
        self, 
        user_message: str, 
        intent: Dict, 
        category: Optional[str]
    ) -> Dict:
        """
        Genera contenido nuevo basado en la solicitud del usuario
        """
        # Determinar categoría si no está especificada
        if not category:
            # Intentar detectar categoría del mensaje
            for cat_name, cat_data in CONTENT_CATEGORIES.items():
                if any(keyword in user_message.lower() for keyword in cat_data["keywords"][:5]):
                    category = cat_name
                    break
        
        if not category:
            return {
                "response": "Para generar el mejor contenido, ¿de qué categoría será la publicación?\n\n💼 EMPLEOS - Ofertas laborales y vacantes\n🔧 SERVICIOS - Servicios profesionales\n🛒 VENTAS - Productos y ofertas comerciales",
                "action": "clarify",
                "data": {"needs_category": True},
                "suggestions": ["💼 Empleos", "🔧 Servicios", "🛒 Ventas"]
            }
        
        # Generar contenido
        generated_texts = self._generate_texts_for_category(user_message, category, count=3)
        
        category_info = CONTENT_CATEGORIES[category]
        
        response = f"{category_info['icon']} He generado 3 opciones de contenido para **{category_info['name']}**:\n\n"
        
        for i, text in enumerate(generated_texts, 1):
            response += f"**Opción {i}:**\n{text}\n\n"
        
        response += "¿Quieres que guarde alguna o prefieres que genere más variaciones?"
        
        return {
            "response": response,
            "action": "generate",
            "data": {
                "texts": generated_texts,
                "category": category
            },
            "suggestions": [
                "✅ Guardar todas",
                "🔄 Más variaciones", 
                "✏️ Modificar una"
            ]
        }
    
    def _handle_create_variations(
        self, 
        user_message: str, 
        intent: Dict,
        category: Optional[str]
    ) -> Dict:
        """
        Crea variaciones basadas en un ejemplo proporcionado por el usuario
        """
        # Extraer el ejemplo del mensaje
        example_text = self._extract_example_from_message(user_message)
        
        if not example_text:
            return {
                "response": "Por favor, comparte el texto de ejemplo que quieres usar como referencia y generaré variaciones similares. 📝",
                "action": "clarify",
                "data": {"needs_example": True},
                "suggestions": []
            }
        
        # Determinar categoría del ejemplo
        if not category:
            analysis = content_categorizer.analyze_content(example_text)
            category = analysis["category"]
        
        # Generar variaciones
        variations = self._create_variations_from_example(example_text, category, count=3)
        
        category_info = CONTENT_CATEGORIES.get(category, {})
        
        response = f"He creado 3 variaciones basadas en tu ejemplo ({category_info.get('name', category)}):\n\n"
        
        for i, text in enumerate(variations, 1):
            response += f"**Variación {i}:**\n{text}\n\n"
        
        return {
            "response": response,
            "action": "generate",
            "data": {
                "texts": variations,
                "category": category,
                "based_on": example_text
            },
            "suggestions": [
                "✅ Guardar todas",
                "🔄 Más variaciones",
                "📋 Ver original"
            ]
        }
    
    def _handle_optimize_content(self, user_message: str, intent: Dict) -> Dict:
        """
        Optimiza un texto existente
        """
        # Extraer texto a optimizar
        text_to_optimize = self._extract_example_from_message(user_message)
        
        if not text_to_optimize:
            return {
                "response": "Comparte el texto que quieres mejorar y te daré sugerencias específicas. ✨",
                "action": "clarify",
                "data": {"needs_text": True},
                "suggestions": []
            }
        
        # Analizar y optimizar
        optimization = self._optimize_text(text_to_optimize)
        
        response = f"📊 **Análisis del texto:**\n\n"
        response += f"Categoría: {optimization['category']}\n"
        response += f"Puntuación: {optimization['score']}/100\n\n"
        response += f"**Sugerencias de mejora:**\n"
        
        for suggestion in optimization['suggestions']:
            response += f"• {suggestion}\n"
        
        response += f"\n**Versión optimizada:**\n{optimization['optimized_text']}"
        
        return {
            "response": response,
            "action": "optimize",
            "data": optimization,
            "suggestions": [
                "✅ Guardar optimizada",
                "📝 Mostrar ambas",
                "🔄 Otra versión"
            ]
        }
    
    def _handle_get_ideas(self, category: Optional[str]) -> Dict:
        """
        Sugiere ideas de contenido basadas en análisis de lo existente
        """
        # Analizar contenido existente
        stats = self._analyze_content_distribution()
        
        # Generar ideas
        ideas = self._generate_content_ideas(stats, category)
        
        response = "💡 **Ideas de contenido basadas en tu biblioteca:**\n\n"
        
        for idea in ideas["suggestions"]:
            response += f"• {idea}\n"
        
        if ideas.get("gaps"):
            response += f"\n⚠️ **Áreas que necesitan más contenido:**\n"
            for gap in ideas["gaps"]:
                response += f"• {gap}\n"
        
        return {
            "response": response,
            "action": "info",
            "data": ideas,
            "suggestions": [
                "📝 Generar contenido",
                "📊 Ver estadísticas",
                "🎯 Elegir categoría"
            ]
        }
    
    def _handle_analyze_content(self, category: Optional[str]) -> Dict:
        """
        Analiza la distribución y estado del contenido actual
        """
        stats = self._analyze_content_distribution()
        
        response = "📊 **Análisis de tu contenido:**\n\n"
        response += f"Total de textos: {stats['total_texts']}\n"
        response += f"Total de imágenes: {stats['total_images']}\n\n"
        
        response += "**Distribución por categoría:**\n"
        for cat, count in stats['distribution'].items():
            percentage = (count / stats['total_texts'] * 100) if stats['total_texts'] > 0 else 0
            emoji = CONTENT_CATEGORIES.get(cat, {}).get('icon', '📄')
            response += f"{emoji} {cat}: {count} ({percentage:.1f}%)\n"
        
        if stats.get('recommendations'):
            response += "\n**Recomendaciones:**\n"
            for rec in stats['recommendations']:
                response += f"• {rec}\n"
        
        return {
            "response": response,
            "action": "info",
            "data": stats,
            "suggestions": [
                "📝 Crear contenido",
                "⚖️ Balancear categorías",
                "🔍 Ver detalles"
            ]
        }
    
    def _handle_general_query(self, user_message: str) -> Dict:
        """
        Maneja consultas generales usando IA
        """
        try:
            # Preparar contexto de conversación
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Agregar últimos mensajes del historial
            for msg in self.conversation_history[-6:]:  # Últimos 3 intercambios
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Agregar mensaje actual
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            bot_response = response.choices[0].message.content
            
            return {
                "response": bot_response,
                "action": "chat",
                "data": {},
                "suggestions": [
                    "📝 Generar contenido",
                    "💡 Dame ideas",
                    "📊 Ver análisis"
                ]
            }
            
        except Exception as e:
            return {
                "response": f"Disculpa, tuve un problema procesando tu mensaje. ¿Puedes reformularlo? 🤔\nError: {str(e)}",
                "action": "error",
                "data": {"error": str(e)},
                "suggestions": []
            }
    
    def _generate_texts_for_category(
        self, 
        user_request: str, 
        category: str, 
        count: int = 3
    ) -> List[str]:
        """
        Genera textos específicos para una categoría
        """
        try:
            category_info = CONTENT_CATEGORIES[category]
            
            prompt = f"""
Genera {count} textos para publicaciones de Facebook en la categoría de {category_info['name']}.

Contexto del usuario: {user_request}

Características de {category_info['name']}:
{category_info['description']}

REQUISITOS:
- Longitud: 60-100 palabras
- Tono: Profesional pero cercano
- Incluir emojis relevantes naturalmente (2-3 por texto)
- Llamado a la acción claro
- Cada texto debe ser único y diferente de los otros
- Enfoque: {category_info['description']}

IMPORTANTE: Separa cada texto con el marcador "###"

Genera ahora los {count} textos:
"""
            
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            texts = [t.strip() for t in content.split("###") if t.strip()]
            
            return texts[:count]
            
        except Exception as e:
            print(f"Error generando textos: {e}")
            return [f"Error generando contenido: {str(e)}"]
    
    def _create_variations_from_example(
        self, 
        example: str, 
        category: str, 
        count: int = 3
    ) -> List[str]:
        """
        Crea variaciones basadas en un ejemplo
        """
        try:
            category_info = CONTENT_CATEGORIES[category]
            
            prompt = f"""
Crea {count} variaciones del siguiente texto, manteniendo el estilo, tono y estructura, pero cambiando las palabras y enfoque.

TEXTO ORIGINAL:
"{example}"

CATEGORÍA: {category_info['name']}

INSTRUCCIONES:
- Mantén la misma longitud aproximada
- Respeta el tono y estilo del original
- Cambia las palabras pero mantén el mensaje
- Cada variación debe sentirse natural y única
- Usa emojis similares al original

IMPORTANTE: Separa cada variación con "###"

Genera las {count} variaciones:
"""
            
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            variations = [v.strip() for v in content.split("###") if v.strip()]
            
            return variations[:count]
            
        except Exception as e:
            print(f"Error creando variaciones: {e}")
            return [example]  # Retornar original si falla
    
    def _optimize_text(self, text: str) -> Dict:
        """
        Analiza y optimiza un texto
        """
        try:
            # Analizar categoría
            analysis = content_categorizer.analyze_content(text)
            
            prompt = f"""
Analiza este texto para Facebook y proporciona:
1. Puntuación de calidad (0-100)
2. 3 sugerencias de mejora específicas
3. Una versión optimizada del texto

TEXTO:
"{text}"

CATEGORÍA DETECTADA: {analysis['category']}

Responde en formato JSON:
{{
    "score": 85,
    "suggestions": ["sugerencia 1", "sugerencia 2", "sugerencia 3"],
    "optimized_text": "texto optimizado aquí"
}}
"""
            
            response = ai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["category"] = analysis["category"]
            result["original_text"] = text
            
            return result
            
        except Exception as e:
            print(f"Error optimizando texto: {e}")
            return {
                "score": 50,
                "category": "GENERAL",
                "suggestions": ["Error analizando el texto"],
                "optimized_text": text,
                "original_text": text
            }
    
    def _analyze_content_distribution(self) -> Dict:
        """
        Analiza la distribución de contenido en la base de datos
        """
        texts = db_manager.fetch_all("SELECT ai_tags FROM texts")
        images = db_manager.fetch_all("SELECT manual_tags FROM images")
        
        distribution = {
            "EMPLEOS": 0,
            "SERVICIOS": 0,
            "VENTAS": 0,
            "GENERAL": 0
        }
        
        # Analizar textos
        for text in texts:
            tags = (text.get("ai_tags") or "").lower()
            for category in distribution.keys():
                if category.lower() in tags:
                    distribution[category] += 1
                    break
            else:
                distribution["GENERAL"] += 1
        
        total = len(texts)
        
        # Generar recomendaciones
        recommendations = []
        if total > 0:
            for cat, count in distribution.items():
                percentage = (count / total) * 100
                if percentage < 15 and cat != "GENERAL":
                    recommendations.append(
                        f"Necesitas más contenido de {cat} (solo {percentage:.1f}%)"
                    )
                elif percentage > 50:
                    recommendations.append(
                        f"Tienes mucho contenido de {cat} ({percentage:.1f}%), considera diversificar"
                    )
        
        return {
            "total_texts": total,
            "total_images": len(images),
            "distribution": distribution,
            "recommendations": recommendations
        }
    
    def _generate_content_ideas(self, stats: Dict, category: Optional[str]) -> Dict:
        """
        Genera ideas de contenido basadas en estadísticas
        """
        ideas = {
            "suggestions": [],
            "gaps": []
        }
        
        # Identificar gaps
        total = stats["total_texts"]
        if total > 0:
            for cat, count in stats["distribution"].items():
                percentage = (count / total) * 100
                if percentage < 20 and cat != "GENERAL":
                    ideas["gaps"].append(f"{cat} ({percentage:.0f}% del contenido)")
        
        # Generar sugerencias
        if category:
            cat_info = CONTENT_CATEGORIES.get(category, {})
            ideas["suggestions"] = [
                f"Post destacando beneficios de {cat_info.get('name', category)}",
                f"Testimonio o caso de éxito",
                f"Pregunta para generar engagement",
                f"Tip o consejo relacionado",
                f"Oferta o llamado a la acción directo"
            ]
        else:
            ideas["suggestions"] = [
                "Contenido sobre tus servicios más solicitados",
                "Historias de éxito de clientes",
                "Tips o consejos del sector",
                "Ofertas especiales o promociones",
                "Contenido educativo o informativo"
            ]
        
        return ideas
    
    def _extract_example_from_message(self, message: str) -> Optional[str]:
        """
        Intenta extraer un ejemplo de texto del mensaje del usuario
        """
        # Buscar patrones comunes
        patterns = [
            'ejemplo:',
            'como este:',
            'similar a:',
            'basado en:',
            '"',
            '"""'
        ]
        
        for pattern in patterns:
            if pattern in message.lower():
                parts = message.split(pattern, 1)
                if len(parts) > 1:
                    example = parts[1].strip()
                    # Limpiar comillas
                    example = example.strip('"').strip("'").strip('"""')
                    if len(example) > 20:  # Mínimo 20 caracteres para ser considerado
                        return example
        
        # Si no hay patrón, y el mensaje es largo, asumir que todo es el ejemplo
        if len(message) > 50 and not any(word in message.lower() for word in ['generar', 'crear', 'necesito']):
            return message
        
        return None
    
    def _save_conversation_to_db(self, user_msg: str, bot_response: str, action: str):
        """
        Guarda la conversación en la base de datos
        """
        try:
            db_manager.execute_query(
                """
                INSERT INTO chat_conversations (user_message, bot_response, action_taken, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (user_msg, bot_response, action, datetime.now())
            )
        except Exception as e:
            print(f"Error guardando conversación: {e}")
    
    def clear_history(self):
        """
        Limpia el historial de conversación
        """
        self.conversation_history = []
        self.context = {
            "last_category": None,
            "last_example": None,
            "user_preferences": {}
        }


# Instancia global
chatbot_assistant = ChatbotAssistant()
