# -*- coding: utf-8 -*-
import eel
import os
import random
import time
import threading
import uuid
import json
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Módulos del proyecto
from database import db_manager
from ai_services import ai_service
from content_categorizer import content_categorizer, CONTENT_CATEGORIES
from chatbot_service import chatbot_assistant
from intelligent_matcher import intelligent_matcher


# Importaciones de Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement

eel.init('web')

# Configurar Eel para servir archivos estáticos
import os
from flask import Flask, send_file, request
from flask_cors import CORS

# Crear una aplicación Flask para servir imágenes
app = Flask(__name__)
CORS(app)

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Sirve las imágenes desde el directorio images/"""
    try:
        image_path = os.path.join('images', filename)
        if os.path.exists(image_path):
            return send_file(image_path)
        else:
            return "Imagen no encontrada", 404
    except Exception as e:
        return f"Error: {str(e)}", 500

# Iniciar el servidor Flask en un hilo separado
import threading
def start_image_server():
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)

image_server_thread = threading.Thread(target=start_image_server, daemon=True)
image_server_thread.start()

class SessionManager:
    """Gestor de múltiples sesiones de Facebook."""
    
    def __init__(self):
        self.sessions = {}  # Dict para almacenar sesiones activas
        self.max_sessions = 10 # Aumentado para soportar más cuentas
        self.session_counter = 0
        
        # Asegurar directorio de perfiles
        self.profiles_dir = os.path.join(os.getcwd(), 'chrome_profiles')
        os.makedirs(self.profiles_dir, exist_ok=True)
    
    def create_session(self, name, group_tags="", content_tags="", publication_type="text-and-image"):
        """Crea una nueva sesión de Facebook (Cuenta)."""
        if len(self.sessions) >= self.max_sessions:
            return {"success": False, "message": f"Máximo {self.max_sessions} sesiones permitidas"}
        
        # Sanitizar nombre para usar en carpeta
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
        chrome_profile = os.path.join(self.profiles_dir, safe_name)
        
        # Crear sesión en la base de datos
        result = db_manager.create_session(
            name=name,
            chrome_profile=chrome_profile,
            group_tags=group_tags,
            content_tags=content_tags,
            publication_type=publication_type
        )
        
        if not result["success"]:
            return result
        
        # Crear instancia de AppLogic para esta sesión
        session_logic = SessionLogic(
            session_id=session_id,
            name=name,
            chrome_profile=chrome_profile,
            group_tags=group_tags,
            content_tags=content_tags,
            publication_type=publication_type
        )
        
        self.sessions[session_id] = {
            "id": session_id,
            "name": name,
            "logic": session_logic,
            "status": "inactive",
            "config": {
                "group_tags": group_tags,
                "content_tags": content_tags,
                "publication_type": publication_type
            }
        }
        
        return {"success": True, "session_id": session_id, "message": f"Cuenta '{name}' creada correctamente"}

    def open_browser_for_login(self, session_id):
        """Abre el navegador para que el usuario inicie sesión manualmente."""
        if session_id not in self.sessions:
            return {"success": False, "message": "Sesión no encontrada"}
            
        session = self.sessions[session_id]
        
        try:
            # Usar la lógica de SessionLogic para abrir el navegador
            # pero sin iniciar el proceso de publicación
            success = session["logic"].open_browser_only()
            if success:
                return {"success": True, "message": "Navegador abierto. Por favor inicie sesión y cierre la ventana cuando termine."}
            else:
                return {"success": False, "message": "Error al abrir el navegador."}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def start_session(self, session_id):
        """Inicia una sesión específica."""
        if session_id not in self.sessions:
            return {"success": False, "message": "Sesión no encontrada"}
        
        session = self.sessions[session_id]
        if session["status"] == "active":
            return {"success": False, "message": "La sesión ya está activa"}
        
        try:
            # Actualizar estado en BD
            db_manager.update_session_status(session_id, "active")
            session["status"] = "active"
            
            # Iniciar publicación
            result = session["logic"].start_publishing()
            return result
            
        except Exception as e:
            db_manager.update_session_status(session_id, "error")
            session["status"] = "error"
            return {"success": False, "message": str(e)}
    
    def pause_session(self, session_id):
        """Pausa una sesión específica."""
        if session_id not in self.sessions:
            return {"success": False, "message": "Sesión no encontrada"}
        
        session = self.sessions[session_id]
        if session["status"] != "active":
            return {"success": False, "message": "La sesión no está activa"}
        
        try:
            session["logic"].pause_publishing()
            db_manager.update_session_status(session_id, "paused")
            session["status"] = "paused"
            return {"success": True, "message": "Sesión pausada"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def stop_session(self, session_id):
        """Detiene una sesión específica."""
        if session_id not in self.sessions:
            return {"success": False, "message": "Sesión no encontrada"}
        
        session = self.sessions[session_id]
        
        try:
            session["logic"].stop_publishing()
            db_manager.update_session_status(session_id, "inactive")
            session["status"] = "inactive"
            return {"success": True, "message": "Sesión detenida"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def delete_session(self, session_id):
        """Elimina una sesión completamente."""
        if session_id not in self.sessions:
            return {"success": False, "message": "Sesión no encontrada"}
        
        session = self.sessions[session_id]
        
        try:
            # Detener si está activa
            if session["status"] in ["active", "paused"]:
                session["logic"].stop_publishing()
            
            # Eliminar de la base de datos
            db_manager.delete_session(session_id)
            
            # Eliminar de la memoria
            del self.sessions[session_id]
            
            return {"success": True, "message": "Sesión eliminada"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_session_status(self, session_id):
        """Obtiene el estado de una sesión."""
        if session_id not in self.sessions:
            return {"success": False, "message": "Sesión no encontrada"}
        
        session = self.sessions[session_id]
        session_data = db_manager.get_session(session_id)
        
        return {
            "success": True,
            "session": {
                "id": session_id,
                "name": session["name"],
                "status": session["status"],
                "config": session["config"],
                "current_group_index": session_data["current_group_index"] if session_data else 0,
                "total_groups": session_data["total_groups"] if session_data else 0
            }
        }
    
    def get_all_sessions(self):
        """Obtiene el estado de todas las sesiones."""
        sessions_status = []
        for session_id in self.sessions:
            status = self.get_session_status(session_id)
            if status["success"]:
                sessions_status.append(status["session"])
        
        return {"success": True, "sessions": sessions_status}
    
    def get_session_logs(self, session_id, limit=20):
        """Obtiene los logs de una sesión."""
        logs = db_manager.get_session_logs(session_id, limit)
        return {"success": True, "logs": logs}

class SessionLogic:
    """Lógica individual para cada sesión de Facebook."""
    
    def __init__(self, session_id, name, chrome_profile, group_tags, content_tags, publication_type):
        self.session_id = session_id
        self.name = name
        self.chrome_profile = chrome_profile
        self.group_tags = group_tags
        self.content_tags = content_tags
        self.publication_type = publication_type
        
        # Estado de la automatización para esta sesión
        self.driver = None
        self.running_groups_process = False
        self.paused = False
        self.publishing_thread = None
        
        # Configurar opciones de Chrome para esta sesión
        self.setup_chrome_options()
    
    def setup_chrome_options(self):
        """Configura las opciones de Chrome para esta sesión específica."""
        import os
        
        self.options = webdriver.ChromeOptions()
        
        # Opciones estándar para estabilidad
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Opciones para parecer menos un bot
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)
        
        # Perfil específico para esta sesión
        # chrome_profile ya es una ruta absoluta o relativa a chrome_profiles/nombre
        self.options.add_argument(f"user-data-dir={os.path.abspath(self.chrome_profile)}")

    def open_browser_only(self):
        """Abre el navegador solo para login/verificación."""
        return self._init_browser(wait_for_user=True)
    
    def log_to_session(self, message, message_type='info'):
        """Registra un mensaje específico para esta sesión."""
        db_manager.log_session_message(self.session_id, message, message_type)
    
    def start_publishing(self):
        """Inicia el proceso de publicación para esta sesión."""
        if self.running_groups_process:
            return {"success": False, "message": "La publicación ya está en curso"}
        
        self.publishing_thread = threading.Thread(
            target=self._group_publishing_process,
            daemon=True
        )
        self.publishing_thread.start()
        
        return {"success": True, "message": f"Sesión '{self.name}' iniciada correctamente"}
    
    def pause_publishing(self):
        """Pausa el proceso de publicación."""
        self.paused = True
        self.log_to_session("Publicación pausada por el usuario")
    
    def stop_publishing(self):
        """Detiene el proceso de publicación de forma segura."""
        self.log_to_session("🛑 Deteniendo publicación...")
        
        # Señalar al thread que debe detenerse
        self.running_groups_process = False
        self.paused = False
        
        # Cerrar navegador de forma segura
        if self.driver:
            try:
                self.log_to_session("Cerrando navegador...")
                self.driver.quit()
                self.log_to_session("✅ Navegador cerrado correctamente")
            except Exception as e:
                self.log_to_session(f"⚠️ Error al cerrar navegador: {e}")
            finally:
                self.driver = None
        
        # Esperar a que el thread termine (máximo 5 segundos)
        if hasattr(self, 'publishing_thread') and self.publishing_thread and self.publishing_thread.is_alive():
            try:
                self.log_to_session("Esperando a que termine el proceso...")
                self.publishing_thread.join(timeout=5)
                if self.publishing_thread.is_alive():
                    self.log_to_session("⚠️ El proceso tardó en terminar pero se detuvo")
                else:
                    self.log_to_session("✅ Proceso terminado correctamente")
            except Exception as e:
                self.log_to_session(f"⚠️ Error esperando al thread: {e}")
        
        self.log_to_session("✅ Publicación detenida. Lista para reiniciar.")
    
    def _group_publishing_process(self):
        """Proceso de publicación para esta sesión específica."""
        self.running_groups_process = True
        self.paused = False
        
        if not self._init_browser():
            self.running_groups_process = False
            return
        
        try:
            # Obtener grupos basados en las etiquetas de esta sesión
            query = "SELECT * FROM groups WHERE " + " OR ".join([f"tags LIKE '%{tag.strip()}%'" for tag in self.group_tags.split(',')])
            groups_to_publish = db_manager.fetch_all(query)
            
            # Actualizar total de grupos en BD
            db_manager.update_session_status(
                self.session_id, 
                "active", 
                0, 
                len(groups_to_publish)
            )
            
            self.log_to_session(f"Iniciando publicación en {len(groups_to_publish)} grupos...")
            
            for i, group in enumerate(groups_to_publish):
                if not self.running_groups_process:
                    self.log_to_session("Proceso detenido por el usuario.")
                    break
                
                # Verificar si está pausado
                while self.paused and self.running_groups_process:
                    time.sleep(1)
                
                if not self.running_groups_process:
                    break
                
                self.log_to_session(f"({i+1}/{len(groups_to_publish)}) Preparando publicación para: {group['url']}")
                
                # Actualizar progreso en BD
                db_manager.update_session_status(
                    self.session_id, 
                    "active", 
                    i, 
                    len(groups_to_publish)
                )
                
                text, image = self._find_coherent_pair_for_group(group)
                
                if not text:
                    self.log_to_session("No se encontró contenido de texto usable. Saltando grupo.")
                    continue
                
                # Verificar si se necesita imagen pero no se encontró
                if 'text-and-image' in self.publication_type and not image:
                    self.log_to_session("⚠️ Modo 'texto + imagen' seleccionado pero no hay imágenes disponibles. Continuando solo con texto.")
                
                try:
                    self.log_to_session(f"🌐 Navegando al grupo: {group['url']}")
                    self.driver.get(group["url"])
                    
                    # Espera inteligente
                    try:
                        WebDriverWait(self.driver, 15).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                        self.log_to_session("✓ Página cargada completamente")
                    except TimeoutException:
                        self.log_to_session("⚠️ Página tardó en cargar, continuando...")
                    
                    time.sleep(random.uniform(3, 5))
                    
                    # Publicar contenido
                    image_path = image['path'] if image else None
                    result = self._create_post_on_facebook(text['content'], image_path)
                    
                    if result['success']:
                        self.log_to_session(f"✅ Publicación exitosa en: {group['url']}")
                        
                        # Actualizar contadores de uso
                        if image:
                            db_manager.execute_query(
                                "INSERT INTO group_image_usage_log (image_id, group_id, timestamp) VALUES (?, ?, ?)",
                                (image['id'], group['id'], datetime.now())
                            )
                            db_manager.execute_query(
                                "UPDATE images SET usage_count = usage_count + 1 WHERE id = ?",
                                (image['id'],)
                            )
                        
                        db_manager.execute_query(
                            "INSERT INTO group_text_usage_log (text_id, group_id, timestamp) VALUES (?, ?, ?)",
                            (text['id'], group['id'], datetime.now())
                        )
                        db_manager.execute_query(
                            "UPDATE texts SET usage_count = usage_count + 1 WHERE id = ?",
                            (text['id'],)
                        )
                        
                        self.log_to_session(f"📊 Contadores actualizados - Texto ID: {text['id']}" + (f", Imagen ID: {image['id']}" if image else " (solo texto)"))
                    else:
                        self.log_to_session(f"❌ Error en publicación: {result['error']}")
                    
                    # Tiempo de espera entre publicaciones
                    time.sleep(random.uniform(10, 20))
                    
                except Exception as e:
                    self.log_to_session(f"❌ Error procesando grupo {group['url']}: {str(e)}")
                    continue
            
            # Proceso completado
            db_manager.update_session_status(self.session_id, "completed")
            self.log_to_session("🎉 Proceso de publicación completado")
            
        except Exception as e:
            db_manager.update_session_status(self.session_id, "error")
            self.log_to_session(f"❌ Error crítico: {str(e)}", "error")
        finally:
            self.running_groups_process = False
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def _init_browser(self, wait_for_user=False):
        """Inicializa el navegador para esta sesión."""
        try:
            # Limpiar caché corrupto y reinstalar ChromeDriver
            self.log_to_session("Configurando ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            
            # Verificar que el driver_path apunte al ejecutable correcto
            if not driver_path.endswith('chromedriver'):
                # Buscar el ejecutable correcto en el directorio
                import glob
                driver_dir = os.path.dirname(driver_path)
                possible_drivers = glob.glob(os.path.join(driver_dir, '**/chromedriver'), recursive=True)
                if possible_drivers:
                    driver_path = possible_drivers[0]
                    self.log_to_session(f"Driver corregido: {driver_path}")
            
            service = ChromeService(executable_path=driver_path)
            
            # Verificar si es la primera vez con este perfil
            profile_path = os.path.abspath(self.chrome_profile)
            is_first_run = not os.path.exists(profile_path)
            
            self.driver = webdriver.Chrome(service=service, options=self.options)
            
            if wait_for_user or is_first_run:
                self.log_to_session("¡ACCIÓN REQUERIDA! Ventana de navegador abierta.")
                self.log_to_session("Por favor, inicia sesión en Facebook si es necesario.")
                self.log_to_session("El sistema esperará hasta que cierres la ventana.")
                
                try:
                    self.driver.wait() # Espera a que se cierre la ventana
                except WebDriverException:
                    self.log_to_session("Ventana cerrada por el usuario.")
                    self.driver = None # Reset driver
                    return True # Éxito (el usuario completó la acción)
            
            self.log_to_session("Navegador iniciado y listo.")
            return True
        except Exception as e:
            self.log_to_session(f"Error crítico al iniciar Chrome: {e}", "error")
            self.driver = None
            return False
    
    def _find_coherent_pair_for_group(self, group):
        """
        Encuentra un par coherente de texto e imagen usando el matcher inteligente.
        
        Args:
            group: Diccionario con información del grupo
            
        Returns:
            (text_dict, image_dict) - Par de contenido coherente
        """
        self.log_to_session(f"🎯 Buscando contenido coherente para el grupo...")
        
        # Usar el matcher inteligente
        text, image = intelligent_matcher.find_best_content_for_group(
            group=group,
            content_tags=self.content_tags,
            publication_type=self.publication_type
        )
        
        if not text:
            self.log_to_session("⚠️ No se encontró texto apropiado para este grupo")
            return None, None
        
        # Validar coherencia del par seleccionado
        validation = intelligent_matcher.validate_content_pair(text, image)
        
        # Log de resultados
        if validation["valid"]:
            confidence_emoji = "✅" if validation["confidence"] > 0.8 else "⚡"
            self.log_to_session(
                f"{confidence_emoji} Contenido seleccionado (confianza: {validation['confidence']*100:.0f}%)"
            )
            
            if text.get('ai_tags'):
                # Extraer categoría principal del texto
                tags = text['ai_tags'].split(',')
                category = next((tag for tag in tags if tag.upper() in ['EMPLEOS', 'SERVICIOS', 'VENTAS']), 'GENERAL')
                self.log_to_session(f"📋 Categoría: {category.upper()}")
            
            if image:
                self.log_to_session(f"🖼️ Con imagen coherente")
            else:
                self.log_to_session(f"📝 Solo texto (sin imagen)")
                
        else:
            self.log_to_session(f"⚠️ Advertencia: {validation.get('recommendation', 'Baja coherencia')}")
            for warning in validation.get("warnings", []):
                self.log_to_session(f"  - {warning}")
        
        return text, image
    
    def _create_post_on_facebook(self, text_content, image_path=None):
        """Crea una publicación en Facebook para esta sesión."""
        try:
            # Buscar el campo de texto
            text_area = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='status-attachment-mentions-input']"))
            )
            
            # Limpiar y escribir texto
            text_area.clear()
            text_area.send_keys(text_content)
            self.log_to_session("✓ Texto escrito correctamente")
            
            # Subir imagen si se proporciona
            if image_path:
                try:
                    # Buscar botón de foto
                    photo_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='photo-video-button']"))
                    )
                    photo_button.click()
                    
                    # Buscar input de archivo
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                    )
                    
                    # Subir archivo
                    file_input.send_keys(os.path.abspath(image_path))
                    self.log_to_session("✓ Imagen subida correctamente")
                    
                    # Esperar a que la imagen se procese
                    time.sleep(3)
                    
                except Exception as e:
                    self.log_to_session(f"⚠️ Error subiendo imagen: {str(e)}")
            
            # Publicar
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='react-composer-post-button']"))
            )
            post_button.click()
            
            self.log_to_session("✓ Publicación enviada")
            time.sleep(3)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Instancia global del gestor de sesiones
session_manager = SessionManager()

class AppLogic:
    def __init__(self):
        # Estado de la automatización
        self.driver = None
        self.running_groups_process = False
        self.paused = False
        self.publishing_thread = None
        self.scheduler_thread = None
        self.stop_scheduler = threading.Event()

        # Configuración
        self.setup_chrome_options()
        self.start_scheduler_thread()

    def setup_chrome_options(self):
        """
        Configura las opciones para el navegador Chrome de Selenium.
        Esta función instruye a Selenium para que utilice un perfil de datos
        dedicado y persistente ('automation_profile') ubicado en la carpeta
        del proyecto. Esto evita conflictos y problemas de permisos.
        """
        import os

        self.options = webdriver.ChromeOptions()
        
        # Opciones estándar para estabilidad
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--start-maximized")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Opciones para parecer menos un bot
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option("useAutomationExtension", False)

        # --- Lógica para usar un perfil de bot dedicado y local ---

        # 1. Creamos una ruta absoluta a la carpeta del perfil del bot.
        #    Esto es mucho más robusto.
        automation_profile_path = os.path.abspath('automation_profile')
        
        # 2. Le decimos a Selenium que use esa carpeta de perfil.
        self.options.add_argument(f"user-data-dir={automation_profile_path}")
        
        
    def log_to_panel(self, message, message_type='info'):
        """
        Registra un mensaje en el panel de registro.
        
        Args:
            message (str): El mensaje a mostrar
            message_type (str): Tipo de mensaje ('info', 'warning', 'error')
        """
        timestamp = time.strftime('%H:%M:%S')
        
        # Añadir prefijo según el tipo de mensaje
        if message_type == 'warning':
            prefix = '⚠️ '
        elif message_type == 'error':
            prefix = '❌ '
        else:  # info por defecto
            prefix = 'ℹ️ '
            
        formatted_message = f"[{timestamp}] {prefix}{message}"
        
        try:
            # Intentar llamar a la función JavaScript
            eel.log_to_panel(formatted_message)()
        except Exception as e:
            # Si falla, imprimir en consola como respaldo
            print(formatted_message)
            # Solo mostrar error si no es porque eel no está disponible
            if "RuntimeError" not in str(e) and "WebSocketError" not in str(e):
                print(f"Error enviando log a UI: {e}")

    # --- LÓGICA DE SELENIUM ---
    def init_browser(self):
        """
        Inicia el navegador y maneja de forma inteligente el primer inicio de sesión.
        """
        if self.driver:
            self.log_to_panel("El navegador ya está iniciado.")
            return True
        try:
            self.log_to_panel("Configurando ChromeDriver automáticamente...")
            
            # Comprobamos si el perfil del bot ya existe.
            # Si no existe, significa que es la primera vez que se ejecuta.
            import os
            import glob
            profile_path = os.path.abspath('automation_profile')
            is_first_run = not os.path.exists(profile_path)

            # Limpiar caché corrupto y reinstalar ChromeDriver
            driver_path = ChromeDriverManager().install()
            
            # Verificar que el driver_path apunte al ejecutable correcto
            if not driver_path.endswith('chromedriver'):
                # Buscar el ejecutable correcto en el directorio
                driver_dir = os.path.dirname(driver_path)
                possible_drivers = glob.glob(os.path.join(driver_dir, '**/chromedriver'), recursive=True)
                if possible_drivers:
                    driver_path = possible_drivers[0]
                    self.log_to_panel(f"Driver corregido: {driver_path}")
            
            service = ChromeService(executable_path=driver_path)
            self.driver = webdriver.Chrome(service=service, options=self.options)
            
            # Si es la primera vez, pausamos el script para el login manual.
            if is_first_run:
                self.log_to_panel("¡ACCIÓN REQUERIDA! Es la primera ejecución con este perfil.")
                self.log_to_panel("Por favor, inicia sesión en Facebook en la ventana del navegador que se ha abierto.")
                self.log_to_panel("Marca 'Recordarme' para no volver a hacerlo.")
                self.log_to_panel("El bot continuará automáticamente cuando cierres esa ventana del navegador.")
                
                # Esta es la magia: el script se detendrá aquí hasta que cierres la ventana del bot.
                try:
                    # Esperamos indefinidamente. El script solo continuará si la ventana se cierra
                    # o si hay un error (por ejemplo, el usuario cierra la terminal).
                    self.driver.wait() 
                except WebDriverException:
                    # Esto es normal, ocurre cuando cierras la ventana manualmente.
                    self.log_to_panel("Ventana cerrada por el usuario. Re-inicializando el navegador para continuar...")
                    # Después de cerrar, necesitamos reiniciar el driver para que la sesión se guarde y se pueda usar.
                    self.driver = webdriver.Chrome(service=service, options=self.options)
            
            self.log_to_panel("Navegador iniciado y listo.")
            return True
        except Exception as e:
            self.log_to_panel(f"Error crítico al iniciar Chrome: {e}")
            self.driver = None
            return False

    def close_browser(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.log_to_panel(f"Error al cerrar el driver: {e}")
            finally:
                self.driver = None
                self.log_to_panel("Navegador cerrado.")
    
    # Dentro de la clase AppLogic en main.py

    def _validate_image_path(self, image_path):
        """
        Valida que el archivo de imagen exista antes de intentar subirlo.
        
        Args:
            image_path: Ruta del archivo de imagen
            
        Returns:
            dict: {"valid": bool, "path": str, "error": str}
        """
        if not image_path:
            return {"valid": True, "path": None, "error": None}
            
        try:
            import os
            
            # Convertir a ruta absoluta
            abs_path = os.path.abspath(image_path)
            
            # Verificar que el archivo existe
            if not os.path.exists(abs_path):
                self.log_to_panel(f"❌ Archivo no encontrado: {abs_path}")
                return {"valid": False, "path": abs_path, "error": "Archivo no encontrado"}
            
            # Verificar que es un archivo (no directorio)
            if not os.path.isfile(abs_path):
                self.log_to_panel(f"❌ La ruta no es un archivo: {abs_path}")
                return {"valid": False, "path": abs_path, "error": "No es un archivo"}
                
            # Verificar extensión de imagen
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            file_ext = os.path.splitext(abs_path)[1].lower()
            if file_ext not in valid_extensions:
                self.log_to_panel(f"⚠️ Extensión no válida: {file_ext}")
                return {"valid": False, "path": abs_path, "error": f"Extensión no soportada: {file_ext}"}
            
            # Verificar tamaño del archivo
            file_size = os.path.getsize(abs_path)
            max_size = 10 * 1024 * 1024  # 10 MB
            if file_size > max_size:
                self.log_to_panel(f"⚠️ Archivo demasiado grande: {file_size / 1024 / 1024:.1f}MB")
                return {"valid": False, "path": abs_path, "error": f"Archivo demasiado grande"}
                
            self.log_to_panel(f"✅ Imagen validada: {os.path.basename(abs_path)} ({file_size / 1024:.1f}KB)")
            return {"valid": True, "path": abs_path, "error": None}
            
        except Exception as e:
            error_msg = f"Error validando imagen: {str(e)}"
            self.log_to_panel(f"❌ {error_msg}")
            return {"valid": False, "path": image_path, "error": error_msg}

    def _remove_non_bmp_characters(self, text):
        """Elimina caracteres que no están en el plano BMP (como emojis) para evitar errores de ChromeDriver."""
        if not text:
            return ""
        return "".join(c for c in text if ord(c) <= 0xFFFF)

    def _fast_human_type(self, element, text):
        """Escribe texto de forma rápida pero humana, evitando bloqueos."""
        # Limpiar primero
        element.clear()
        
        # Escribir en bloques pequeños para ser más rápido que char a char
        # pero más seguro que send_keys completo
        chunk_size = 5
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            element.send_keys(chunk)
            # Pausa muy breve, casi imperceptible pero suficiente para el navegador
            time.sleep(random.uniform(0.01, 0.03))

    def _find_coherent_pair_for_group(self, group, content_tags):
        """
        Encuentra un par coherente de texto e imagen usando el matcher inteligente.
        """
        self.log_to_panel(f"🎯 Buscando contenido coherente para el grupo...")
        
        # Usar el matcher inteligente
        # Asumimos publication_type='text-and-image' por defecto para AppLogic
        text, image = intelligent_matcher.find_best_content_for_group(
            group=group,
            content_tags=content_tags,
            publication_type='text-and-image'
        )
        
        if not text:
            self.log_to_panel("⚠️ No se encontró texto apropiado para este grupo")
            return None, None
        
        # Validar coherencia del par seleccionado
        validation = intelligent_matcher.validate_content_pair(text, image)
        
        # Log de resultados
        if validation["valid"]:
            confidence_emoji = "✅" if validation["confidence"] > 0.8 else "⚡"
            self.log_to_panel(
                f"{confidence_emoji} Contenido seleccionado (confianza: {validation['confidence']*100:.0f}%)"
            )
            
            if text.get('ai_tags'):
                tags = text['ai_tags'].split(',')
                category = next((tag for tag in tags if tag.upper() in ['EMPLEOS', 'SERVICIOS', 'VENTAS']), 'GENERAL')
                self.log_to_panel(f"📋 Categoría: {category.upper()}")
            
            if image:
                self.log_to_panel(f"🖼️ Con imagen coherente")
            else:
                self.log_to_panel(f"📝 Solo texto (sin imagen)")
                
        else:
            self.log_to_panel(f"⚠️ Advertencia: {validation.get('recommendation', 'Baja coherencia')}")
            for warning in validation.get("warnings", []):
                self.log_to_panel(f"  - {warning}")
        
        return text, image

    def _create_post_on_facebook(self, text_content, image_path=None, max_retries=3):
        """
        Crea una publicación en Facebook con manejo robusto de errores y reintentos.
        """
        # 0. LIMPIEZA DE TEXTO (CRÍTICO PARA EVITAR CRASH)
        original_len = len(text_content)
        text_content = self._remove_non_bmp_characters(text_content)
        if len(text_content) < original_len:
            self.log_to_panel("⚠️ Emojis/caracteres especiales eliminados para evitar errores de driver.")

        # VALIDACIÓN PREVIA DE IMAGEN
        image_validation = self._validate_image_path(image_path)
        if not image_validation["valid"]:
            self.log_to_panel(f"🖼️ IMAGEN INVÁLIDA: {image_validation['error']}")
            if image_validation["error"] in ["Archivo no encontrado", "No es un archivo"]:
                self.log_to_panel("📝 Continuando con publicación SOLO TEXTO...")
                image_path = None
            else:
                return {
                    "success": False, 
                    "error": f"Imagen inválida: {image_validation['error']}", 
                    "should_discard_group": False,
                    "image_invalid": True
                }
        else:
            if image_validation["path"]:
                image_path = image_validation["path"]
        
        for attempt in range(max_retries):
            try:
                # 1. Abrir el modal de publicación
                self.log_to_panel(f"Intento {attempt + 1}/{max_retries}: Abriendo cuadro de publicación...")
                
                # Selectores priorizados
                open_button_selectors = [
                    '//div[contains(@aria-label, "Crear una publicación")]',
                    '//*[contains(text(), "Escribe algo")]',
                    '//div[@role="button"]//span[normalize-space(text())="Escribe algo..."]',
                    '//div[contains(@aria-label, "¿En qué estás pensando")]'
                ]
                
                open_button = None
                for selector in open_button_selectors:
                    try:
                        open_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        break
                    except TimeoutException:
                        continue
                
                if not open_button:
                    if attempt == max_retries - 1:
                        return {"success": False, "error": "Cuadro de publicación no encontrado", "should_discard_group": True}
                    time.sleep(2)
                    continue
                
                # Click seguro
                try:
                    open_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", open_button)
                
                self.log_to_panel("✓ Cuadro abierto. Esperando...")
                time.sleep(2)

                # 2. Escribir el texto (MODO RÁPIDO Y SEGURO)
                self.log_to_panel("Identificando campo de texto...")
                
                post_box = None
                # Intentar encontrar el campo activo explícitamente para evitar la barra de búsqueda
                try:
                    # Esperar a que aparezca el diálogo
                    dialog = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
                    )
                    # Buscar el textbox DENTRO del diálogo
                    post_box = dialog.find_element(By.XPATH, ".//div[@role='textbox']")
                except:
                    # Fallback al elemento activo si no encontramos el diálogo
                    post_box = self.driver.switch_to.active_element
                
                if not post_box:
                    self.log_to_panel("⚠️ Campo de texto no identificado.")
                    continue
                
                # Escribir usando el método rápido
                self.log_to_panel("✓ Escribiendo contenido...")
                self._fast_human_type(post_box, text_content)
                
                # 3. Subida de imágenes
                if image_path:
                    try:
                        # Buscar input file en todo el documento (es más fiable que buscar el botón de foto)
                        file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                        file_input.send_keys(image_path)
                        self.log_to_panel("✓ Imagen subida. Esperando carga...")
                        
                        # Esperar brevemente a que se procese
                        time.sleep(3)
                    except Exception as e:
                        self.log_to_panel(f"⚠️ Error subiendo imagen: {e}")

                # 4. Publicar
                self.log_to_panel("Enviando publicación...")
                
                # Buscar botón publicar específico del diálogo
                publish_button = None
                try:
                    publish_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@role='dialog']//div[@aria-label='Publicar']"))
                    )
                except:
                    # Fallback a selectores genéricos
                    try:
                        publish_button = self.driver.find_element(By.XPATH, "//div[@aria-label='Publicar']")
                    except:
                        pass
                
                if not publish_button:
                    self.log_to_panel("❌ Botón Publicar no encontrado.")
                    continue
                
                # Click en Publicar
                try:
                    publish_button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", publish_button)
                
                self.log_to_panel("✓ Click en Publicar realizado.")
                time.sleep(3)
                
                return {"success": True, "should_discard_group": False}
                
            except Exception as e:
                self.log_to_panel(f"❌ Error en intento {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "should_discard_group": False}
                time.sleep(3)
        
        return {"success": False, "error": "Max retries exceeded", "should_discard_group": False}

    def _group_publishing_process(self, group_tags, content_tags):
        self.running_groups_process = True
    
        if not self.init_browser():
            self.running_groups_process = False
            return

        try:
            query = "SELECT * FROM groups WHERE " + " OR ".join([f"tags LIKE '%{tag.strip()}%'" for tag in group_tags.split(',')])
            groups_to_publish = db_manager.fetch_all(query)
        
            self.log_to_panel(f"Iniciando publicación en {len(groups_to_publish)} grupos...")
        
            for i, group in enumerate(groups_to_publish):
                if not self.running_groups_process:
                    break
            
                # RECOVERY CHECK: Verificar si el navegador sigue vivo
                if not self.driver:
                    self.log_to_panel("⚠️ Navegador no detectado. Reiniciando...")
                    if not self.init_browser():
                        self.log_to_panel("❌ No se pudo reiniciar el navegador. Abortando.")
                        break
                
                try:
                    # Verificar ventana activa
                    self.driver.current_url
                except Exception:
                    self.log_to_panel("⚠️ Ventana del navegador cerrada o perdida. Reiniciando sesión...")
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    if not self.init_browser():
                        self.log_to_panel("❌ No se pudo recuperar la sesión. Abortando.")
                        break

                self.log_to_panel(f"({i+1}/{len(groups_to_publish)}) Grupo: {group['url']}")
            
                text, image = self._find_coherent_pair_for_group(group, content_tags)
                if not text:
                    continue
                
                try:
                    self.driver.get(group["url"])
                    time.sleep(random.uniform(3, 5))
                
                    image_path = image['path'] if image else None
                    result = self._create_post_on_facebook(text['content'], image_path)
                    
                    if result['success']:
                        self.log_to_panel(f"✅ Publicación exitosa!")
                        # Registrar éxito (código simplificado para brevedad)
                        db_manager.execute_query("UPDATE texts SET usage_count = usage_count + 1 WHERE id = ?", (text['id'],))
                        if image:
                            db_manager.execute_query("UPDATE images SET usage_count = usage_count + 1 WHERE id = ?", (image['id'],))
                    else:
                        self.log_to_panel(f"❌ Falló: {result.get('error')}")
                        if result.get('should_discard_group'):
                            self.log_to_panel("🚨 Marcando grupo como problemático.")
                            # Aquí iría la lógica de marcar grupo (simplificado)

                except Exception as e:
                    self.log_to_panel(f"💥 Error crítico en grupo: {e}")
                    # No abortamos el loop, intentamos con el siguiente grupo
                    continue

                if i < len(groups_to_publish) - 1:
                    wait_time = random.randint(30, 60) # Tiempo reducido para pruebas
                    self.log_to_panel(f"Esperando {wait_time}s...")
                    time.sleep(wait_time)
    
        finally:
            self.log_to_panel("Finalizando proceso.")
            self.close_browser()
            self.running_groups_process = False
        
        
    def start_publishing_groups(self, group_tags, content_tags):
        """Inicia el hilo para el proceso de publicación en grupos."""
        if self.running_groups_process:
            self.log_to_panel("Intento de iniciar publicación mientras ya estaba en ejecución.")
            return {"success": False, "message": "El proceso para grupos ya está en ejecución."}
        
        # Notifica a la interfaz de JavaScript que el proceso ha comenzado.
        # El botón cambiará a "Detener" inmediatamente.
        eel.update_publishing_status(True)()

        # Creamos y lanzamos el hilo que hará el trabajo pesado.
        self.publishing_thread = threading.Thread(
            target=self._group_publishing_process, 
            args=(group_tags, content_tags), 
            daemon=True
        )
        self.publishing_thread.start()
        
        return {"success": True, "message": "Proceso de publicación en grupos iniciado."}
    def stop_publishing_groups(self):
        """Detiene el proceso de publicación en grupos de forma segura."""
        self.log_to_panel("🛑 Deteniendo publicación en grupos...")
        
        # Señalar al thread que debe detenerse
        self.running_groups_process = False
        
        # Cerrar navegador de forma segura
        try:
            self.close_browser()
            self.log_to_panel("✅ Navegador cerrado correctamente")
        except Exception as e:
            self.log_to_panel(f"⚠️ Error al cerrar navegador: {e}")
        
        # Esperar a que el thread termine (máximo 5 segundos)
        if hasattr(self, 'publishing_thread') and self.publishing_thread and self.publishing_thread.is_alive():
            try:
                self.log_to_panel("Esperando a que termine el proceso...")
                self.publishing_thread.join(timeout=5)
                if self.publishing_thread.is_alive():
                    self.log_to_panel("⚠️ El proceso tardó en terminar pero se detuvo")
                else:
                    self.log_to_panel("✅ Proceso terminado correctamente")
            except Exception as e:
                self.log_to_panel(f"⚠️ Error esperando al thread: {e}")
        
        self.log_to_panel("✅ Proceso de publicación detenido. Listo para reiniciar.")
        return {"success": True, "message": "Publicación detenida correctamente"}
    
    def get_problematic_groups_report(self):
        """
        Genera un reporte de grupos problemáticos para revisión del usuario.
        """
        try:
            problematic_groups = db_manager.fetch_all("""
                SELECT url, tags, 
                       (SELECT COUNT(*) FROM publication_log 
                        WHERE target_url = groups.url AND status LIKE '%Problematic%') as failed_attempts
                FROM groups 
                WHERE tags LIKE '%PROBLEMÁTICO%'
                ORDER BY failed_attempts DESC
            """)
            
            if problematic_groups:
                self.log_to_panel("📋 REPORTE DE GRUPOS PROBLEMÁTICOS:")
                self.log_to_panel("=" * 50)
                for group in problematic_groups:
                    self.log_to_panel(f"🚨 URL: {group['url']}")
                    self.log_to_panel(f"   Intentos fallidos: {group['failed_attempts']}")
                    self.log_to_panel(f"   Etiquetas: {group['tags']}")
                    self.log_to_panel("-" * 30)
                
                self.log_to_panel("💡 RECOMENDACIÓN: Revisa estos grupos manualmente")
                self.log_to_panel("   Considera eliminarlos si siguen siendo problemáticos")
            else:
                self.log_to_panel("✅ No se encontraron grupos problemáticos")
                
            return {"success": True, "problematic_count": len(problematic_groups)}
            
        except Exception as e:
            self.log_to_panel(f"❌ Error generando reporte: {e}")
            return {"success": False, "error": str(e)}
    
    def clean_problematic_groups(self, confirm=False):
        """
        Limpia grupos marcados como problemáticos después de confirmación.
        
        Args:
            confirm: Si es True, elimina los grupos problemáticos. Si es False, solo muestra el conteo.
            
        Returns:
            dict: Resultado de la operación con mensaje y estado.
        """
        try:
            if not confirm:
                count = db_manager.fetch_one("SELECT COUNT(*) as count FROM groups WHERE tags LIKE '%PROBLEMÁTICO%'")
                return {
                    "success": False, 
                    "message": f"Se encontraron {count['count']} grupos problemáticos. Usa confirm=True para eliminarlos.",
                    "count": count['count']
                }
                
            # Si se confirma, proceder con la eliminación
            cursor = db_manager.conn.cursor()
            
            # Primero obtenemos los IDs de los grupos problemáticos
            cursor.execute("SELECT id FROM groups WHERE tags LIKE '%PROBLEMÁTICO%'")
            problematic_groups = cursor.fetchall()
            
            if not problematic_groups:
                return {
                    "success": True,
                    "message": "No se encontraron grupos problemáticos para eliminar.",
                    "deleted_count": 0
                }
                
            # Eliminamos los registros relacionados en otras tablas
            group_ids = [str(group['id']) for group in problematic_groups]
            placeholders = ','.join(['?'] * len(group_ids))
            
            # Eliminar referencias en group_image_usage_log
            cursor.execute(f"DELETE FROM group_image_usage_log WHERE group_id IN ({placeholders})", group_ids)
            
            # Eliminar referencias en group_text_usage_log
            cursor.execute(f"DELETE FROM group_text_usage_log WHERE group_id IN ({placeholders})", group_ids)
            
            # Finalmente, eliminar los grupos
            cursor.execute(f"DELETE FROM groups WHERE id IN ({placeholders})", group_ids)
            
            db_manager.conn.commit()
            
            return {
                "success": True,
                "message": f"Se eliminaron {len(problematic_groups)} grupos problemáticos.",
                "deleted_count": len(problematic_groups)
            }
                
        except Exception as e:
            db_manager.conn.rollback()
            return {
                'success': False, 
                'message': f'Error al limpiar grupos problemáticos: {str(e)}',
                'deleted_count': 0
            }
    def validate_and_clean_images(self, scan_directories=False):
        """
        Valida todas las imágenes en la base de datos y limpia las que no existen.
        
        Args:
            scan_directories: Si True, también escanea directorios comunes para encontrar imágenes movidas
        """
        self.log_to_panel("🔍 INICIANDO VALIDACIÓN DE IMÁGENES...")
        self.log_to_panel("=" * 50)
        
        try:
            # Obtener todas las imágenes de la BD
            all_images = db_manager.fetch_all("SELECT id, path, manual_tags FROM images")
            
            invalid_images = []
            valid_images = []
            moved_images = []
            
            self.log_to_panel(f"📊 Validando {len(all_images)} imágenes en la base de datos...")
            
            for image in all_images:
                validation = self._validate_image_path(image['path'])
                
                if validation["valid"]:
                    valid_images.append(image)
                    self.log_to_panel(f"✅ Válida: {os.path.basename(image['path'])}")
                else:
                    invalid_images.append({**image, "error": validation["error"]})
                    self.log_to_panel(f"❌ Inválida: {os.path.basename(image['path'])} - {validation['error']}")
                    
                    # Si scan_directories está habilitado, intentar encontrar la imagen
                    if scan_directories and validation["error"] == "Archivo no encontrado":
                        found_path = self._search_moved_image(image['path'])
                        if found_path:
                            moved_images.append({
                                "id": image['id'],
                                "old_path": image['path'],
                                "new_path": found_path
                            })
                            self.log_to_panel(f"📍 Encontrada en: {found_path}")
            
            # Reporte de resultados
            self.log_to_panel("\n📋 RESUMEN DE VALIDACIÓN:")
            self.log_to_panel(f"✅ Imágenes válidas: {len(valid_images)}")
            self.log_to_panel(f"❌ Imágenes inválidas: {len(invalid_images)}")
            self.log_to_panel(f"📍 Imágenes encontradas en nueva ubicación: {len(moved_images)}")
            
            # Actualizar rutas de imágenes encontradas
            if moved_images:
                self.log_to_panel(f"\n🔄 Actualizando rutas de {len(moved_images)} imágenes encontradas...")
                for moved in moved_images:
                    db_manager.execute_query(
                        "UPDATE images SET path = ? WHERE id = ?",
                        (moved['new_path'], moved['id'])
                    )
                    self.log_to_panel(f"✅ Actualizada: ID {moved['id']} -> {os.path.basename(moved['new_path'])}")
            
            # Mostrar imágenes inválidas que se pueden limpiar
            if invalid_images:
                self.log_to_panel(f"\n🗑️ IMÁGENES INVÁLIDAS ENCONTRADAS:")
                for img in invalid_images[:10]:  # Mostrar solo las primeras 10
                    self.log_to_panel(f"   ID {img['id']}: {img['path']} - {img['error']}")
                if len(invalid_images) > 10:
                    self.log_to_panel(f"   ... y {len(invalid_images) - 10} más")
                
                self.log_to_panel(f"\n💡 Usa clean_invalid_images(confirm=True) para eliminar las inválidas")
            
            return {
                "success": True,
                "total": len(all_images),
                "valid": len(valid_images),
                "invalid": len(invalid_images),
                "updated": len(moved_images),
                "invalid_list": invalid_images
            }
            
        except Exception as e:
            self.log_to_panel(f"❌ Error en validación: {e}")
            return {"success": False, "error": str(e)}
    
    def _search_moved_image(self, original_path):
        """
        Busca una imagen que pudo haber sido movida a directorios comunes.
        """
        try:
            import os
            
            filename = os.path.basename(original_path)
            
            # Directorios comunes donde buscar
            search_dirs = [
                os.path.expanduser("~/Downloads"),
                os.path.expanduser("~/Pictures"),
                os.path.expanduser("~/Desktop"),
                "C:/Users/Public/Pictures",
                os.path.dirname(original_path),  # Directorio original por si cambió de nombre
            ]
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    # Buscar recursivamente hasta 2 niveles de profundidad
                    for root, dirs, files in os.walk(search_dir):
                        # Limitar profundidad
                        level = root.replace(search_dir, '').count(os.sep)
                        if level < 2:
                            if filename in files:
                                found_path = os.path.join(root, filename)
                                # Validar que realmente es el archivo correcto
                                if os.path.isfile(found_path):
                                    return found_path
                        else:
                            dirs[:] = []  # No profundizar más
            
            return None
            
        except Exception:
            return None
    
    def clean_invalid_images(self, confirm=False):
        """
        Elimina imágenes inválidas de la base de datos.
        """
        if not confirm:
            # Contar imágenes inválidas
            all_images = db_manager.fetch_all("SELECT id, path FROM images")
            invalid_count = 0
            
            for image in all_images:
                validation = self._validate_image_path(image['path'])
                if not validation["valid"]:
                    invalid_count += 1
            
            return {
                "success": False,
                "message": f"Se encontraron {invalid_count} imágenes inválidas. Usa confirm=True para eliminarlas.",
                "count": invalid_count
            }
        
        try:
            # Identificar y eliminar imágenes inválidas
            all_images = db_manager.fetch_all("SELECT id, path FROM images")
            invalid_ids = []
            
            for image in all_images:
                validation = self._validate_image_path(image['path'])
                if not validation["valid"]:
                    invalid_ids.append(image['id'])
            
            if invalid_ids:
                # Eliminar registros de uso relacionados primero
                for img_id in invalid_ids:
                    db_manager.execute_query("DELETE FROM group_image_usage_log WHERE image_id = ?", (img_id,))
                    db_manager.execute_query("DELETE FROM page_image_usage WHERE image_id = ?", (img_id,))
                
                # Eliminar las imágenes
                placeholders = ','.join(['?'] * len(invalid_ids))
                db_manager.execute_query(f"DELETE FROM images WHERE id IN ({placeholders})", invalid_ids)
                
                self.log_to_panel(f"🧹 Eliminadas {len(invalid_ids)} imágenes inválidas de la base de datos")
                return {"success": True, "message": f"Eliminadas {len(invalid_ids)} imágenes inválidas", "count": len(invalid_ids)}
            else:
                self.log_to_panel("✅ No se encontraron imágenes inválidas para eliminar")
                return {"success": True, "message": "No hay imágenes inválidas", "count": 0}
                
        except Exception as e:
            self.log_to_panel(f"❌ Error limpiando imágenes: {e}")
            return {"success": False, "error": str(e)}

    # --- LÓGICA DEL SCHEDULER PARA PÁGINAS ---


    def _scheduler_process(self):
        self.log_to_panel("Scheduler iniciado. Buscando publicaciones programadas...")
    
        while not self.stop_scheduler.is_set():
            try:
                current_time_iso = datetime.now().isoformat()

                jobs = db_manager.fetch_all(
                    "SELECT * FROM scheduled_posts WHERE status = 'pending' AND publish_at <= ?", 
                    (current_time_iso,)
                )

                if jobs:
                    self.log_to_panel(f"Scheduler encontró {len(jobs)} trabajo(s) pendiente(s).")
                    browser_iniciado = self.init_browser()
                    if browser_iniciado:
                        try:
                            for job in jobs:
                                self.log_to_panel(f"Procesando publicación programada #{job['id']} para la página.")
                                db_manager.execute_query("UPDATE scheduled_posts SET status = 'processing' WHERE id = ?", (job['id'],))
                                
                                page = db_manager.fetch_one("SELECT * FROM pages WHERE id = ?", (job['page_id'],))
                                image = db_manager.fetch_one("SELECT path FROM images WHERE id = ?", (job['image_id'],)) if job['image_id'] else None
                                image_path = image['path'] if image else None
                                
                                # --- NUEVO: Necesitamos el ID del texto para actualizar su contador ---
                                # Asumimos que el contenido del texto en el job es único.
                                text_from_db = db_manager.fetch_one("SELECT id FROM texts WHERE content = ?", (job['text_content'],))

                                if page:
                                    self.driver.get(page['page_url'])
                                    time.sleep(random.uniform(5, 8))
                                
                                    result = self._create_post_on_facebook(job['text_content'], image_path)
                                
                                    final_status = 'completed' if result['success'] else 'failed'
                                    db_manager.execute_query("UPDATE scheduled_posts SET status = ? WHERE id = ?", (final_status, job['id'],))

                                    if result['success']:
                                        if job['image_id']:
                                            db_manager.execute_query("INSERT OR IGNORE INTO page_image_usage (page_id, image_id) VALUES (?, ?)", (job['page_id'], job['image_id']))
                                        # --- NUEVO: Incrementar contador de texto si se encontró y la publicación fue exitosa ---
                                        if text_from_db:
                                            db_manager.execute_query("UPDATE texts SET usage_count = usage_count + 1 WHERE id = ?", (text_from_db['id'],))
                                            self.log_to_panel(f"Contador de uso para el texto ID {text_from_db['id']} incrementado.")
                                
                                    log_data = {
                                        "timestamp": datetime.now(), "target_type": "page", "target_url": page['page_url'],
                                        "text_content": job['text_content'], "image_path": image_path,
                                        "status": "Success" if result['success'] else "Failed",
                                        "published_post_url": result.get('post_url')
                                    }
                                    db_manager.execute_query("""
                                        INSERT INTO publication_log (timestamp, status, target_type, target_url, text_content, image_path, published_post_url)
                                        VALUES (:timestamp, :status, :target_type, :target_url, :text_content, :image_path, :published_post_url)
                                    """, log_data)
                                else:
                                    self.log_to_panel(f"Error: No se encontró la página con ID {job['page_id']}. Marcando como fallido.")
                                    db_manager.execute_query("UPDATE scheduled_posts SET status = 'failed' WHERE id = ?", (job['id'],))

                        finally:
                            self.close_browser()
            
            except Exception as e:
                self.log_to_panel(f"Error en el ciclo del scheduler: {e}")

            time.sleep(60)
            
    def start_scheduler_thread(self):
        self.scheduler_thread = threading.Thread(target=self._scheduler_process, daemon=True)
        self.scheduler_thread.start()

    def stop_scheduler_thread(self):
        self.stop_scheduler.set()




    def validate_and_clean_images(self, scan_directories=False):
        """
        Valida todas las imágenes en la base de datos y opcionalmente busca archivos movidos.
        
        Args:
            scan_directories: Si es True, busca archivos movidos en directorios comunes
            
        Returns:
            dict: Resultado de la validación con estadísticas
        """
        try:
            self.log_to_panel("🔍 Iniciando validación completa de imágenes...")
            all_images = db_manager.fetch_all("SELECT id, path FROM images ORDER BY id")
            
            if not all_images:
                message = "No hay imágenes en la base de datos."
                self.log_to_panel(f"ℹ️ {message}")
                return {"success": True, "message": message}
            
            valid_images = []
            invalid_images = []
            
            self.log_to_panel(f"📊 Verificando {len(all_images)} imágenes...")
            
            for image in all_images:
                validation = self._validate_image_path(image['path'])
                
                if validation["valid"]:
                    valid_images.append(image)
                    self.log_to_panel(f"✅ Válida: {os.path.basename(image['path'])}")
                else:
                    invalid_images.append({**image, "error": validation["error"]})
                    self.log_to_panel(f"❌ Inválida: {os.path.basename(image['path'])} - {validation['error']}")
            
            # Reporte de resultados
            self.log_to_panel("\n📋 RESUMEN DE VALIDACIÓN:")
            self.log_to_panel(f"✅ Imágenes válidas: {len(valid_images)}")
            self.log_to_panel(f"❌ Imágenes inválidas: {len(invalid_images)}")
            
            if invalid_images:
                self.log_to_panel(f"\n🗑️ IMÁGENES INVÁLIDAS ENCONTRADAS:")
                for img in invalid_images[:10]:  # Mostrar solo las primeras 10
                    self.log_to_panel(f"   ID {img['id']}: {img['path']} - {img['error']}")
                if len(invalid_images) > 10:
                    self.log_to_panel(f"   ... y {len(invalid_images) - 10} más")
                
                self.log_to_panel(f"\n💡 Usa clean_invalid_images() para eliminar las inválidas")
            
            return {
                "success": True,
                "total": len(all_images),
                "valid": len(valid_images),
                "invalid": len(invalid_images),
                "invalid_details": invalid_images[:20]  # Primeras 20 para UI
            }
            
        except Exception as e:
            error_msg = f"Error durante la validación: {str(e)}"
            self.log_to_panel(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def clean_invalid_images(self, confirm=False):
        """
        Elimina imágenes inválidas de la base de datos después de validarlas.
        
        Args:
            confirm: Si es True, procede sin confirmación
            
        Returns:
            dict: Resultado de la operación de limpieza
        """
        try:
            self.log_to_panel("🧹 Iniciando limpieza de imágenes inválidas...")
            all_images = db_manager.fetch_all("SELECT id, path FROM images ORDER BY id")
            
            if not all_images:
                message = "No hay imágenes en la base de datos."
                self.log_to_panel(f"ℹ️ {message}")
                return {"success": True, "message": message}
            
            invalid_images = []
            
            # Identificar imágenes inválidas
            for image in all_images:
                validation = self._validate_image_path(image['path'])
                if not validation["valid"]:
                    invalid_images.append({**image, "error": validation["error"]})
            
            if not invalid_images:
                message = f"✅ Todas las {len(all_images)} imágenes son válidas. No hay nada que limpiar."
                self.log_to_panel(message)
                return {"success": True, "message": message}
            
            # Proceder con la eliminación
            self.log_to_panel(f"🗑️ Eliminando {len(invalid_images)} imágenes inválidas...")
            cursor = db_manager.conn.cursor()
            
            for img in invalid_images:
                img_id = img['id']
                img_path = img['path']
                
                try:
                    # Eliminar la imagen y todas sus referencias
                    cursor.execute("DELETE FROM images WHERE id = ?", (img_id,))
                    cursor.execute("DELETE FROM group_image_usage_log WHERE image_id = ?", (img_id,))
                    cursor.execute("DELETE FROM page_image_usage WHERE image_id = ?", (img_id,))
                    cursor.execute("DELETE FROM scheduled_posts WHERE image_id = ?", (img_id,))
                    
                    self.log_to_panel(f"   ✅ Eliminada ID {img_id}: {os.path.basename(img_path)}")
                    
                except Exception as e:
                    self.log_to_panel(f"   ❌ Error eliminando ID {img_id}: {e}")
            
            db_manager.conn.commit()
            
            message = f"✅ Limpieza completada. {len(invalid_images)} imágenes eliminadas de la base de datos."
            self.log_to_panel(message)
            
            return {
                "success": True,
                "message": message,
                "cleaned_count": len(invalid_images),
                "remaining_count": len(all_images) - len(invalid_images)
            }
            
        except Exception as e:
            error_msg = f"Error durante la limpieza: {str(e)}"
            self.log_to_panel(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    def shutdown(self):
        """Función para apagar de forma segura todos los procesos."""
        self.log_to_panel("Iniciando secuencia de apagado...")
        self.stop_scheduler_thread()
        self.stop_publishing_groups() # Esto ya llama a close_browser
        self.log_to_panel("Aplicación apagada de forma segura.")
        
        
# --- INSTANCIA GLOBAL DE LA LÓGICA ---
app_logic = AppLogic()

# --- FUNCIONES EXPUESTAS A JAVASCRIPT ---

# En main.py

@eel.expose
def get_initial_data():
    all_data = {
        "texts": db_manager.fetch_all("SELECT id, content, ai_tags, usage_count FROM texts ORDER BY id DESC"),
        "groups": db_manager.fetch_all("SELECT * FROM groups ORDER BY id DESC"),
        "pages": db_manager.fetch_all("SELECT * FROM pages ORDER BY id DESC"),
        "scheduled_posts": db_manager.fetch_all("""
            SELECT sp.*, p.name as page_name 
            FROM scheduled_posts sp 
            LEFT JOIN pages p ON sp.page_id = p.id 
            ORDER BY sp.publish_at DESC
        """),
        
        # --- CONSULTA OPTIMIZADA PARA HISTORIAL ---
        "publication_log": db_manager.fetch_all("""
            SELECT 
                timestamp,
                target_type,
                target_url,
                status,
                published_post_url
            FROM publication_log 
            ORDER BY timestamp DESC 
            LIMIT 50
        """),

        # --- NUEVA CONSULTA MODIFICADA PARA IMÁGENES ---
        # Calcula dinámicamente 'usage_count' sumando los usos en grupos y páginas.
        "images": db_manager.fetch_all("""
            SELECT 
                i.id,
                i.path,
                i.manual_tags,
                (
                    (SELECT COUNT(*) FROM group_image_usage_log WHERE image_id = i.id) +
                    (SELECT COUNT(*) FROM page_image_usage WHERE image_id = i.id)
                ) as usage_count
            FROM images i
            ORDER BY i.id DESC
        """)
    }
    return all_data
# --- Gestión de Textos ---


@eel.expose
def delete_text(item_id):
    db_manager.delete_item("texts", item_id)
    return db_manager.get_all_data()["texts"]

@eel.expose
def update_text(item_id, new_content):
    """
    Actualiza el contenido de un texto y regenera sus etiquetas de IA.
    """
    try:
        app_logic.log_to_panel(f"Actualizando texto ID: {item_id}...")
        
        # 1. Regenerar etiquetas IA para el nuevo contenido
        new_tags = ai_service.generate_tags_for_text(new_content)
        tags_str = ",".join(new_tags)
        
        # 2. Actualizar la base de datos con el nuevo contenido y las nuevas etiquetas
        db_manager.execute_query(
            "UPDATE texts SET content = ?, ai_tags = ? WHERE id = ?",
            (new_content, tags_str, item_id)
        )
        
        app_logic.log_to_panel(f"Texto ID: {item_id} actualizado con éxito. Nuevas etiquetas: '{tags_str}'")
        
        # 3. Devolver la lista actualizada de textos para refrescar la UI
        return db_manager.fetch_all("SELECT * FROM texts ORDER BY id DESC")
    except Exception as e:
        app_logic.log_to_panel(f"Error al actualizar el texto ID {item_id}: {e}")
        # En caso de error, devuelve los datos actuales para no romper la UI
        return db_manager.get_all_data()["texts"]

    
# --- Gestión de Imágenes ---
from image_manager import image_manager

@eel.expose
def delete_image(item_id):
    """
    Elimina una imagen de la base de datos y sus referencias.
    
    Args:
        item_id: ID de la imagen a eliminar
        
    Returns:
        dict: {
            'success': bool, 
            'message': str,
            'images': list  # Lista actualizada de imágenes
        }
    """
    try:
        # Convertir a entero por si viene como string
        item_id = int(item_id)
        
        with db_manager.conn:  # Usar el manejador de contexto para transacciones
            cursor = db_manager.conn.cursor()
            
            # 1. Obtener información de la imagen
            cursor.execute("""
                SELECT path, id FROM images 
                WHERE id = ?
            """, (item_id,))
            
            image_data = cursor.fetchone()
            
            if not image_data:
                return {
                    'success': False,
                    'message': f'No se encontró la imagen con ID {item_id}',
                    'images': db_manager.get_all_data()["images"]
                }
            
            image_path = image_data['path']
            
            # 2. Eliminar el archivo físico si existe
            try:
                # Convertir ruta relativa a absoluta si es necesario
                if not os.path.isabs(image_path):
                    image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), image_path)
                
                if os.path.exists(image_path):
                    os.remove(image_path)
                    app_logic.log_to_panel(f"✅ Archivo de imagen eliminado: {os.path.basename(image_path)}")
                else:
                    app_logic.log_to_panel(f"⚠️ El archivo no existe: {image_path}", 'warning')
                    
            except Exception as e:
                app_logic.log_to_panel(f"⚠️ No se pudo eliminar el archivo de imagen: {str(e)}", 'error')
            
            # 3. Eliminar referencias en tablas relacionadas
            try:
                cursor.execute("DELETE FROM group_image_usage_log WHERE image_id = ?", (item_id,))
                cursor.execute("DELETE FROM page_image_usage WHERE image_id = ?", (item_id,))
                cursor.execute("UPDATE scheduled_posts SET image_id = NULL WHERE image_id = ?", (item_id,))
                
                # 4. Finalmente, eliminar la imagen de la tabla images
                cursor.execute("DELETE FROM images WHERE id = ?", (item_id,))
                
                app_logic.log_to_panel(f"✅ Imagen ID {item_id} eliminada de la base de datos")
                
            except Exception as e:
                app_logic.log_to_panel(f"❌ Error en operaciones de base de datos: {str(e)}", 'error')
                raise
            
            # 5. Obtener la lista actualizada de imágenes
            cursor.execute("SELECT * FROM images ORDER BY id DESC")
            updated_images = [dict(row) for row in cursor.fetchall()]
            
            return {
                'success': True,
                'message': f'Imagen {item_id} eliminada correctamente',
                'images': updated_images
            }
            
    except Exception as e:
        if 'db_manager' in locals() and hasattr(db_manager, 'conn'):
            db_manager.conn.rollback()
            
        error_msg = f'Error al eliminar la imagen: {str(e)}'
        app_logic.log_to_panel(f"❌ {error_msg}", 'error')
        
        return {
            'success': False,
            'message': error_msg,
            'images': db_manager.get_all_data().get("images", [])
        }

@eel.expose
def delete_group(item_id):
    db_manager.delete_item("groups", item_id)
    return db_manager.get_all_data()["groups"]

    
@eel.expose
def add_page(name, url):
    db_manager.execute_query("INSERT OR IGNORE INTO pages (name, page_url) VALUES (?, ?)", (name, url))
    return db_manager.get_all_data()["pages"]

@eel.expose
def delete_page(item_id):
    db_manager.delete_item("pages", item_id)
    return db_manager.get_all_data()["pages"]


# En main.py, junto a las otras funciones expuestas

@eel.expose
def add_groups_bulk(urls_string, tags):
    """Añade múltiples grupos desde un string de URLs separadas por saltos de línea."""
    # Aseguramos que app_logic esté disponible para loguear
    global app_logic
    
    urls = [url.strip() for url in urls_string.splitlines() if url.strip()]
    if not urls:
        app_logic.log_to_panel("Importación masiva fallida: No se proporcionaron URLs válidas.")
        # Devolvemos los datos actuales para no romper la UI
        return db_manager.get_all_data()

    try:
        for url in urls:
            # Usamos INSERT OR IGNORE para evitar errores si el grupo ya existe
            db_manager.execute_query("INSERT OR IGNORE INTO groups (url, tags) VALUES (?, ?)", (url, tags))
        
        app_logic.log_to_panel(f"Importación masiva completada. {len(urls)} URLs procesadas.")
    except Exception as e:
        app_logic.log_to_panel(f"Error durante la importación masiva: {e}")

    # Devolvemos todos los datos para que la UI se refresque completamente
    return db_manager.get_all_data()

# --- Lógica de Programación y Publicación ---
@eel.expose
def start_group_publishing_process(group_tags, content_tags):
    return app_logic.start_publishing_groups(group_tags, content_tags)
    
@eel.expose
def stop_group_publishing_process():
    return app_logic.stop_publishing_groups()

# --- NUEVAS FUNCIONES PARA GESTIÓN DE SESIONES ---

@eel.expose
def create_session(name, group_tags, content_tags, publication_type="text-and-image"):
    """Crea una nueva sesión de Facebook."""
    return session_manager.create_session(name, group_tags, content_tags, publication_type)

@eel.expose
def start_session(session_id):
    """Inicia una sesión específica."""
    return session_manager.start_session(session_id)

@eel.expose
def pause_session(session_id):
    """Pausa una sesión específica."""
    return session_manager.pause_session(session_id)

@eel.expose
def stop_session(session_id):
    """Detiene una sesión específica."""
    return session_manager.stop_session(session_id)

@eel.expose
def delete_session(session_id):
    """Elimina una sesión completamente."""
    return session_manager.delete_session(session_id)

@eel.expose
def get_session_status(session_id):
    """Obtiene el estado de una sesión específica."""
    return session_manager.get_session_status(session_id)

@eel.expose
def get_all_sessions():
    """Obtiene el estado de todas las sesiones."""
    return session_manager.get_all_sessions()

@eel.expose
def get_session_logs(session_id, limit=20):
    """Obtiene los logs de una sesión específica."""
    return session_manager.get_session_logs(session_id, limit)

@eel.expose
def schedule_page_post(data):
    # data = { page_id, publish_at, text_content, image_id }
    query = "INSERT INTO scheduled_posts (page_id, publish_at, text_content, image_id) VALUES (?, ?, ?, ?)"
    params = (data['page_id'], data['publish_at'], data['text_content'], data.get('image_id'))
    db_manager.execute_query(query, params)
    return db_manager.get_all_data()["scheduled_posts"]
    
@eel.expose
def delete_scheduled_post(item_id):
    db_manager.delete_item("scheduled_posts", item_id)
    return db_manager.get_all_data()["scheduled_posts"]

@eel.expose
def get_content_suggestion(page_id, inspiration_tags):
    # Lógica simplificada: sugerir cualquier imagen no usada en la página y un texto coherente
    page_id = int(page_id)
    
    # 1. Encontrar imagen no usada en esta página
    query = """
        SELECT i.id, i.path, i.manual_tags FROM images i
        WHERE i.id NOT IN (SELECT image_id FROM page_image_usage WHERE page_id = ?)
        ORDER BY RANDOM() LIMIT 1
    """
    image = db_manager.fetch_one(query, (page_id,))
    if not image:
        return {"success": False, "message": "No hay imágenes nuevas disponibles para esta página."}
        
    image_tags = image['manual_tags'].split(',')
    
    # 2. Encontrar texto coherente
    all_texts = db_manager.fetch_all("SELECT id, content, ai_tags FROM texts")
    coherent_texts = [
        text for text in all_texts if any(tag in text.get('ai_tags', '') for tag in image_tags)
    ]
    if not coherent_texts:
         return {"success": False, "message": "No se encontró un texto coherente para la imagen sugerida."}
         
    text = random.choice(coherent_texts)
    
    return {"success": True, "text": text, "image": image}

# --- FUNCIONES PARA EDITAR ETIQUETAS ---

@eel.expose
def update_text_tags(text_id, new_tags):
    """Actualiza las etiquetas de un texto específico."""
    try:
        # Validar que el texto existe
        text = db_manager.fetch_one("SELECT id, content FROM texts WHERE id = ?", (text_id,))
        if not text:
            return {
                "success": False, 
                "message": "Texto no encontrado",
                "data": None
            }
        
        # Limpiar y validar las etiquetas
        if not new_tags or not new_tags.strip():
            return {
                "success": False,
                "message": "Las etiquetas no pueden estar vacías",
                "data": None
            }
        
        tags_list = [tag.strip().lower() for tag in new_tags.split(',') if tag.strip()]
        tags_str = ",".join(tags_list)
        
        # Actualizar en la base de datos
        db_manager.execute_query(
            "UPDATE texts SET ai_tags = ? WHERE id = ?", 
            (tags_str, text_id)
        )
        
        # Obtener el texto actualizado
        updated_text = db_manager.fetch_one(
            "SELECT id, content, ai_tags, usage_count FROM texts WHERE id = ?",
            (text_id,)
        )
        
        app_logic.log_to_panel(f"✅ Etiquetas del texto ID {text_id} actualizadas: {tags_str}")
        
        # Retornar el texto actualizado para actualizar la UI sin recargar todo
        return {
            "success": True, 
            "message": "Etiquetas actualizadas correctamente",
            "data": updated_text
        }
        
    except Exception as e:
        error_msg = f"Error actualizando etiquetas del texto: {str(e)}"
        app_logic.log_to_panel(f"❌ {error_msg}")
        return {
            "success": False, 
            "message": error_msg,
            "data": None
        }

@eel.expose
def update_image_tags(image_id, new_tags):
    """Actualiza las etiquetas de una imagen específica."""
    try:
        # Validar que la imagen existe
        image = db_manager.fetch_one(
            "SELECT id, file_path, manual_tags FROM images WHERE id = ?", 
            (image_id,)
        )
        if not image:
            return {
                "success": False, 
                "message": "Imagen no encontrada",
                "data": None
            }
        
        # Limpiar y validar las etiquetas
        if not new_tags or not new_tags.strip():
            return {
                "success": False,
                "message": "Las etiquetas no pueden estar vacías",
                "data": None
            }
        
        tags_list = [tag.strip().lower() for tag in new_tags.split(',') if tag.strip()]
        tags_str = ",".join(tags_list)
        
        # Actualizar en la base de datos
        db_manager.execute_query(
            "UPDATE images SET manual_tags = ? WHERE id = ?", 
            (tags_str, image_id)
        )
        
        # Obtener la imagen actualizada
        updated_image = db_manager.fetch_one(
            "SELECT id, file_path, manual_tags, usage_count FROM images WHERE id = ?",
            (image_id,)
        )
        
        app_logic.log_to_panel(f"✅ Etiquetas de la imagen ID {image_id} actualizadas: {tags_str}")
        
        # Retornar la imagen actualizada para actualizar la UI sin recargar todo
        return {
            "success": True, 
            "message": "Etiquetas actualizadas correctamente",
            "data": updated_image
        }
        
    except Exception as e:
        error_msg = f"Error actualizando etiquetas de la imagen: {str(e)}"
        app_logic.log_to_panel(f"❌ {error_msg}")
        return {
            "success": False, 
            "message": error_msg,
            "data": None
        }

@eel.expose
def regenerate_text_tags(text_id):
    """Regenera las etiquetas de un texto usando IA."""
    try:
        # Obtener el contenido del texto
        text = db_manager.fetch_one("SELECT id, content FROM texts WHERE id = ?", (text_id,))
        if not text:
            return {"success": False, "message": "Texto no encontrado"}
        
        # Generar nuevas etiquetas con IA
        new_tags = ai_service.generate_tags_for_text(text['content'])
        tags_str = ",".join(new_tags)
        
        # Actualizar en la base de datos
        db_manager.execute_query(
            "UPDATE texts SET ai_tags = ? WHERE id = ?", 
            (tags_str, text_id)
        )
        
        app_logic.log_to_panel(f"Etiquetas regeneradas para texto ID {text_id}: {tags_str}")
        
        return {"success": True, "message": "Etiquetas regeneradas correctamente", "tags": tags_str}
        
    except Exception as e:
        app_logic.log_to_panel(f"Error regenerando etiquetas del texto: {e}")
        return {"success": False, "message": str(e)}

# --- Funciones Worker para Tareas Lentas (AÑADIR A MAIN.PY) ---

def _add_manual_text_worker(content):
    """
    Worker que se ejecuta en segundo plano para añadir un texto manual.
    Esto evita que la UI se congele mientras la IA genera las etiquetas.
    """
    try:
        app_logic.log_to_panel("Generando etiquetas IA para texto manual...")
        tags = ai_service.generate_tags_for_text(content)
        tags_str = ",".join(tags)
        db_manager.execute_query("INSERT INTO texts (content, ai_tags) VALUES (?, ?)", (content, tags_str))
        app_logic.log_to_panel("Texto manual añadido y etiquetado.")
        # Llama a la función de JS para actualizar la tabla de textos
        eel.update_data_view('texts', db_manager.get_all_data()["texts"])()
    except Exception as e:
        app_logic.log_to_panel(f"Error en worker de texto manual: {e}")

@eel.expose
def add_manual_text(content):
    """Lanza el worker que añade texto manual en un hilo separado."""
    eel.spawn(_add_manual_text_worker, content)


def _generate_ai_texts_worker(topic, count):
    """
    Worker que se ejecuta en segundo plano para generar textos con IA.
    """
    try:
        app_logic.log_to_panel(f"Iniciando generación de {count} textos con IA sobre '{topic}'...")
        texts = ai_service.generate_text_variations(topic, int(count))
        for text in texts:
            tags = ai_service.generate_tags_for_text(text)
            tags_str = ",".join(tags)
            db_manager.execute_query("INSERT INTO texts (content, ai_tags) VALUES (?, ?)", (text, tags_str))
        app_logic.log_to_panel("Generación de textos con IA completada.")
        # Llama a la función de JS para actualizar la tabla de textos
        eel.update_data_view('texts', db_manager.get_all_data()["texts"])()
    except Exception as e:
        app_logic.log_to_panel(f"Error en worker de generación IA: {e}")

@eel.expose
def generate_ai_texts(topic, count):
    """Lanza el worker de generación de IA en un hilo separado."""
    eel.spawn(_generate_ai_texts_worker, topic, count)


def _add_images_worker(tags_string):
    """
    Worker que abre el diálogo para seleccionar múltiples imágenes sin congelar la UI.
    Maneja la carga de archivos en lotes con retroalimentación de progreso.
    """
    try:
        # Crea una ventana raíz de Tkinter para el diálogo de archivo
        root = tk.Tk()
        root.withdraw()  # Oculta la ventana principal de Tkinter
        root.attributes('-topmost', True)  # Pone el diálogo al frente

        # Configurar el diálogo para selección múltiple
        files = filedialog.askopenfilenames(
            title="Seleccionar imágenes (puedes seleccionar varias)", 
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png"),
                ("Todos los archivos", "*.*")
            ]
        )
        root.destroy()
        
        if not files:
            app_logic.log_to_panel("No se seleccionaron imágenes.", 'warning')
            return

        total_files = len(files)
        app_logic.log_to_panel(f"Procesando {total_files} imágenes...")
        
        # Mostrar la barra de progreso
        eel.update_upload_progress(0, "Preparando para subir imágenes...")
        
        # Procesar imágenes en lotes
        success_count = 0
        error_count = 0
        
        for i, file_path in enumerate(files, 1):
            try:
                # Actualizar progreso
                progress = int((i / total_files) * 100)
                eel.update_upload_progress(
                    progress, 
                    f"Subiendo imagen {i} de {total_files}: {os.path.basename(file_path)}"
                )
                
                # Normalizar la ruta del archivo
                normalized_path = os.path.normpath(file_path)
                
                # Usar el ImageManager para manejar la imagen
                result = image_manager.add_image(
                    source_path=normalized_path,
                    tags=tags_string.split(',') if tags_string else None
                )
                
                if result.get('success'):
                    success_count += 1
                    app_logic.log_to_panel(
                        f"Imagen {i}/{total_files} procesada: {os.path.basename(normalized_path)}",
                        'info'
                    )
                else:
                    error_count += 1
                    error_msg = result.get('message', 'Error desconocido')
                    app_logic.log_to_panel(
                        f"Error al procesar {os.path.basename(normalized_path)}: {error_msg}",
                        'error'
                    )
                    
            except Exception as e:
                error_count += 1
                app_logic.log_to_panel(
                    f"Error al procesar {os.path.basename(file_path)}: {str(e)}",
                    'error'
                )
        
        # Actualizar la vista de datos
        all_data = db_manager.get_all_data()
        eel.update_data_view('images', all_data["images"])(lambda _: None)
        
        # Mostrar resumen
        summary_msg = f"Proceso completado: {success_count} imágenes añadidas"
        if error_count > 0:
            summary_msg += f", {error_count} errores"
        
        app_logic.log_to_panel(summary_msg, 'info' if error_count == 0 else 'warning')
        
    except Exception as e:
        app_logic.log_to_panel(f"Error en el proceso de carga de imágenes: {str(e)}", 'error')
    finally:
        # Asegurarse de limpiar el indicador de progreso
        eel.hide_upload_progress()

@eel.expose
def add_images(tags_string):
    """Lanza el worker de selección de imágenes en un hilo separado."""
    eel.spawn(_add_images_worker, tags_string)

# --- FUNCIONES PARA MANEJO DE GRUPOS PROBLEMÁTICOS ---

@eel.expose
def get_problematic_groups_report():
    """Genera un reporte de grupos problemáticos."""
    return app_logic.get_problematic_groups_report()

@eel.expose
def clean_problematic_groups(confirm=False):
    """Limpia grupos marcados como problemáticos."""
    return app_logic.clean_problematic_groups(confirm)

@eel.expose
def get_publishing_statistics():
    """Obtiene estadísticas detalladas de publicaciones."""
    try:
        stats = {
            "total_publications": db_manager.fetch_one("SELECT COUNT(*) as count FROM publication_log")['count'],
            "successful_publications": db_manager.fetch_one("SELECT COUNT(*) as count FROM publication_log WHERE status = 'Success'")['count'],
            "failed_publications": db_manager.fetch_one("SELECT COUNT(*) as count FROM publication_log WHERE status LIKE 'Failed%'")['count'],
            "problematic_groups": db_manager.fetch_one("SELECT COUNT(*) as count FROM groups WHERE tags LIKE '%PROBLEMÁTICO%'")['count'],
            "recent_errors": db_manager.fetch_all("""
                SELECT target_url, status, timestamp, error_details 
                FROM publication_log 
                WHERE status LIKE 'Failed%' 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
        }
        
        # Calcular tasa de éxito
        if stats['total_publications'] > 0:
            stats['success_rate'] = round((stats['successful_publications'] / stats['total_publications']) * 100, 2)
        else:
            stats['success_rate'] = 0
            
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- FUNCIONES PARA MANEJO DE IMÁGENES INVÁLIDAS ---

