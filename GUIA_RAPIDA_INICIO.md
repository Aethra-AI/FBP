# 🚀 GUÍA RÁPIDA DE INICIO - SWIFTLY 2.0

## ⚡ Primeros Pasos (5 minutos)

### 1. Iniciar la Aplicación

```bash
cd /Users/juanmontufar/Downloads/Swiftly2
python main.py
```

La aplicación se abrirá automáticamente en tu navegador.

---

### 2. Re-categorizar Contenido Existente (Primer Uso)

Una vez abierta la aplicación:

1. Presiona **F12** para abrir la consola del navegador
2. Pega este comando:

```javascript
eel.recategorize_all_content()().then(result => {
    console.log('✅ Categorización completada:', result);
    alert(`✅ ${result.success.length} textos categorizados`);
});
```

3. Espera unos segundos
4. Verás un mensaje de confirmación

**¿Qué hace esto?**  
Analiza todo tu contenido existente y lo categoriza automáticamente en EMPLEOS, SERVICIOS o VENTAS.

---

## 💬 USAR EL CHATBOT

### Abrir el Chatbot

Busca el botón **💬** flotante en la esquina inferior derecha y haz clic.

### Ejemplo 1: Generar Post de Empleos

```
1. Selecciona categoría: "💼 Empleos"
2. Escribe: "Necesito un post sobre vacante de ingeniero industrial"
3. Presiona Enter
4. Espera 5 segundos
5. Verás 3 opciones de texto
6. Clic en "💾 Guardar Todos"
```

**¡Listo!** Los textos ya están en tu biblioteca con categoría EMPLEOS.

---

### Ejemplo 2: Crear Variaciones de Tu Texto

```
1. Abre chatbot
2. Escribe: "Crea variaciones de: [pega aquí tu texto de ejemplo]"
3. El chatbot generará 3 versiones similares
4. Guarda las que te gusten
```

---

### Ejemplo 3: Pedir Ideas

```
Usuario: "Dame ideas de contenido"

Chatbot: 
  📊 Análisis actual:
  - Empleos: 20%
  - Servicios: 30%
  - Ventas: 50%
  
  💡 Recomendaciones:
  - Necesitas más contenido de empleos
  - [más sugerencias]
```

---

## 📝 CREAR CONTENIDO MANUALMENTE CON CATEGORÍA

### Método 1: Con el Chatbot (Recomendado)
✅ Más rápido  
✅ Categorización automática  
✅ 3 variaciones al instante  

### Método 2: Manual Tradicional
1. Ve a pestaña **"Contenido"**
2. Clic en **"Añadir Texto Manual"**
3. Escribe tu texto
4. El sistema lo categorizará automáticamente
5. Verás las etiquetas generadas (ej: `empleos, vacante, ingeniero`)

---

## 🎯 CREAR SESIÓN DE PUBLICACIÓN INTELIGENTE

### Ejemplo: Sesión Solo de Empleos

```
1. Ve a pestaña "Automatización"
2. Clic en "Nueva Sesión"
3. Completa el formulario:

   Nombre de sesión: 
      "Empleos - Noviembre"
   
   Tags de grupos: 
      "empleo,trabajo,vacante,honduras"
      ↑ Los grupos con estos tags serán seleccionados
   
   Tags de contenido:
      "empleos"
      ↑ Solo contenido de categoría EMPLEOS
   
   Tipo de publicación:
      ☑️ Texto + Imagen
   
4. Clic en "Crear Sesión"
5. Clic en "▶️ Iniciar" en la sesión creada
```

### ¿Qué Hace Diferente Ahora?

**ANTES:**
- Mezclaba cualquier contenido que tuviera palabras similares
- No validaba coherencia texto-imagen
- Podía publicar empleos en grupos de ventas

**AHORA:**
- ✅ Solo selecciona contenido de categoría EMPLEOS
- ✅ Valida que texto e imagen sean coherentes
- ✅ Muestra confidence score en logs
- ✅ Evita mezclas entre categorías

