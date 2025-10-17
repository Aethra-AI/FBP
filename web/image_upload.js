// Función para actualizar la barra de progreso de carga de imágenes
eel.expose(update_upload_progress);
function update_upload_progress(percent, message) {
    try {
        const progressBar = document.querySelector('#image-upload-progress .progress');
        const progressText = document.querySelector('#image-upload-progress .progress-text');
        const progressContainer = document.getElementById('image-upload-progress');
        
        if (progressBar && progressText && progressContainer) {
            progressBar.style.width = `${percent}%`;
            progressText.textContent = message || `Subiendo: ${percent}%`;
            progressContainer.style.display = 'block';
        }
    } catch (error) {
        console.error('Error actualizando progreso de carga:', error);
    }
}

// Función para ocultar la barra de progreso
eel.expose(hide_upload_progress);
function hide_upload_progress() {
    try {
        const progressContainer = document.getElementById('image-upload-progress');
        if (progressContainer) {
            // Resetear la barra de progreso
            const progressBar = progressContainer.querySelector('.progress');
            if (progressBar) {
                progressBar.style.width = '0%';
            }
            
            // Ocultar el contenedor después de un breve retraso para que se vea el 100%
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 1000);
        }
    } catch (error) {
        console.error('Error ocultando barra de progreso:', error);
    }
}

// Función para manejar la subida de imágenes
async function handleImageUpload() {
    const tagsInput = document.getElementById('image-tags-input');
    const tags = tagsInput ? tagsInput.value.trim() : '';
    
    if (!tags) {
        Utils.showNotification('Advertencia', 'Por favor ingresa etiquetas para las imágenes', 'warning');
        return;
    }
    
    try {
        // Mostrar indicador de carga
        Utils.showLoading(true);
        
        // Llamar a la función de Python para manejar la subida
        await eel.add_images(tags)();
        
        // Actualizar la vista de imágenes
        const data = await eel.get_initial_data()();
        appState.data = data;
        DataManager.updateUI();
        
        Utils.showNotification('Éxito', 'Imágenes subidas correctamente', 'success');
    } catch (error) {
        console.error('Error subiendo imágenes:', error);
        Utils.showNotification('Error', 'No se pudieron subir las imágenes', 'error');
    } finally {
        Utils.showLoading(false);
    }
}

// Inicializar eventos de carga de imágenes
document.addEventListener('DOMContentLoaded', () => {
    const addImagesBtn = document.getElementById('add-images');
    if (addImagesBtn) {
        addImagesBtn.addEventListener('click', handleImageUpload);
    }
});
