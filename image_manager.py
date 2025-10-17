import os
import shutil
import uuid
from datetime import datetime
from database import db_manager

class ImageManager:
    def __init__(self):
        self.images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
        os.makedirs(self.images_dir, exist_ok=True)
    
    def get_absolute_path(self, relative_path):
        """Convierte una ruta relativa a absoluta."""
        return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path))
    
    def validate_image(self, image_path):
        """Valida si una imagen existe y es accesible."""
        try:
            if not os.path.isabs(image_path):
                image_path = self.get_absolute_path(image_path)
            return os.path.exists(image_path) and os.path.isfile(image_path)
        except Exception:
            return False
    
    def add_image(self, source_path, tags=None):
        """
        Añade una imagen al sistema de gestión de imágenes.
        
        Args:
            source_path (str): Ruta absoluta o relativa a la imagen de origen
            tags (list, optional): Lista de etiquetas para la imagen
            
        Returns:
            dict: Diccionario con el resultado de la operación
        """
        try:
            # Validar ruta de origen
            if not self.validate_image(source_path):
                return {
                    'success': False,
                    'message': f'La imagen no existe o no es accesible: {source_path}'
                }
            
            # Generar un nombre de archivo único
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}{os.path.splitext(source_path)[1]}"
            dest_path = os.path.join(self.images_dir, filename)
            
            # Copiar la imagen al directorio de imágenes
            shutil.copy2(source_path, dest_path)
            
            # Guardar en la base de datos (ruta relativa)
            relative_path = os.path.relpath(dest_path, os.path.dirname(os.path.abspath(__file__)))
            
            cursor = db_manager.conn.cursor()
            cursor.execute(
                "INSERT INTO images (path, manual_tags) VALUES (?, ?)",
                (relative_path, ",".join(tags) if tags else None)
            )
            db_manager.conn.commit()
            
            return {
                'success': True,
                'image_id': cursor.lastrowid,
                'path': relative_path,
                'absolute_path': dest_path
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al agregar la imagen: {str(e)}'
            }
    
    def get_image(self, image_id):
        """Obtiene la información de una imagen por su ID."""
        try:
            cursor = db_manager.conn.cursor()
            cursor.execute("SELECT * FROM images WHERE id = ?", (image_id,))
            result = cursor.fetchone()
            
            if not result:
                return None
                
            image_data = dict(result)
            abs_path = self.get_absolute_path(image_data['path'])
            
            return {
                'id': image_data['id'],
                'path': image_data['path'],
                'absolute_path': abs_path,
                'tags': image_data['manual_tags'].split(',') if image_data['manual_tags'] else [],
                'exists': os.path.exists(abs_path)
            }
            
        except Exception as e:
            print(f"Error al obtener imagen {image_id}: {e}")
            return None
    
    def cleanup_images(self):
        """
        Limpia las imágenes que están en la base de datos pero no en el sistema de archivos.
        
        Returns:
            dict: Diccionario con el resultado de la operación
        """
        try:
            cursor = db_manager.conn.cursor()
            
            # Obtener todas las imágenes de la base de datos
            cursor.execute("SELECT id, path FROM images")
            images = cursor.fetchall()
            
            deleted_count = 0
            
            for img_id, relative_path in images:
                abs_path = self.get_absolute_path(relative_path)
                
                # Si el archivo no existe, eliminarlo de la base de datos
                if not os.path.exists(abs_path):
                    # Eliminar referencias en otras tablas
                    cursor.execute("DELETE FROM group_image_usage_log WHERE image_id = ?", (img_id,))
                    cursor.execute("DELETE FROM page_image_usage WHERE image_id = ?", (img_id,))
                    cursor.execute("UPDATE scheduled_posts SET image_id = NULL WHERE image_id = ?", (img_id,))
                    # Eliminar la imagen
                    cursor.execute("DELETE FROM images WHERE id = ?", (img_id,))
                    deleted_count += 1
            
            if deleted_count > 0:
                db_manager.conn.commit()
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Se eliminaron {deleted_count} imágenes inválidas de la base de datos.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error al limpiar imágenes: {str(e)}'
            }

# Instancia global para ser usada en toda la aplicación
image_manager = ImageManager()