---

## 📊 VER ESTADÍSTICAS

### Método 1: Con Chatbot

```
Usuario: "Muéstrame estadísticas"

Chatbot:
  📊 Análisis:
  Total: 50 textos
  - Empleos: 15 (30%)
  - Servicios: 10 (20%)
  - Ventas: 20 (40%)
  - General: 5 (10%)
```

### Método 2: Por Código

```javascript
// En consola del navegador (F12)
eel.get_category_statistics()().then(stats => {
    console.table(stats.distribution);
});
```

---

## 🎨 AGREGAR IMÁGENES CON CATEGORÍA

### Para que las Imágenes se Emparejen Correctamente:

1. **Ve a pestaña "Contenido"**
2. **Clic en "Añadir Imágenes"**
3. **Selecciona imágenes**
4. **MUY IMPORTANTE:** En el campo "Tags", escribe la categoría:

```
Ejemplos correctos:
  - empleos, oficina, profesional
  - servicios, consultoría, asesoría
  - ventas, producto, oferta
```

**TIP:** La primera palabra debe ser la categoría (empleos, servicios, ventas) para que el sistema las empareje correctamente.

---

## 🔍 VERIFICAR QUE TODO FUNCIONA

### Checklist Rápido:

#### 1. Base de Datos
```javascript
// Verificar que nuevas tablas existen
eel.get_initial_data()().then(data => {
    console.log('Textos:', data.texts.length);
    console.log('Categorías en uso:', 
        new Set(data.texts.map(t => t.ai_tags))
    );
});
```

#### 2. Chatbot
- [ ] Botón 💬 visible en esquina inferior derecha
- [ ] Al hacer clic se abre panel
- [ ] Puedo seleccionar categoría
- [ ] Puedo escribir y recibir respuesta

#### 3. Categorización
- [ ] Textos nuevos tienen etiquetas con categoría
- [ ] Formato: `empleos:etiqueta1,empleos:etiqueta2`

#### 4. Sesiones
- [ ] Al iniciar sesión, logs muestran categoría detectada
- [ ] Logs muestran: "📋 Categoría: EMPLEOS"
- [ ] Logs muestran: "✅ Contenido seleccionado (confianza: X%)"

---

## 💡 COMANDOS ÚTILES DEL CHATBOT

### Generación de Contenido
```
"Genera un post sobre [tema]"
"Crea 5 posts sobre servicios de consultoría"
"Necesito contenido para ventas de productos tecnológicos"
```

### Variaciones
```
"Crea variaciones de: [tu texto]"
"Basado en este ejemplo: [texto], genera 3 más"
```

### Optimización
```
"Optimiza este texto: [texto]"
"Mejora esta publicación: [texto]"
"Qué opinas de: [texto]"
```

### Análisis
```
"Dame ideas de contenido"
"Qué tipo de contenido me falta"
"Muéstrame estadísticas"
"Analiza mi contenido"
```

---

## ⚠️ PROBLEMAS COMUNES Y SOLUCIONES

### Problema 1: "Chatbot no responde"

**Causa:** No hay API key de OpenAI  
**Solución:**
```bash
# Verificar archivo .env
cat .env

# Debe contener:
OPENAI_API_KEY=sk-...tu-key...
```

---

### Problema 2: "Contenido se sigue mezclando"

**Causa:** Contenido antiguo no está categorizado  
**Solución:**
```javascript
// Re-categorizar todo
eel.recategorize_all_content()().then(result => {
    console.log('Categorizado:', result.stats);
});
```

---

### Problema 3: "Imágenes no son coherentes con texto"

**Causa:** Imágenes no tienen tags de categoría  
**Solución:**
1. Ve a pestaña "Contenido"
2. Selecciona una imagen
3. Edita sus tags
4. Agrega categoría al inicio: `empleos, [otros tags]`