@eel.expose
def validate_images(scan_directories=False):
    """Valida todas las imágenes en la base de datos."""
    return app_logic.validate_and_clean_images(scan_directories)

@eel.expose
def clean_invalid_images(confirm=False):
    """Limpia imágenes inválidas de la base de datos."""
    return app_logic.clean_invalid_images(confirm)

@eel.expose
def get_images_health_report():
    """Genera un reporte rápido del estado de las imágenes."""
    try:
        all_images = db_manager.fetch_all("SELECT id, path FROM images")
        
        valid_count = 0
        invalid_count = 0
        invalid_details = []
        
        for image in all_images[:50]:  # Solo revisar primeras 50 para reporte rápido
            validation = app_logic._validate_image_path(image['path'])
            if validation["valid"]:
                valid_count += 1
            else:
                invalid_count += 1
                invalid_details.append({
                    "id": image['id'],
                    "path": image['path'],
                    "error": validation['error']
                })
        
        return {
            "success": True,
            "total_checked": len(all_images[:50]),
            "total_in_db": len(all_images),
            "valid": valid_count,
            "invalid": invalid_count,
            "invalid_details": invalid_details[:10],  # Solo primeras 10
            "needs_full_scan": len(all_images) > 50
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- FUNCIONES PARA CHATBOT ASISTENTE ---

@eel.expose
def chat_with_assistant(message, category=None):
    """
    Envía un mensaje al chatbot asistente y obtiene respuesta.
    
    Args:
        message: Mensaje del usuario
        category: Categoría opcional para contextualizar (EMPLEOS, SERVICIOS, VENTAS)
    
    Returns:
        {
            "response": str,
            "action": str,
            "data": dict,
            "suggestions": list
        }
    """
    try:
        result = chatbot_assistant.chat(message, category)
        return result
    except Exception as e:
        return {
            "response": f"Error procesando tu mensaje: {str(e)}",
            "action": "error",
            "data": {},
            "suggestions": []
        }

@eel.expose
def save_generated_texts(texts, category):
    """
    Guarda textos generados por el chatbot en la base de datos.
    
    Args:
        texts: Lista de textos a guardar
        category: Categoría del contenido (EMPLEOS, SERVICIOS, VENTAS)
    
    Returns:
        {
            "success": bool,
            "saved_count": int,
            "texts": list
        }
    """
    try:
        saved_texts = []
        
        for text in texts:
            # Analizar y categorizar el texto
            analysis = content_categorizer.analyze_content(text, category)
            
            # Crear etiquetas jerárquicas: categoria:tag1,categoria:tag2
            hierarchical_tags = [
                f"{category.lower()}:{tag}"
                for tag in analysis.get("suggested_tags", [])
            ]
            
            # Agregar categoría principal
            all_tags = [category.lower()] + hierarchical_tags
            final_tags = ",".join(all_tags)
            
            # Guardar en base de datos
            cursor = db_manager.execute_query(
                "INSERT INTO texts (content, ai_tags, usage_count) VALUES (?, ?, 0)",
                (text, final_tags)
            )
            
            # Guardar relación con categoría
            text_id = cursor.lastrowid
            db_manager.execute_query(
                "INSERT OR REPLACE INTO text_categories (text_id, category, confidence_score) VALUES (?, ?, ?)",
                (text_id, category, analysis.get("confidence", 0.9))
            )
            
            saved_texts.append({
                "id": text_id,
                "content": text,
                "category": category,
                "tags": final_tags
            })
        
        return {
            "success": True,
            "saved_count": len(saved_texts),
            "texts": saved_texts,
            "message": f"✅ {len(saved_texts)} textos guardados en categoría {category}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "saved_count": 0,
            "texts": [],
            "message": f"Error guardando textos: {str(e)}"
        }

@eel.expose
def clear_chat_history():
    """Limpia el historial de conversación del chatbot."""
    try:
        chatbot_assistant.clear_history()
        return {"success": True, "message": "Historial limpiado"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# --- FUNCIONES PARA CATEGORIZACIÓN INTELIGENTE ---

@eel.expose
def get_content_categories():
    """
    Obtiene todas las categorías disponibles.
    
    Returns:
        {
            "EMPLEOS": {...},
            "SERVICIOS": {...},
            "VENTAS": {...}
        }
    """
    return CONTENT_CATEGORIES

@eel.expose
def categorize_content(text, manual_category=None):
    """
    Analiza un texto y determina su categoría.
    
    Args:
        text: Contenido a analizar
        manual_category: Categoría manual si el usuario la especifica
    
    Returns:
        {
            "category": str,
            "confidence": float,
            "keywords_found": list,
            "suggested_tags": list
        }
    """
    try:
        result = content_categorizer.analyze_content(text, manual_category)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "category": "GENERAL",
            "confidence": 0.0
        }

@eel.expose
def validate_content_coherence(text_content, image_tags):
    """
    Valida que un texto y una imagen sean coherentes (misma categoría).
    
    Args:
        text_content: Contenido del texto
        image_tags: Etiquetas de la imagen
    
    Returns:
        {
            "coherent": bool,
            "text_category": str,
            "image_category": str,
            "confidence": float,
            "message": str
        }
    """
    try:
        result = content_categorizer.validate_content_coherence(text_content, image_tags)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "coherent": False
        }

