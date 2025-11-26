# 📦 GUÍA DE GITHUB - SWIFTLY

## 🎯 Qué Archivos Subir a GitHub

### ✅ **ARCHIVOS QUE SÍ DEBES SUBIR:**

#### **Código Python (Backend):**
```
✓ main.py
✓ database.py
✓ ai_services.py
✓ image_manager.py
✓ content_categorizer.py
✓ chatbot_service.py
✓ intelligent_matcher.py
```

#### **Frontend (Web):**
```
✓ web/index.html
✓ web/main.js
✓ web/styles.css
✓ web/chatbot.js
✓ web/chatbot.css
✓ web/onboarding.js
✓ web/onboarding.css
```

#### **Documentación:**
```
✓ README.md
✓ PLAN_DE_MEJORA.md
✓ IMPLEMENTACION_COMPLETADA.md
✓ MEJORAS_INTERFAZ_COMPLETADAS.md
✓ GUIA_RAPIDA_INICIO.md
✓ GITHUB_SETUP.md (este archivo)
```

#### **Configuración:**
```
✓ requirements.txt
✓ .gitignore
✓ LICENSE (opcional)
```

---

### ❌ **ARCHIVOS QUE NO DEBES SUBIR:**

#### **Base de Datos:**
```
✗ *.db
✗ *.sqlite
✗ swiftly.db
✗ marketing.db
```
**Razón:** Contiene TODOS tus datos privados (textos, grupos, sesiones, etc.)

#### **Imágenes de Contenido:**
```
✗ uploaded_images/
✗ images/
✗ screenshots/
✗ *.jpg, *.png, *.gif
```
**Razón:** Son tus imágenes personales de contenido

#### **Configuración Privada:**
```
✗ .env
✗ config.ini
✗ secrets.json
```
**Razón:** Contiene tu API Key de OpenAI y otras claves privadas

#### **Perfiles de Chrome:**
```
✗ chrome_profiles/
✗ selenium_profiles/
✗ *.profile
```
**Razón:** Contiene sesiones de Facebook guardadas

#### **Archivos Temporales:**
```
✗ __pycache__/
✗ *.pyc
✗ *.log
✗ tmp/
✗ debug_*.png
```
**Razón:** Se generan automáticamente

---

## 🚀 Cómo Subir a GitHub (Primera Vez)

### **Paso 1: Crear Repositorio en GitHub**

1. Ve a https://github.com
2. Clic en "New Repository"
3. Nombre: `swiftly-automation` (o el que prefieras)
4. Descripción: "Sistema inteligente de automatización para Facebook"
5. **Privado:** ✅ Marca como privado (recomendado)
6. ❌ NO inicialices con README (ya tienes uno)
7. Clic en "Create Repository"

---

### **Paso 2: Inicializar Git en tu Proyecto**

Abre la terminal en la carpeta del proyecto:

```bash
cd /Users/juanmontufar/Downloads/Swiftly2

# Inicializar repositorio Git
git init

# Agregar todos los archivos (el .gitignore excluirá los que no deben subirse)
git add .

# Hacer el primer commit
git commit -m "Initial commit - Swiftly 2.1 con IA y Onboarding"

# Conectar con tu repositorio de GitHub
git remote add origin https://github.com/TU_USUARIO/swiftly-automation.git

# Subir los archivos
git push -u origin main
```

**Nota:** Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub.

---

### **Paso 3: Verificar que se Subió Correctamente**

1. Ve a tu repositorio en GitHub
2. Deberías ver:
   - ✅ Todos los archivos .py
   - ✅ Carpeta web/ con todos los archivos
   - ✅ Archivos de documentación .md
   - ✅ requirements.txt
   - ❌ NO deberías ver .db, .env, uploaded_images/

---

## 💻 Cómo Usar en Otra PC

### **Paso 1: Clonar el Repositorio**

En la nueva PC:

```bash
# Navegar a donde quieres el proyecto
cd ~/Documents

# Clonar el repositorio
git clone https://github.com/TU_USUARIO/swiftly-automation.git

# Entrar a la carpeta
cd swiftly-automation
```

