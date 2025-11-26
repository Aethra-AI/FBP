# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="marketing_tool.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row # Permite acceder a las columnas por nombre
        self.setup_tables()
        self.setup_image_validation_trigger()

    def setup_image_validation_trigger(self):
        """Configura un trigger para validar imágenes al insertar/actualizar."""
        cursor = self.conn.cursor()
        
        # Crear una tabla para almacenar las imágenes no válidas temporalmente
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invalid_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            error_message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE
        );
        """)
        
        # Crear trigger para validar imágenes al insertar/actualizar
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS validate_image_on_insert
        AFTER INSERT ON images
        BEGIN
            INSERT INTO invalid_images (image_id, error_message)
            SELECT NEW.id, 'Image file does not exist'
            WHERE NOT EXISTS (
                SELECT 1 
                FROM images 
                WHERE id = NEW.id 
                AND path IS NOT NULL 
                AND path != ''
                AND EXISTS (
                    SELECT 1 FROM pragma_table_info('images') 
                    WHERE name = 'path' AND type = 'TEXT'
                )
            );
        END;
        """)
        
        self.conn.commit()

    def validate_image_exists(self, image_id):
        """Verifica si una imagen existe en el sistema de archivos."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT path FROM images WHERE id = ?", (image_id,))
        result = cursor.fetchone()
        
        if not result or not result['path']:
            return False
            
        # Usar la función de utilidad para validar la ruta
        from image_utils import validate_image_path
        return validate_image_path(result['path']) is not None

    def get_image_path(self, image_id):
        """Obtiene la ruta de la imagen, verificando su existencia."""
        if not self.validate_image_exists(image_id):
            return None
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT path FROM images WHERE id = ?", (image_id,))
        result = cursor.fetchone()
        
        if not result:
            return None
            
        from image_utils import get_absolute_path
        return get_absolute_path(result['path'])

    def add_image(self, image_path, tags=None):
        """
        Añade una imagen a la base de datos usando el sistema de gestión de imágenes.
        Devuelve el ID de la imagen o None si falla.
        """
        from image_utils import save_image
        relative_path = save_image(image_path, tags)
        
        if not relative_path:
            return None
            
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM images WHERE path = ?", 
            (relative_path,)
        )
        result = cursor.fetchone()
        
        return result['id'] if result else None

    def cleanup_invalid_images(self):
        """
        Limpia las imágenes que ya no existen en el sistema de archivos.
        Devuelve el número de imágenes eliminadas.
        """
        from image_utils import cleanup_images
        return cleanup_images()

    def setup_tables(self):
        cursor = self.conn.cursor()
        
        # --- TABLAS DE CONTENIDO ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                ai_tags TEXT,
                usage_count INTEGER DEFAULT 0
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                manual_tags TEXT,
                usage_count INTEGER DEFAULT 0
            );
        """)

        # --- TABLAS DE DESTINO ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                tags TEXT
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                page_url TEXT NOT NULL UNIQUE
            );
        """)
        
        # --- TABLAS DE REGISTRO DE USO ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_image_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER,
                group_id INTEGER,
                timestamp DATETIME,
                FOREIGN KEY(image_id) REFERENCES images(id),
                FOREIGN KEY(group_id) REFERENCES groups(id)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_text_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_id INTEGER,
                group_id INTEGER,
                timestamp DATETIME,
                FOREIGN KEY(text_id) REFERENCES texts(id),
                FOREIGN KEY(group_id) REFERENCES groups(id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_image_usage (
                page_id INTEGER,
                image_id INTEGER,
                PRIMARY KEY (page_id, image_id),
                FOREIGN KEY(page_id) REFERENCES pages(id),
                FOREIGN KEY(image_id) REFERENCES images(id)
            );
        """)

        # --- TABLAS DE OPERACIONES ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER,
                publish_at DATETIME NOT NULL,
                text_content TEXT,
                image_id INTEGER,
                status TEXT DEFAULT 'pending', /* pending, processing, completed, failed */
                FOREIGN KEY(page_id) REFERENCES pages(id),
                FOREIGN KEY(image_id) REFERENCES images(id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publication_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                status TEXT NOT NULL, /* Success, Failed */
                target_type TEXT NOT NULL, /* group, page */
                target_url TEXT,
                text_content TEXT,
                image_path TEXT,
                published_post_url TEXT
            );
        """)

        # --- MIGRACIÓN: Añadir columna usage_count a texts si no existe ---
        try:
            # Intenta seleccionar la columna para ver si existe.
            cursor.execute("SELECT usage_count FROM texts LIMIT 1")
        except sqlite3.OperationalError:
            # Si no existe, la añade.
            print("Realizando migración: Añadiendo 'usage_count' a la tabla 'texts'...") # <-- LÍNEA MODIFICADA
            cursor.execute("ALTER TABLE texts ADD COLUMN usage_count INTEGER DEFAULT 0")

        # --- MIGRACIÓN: Añadir columna usage_count a images si no existe ---
        try:
            cursor.execute("SELECT usage_count FROM images LIMIT 1")
        except sqlite3.OperationalError:
            print("Realizando migración: Añadiendo 'usage_count' a la tabla 'images'...")
            cursor.execute("ALTER TABLE images ADD COLUMN usage_count INTEGER DEFAULT 0")

        # --- MIGRACIÓN: Añadir columna error_details a publication_log si no existe ---
        try:
            # Intenta seleccionar la columna para ver si existe.
            cursor.execute("SELECT error_details FROM publication_log LIMIT 1")
        except sqlite3.OperationalError:
            # Si no existe, la añade.
            print("Realizando migración: Añadiendo 'error_details' a la tabla 'publication_log'...")
            cursor.execute("ALTER TABLE publication_log ADD COLUMN error_details TEXT")

        # --- NUEVAS TABLAS PARA SESIONES ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                chrome_profile TEXT NOT NULL,
                group_tags TEXT,
                content_tags TEXT,
                publication_type TEXT DEFAULT 'text-and-image',
                status TEXT DEFAULT 'inactive',
                current_group_index INTEGER DEFAULT 0,
                total_groups INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                message TEXT,
                message_type TEXT DEFAULT 'info',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            );
        """)

        # --- TABLAS PARA SISTEMA DE CHATBOT ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                action_taken TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                context JSON
            );
        """)

        # --- TABLAS PARA CATEGORIZACIÓN INTELIGENTE ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                keywords TEXT,
                color TEXT,
                icon TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS text_categories (
                text_id INTEGER,
                category TEXT NOT NULL,
                confidence_score FLOAT DEFAULT 0.0,
                PRIMARY KEY (text_id, category),
                FOREIGN KEY (text_id) REFERENCES texts(id) ON DELETE CASCADE
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_categories (
                image_id INTEGER,
                category TEXT NOT NULL,
                confidence_score FLOAT DEFAULT 0.0,
                PRIMARY KEY (image_id, category),
                FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
            );
        """)

        self.conn.commit()
        
    # --- MÉTODOS PARA OBTENER DATOS ---
    def get_all_data(self):
        cursor = self.conn.cursor()
        
        texts = [dict(row) for row in cursor.execute("SELECT * FROM texts ORDER BY id DESC").fetchall()]
        images = [dict(row) for row in cursor.execute("SELECT * FROM images ORDER BY id DESC").fetchall()]
        groups = [dict(row) for row in cursor.execute("SELECT * FROM groups ORDER BY id DESC").fetchall()]
        pages = [dict(row) for row in cursor.execute("SELECT * FROM pages ORDER BY id DESC").fetchall()]
        
        # Obtener scheduled posts con el nombre de la página
        scheduled_posts = [dict(row) for row in cursor.execute("""
            SELECT sp.*, p.name as page_name, i.path as image_path
            FROM scheduled_posts sp
            JOIN pages p ON sp.page_id = p.id
            LEFT JOIN images i ON sp.image_id = i.id
            ORDER BY sp.publish_at ASC
        """).fetchall()]

        # Obtener sesiones
        sessions = [dict(row) for row in cursor.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()]

        return {
            "texts": texts,
            "images": images,
            "groups": groups,
            "pages": pages,
            "scheduled_posts": scheduled_posts,
            "sessions": sessions
        }

    # --- MÉTODOS PARA ELIMINAR DATOS ---
    def delete_item(self, table, item_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # --- MÉTODOS PARA GESTIÓN DE SESIONES ---
    
    def create_session(self, name, chrome_profile, group_tags="", content_tags="", publication_type="text-and-image"):
        """Crea una nueva sesión en la base de datos."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (name, chrome_profile, group_tags, content_tags, publication_type)
                VALUES (?, ?, ?, ?, ?)
            """, (name, chrome_profile, group_tags, content_tags, publication_type))
            self.conn.commit()
            return {"success": True, "id": cursor.lastrowid}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def update_session_status(self, session_id, status, current_group_index=0, total_groups=0):
        """Actualiza el estado de una sesión."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE sessions 
                SET status = ?, current_group_index = ?, total_groups = ?, last_activity = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, current_group_index, total_groups, session_id))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_session(self, session_id):
        """Obtiene una sesión específica."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def get_session_logs(self, session_id, limit=50):
        """Obtiene los logs de una sesión específica."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM session_logs 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (session_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def log_session_message(self, session_id, message, message_type="info"):
        """Registra un mensaje en el log de una sesión."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO session_logs (session_id, message, message_type)
                VALUES (?, ?, ?)
            """, (session_id, message, message_type))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def delete_session(self, session_id):
        """Elimina una sesión y todos sus logs."""
        try:
            cursor = self.conn.cursor()
            # Eliminar logs primero
            cursor.execute("DELETE FROM session_logs WHERE session_id = ?", (session_id,))
            # Eliminar sesión
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    # --- Métodos específicos para la lógica de la aplicación ---
    
    # ... (Se añadirán más métodos según los necesite AppLogic) ...

    def execute_query(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def fetch_all(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def fetch_one(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

# Instancia global para ser usada por toda la aplicación
db_manager = DatabaseManager()