@eel.expose
def recategorize_all_content():
    """
    Re-categoriza todo el contenido existente usando el nuevo sistema.
    
    Returns:
        {
            "success": bool,
            "stats": dict,
            "categorized": list,
            "errors": list
        }
    """
    try:
        result = content_categorizer.categorize_existing_content()
        return {
            "success": True,
            **result,
            "message": f"✅ {len(result['success'])} textos categorizados correctamente"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error en re-categorización: {str(e)}"
        }

@eel.expose
def get_content_by_category(category):
    """
    Obtiene todo el contenido de una categoría específica.
    
    Args:
        category: Categoría a filtrar (EMPLEOS, SERVICIOS, VENTAS)
    
    Returns:
        {
            "texts": list,
            "images": list,
            "count": int
        }
    """
    try:
        category_lower = category.lower()
        
        # Buscar textos con la categoría
        texts = db_manager.fetch_all(
            "SELECT * FROM texts WHERE ai_tags LIKE ? ORDER BY id DESC",
            (f"%{category_lower}%",)
        )
        
        # Buscar imágenes con la categoría
        images = db_manager.fetch_all(
            "SELECT * FROM images WHERE manual_tags LIKE ? ORDER BY id DESC",
            (f"%{category_lower}%",)
        )
        
        return {
            "success": True,
            "category": category,
            "texts": texts,
            "images": images,
            "count": {
                "texts": len(texts),
                "images": len(images)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "texts": [],
            "images": [],
            "count": {"texts": 0, "images": 0}
        }

@eel.expose
def get_category_statistics():
    """
    Obtiene estadísticas de distribución de contenido por categoría.
    
    Returns:
        {
            "total_texts": int,
            "total_images": int,
            "distribution": dict,
            "recommendations": list
        }
    """
    try:
        texts = db_manager.fetch_all("SELECT ai_tags FROM texts")
        images = db_manager.fetch_all("SELECT manual_tags FROM images")
        
        distribution = {
            "EMPLEOS": 0,
            "SERVICIOS": 0,
            "VENTAS": 0,
            "GENERAL": 0
        }
        
        # Contar textos por categoría
        for text in texts:
            tags = (text.get("ai_tags") or "").lower()
            categorized = False
            for category in ["EMPLEOS", "SERVICIOS", "VENTAS"]:
                if category.lower() in tags:
                    distribution[category] += 1
                    categorized = True
                    break
            if not categorized:
                distribution["GENERAL"] += 1
        
        total = len(texts)
        
        # Generar recomendaciones
        recommendations = []
        if total > 0:
            for cat, count in distribution.items():
                percentage = (count / total) * 100
                if percentage < 15 and cat != "GENERAL":
                    recommendations.append(
                        f"⚠️ Necesitas más contenido de {cat} (solo {percentage:.1f}%)"
                    )
                elif percentage > 50 and cat != "GENERAL":
                    recommendations.append(
                        f"📊 Tienes mucho contenido de {cat} ({percentage:.1f}%), considera diversificar"
                    )
        
        return {
            "success": True,
            "total_texts": total,
            "total_images": len(images),
            "distribution": distribution,
            "percentages": {
                cat: (count / total * 100) if total > 0 else 0
                for cat, count in distribution.items()
            },
            "recommendations": recommendations
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """
    Punto de entrada principal de la aplicación.
    Lanza la GUI en un perfil de Chrome separado y desechable ('gui_profile')
    para evitar conflictos con el perfil principal que usará el bot de Selenium.
    """
    try:
        import os

        # Creamos una ruta absoluta para el perfil de la GUI.
        gui_profile_path = os.path.abspath('gui_profile')

        # Definimos los argumentos de línea de comandos para lanzar Chrome
        # en modo 'app' y con un perfil de datos de usuario separado.
        eel_cmdline_args = [
            f'--user-data-dir={gui_profile_path}'  # Usa un perfil de datos dedicado
        ]
        
        print(f"Iniciando GUI con perfil dedicado en: {gui_profile_path}")
        
        # Iniciamos Eel. Pasamos los argumentos de línea de comandos para
        # controlar cómo se lanza Chrome.
        eel.start(
            'index.html',
            size=(1400, 900),
            mode='chrome',  # Solo una definición del modo
            cmdline_args=eel_cmdline_args,
            block=True
        )

    except (SystemExit, KeyboardInterrupt):
        print("Cierre de la aplicación solicitado por el usuario.")
    except Exception as e:
        print(f"No se pudo iniciar la interfaz gráfica: {e}")
    finally:
        if 'app_logic' in locals() and app_logic:
            app_logic.shutdown()
        
 
 