---

### **Paso 2: Instalar Python y Dependencias**

**Instalar Python 3.9+:**
- **Mac:** `brew install python3`
- **Windows:** Descargar de https://python.org
- **Linux:** `sudo apt install python3 python3-pip`

**Instalar dependencias:**

```bash
# Instalar todas las librerías necesarias
pip install -r requirements.txt

# O con pip3
pip3 install -r requirements.txt
```

**Verificar instalación:**
```bash
python --version  # Debe ser 3.9+
pip list  # Debe mostrar: eel, selenium, openai, etc.
```

---

### **Paso 3: Configurar Archivo .env**

**Crear archivo `.env` en la carpeta del proyecto:**

```bash
# Crear archivo
nano .env

# O con cualquier editor de texto
```

**Contenido del archivo `.env`:**
```
OPENAI_API_KEY=sk-tu-clave-aqui
```

**Guardar y cerrar** (en nano: Ctrl+X, luego Y, luego Enter)

**Importante:** Conseguir tu API Key de OpenAI:
1. Ve a https://platform.openai.com/api-keys
2. Crea una nueva API key
3. Cópiala y pégala en el archivo .env

---

### **Paso 4: Crear Estructura de Carpetas**

```bash
# Crear carpetas necesarias
mkdir uploaded_images
mkdir chrome_profiles

# Dar permisos
chmod 755 uploaded_images
chmod 755 chrome_profiles
```

---

### **Paso 5: Ejecutar la Aplicación**

```bash
# Ejecutar
python main.py

# O
python3 main.py
```

**¡Listo!** La aplicación debería abrir automáticamente en tu navegador.

---

## 🔄 Actualizar Cambios entre PCs

### **Subir Cambios desde PC 1:**

```bash
# Ver qué cambió
git status

# Agregar cambios
git add .

# Commit con mensaje descriptivo
git commit -m "Descripción de los cambios"

# Subir a GitHub
git push
```

---

### **Descargar Cambios en PC 2:**

```bash
# Entrar a la carpeta del proyecto
cd ~/Documents/swiftly-automation

# Descargar últimos cambios
git pull
```

---

## 📋 Checklist de Configuración Nueva PC

### **Antes de Empezar:**
- [ ] Python 3.9+ instalado
- [ ] pip actualizado: `pip install --upgrade pip`
- [ ] Git instalado
- [ ] Cuenta de GitHub activa

### **Configuración:**
- [ ] Clonar repositorio: `git clone ...`
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Crear archivo `.env` con API Key
- [ ] Crear carpetas: `uploaded_images/`, `chrome_profiles/`
- [ ] Ejecutar: `python main.py`
- [ ] Verificar que abre en navegador

### **Primera Vez en Nueva PC:**
- [ ] La base de datos se creará automáticamente (vacía)
- [ ] Hacer tour de onboarding
- [ ] Agregar tu primer contenido
- [ ] Configurar grupos de Facebook
- [ ] ¡Listo para usar!

---

## 🔧 Solución de Problemas Comunes

### **Problema 1: "No module named 'eel'"**
```bash
# Solución:
pip install -r requirements.txt
```

### **Problema 2: "OPENAI_API_KEY not found"**
```bash
# Solución:
# Crear archivo .env con tu API key
echo "OPENAI_API_KEY=sk-tu-clave" > .env
```

### **Problema 3: Error con Selenium/Chrome**
```bash
# Solución:
# Reinstalar webdriver-manager
pip install --upgrade webdriver-manager selenium
```

### **Problema 4: Base de datos corrupta**
```bash
# Solución:
# Eliminar y dejar que se cree nueva
rm swiftly.db
python main.py
```

### **Problema 5: Puerto 8080 ocupado**
```bash
# Solución:
# Matar proceso en puerto 8080
lsof -ti:8080 | xargs kill -9

# O cambiar puerto en main.py (línea con eel.start)
```

---

## 🎯 Comandos Git Útiles

### **Ver Estado:**
```bash
git status  # Ver qué cambió
git log     # Ver historial de commits
```

