import os
import shutil
from datetime import datetime
import uuid
from database import db_manager

# Configuración
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(PROJECT_ROOT, 'images')

# Asegurarse de que el directorio de imágenes existe
os.makedirs(IMAGES_DIR, exist_ok=True)

def get_relative_path(absolute_path):
    """Convierte una ruta absoluta a relativa al directorio del proyecto."""
    return os.path.relpath(absolute_path, PROJECT_ROOT)

def get_absolute_path(relative_path):
    """Convierte una ruta relativa a absoluta."""
    return os.path.abspath(os.path.join(PROJECT_ROOT, relative_path))

def validate_image_path(image_path):
    """Verifica si una imagen existe y devuelve su ruta absoluta o None."""
    # Si es una ruta relativa, intentar convertir a absoluta
    if not os.path.isabs(image_path):
        image_path = get_absolute_path(image_path)
    
    return image_path if os.path.exists(image_path) else None

def save_image(source_path, tags=None):
    """
    Guarda una imagen en el directorio de imágenes del proyecto.
    Devuelve la ruta relativa a la imagen guardada o None si falla.
    """
    try:
        # Validar que el archivo fuente existe
        if not os.path.exists(source_path):
            return None
            
        # Crear un nombre de archivo único
        ext = os.path.splitext(source_path)[1].lower()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}{ext}"
        dest_path = os.path.join(IMAGES_DIR, filename)
        
        # Copiar la imagen al directorio de imágenes
        shutil.copy2(source_path, dest_path)
        
        # Obtener la ruta relativa para almacenar en la base de datos
        relative_path = get_relative_path(dest_path)
        
        # Guardar en la base de datos
        cursor = db_manager.conn.cursor()
        cursor.execute(
            "INSERT INTO images (path, manual_tags) VALUES (?, ?)",
            (relative_path, ",".join(tags) if tags else None)
        )
        db_manager.conn.commit()
        
        return relative_path
        
    except Exception as e:
        print(f"Error al guardar la imagen: {e}")
        return None

def get_image_path(image_id):
    """Obtiene la ruta absoluta de una imagen por su ID."""
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT path FROM images WHERE id = ?", (image_id,))
    result = cursor.fetchone()
    
    if not result:
        return None
        
    relative_path = result[0]
    absolute_path = get_absolute_path(relative_path)
    
    # Verificar si el archivo existe
    return absolute_path if os.path.exists(absolute_path) else None

def cleanup_images():
    """Elimina imágenes que existen en la base de datos pero no en el sistema de archivos."""
    cursor = db_manager.conn.cursor()
    
    # Obtener todas las imágenes de la base de datos
    cursor.execute("SELECT id, path FROM images")
    images = cursor.fetchall()
    
    deleted_count = 0
    
    for img_id, relative_path in images:
        absolute_path = get_absolute_path(relative_path)
        
        # Si el archivo no existe, eliminarlo de la base de datos
        if not os.path.exists(absolute_path):
            cursor.execute("DELETE FROM images WHERE id = ?", (img_id,))
            # También limpiar referencias en otras tablas
            cursor.execute("DELETE FROM group_image_usage_log WHERE image_id = ?", (img_id,))
            cursor.execute("DELETE FROM page_image_usage WHERE image_id = ?", (img_id,))
            cursor.execute("UPDATE scheduled_posts SET image_id = NULL WHERE image_id = ?", (img_id,))
            deleted_count += 1
    
    if deleted_count > 0:
        db_manager.conn.commit()
    
    return deleted_count
