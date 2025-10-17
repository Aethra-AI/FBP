# -*- coding: utf-8 -*-
import os
import sqlite3
from database import db_manager

def validate_images():
    """
    Función para validar y limpiar imágenes de la base de datos que ya no existen físicamente.
    Esta es la función que sugiere el log para resolver el problema.
    """
    print("🔍 Iniciando validación de imágenes...")
    
    # Obtener todas las imágenes de la base de datos
    cursor = db_manager.conn.cursor()
    images = cursor.execute("SELECT id, path FROM images ORDER BY id").fetchall()
    
    if not images:
        print("✅ No hay imágenes en la base de datos.")
        return
    
    invalid_images = []
    valid_images = []
    
    print(f"📊 Verificando {len(images)} imágenes...")
    
    for image_row in images:
        image_id = image_row[0]
        image_path = image_row[1]
        
        # Verificar si el archivo existe
        if not os.path.exists(image_path):
            invalid_images.append((image_id, image_path))
            print(f"❌ ID {image_id}: {image_path} (NO EXISTE)")
        else:
            valid_images.append((image_id, image_path))
            print(f"✅ ID {image_id}: {os.path.basename(image_path)} (OK)")
    
    print(f"\n📋 RESUMEN:")
    print(f"✅ Imágenes válidas: {len(valid_images)}")
    print(f"❌ Imágenes inválidas: {len(invalid_images)}")
    
    if invalid_images:
        print(f"\n🗑️ IMÁGENES A ELIMINAR DE LA BASE DE DATOS:")
        for img_id, img_path in invalid_images:
            print(f"   ID {img_id}: {img_path}")
        
        response = input(f"\n¿Deseas eliminar estas {len(invalid_images)} imágenes inválidas? (s/n): ").lower().strip()
        
        if response in ['s', 'si', 'y', 'yes']:
            remove_invalid_images(invalid_images)
        else:
            print("🚫 Operación cancelada. Las imágenes inválidas permanecen en la base de datos.")
    else:
        print("🎉 Todas las imágenes son válidas. No hay nada que limpiar.")

def remove_invalid_images(invalid_images):
    """
    Elimina las imágenes inválidas de la base de datos y sus referencias.
    """
    print("🗑️ Eliminando imágenes inválidas...")
    cursor = db_manager.conn.cursor()
    
    for img_id, img_path in invalid_images:
        try:
            # Eliminar la imagen de la tabla principal
            cursor.execute("DELETE FROM images WHERE id = ?", (img_id,))
            
            # Eliminar referencias en otras tablas
            cursor.execute("DELETE FROM group_image_usage_log WHERE image_id = ?", (img_id,))
            cursor.execute("DELETE FROM page_image_usage WHERE image_id = ?", (img_id,))
            cursor.execute("DELETE FROM scheduled_posts WHERE image_id = ?", (img_id,))
            
            print(f"   ✅ Eliminada imagen ID {img_id}: {os.path.basename(img_path)}")
            
        except Exception as e:
            print(f"   ❌ Error eliminando imagen ID {img_id}: {e}")
    
    db_manager.conn.commit()
    print(f"✅ Proceso completado. {len(invalid_images)} imágenes eliminadas de la base de datos.")

def show_database_status():
    """
    Muestra el estado actual de la base de datos.
    """
    print("📊 ESTADO ACTUAL DE LA BASE DE DATOS:")
    cursor = db_manager.conn.cursor()
    
    # Contar elementos en cada tabla
    tables_info = [
        ("Textos", "texts"),
        ("Imágenes", "images"),
        ("Grupos", "groups"),
        ("Páginas", "pages"),
        ("Posts programados", "scheduled_posts")
    ]
    
    for name, table in tables_info:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   {name}: {count}")
    
    print()

def check_specific_images():
    """
    Verifica específicamente las imágenes que aparecen en el log de errores.
    """
    problematic_ids = [7, 8, 9]
    cursor = db_manager.conn.cursor()
    
    print("🔍 Verificando imágenes problemáticas específicas...")
    
    for img_id in problematic_ids:
        result = cursor.execute("SELECT id, path FROM images WHERE id = ?", (img_id,)).fetchone()
        if result:
            image_path = result[1]
            exists = os.path.exists(image_path)
            status = "✅ EXISTE" if exists else "❌ NO EXISTE"
            print(f"   ID {img_id}: {image_path} - {status}")
        else:
            print(f"   ID {img_id}: NO ENCONTRADA EN BASE DE DATOS")

if __name__ == "__main__":
    print("🛠️ HERRAMIENTA DE LIMPIEZA DE IMÁGENES")
    print("=" * 50)
    
    show_database_status()
    check_specific_images()
    print()
    validate_images()