### **Deshacer Cambios:**
```bash
git checkout -- archivo.py  # Deshacer cambios en un archivo
git reset --hard           # Deshacer TODOS los cambios (¡cuidado!)
```

### **Branches (Ramas):**
```bash
git branch nueva-funcion    # Crear rama
git checkout nueva-funcion  # Cambiar a rama
git merge nueva-funcion     # Fusionar rama
```

### **Ver Diferencias:**
```bash
git diff                # Ver qué cambió
git diff archivo.py     # Ver cambios en archivo específico
```

---

## 📦 Estructura del Proyecto en GitHub

```
swiftly-automation/
│
├── main.py                           # Backend principal
├── database.py                       # Gestor de BD
├── ai_services.py                    # Integración OpenAI
├── content_categorizer.py            # Categorizador inteligente
├── chatbot_service.py                # Chatbot asistente
├── intelligent_matcher.py            # Motor de emparejamiento
├── image_manager.py                  # Gestor de imágenes
│
├── web/                              # Frontend
│   ├── index.html
│   ├── main.js
│   ├── styles.css
│   ├── chatbot.js
│   ├── chatbot.css
│   ├── onboarding.js
│   └── onboarding.css
│
├── requirements.txt                  # Dependencias Python
├── .gitignore                        # Archivos a ignorar
├── README.md                         # Documentación principal
├── PLAN_DE_MEJORA.md
├── IMPLEMENTACION_COMPLETADA.md
├── MEJORAS_INTERFAZ_COMPLETADAS.md
├── GUIA_RAPIDA_INICIO.md
└── GITHUB_SETUP.md                   # Este archivo
```

---

## 🔒 Seguridad y Mejores Prácticas

### **✅ HACER:**
- ✅ Mantener repositorio **privado**
- ✅ Nunca subir archivo `.env`
- ✅ Nunca subir base de datos `.db`
- ✅ Hacer commits frecuentes con mensajes claros
- ✅ Usar branches para nuevas funciones
- ✅ Hacer backup de tu `.env` en lugar seguro

### **❌ NO HACER:**
- ❌ Subir API keys a GitHub
- ❌ Subir contraseñas o tokens
- ❌ Hacer el repositorio público si contiene datos sensibles
- ❌ Commitear archivos grandes (>100MB)
- ❌ Subir sesiones de navegador

---

## 💡 Tips Adicionales

### **Backup de Base de Datos:**
```bash
# Hacer backup manual
cp swiftly.db backups/swiftly_backup_$(date +%Y%m%d).db

# O usar la función de backup en la app
```

### **Sincronizar Contenido Entre PCs:**
Si quieres la misma base de datos en ambas PCs, usa un servicio de nube:
```bash
# Opción 1: Dropbox
ln -s ~/Dropbox/swiftly/swiftly.db swiftly.db

# Opción 2: Google Drive
ln -s ~/Google\ Drive/swiftly/swiftly.db swiftly.db
```

### **Múltiples Entornos:**
```bash
# Desarrollo
python main.py

# Producción (con variables diferentes)
PRODUCTION=true python main.py
```

---

## ✨ Resultado Final

Después de seguir esta guía:

- ✅ Tu código estará seguro en GitHub
- ✅ Podrás trabajar desde cualquier PC
- ✅ Los cambios se sincronizarán fácilmente
- ✅ Tus datos privados estarán protegidos
- ✅ La instalación en nueva PC tomará 5 minutos

---

## 📞 Comandos Rápidos de Referencia

### **Primera vez (subir a GitHub):**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/repo.git
git push -u origin main
```

### **Nueva PC (descargar y configurar):**
```bash
git clone https://github.com/TU_USUARIO/repo.git
cd repo
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-tu-clave" > .env
mkdir uploaded_images chrome_profiles
python main.py
```

### **Actualizar cambios (día a día):**
```bash
# PC 1 (hacer cambios)
git add .
git commit -m "Mensaje"
git push

# PC 2 (descargar cambios)
git pull
```

---

**¿Dudas?** Revisa la documentación de Git: https://git-scm.com/doc

**Estado:** ✅ Listo para usar en múltiples PCs