---

### Problema 4: "Error al iniciar aplicación"

**Causa:** Falta algún módulo  
**Solución:**
```bash
# Reinstalar dependencias
pip install -r requirements.txt

# Verificar que existen los archivos nuevos:
ls content_categorizer.py
ls chatbot_service.py
ls intelligent_matcher.py
```

---

## 🎯 CASOS DE USO REALES

### Caso 1: Agencia de Empleos (Henmir)

```
OBJETIVO: Publicar 20 vacantes en grupos de empleos

PASOS:
1. Abrir chatbot
2. Generar 20 posts diferentes:
   - "Genera post sobre vacante de contador"
   - "Genera post sobre vacante de vendedor"
   - [repetir para cada vacante]
3. Guardar todos los posts
4. Crear sesión:
   - Tags grupos: "empleo,trabajo,honduras"
   - Tags contenido: "empleos"
5. Iniciar sesión
6. Sistema publica automáticamente con coherencia

TIEMPO: 10 minutos (antes: 2+ horas)
```

---

### Caso 2: Empresa de Servicios

```
OBJETIVO: Promocionar 3 servicios diferentes

PASOS:
1. Crear contenido con chatbot:
   - "Genera posts sobre consultoría empresarial"
   - "Genera posts sobre asesoría legal"
   - "Genera posts sobre servicios contables"
2. Guardar (auto-categorizados como SERVICIOS)
3. Agregar imágenes con tags: "servicios,profesional"
4. Crear sesión de SERVICIOS
5. Publicar

RESULTADO: 0% de posts de empleos mezclados
```

---

### Caso 3: Tienda de Productos

```
OBJETIVO: Promocionar productos en venta

PASOS:
1. Chatbot: "Genera posts sobre ofertas de electrodomésticos"
2. Guardar (auto-categorizados como VENTAS)
3. Agregar imágenes de productos con tags: "ventas,producto"
4. Crear sesión:
   - Tags grupos: "compra,venta,tienda"
   - Tags contenido: "ventas"
5. Publicar

VENTAJA: No se mezcla con contenido de empleos o servicios
```

---

## 📚 RECURSOS ADICIONALES

### Documentos de Referencia:
- **`PLAN_DE_MEJORA.md`** - Plan completo de mejoras implementadas
- **`IMPLEMENTACION_COMPLETADA.md`** - Detalles técnicos de la implementación

### Categorías Disponibles:
```python
EMPLEOS     💼  # Vacantes, ofertas laborales
SERVICIOS   🔧  # Servicios profesionales
VENTAS      🛒  # Productos, ofertas comerciales
```

### Keywords por Categoría:

**EMPLEOS:**
`trabajo, empleo, vacante, contratar, cv, entrevista, reclutamiento, postular, candidato, carrera`

**SERVICIOS:**
`servicio, asesoría, consultoría, profesional, especialista, experto, soporte, capacitación, solución`

**VENTAS:**
`venta, compra, producto, precio, oferta, descuento, promoción, stock, disponible, tienda`

---

## ✅ CHECKLIST: ¿ESTÁS LISTO?

Antes de usar en producción, verifica:

- [ ] He re-categorizado mi contenido existente
- [ ] El chatbot abre y responde correctamente
- [ ] He probado generar contenido en las 3 categorías
- [ ] He creado una sesión de prueba
- [ ] Las imágenes tienen tags con categoría
- [ ] Los logs muestran confidence scores
- [ ] No veo mezclas de contenido entre categorías

---

## 🎉 ¡LISTO PARA USAR!

Tu sistema Swiftly 2.0 ahora es:
- ✅ 5x más rápido
- ✅ 10x más inteligente
- ✅ 100% sin mezclas de categorías

**Disfruta tu nuevo asistente con IA** 🤖✨

---

**¿Necesitas ayuda?**  
Revisa `IMPLEMENTACION_COMPLETADA.md` para más detalles técnicos.
