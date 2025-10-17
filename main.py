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
            profile_path = os.path.abspath('automation_profile')
            is_first_run = not os.path.exists(profile_path)

            service = ChromeService(ChromeDriverManager().install())
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

    def _create_post_on_facebook(self, text_content, image_path=None, max_retries=3):
        """
        Crea una publicación en Facebook con manejo robusto de errores y reintentos.
        
        Args:
            text_content: Contenido de texto para la publicación
            image_path: Ruta opcional de la imagen
            max_retries: Número máximo de reintentos por operación
            
        Returns:
            dict: {"success": bool, "post_url": str, "error": str, "should_discard_group": bool}
        """
        # VALIDACIÓN PREVIA DE IMAGEN
        image_validation = self._validate_image_path(image_path)
        if not image_validation["valid"]:
            self.log_to_panel(f"🖼️ IMAGEN INVÁLIDA: {image_validation['error']}")
            # Si la imagen no es válida, intentar publicar solo texto
            if image_validation["error"] in ["Archivo no encontrado", "No es un archivo"]:
                self.log_to_panel("📝 Continuando con publicación SOLO TEXTO...")
                image_path = None
            else:
                # Otros errores (tamaño, formato) son más críticos
                return {
                    "success": False, 
                    "error": f"Imagen inválida: {image_validation['error']}", 
                    "should_discard_group": False,
                    "image_invalid": True
                }
        else:
            # Si la imagen es válida, usar la ruta absoluta validada
            if image_validation["path"]:
                image_path = image_validation["path"]
        
        for attempt in range(max_retries):
            try:
                # 1. Abrir el modal de publicación con reintentos
                self.log_to_panel(f"Intento {attempt + 1}/{max_retries}: Abriendo cuadro de publicación...")
                
                # Múltiples selectores para encontrar el cuadro de publicación
                open_button_selectors = [
                    '//div[contains(@aria-label, "Crear una publicación")]',
                    '//*[contains(text(), "Escribe algo")]',
                    '//div[contains(@role, "button") and contains(text(), "Escribe algo")]',
                    '//div[contains(@aria-label, "¿En qué estás pensando")]',
                    '//div[contains(@aria-label, "What\'s on your mind")]',
                    '//*[contains(@placeholder, "Escribe algo")]'
                ]
                
                open_button = None
                for selector in open_button_selectors:
                    try:
                        open_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        self.log_to_panel(f"✓ Cuadro encontrado con selector: {selector}")
                        break
                    except TimeoutException:
                        continue
                
                if not open_button:
                    if attempt == max_retries - 1:
                        self.log_to_panel("❌ ERROR CRÍTICO: No se encontró el cuadro de publicación después de todos los intentos")
                        return {
                            "success": False, 
                            "error": "Cuadro de publicación no encontrado", 
                            "should_discard_group": True
                        }
                    self.log_to_panel(f"⚠️ Intento {attempt + 1} fallido. Reintentando en 5 segundos...")
                    time.sleep(5)
                    continue
                
                # Intentar hacer click con JavaScript como respaldo
                try:
                    open_button.click()
                except Exception as click_error:
                    self.log_to_panel(f"⚠️ Click normal falló, usando JavaScript: {click_error}")
                    self.driver.execute_script("arguments[0].click();", open_button)
                
                self.log_to_panel("✓ Cuadro de publicación abierto. Esperando estabilización...")
                time.sleep(random.uniform(2, 4))

                # 2. Escribir el texto con validación mejorada
                self.log_to_panel("Identificando campo de texto activo...")
                
                # Intentar múltiples métodos para encontrar el campo de texto
                post_box = None
                text_field_methods = [
                    lambda: self.driver.switch_to.active_element,
                    lambda: self.driver.find_element(By.XPATH, "//div[@role='textbox']"),
                    lambda: self.driver.find_element(By.XPATH, "//div[@contenteditable='true']"),
                    lambda: self.driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Escribe algo')]"),
                    lambda: self.driver.find_element(By.XPATH, "//textarea")
                ]
                
                for method in text_field_methods:
                    try:
                        post_box = method()
                        if post_box and post_box.is_enabled():
                            break
                    except:
                        continue
                
                if not post_box:
                    if attempt == max_retries - 1:
                        self.log_to_panel("❌ ERROR CRÍTICO: Campo de texto no encontrado - Grupo problemático")
                        return {
                            "success": False, 
                            "error": "Campo de texto no encontrado", 
                            "should_discard_group": True
                        }
                    self.log_to_panel(f"⚠️ Campo de texto no encontrado en intento {attempt + 1}. Reintentando...")
                    time.sleep(3)
                    continue
                
                # Escribir texto caracter por caracter con verificación
                self.log_to_panel("✓ Escribiendo contenido...")
                post_box.clear()  # Limpiar contenido previo
                for char in text_content:
                    post_box.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.1))
                
                # Verificar que el texto se escribió correctamente
                written_text = post_box.get_attribute('textContent') or post_box.get_attribute('value') or ""
                if len(written_text.strip()) < len(text_content.strip()) * 0.8:  # 80% del texto esperado
                    self.log_to_panel("⚠️ Verificación de texto falló. Reintentando...")
                    continue
                
                break  # Si llegamos aquí, la escritura fue exitosa
                
            except Exception as e:
                self.log_to_panel(f"❌ Error en intento {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return {
                        "success": False, 
                        "error": f"Error después de {max_retries} intentos: {str(e)}", 
                        "should_discard_group": False
                    }
                time.sleep(5)
        
        # 3. Lógica de subida de imágenes con reintentos
        try:
            if image_path:
                for img_attempt in range(max_retries):
                    self.log_to_panel(f"Intento de subida {img_attempt + 1}/{max_retries}")
                    dialog_xpath = "//div[@role='dialog']"
                    file_input_element = None
                    
                    # Múltiples selectores para el input de archivos
                    file_input_selectors = [
                        f"{dialog_xpath}//input[@type='file' and @multiple]",
                        f"{dialog_xpath}//input[@type='file' and not(@multiple)]",
                        "//input[@type='file'][@multiple]",
                        "//input[@type='file']",
                    ]
                
                    for selector in file_input_selectors:
                        try:
                            file_input_element = self.driver.find_element(By.XPATH, selector)
                            if file_input_element:
                                self.log_to_panel(f"✓ Input encontrado: {selector}")
                                break
                        except:
                            continue
                    
                    if not file_input_element:
                        if img_attempt == max_retries - 1:
                            self.log_to_panel("❌ No se pudo localizar input para subir archivos")
                            self.driver.save_screenshot(f"debug_error_input_{int(time.time())}.png")
                            return {"success": False, "error": "Input de archivos no encontrado", "should_discard_group": False}
                        time.sleep(3)
                        continue
                
                    try:
                        self.log_to_panel(f"✓ Subiendo imagen: {os.path.basename(image_path)}")
                        file_input_element.send_keys(image_path)
                    
                        # Esperar confirmación de carga con múltiples indicadores
                        preview_selectors = [
                            f"{dialog_xpath}//div[contains(@aria-label, 'foto')]",
                            f"{dialog_xpath}//a[contains(@aria-label, 'Eliminar')]",
                            f"{dialog_xpath}//img[@alt]",
                            "//div[contains(@aria-label, 'foto')]"
                        ]
                        
                        preview_found = False
                        for selector in preview_selectors:
                            try:
                                WebDriverWait(self.driver, 30).until(
                                    EC.presence_of_element_located((By.XPATH, selector))
                                )
                                preview_found = True
                                break
                            except TimeoutException:
                                continue
                        
                        if preview_found:
                            self.log_to_panel("✓ Imagen cargada correctamente")
                            time.sleep(random.uniform(2, 4))
                            break
                        else:
                            self.log_to_panel(f"⚠️ Vista previa no encontrada en intento {img_attempt + 1}")
                            if img_attempt < max_retries - 1:
                                time.sleep(3)
                                continue
                            
                    except Exception as upload_error:
                        self.log_to_panel(f"⚠️ Error en subida {img_attempt + 1}: {upload_error}")
                        if img_attempt == max_retries - 1:
                            return {"success": False, "error": f"Error de subida: {str(upload_error)}", "should_discard_group": False}
                        time.sleep(3)

            # 4. Hacer clic en 'Publicar' con reintentos mejorados
            self.log_to_panel("Buscando botón 'Publicar'...")
            
            publish_selectors = [
                "//div[@aria-label='Publicar' and @role='button' and not(@aria-disabled='true')]",
                "//div[@aria-label='Publish' and @role='button' and not(@aria-disabled='true')]",
                "//button[contains(text(), 'Publicar')]",
                "//button[contains(text(), 'Publish')]",
                "//div[@role='button'][contains(text(), 'Publicar')]"
            ]
            
            publish_button = None
            for selector in publish_selectors:
                try:
                    publish_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if publish_button:
                        break
                except TimeoutException:
                    continue
            
            if not publish_button:
                self.log_to_panel("❌ Botón de publicar no encontrado")
                return {"success": False, "error": "Botón de publicar no encontrado", "should_discard_group": True}
            
            # Intentar click con reintentos
            for pub_attempt in range(max_retries):
                try:
                    if pub_attempt > 0:
                        self.log_to_panel(f"Reintento de publicación {pub_attempt + 1}/{max_retries}")
                    
                    # Scroll hasta el botón si es necesario
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", publish_button)
                    time.sleep(1)
                    
                    # Intentar click normal, luego JavaScript
                    try:
                        publish_button.click()
                    except Exception:
                        self.log_to_panel("⚠️ Click normal falló, usando JavaScript...")
                        self.driver.execute_script("arguments[0].click();", publish_button)
                    
                    self.log_to_panel("✓ Publicación enviada")
                    break
                    
                except Exception as pub_error:
                    if pub_attempt == max_retries - 1:
                        return {"success": False, "error": f"Error al publicar: {str(pub_error)}", "should_discard_group": False}
                    time.sleep(2)
        
            # 5. Rastreo de URL con múltiples métodos
            self.log_to_panel("Intentando rastrear URL de la publicación...")
            post_url = None
        
            # MÉTODO 1: Buscar pop-up "Ver publicación"
            view_post_selectors = [
                "//a[.//span[contains(text(), 'Ver publicación')]]",
                "//a[contains(text(), 'Ver publicación')]",
                "//a[.//span[contains(text(), 'View post')]]",
                "//a[contains(text(), 'View post')]"
            ]
            
            for selector in view_post_selectors:
                try:
                    view_post_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    post_url = view_post_button.get_attribute('href')
                    if post_url:
                        self.log_to_panel(f"✓ URL encontrada: {post_url}")
                        break
                except TimeoutException:
                    continue
            
            # MÉTODO 2: Buscar por enlaces de tiempo
            if not post_url:
                time_selectors = [
                    "//a[contains(text(), 'Justo ahora')]",
                    "//a[contains(text(), 'minuto')]",
                    "//a[contains(text(), 'Just now')]",
                    "//a[contains(text(), 'minute')]"
                ]
                
                for selector in time_selectors:
                    try:
                        post_link_element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        post_url = post_link_element.get_attribute('href')
                        if post_url:
                            self.log_to_panel(f"✓ URL encontrada por tiempo: {post_url}")
                            break
                    except TimeoutException:
                        continue
            
            if not post_url:
                self.log_to_panel("⚠️ No se pudo rastrear la URL, pero la publicación probablemente fue exitosa")
            
            return {"success": True, "post_url": post_url, "should_discard_group": False}
        
        except Exception as e:
            self.log_to_panel(f"❌ Error fatal durante la creación de la publicación: {e}")
            self.driver.save_screenshot(f"debug_error_fatal_{int(time.time())}.png")
            return {"success": False, "error": str(e), "should_discard_group": False}

    def _find_coherent_pair_for_group(self, group_tags_str):
        """
        Encuentra un par de texto e imagen coherentes basándose en las etiquetas
        y respetando los límites de uso:
        - Imágenes: 10 total, 1 por día.
        - Textos: 10 total, 3 por día.
        """
        # 1. Encontrar una IMAGEN usable con validación de archivo.
        #    - Menos de 10 usos en total.
        #    - Que NO HAYA SIDO USADA HOY (límite de 1 por día).
        #    - Que el archivo exista físicamente.
        usable_images_query = """
            SELECT i.id, i.path, i.manual_tags FROM images i
            WHERE
                (SELECT COUNT(*) FROM group_image_usage_log WHERE image_id = i.id) < 10
            AND
                i.id NOT IN (
                    SELECT image_id FROM group_image_usage_log WHERE DATE(timestamp) = DATE('now')
                )
        """
        all_usable_images = db_manager.fetch_all(usable_images_query)
        if not all_usable_images:
            self.log_to_panel("No hay imágenes usables disponibles (respetando límites de 1/día).")
            return None, None

        # NUEVA LÓGICA: Filtrar imágenes que físicamente existen
        valid_images = []
        for image in all_usable_images:
            validation = self._validate_image_path(image['path'])
            if validation["valid"]:
                valid_images.append(image)
            else:
                self.log_to_panel(f"🖼️ Imagen ID {image['id']} omitida: {validation['error']}")
        
        if not valid_images:
            self.log_to_panel("❌ No hay imágenes válidas disponibles después de la validación.")
            self.log_to_panel("💡 Ejecuta validate_images() para limpiar la base de datos.")
            return None, None
            
        random.shuffle(valid_images)
        image_to_use = valid_images[0]
        self.log_to_panel(f"✅ Imagen validada: {os.path.basename(image_to_use['path'])}")
        image_tags = {tag.strip().lower() for tag in image_to_use['manual_tags'].split(',') if tag.strip()}

        # 2. Encontrar un TEXTO coherente y usable (NUEVA LÓGICA).
        #    - Menos de 10 usos en total (usage_count).
        #    - Menos de 3 usos en el día actual.
        texts_query = """
            SELECT t.id, t.content, t.ai_tags, t.usage_count FROM texts t
            WHERE
                t.usage_count < 10
            AND
                (SELECT COUNT(*) FROM group_text_usage_log WHERE text_id = t.id AND DATE(timestamp) = DATE('now')) < 3
        """
        all_usable_texts = db_manager.fetch_all(texts_query)
        if not all_usable_texts:
            self.log_to_panel("No hay textos usables disponibles (respetando límites de 3/día).")
            return None, None

        # Filtrar textos por coherencia con la imagen seleccionada
        coherent_texts = []
        for text in all_usable_texts:
            if text.get('ai_tags'):
                text_ai_tags = {tag.strip().lower() for tag in text['ai_tags'].split(',') if tag.strip()}
                if not image_tags.isdisjoint(text_ai_tags):
                    coherent_texts.append(text)

        if not coherent_texts:
            self.log_to_panel(f"No se encontró un texto coherente y usable para la imagen seleccionada.")
            return None, None

        text_to_use = random.choice(coherent_texts)
        self.log_to_panel(f"Match encontrado: Imagen ID {image_to_use['id']} con Texto ID {text_to_use['id']} (usado {text_to_use['usage_count']} veces)")

        return text_to_use, image_to_use
    
    # Dentro de la clase AppLogic en main.py

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
                    self.log_to_panel("Proceso detenido por el usuario.")
                    break
            
                self.log_to_panel(f"({i+1}/{len(groups_to_publish)}) Preparando publicación para: {group['url']}")
            
                text, image = self._find_coherent_pair_for_group(content_tags.split(','))
            
                if not text or not image:
                    self.log_to_panel("No se encontró un par de contenido coherente y usable. Saltando grupo.")
                    continue

                # Lista de grupos problemáticos para tracking
                problematic_groups = []
                
                try:
                    self.log_to_panel(f"🌐 Navegando al grupo: {group['url']}")
                    self.driver.get(group["url"])
                    
                    # Espera más inteligente - verificar que la página haya cargado
                    try:
                        WebDriverWait(self.driver, 15).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                        self.log_to_panel("✓ Página cargada completamente")
                    except TimeoutException:
                        self.log_to_panel("⚠️ Página tardó en cargar, continuando...")
                    
                    time.sleep(random.uniform(3, 5))  # Tiempo reducido tras verificación
                
                    # Intentar publicar con manejo mejorado de errores
                    result = self._create_post_on_facebook(text['content'], image['path'])
                    
                    # Manejo específico de grupos problemáticos
                    if result.get('should_discard_group', False):
                        self.log_to_panel(f"🚨 GRUPO PROBLEMÁTICO DETECTADO: {group['url']}")
                        self.log_to_panel(f"💡 Razón: {result.get('error', 'Desconocida')}")
                        
                        # Marcar grupo como problemático en la base de datos
                        try:
                            db_manager.execute_query(
                                "UPDATE groups SET tags = CASE WHEN tags LIKE '%PROBLEMÁTICO%' THEN tags ELSE tags || ',PROBLEMÁTICO' END WHERE id = ?", 
                                (group['id'],)
                            )
                            self.log_to_panel(f"🏷️ Grupo marcado como PROBLEMÁTICO en la base de datos")
                        except Exception as tag_error:
                            self.log_to_panel(f"⚠️ Error marcando grupo: {tag_error}")
                        
                        # Registrar en log especial
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "Failed - Problematic Group",
                            "target_type": "Group",
                            "target_url": group['url'],
                            "text_content": text['content'],
                            "image_path": image['path'],
                            "published_post_url": None,
                            "error_details": result.get('error', '')
                        }
                        
                        db_manager.execute_query("""
                            INSERT INTO publication_log (timestamp, status, target_type, target_url, text_content, image_path, published_post_url)
                            VALUES (:timestamp, :status, :target_type, :target_url, :text_content, :image_path, :published_post_url)
                        """, log_data)
                        
                        self.log_to_panel("⏭️ Saltando al siguiente grupo...")
                        continue
                    
                    # Registro normal de resultados
                    status = "Success" if result['success'] else "Failed"
                    log_data = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": status,
                        "target_type": "Group",
                        "target_url": group['url'],
                        "text_content": text['content'],
                        "image_path": image['path'],
                        "published_post_url": result.get('post_url'),
                        "error_details": result.get('error', '') if not result['success'] else ""
                    }
                
                    db_manager.execute_query("""
                        INSERT INTO publication_log (timestamp, status, target_type, target_url, text_content, image_path, published_post_url)
                        VALUES (:timestamp, :status, :target_type, :target_url, :text_content, :image_path, :published_post_url)
                    """, log_data)
                
                    if result['success']:
                        self.log_to_panel(f"✅ Publicación exitosa en {group['url']}")
                        
                        # Registrar uso de imagen y texto
                        db_manager.execute_query(
                            "INSERT INTO group_image_usage_log (image_id, group_id, timestamp) VALUES (?, ?, ?)",
                            (image['id'], group['id'], datetime.now())
                        )
                        db_manager.execute_query(
                            "INSERT INTO group_text_usage_log (text_id, group_id, timestamp) VALUES (?, ?, ?)",
                            (text['id'], group['id'], datetime.now())
                        )
                        db_manager.execute_query(
                            "UPDATE texts SET usage_count = usage_count + 1 WHERE id = ?", 
                            (text['id'],)
                        )
                        
                        self.log_to_panel(f"📊 Contadores actualizados - Texto ID: {text['id']}, Imagen ID: {image['id']}")
                        
                        if result.get('post_url'):
                            self.log_to_panel(f"🔗 URL de la publicación: {result['post_url']}")
                    else:
                        self.log_to_panel(f"❌ Falló la publicación en {group['url']}")
                        if result.get('error'):
                            self.log_to_panel(f"💬 Detalles del error: {result['error']}")
                            
                except WebDriverException as web_error:
                    error_msg = f"Error de navegador en {group['url']}: {str(web_error)}"
                    self.log_to_panel(f"🌐 {error_msg}")
                    
                    # Log del error de navegación
                    db_manager.execute_query("""
                        INSERT INTO publication_log (timestamp, status, target_type, target_url, text_content, image_path, published_post_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Failed - Navigation Error", 
                          "Group", group['url'], text['content'], image['path'], None))
                          
                except Exception as e:
                    error_msg = f"Error inesperado en {group['url']}: {str(e)}"
                    self.log_to_panel(f"💥 {error_msg}")
                    
                    # Screenshot para debugging
                    try:
                        screenshot_name = f"error_group_{group['id']}_{int(time.time())}.png"
                        self.driver.save_screenshot(screenshot_name)
                        self.log_to_panel(f"📷 Screenshot guardado: {screenshot_name}")
                    except:
                        pass

                if i < len(groups_to_publish) - 1:
                    wait_time = random.randint(60, 120)
                    self.log_to_panel(f"Esperando {wait_time} segundos...")
                    time.sleep(wait_time)
    
        finally:
            self.log_to_panel("Finalizando proceso de publicación en grupos.")
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
        self.running_groups_process = False
        self.close_browser()
        self.log_to_panel("Proceso de publicación en grupos detenido.")
        return {"success": True}
    
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
                
            except sqlite3.Error as e:
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
        
 