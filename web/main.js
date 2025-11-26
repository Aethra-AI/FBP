// Estado global de la aplicación
let appState = {
    data: {
        texts: [],
        images: [],
        groups: [],
        pages: [],
        scheduled_posts: []
    },
    ui: {
        currentTab: 'dashboard',
        isGroupPublishing: false
    }
};

// Utilidades
const Utils = {
    // Mostrar/ocultar loading
    showLoading(show = true) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    },

    // Construir ruta de imagen correcta para el servidor HTTP
    getImageSrc(imagePath) {
        if (!imagePath) return '';
        // Extraer solo el nombre del archivo de la ruta
        const filename = imagePath.split('/').pop().split('\\').pop();
        return `http://127.0.0.1:5001/images/${filename}`;
    },

    // Mostrar notificaciones
    showNotification(title, message, type = 'success') {
        const notification = document.getElementById('notification');
        const titleEl = notification.querySelector('.notification-title');
        const messageEl = notification.querySelector('.notification-content div:last-child');
        const iconEl = notification.querySelector('.notification-icon i');

        titleEl.textContent = title;
        messageEl.textContent = message;

        // Cambiar icono según el tipo
        switch (type) {
            case 'success':
                iconEl.className = 'fas fa-check';
                break;
            case 'error':
                iconEl.className = 'fas fa-exclamation-triangle';
                break;
            case 'warning':
                iconEl.className = 'fas fa-exclamation-circle';
                break;
            default:
                iconEl.className = 'fas fa-info';
        }

        notification.className = `notification ${type}`;
        notification.classList.add('show');

        // Auto-ocultar después de 5 segundos
        setTimeout(() => {
            notification.classList.remove('show');
        }, 5000);
    },

    // Formatear fecha
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString('es-ES');
    },

    // Truncar texto
    truncateText(text, maxLength = 100) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    },

    // Validar URL
    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
};

// Manejo de datos
const DataManager = {
    // Cargar datos iniciales
    async loadInitialData() {
        try {
            Utils.showLoading(true);
            const data = await eel.get_initial_data()();
            appState.data = data;
            this.updateUI();

            // Cargar sesiones
            await this.loadSessions();

            this.updateStatus(true);
            Utils.showNotification('Sistema Iniciado', 'Datos cargados correctamente', 'success');
        } catch (error) {
            console.error('Error cargando datos:', error);
            Utils.showNotification('Error', 'No se pudieron cargar los datos iniciales', 'error');
            this.updateStatus(false);
        } finally {
            Utils.showLoading(false);
        }
    },

    // Cargar sesiones
    async loadSessions() {
        try {
            const result = await eel.get_all_sessions()();
            if (result.success) {
                appState.sessions = result.sessions;
                this.updateSessionsUI();
            }
        } catch (error) {
            console.error('Error cargando sesiones:', error);
        }
    },

    // Actualizar interfaz de sesiones
    updateSessionsUI() {
        const container = document.getElementById('sessions-container');
        if (!container) return;

        if (!appState.sessions || appState.sessions.length === 0) {
            container.innerHTML = `
                <div class="sessions-loading">
                    <i class="fas fa-layer-group"></i>
                    <p>No hay sesiones creadas</p>
                    <p style="color: var(--text-muted); font-size: 0.9rem;">Haz clic en "Nueva Sesión" para crear una</p>
                </div>
            `;
            return;
        }

        container.innerHTML = appState.sessions.map(session => {
            const progressPercentage = session.total_groups > 0
                ? (session.current_group_index / session.total_groups) * 100
                : 0;

            return `
                <div class="session-card" data-session-id="${session.id}">
                    <div class="session-header">
                        <h3 class="session-name">${session.name}</h3>
                        <span class="session-status ${session.status}">${this.getStatusText(session.status)}</span>
                    </div>
                    
                    <div class="session-progress">
                        Progreso: ${session.current_group_index}/${session.total_groups} grupos
                    </div>
                    <div class="session-progress-bar">
                        <div class="session-progress-fill" style="width: ${progressPercentage}%"></div>
                    </div>
                    
                    <div class="session-config">
                        <div class="session-config-item">
                            <span class="session-config-label">Grupos:</span>
                            <span class="session-config-value">${session.config.group_tags}</span>
                        </div>
                        <div class="session-config-item">
                            <span class="session-config-label">Contenido:</span>
                            <span class="session-config-value">${session.config.content_tags}</span>
                        </div>
                        <div class="session-config-item">
                            <span class="session-config-label">Tipo:</span>
                            <span class="session-config-value">${this.getPublicationTypeText(session.config.publication_type)}</span>
                        </div>
                    </div>
                    
                    <div class="session-actions">
                        ${this.getSessionActionButtons(session)}
                    </div>
                </div>
            `;
        }).join('');
    },

    getStatusText(status) {
        const statusMap = {
            'active': 'Activa',
            'paused': 'Pausada',
            'inactive': 'Inactiva',
            'error': 'Error',
            'completed': 'Completada'
        };
        return statusMap[status] || status;
    },

    getPublicationTypeText(type) {
        const typeMap = {
            'text-only': 'Solo Texto',
            'text-and-image': 'Texto + Imagen'
        };
        return typeMap[type] || type;
    },

    getSessionActionButtons(session) {
        let buttons = [];

        switch (session.status) {
            case 'inactive':
                buttons.push(`<button class="session-action-btn start" onclick="SessionManager.startSession(${session.id})">
                    <i class="fas fa-play"></i> Iniciar
                </button>`);
                break;
            case 'active':
                buttons.push(`<button class="session-action-btn pause" onclick="SessionManager.pauseSession(${session.id})">
                    <i class="fas fa-pause"></i> Pausar
                </button>`);
                buttons.push(`<button class="session-action-btn stop" onclick="SessionManager.stopSession(${session.id})">
                    <i class="fas fa-stop"></i> Detener
                </button>`);
                break;
            case 'paused':
                buttons.push(`<button class="session-action-btn start" onclick="SessionManager.startSession(${session.id})">
                    <i class="fas fa-play"></i> Reanudar
                </button>`);
                buttons.push(`<button class="session-action-btn stop" onclick="SessionManager.stopSession(${session.id})">
                    <i class="fas fa-stop"></i> Detener
                </button>`);
                break;
            case 'error':
                buttons.push(`<button class="session-action-btn start" onclick="SessionManager.startSession(${session.id})">
                    <i class="fas fa-redo"></i> Reintentar
                </button>`);
                break;
        }

        buttons.push(`<button class="session-action-btn delete" onclick="SessionManager.deleteSession(${session.id})">
            <i class="fas fa-trash"></i> Eliminar
        </button>`);

        return buttons.join('');
    },

    // Actualizar interfaz con los datos
    updateUI() {
        this.updateStats();
        this.updateTextsTable();
        this.updateImagesTable();
        this.updateImageGallery();
        this.updateGroupsTable();
        this.updatePagesTable();
        this.updateScheduledPostsTable();
        this.updateSelects();
        this.updateHistoryTable();
        this.updatePublicationPreview();
    },

    // Actualizar estadísticas del dashboard
    updateStats() {
        document.getElementById('total-texts').textContent = appState.data.texts?.length || 0;
        document.getElementById('total-images').textContent = appState.data.images?.length || 0;
        document.getElementById('total-groups').textContent = appState.data.groups?.length || 0;
        document.getElementById('total-scheduled').textContent = appState.data.scheduled_posts?.length || 0;

        // Actualizar contadores en las pestañas
        document.getElementById('texts-count').textContent = `${appState.data.texts?.length || 0} textos`;
        document.getElementById('images-count').textContent = `${appState.data.images?.length || 0} imágenes`;
        document.getElementById('groups-count').textContent = `${appState.data.groups?.length || 0} grupos`;
        document.getElementById('pages-count').textContent = `${appState.data.pages?.length || 0} páginas`;
        document.getElementById('scheduled-count').textContent = `${appState.data.scheduled_posts?.length || 0} programadas`;
    },


    // Actualizar tabla de textos
    updateTextsTable() {
        const tbody = document.getElementById('texts-table-body');
        if (!appState.data.texts || appState.data.texts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No hay textos disponibles</td></tr>';
            return;
        }

        tbody.innerHTML = appState.data.texts.map(text => {
            const usageCount = text.usage_count || 0;
            let usageClass = '';
            if (usageCount >= 7 && usageCount < 10) {
                usageClass = 'tag-warning';
            } else if (usageCount >= 10) {
                usageClass = 'tag-danger';
            }

            // Escapar el contenido para que no rompa el HTML en el onclick
            const escapedContent = text.content.replace(/`/g, '\\`').replace(/\$/g, '\\$');

            return `
                <tr>
                    <td>${text.id}</td>
                    <td style="max-width: 300px; word-wrap: break-word;">${Utils.truncateText(text.content)}</td>
                    <td>
                        ${(text.ai_tags || '').split(',').filter(tag => tag.trim()).map(tag =>
                `<span class="tag">${tag.trim()}</span>`
            ).join('')}
                    </td>
                    <td>
                        <span class="tag ${usageClass}">${usageCount}</span>
                    </td>
                    <td class="actions">
                        <button class="btn btn-sm btn-icon btn-secondary" onclick="UIManager.showTextEditModal(${text.id}, \`${escapedContent}\`)">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-icon btn-info" onclick="UIManager.showTextTagsEditModal(${text.id}, '${(text.ai_tags || '').replace(/'/g, "\\'")}')" title="Editar etiquetas">
                            <i class="fas fa-tags"></i>
                        </button>
                        <button class="btn btn-sm btn-icon btn-warning" onclick="DataManager.regenerateTextTags(${text.id})" title="Regenerar etiquetas con IA">
                            <i class="fas fa-magic"></i>
                        </button>
                        <button class="btn btn-sm btn-icon btn-danger" onclick="DataManager.deleteText(${text.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    },



    updateImagesTable() {
        const tbody = document.getElementById('images-table-body');
        if (!appState.data.images || appState.data.images.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No hay imágenes disponibles</td></tr>';
            return;
        }

        tbody.innerHTML = appState.data.images.map(image => {
            const usageCount = image.usage_count || 0;
            let usageClass = '';
            if (usageCount >= 7 && usageCount < 10) {
                usageClass = 'tag-warning';
            } else if (usageCount >= 10) {
                usageClass = 'tag-danger';
            }

            const imageSrc = Utils.getImageSrc(image.path);

            return `
                <tr>
                    <td>${image.id}</td>
                    <td>
                        <img 
                            src="${imageSrc}" 
                            class="image-preview" 
                            style="cursor: pointer;"
                            onclick="UIManager.showImageModal('${image.path.replace(/\\/g, '\\\\')}')"
                            onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2250%22 height=%2250%22><rect width=%22100%25%22 height=%22100%25%22 fill=%22%23ccc%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22>IMG</text></svg>'">
                    </td>
                    <td style="max-width: 250px; word-wrap: break-word;">${Utils.truncateText(image.path)}</td>
                    <td>
                        ${(image.manual_tags || '').split(',').filter(tag => tag.trim()).map(tag =>
                `<span class="tag">${tag.trim()}</span>`
            ).join('')}
                    </td>
                    <td>
                        <span class="tag ${usageClass}">${usageCount}</span>
                    </td>
                    <td class="actions">
                        <button class="btn btn-sm btn-icon btn-info" onclick="UIManager.showImageTagsEditModal(${image.id}, '${(image.manual_tags || '').replace(/'/g, "\\'")}')" title="Editar etiquetas">
                            <i class="fas fa-tags"></i>
                        </button>
                        <button class="btn btn-sm btn-icon btn-danger" onclick="DataManager.deleteImage(${image.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    },

    // NUEVA FUNCIÓN: Actualizar galería de imágenes
    updateImageGallery() {
        const gallery = document.getElementById('image-gallery');
        if (!appState.data.images || appState.data.images.length === 0) {
            gallery.innerHTML = '<div class="gallery-loading"><i class="fas fa-images"></i><p>No hay imágenes disponibles</p></div>';
            return;
        }

        gallery.innerHTML = appState.data.images.map(image => {
            const usageCount = image.usage_count || 0;
            let usageClass = '';
            if (usageCount >= 7 && usageCount < 10) {
                usageClass = 'tag-warning';
            } else if (usageCount >= 10) {
                usageClass = 'tag-danger';
            }

            const tags = (image.manual_tags || '').split(',').filter(tag => tag.trim());
            const filename = image.path.split('\\').pop().split('/').pop();

            const imageSrc = Utils.getImageSrc(image.path);

            return `
                <div class="gallery-item" data-image-id="${image.id}">
                    <img 
                        src="${imageSrc}" 
                        class="gallery-item-image"
                        onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22150%22><rect width=%22100%25%22 height=%22100%25%22 fill=%22%23ccc%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22>IMG</text></svg>'">
                    <div class="gallery-item-actions">
                        <button class="gallery-item-action view" onclick="UIManager.showImageModal('${image.path.replace(/\\/g, '\\\\')}')" title="Ver imagen">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="gallery-item-action delete" onclick="DataManager.deleteImage(${image.id})" title="Eliminar imagen">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="gallery-item-info">
                        <div class="gallery-item-tags">
                            ${tags.map(tag => `<span class="tag">${tag.trim()}</span>`).join('')}
                        </div>
                        <div class="gallery-item-usage">
                            <span>${filename}</span>
                            <span class="tag ${usageClass}">${usageCount} usos</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    // Actualizar tabla de grupos
    updateGroupsTable() {
        const tbody = document.getElementById('groups-table-body');
        if (!appState.data.groups || appState.data.groups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No hay grupos disponibles</td></tr>';
            return;
        }

        tbody.innerHTML = appState.data.groups.map(group => `
            <tr>
                <td>${group.id}</td>
                <td style="max-width: 300px; word-wrap: break-word;">
                    <a href="${group.url}" target="_blank" style="color: var(--primary);">${Utils.truncateText(group.url)}</a>
                </td>
                <td>
                    ${(group.tags || '').split(',').filter(tag => tag.trim()).map(tag =>
            `<span class="tag">${tag.trim()}</span>`
        ).join('')}
                </td>
                <td class="actions">
                    <button class="btn btn-sm btn-icon btn-danger" onclick="DataManager.deleteGroup(${group.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    },

    // Actualizar tabla de páginas
    updatePagesTable() {
        const tbody = document.getElementById('pages-table-body');
        if (!appState.data.pages || appState.data.pages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No hay páginas disponibles</td></tr>';
            return;
        }

        tbody.innerHTML = appState.data.pages.map(page => `
            <tr>
                <td>${page.id}</td>
                <td>${page.name}</td>
                <td style="max-width: 300px; word-wrap: break-word;">
                    <a href="${page.page_url}" target="_blank" style="color: var(--primary);">${Utils.truncateText(page.page_url)}</a>
                </td>
                <td class="actions">
                    <button class="btn btn-sm btn-icon btn-danger" onclick="DataManager.deletePage(${page.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    },

    // Actualizar tabla de publicaciones programadas
    updateScheduledPostsTable() {
        const tbody = document.getElementById('scheduled-posts-table-body');
        if (!appState.data.scheduled_posts || appState.data.scheduled_posts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No hay publicaciones programadas</td></tr>';
            return;
        }

        tbody.innerHTML = appState.data.scheduled_posts.map(post => {
            let statusClass = 'tag-warning';
            if (post.status === 'completed') statusClass = 'tag-success';
            else if (post.status === 'failed') statusClass = 'tag-danger';

            return `
                <tr>
                    <td>${post.id}</td>
                    <td>${post.page_name || 'N/A'}</td>
                    <td style="max-width: 250px; word-wrap: break-word;">${Utils.truncateText(post.text_content)}</td>
                    <td>
                        ${post.image_path ?
                    `<img src="file:///${post.image_path}" class="image-preview" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2250%22 height=%2250%22><rect width=%22100%25%22 height=%22100%25%22 fill=%22%23ccc%22/><text x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22>IMG</text></svg>'">` :
                    'Sin imagen'
                }
                    </td>
                    <td>${Utils.formatDateTime(post.publish_at)}</td>
                    <td><span class="tag ${statusClass}">${post.status}</span></td>
                    <td class="actions">
                        <button class="btn btn-sm btn-icon btn-danger" onclick="DataManager.deleteScheduledPost(${post.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    },

    // Actualizar selects
    updateSelects() {
        // Select de páginas para el programador
        const pageSelect = document.getElementById('schedule-page-select');
        pageSelect.innerHTML = '<option value="">Selecciona una página...</option>';
        if (appState.data.pages) {
            appState.data.pages.forEach(page => {
                pageSelect.innerHTML += `<option value="${page.id}">${page.name}</option>`;
            });
        }

        // Select de imágenes para el programador
        const imageSelect = document.getElementById('schedule-image-select');
        imageSelect.innerHTML = '<option value="">Sin imagen</option>';
        if (appState.data.images) {
            appState.data.images.forEach(image => {
                const filename = image.path.split('\\').pop().split('/').pop();
                imageSelect.innerHTML += `<option value="${image.id}">${filename}</option>`;
            });
        }
    },

    // Actualizar estado de conexión
    updateStatus(connected) {
        const statusDot = document.getElementById('status-dot');
        const statusText = document.getElementById('status-text');

        if (connected) {
            statusDot.className = 'status-dot active';
            statusText.textContent = 'Conectado';
        } else {
            statusDot.className = 'status-dot inactive';
            statusText.textContent = 'Desconectado';
        }
    },

    // Métodos para eliminar elementos
    async deleteText(id) {
        if (!confirm('¿Estás seguro de que deseas eliminar este texto?')) return;

        try {
            Utils.showLoading(true);
            const updatedTexts = await eel.delete_text(id)();
            appState.data.texts = updatedTexts;
            this.updateTextsTable();
            this.updateStats();
            Utils.showNotification('Texto eliminado', 'El texto se eliminó correctamente', 'success');
        } catch (error) {
            console.error('Error eliminando texto:', error);
            Utils.showNotification('Error', 'No se pudo eliminar el texto', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async deleteImage(id) {
        if (!confirm('¿Estás seguro de que deseas eliminar esta imagen?')) return;

        try {
            Utils.showLoading(true);
            const response = await eel.delete_image(id)();

            if (response && response.success) {
                // Actualizar la lista de imágenes con la respuesta del servidor
                appState.data.images = response.images || [];
                this.updateImagesTable();
                this.updateStats();
                this.updateSelects();
                Utils.showNotification('Imagen eliminada', response.message || 'La imagen se eliminó correctamente', 'success');
            } else {
                const errorMsg = response ? response.message : 'No se recibió respuesta del servidor';
                Utils.showNotification('Error', errorMsg, 'error');
            }
        } catch (error) {
            console.error('Error eliminando imagen:', error);
            Utils.showNotification('Error', 'Error al comunicarse con el servidor: ' + (error.message || 'Error desconocido'), 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async deleteGroup(id) {
        if (!confirm('¿Estás seguro de que deseas eliminar este grupo?')) return;

        try {
            Utils.showLoading(true);
            const updatedGroups = await eel.delete_group(id)();
            appState.data.groups = updatedGroups;
            this.updateGroupsTable();
            this.updateStats();
            Utils.showNotification('Grupo eliminado', 'El grupo se eliminó correctamente', 'success');
        } catch (error) {
            console.error('Error eliminando grupo:', error);
            Utils.showNotification('Error', 'No se pudo eliminar el grupo', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async deletePage(id) {
        if (!confirm('¿Estás seguro de que deseas eliminar esta página?')) return;

        try {
            Utils.showLoading(true);
            const updatedPages = await eel.delete_page(id)();
            appState.data.pages = updatedPages;
            this.updatePagesTable();
            this.updateStats();
            this.updateSelects();
            Utils.showNotification('Página eliminada', 'La página se eliminó correctamente', 'success');
        } catch (error) {
            console.error('Error eliminando página:', error);
            Utils.showNotification('Error', 'No se pudo eliminar la página', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async deleteScheduledPost(id) {
        if (!confirm('¿Estás seguro de que deseas eliminar esta publicación programada?')) return;

        try {
            Utils.showLoading(true);
            const updatedScheduled = await eel.delete_scheduled_post(id)();
            appState.data.scheduled_posts = updatedScheduled;
            this.updateScheduledPostsTable();
            this.updateStats();
            Utils.showNotification('Publicación cancelada', 'La publicación programada se eliminó correctamente', 'success');
        } catch (error) {
            console.error('Error eliminando publicación programada:', error);
            Utils.showNotification('Error', 'No se pudo eliminar la publicación programada', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },
    updateHistoryTable() {
        const tbody = document.getElementById('history-table-body');
        const logs = appState.data.publication_log;

        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No hay actividades recientes en el historial.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(log => {
            const statusClass = log.status === 'Success' ? 'tag-success' : 'tag-danger';
            const statusText = log.status === 'Success' ? 'Completado' : 'Fallido';

            const actionText = log.target_type === 'group' ? 'Publicación en grupo' : 'Publicación en página';

            let detailsHtml = 'N/A';
            if (log.published_post_url) {
                detailsHtml = `<a href="${log.published_post_url}" target="_blank" style="color: var(--primary);">Ver Publicación</a>`;
            } else if (log.status === 'Failed') {
                detailsHtml = 'No se pudo publicar.';
            }

            return `
                <tr>
                    <td>${Utils.formatDateTime(log.timestamp)}</td>
                    <td>${actionText}</td>
                    <td style="max-width: 250px; word-wrap: break-word;">
                        <a href="${log.target_url}" target="_blank">${Utils.truncateText(log.target_url, 40)}</a>
                    </td>
                    <td><span class="tag ${statusClass}">${statusText}</span></td>
                    <td>${detailsHtml}</td>
                </tr>
            `;
        }).join('');
    },

    // NUEVA FUNCIÓN: Actualizar vista previa de publicación
    updatePublicationPreview() {
        const previewSection = document.getElementById('publication-preview-section');
        const previewText = document.getElementById('preview-text');
        const previewImage = document.getElementById('preview-image');
        const previewImageSrc = document.getElementById('preview-image-src');

        // Obtener el tipo de publicación seleccionado
        const publicationType = document.querySelector('input[name="publication-type"]:checked')?.value;

        if (publicationType === 'text-and-image') {
            previewSection.style.display = 'block';

            // Buscar un par de texto e imagen coherente
            const coherentPair = this.findCoherentPair();
            if (coherentPair) {
                previewText.textContent = coherentPair.text.content;
                if (coherentPair.image) {
                    previewImage.style.display = 'block';
                    previewImageSrc.src = Utils.getImageSrc(coherentPair.image.path);
                } else {
                    previewImage.style.display = 'none';
                }
            } else {
                previewText.textContent = 'No se encontró contenido coherente disponible';
                previewImage.style.display = 'none';
            }
        } else {
            previewSection.style.display = 'none';
        }
    },

    // NUEVA FUNCIÓN: Encontrar par coherente de texto e imagen
    findCoherentPair() {
        if (!appState.data.texts || !appState.data.images) {
            return null;
        }

        // Buscar una imagen disponible
        const availableImages = appState.data.images.filter(img => {
            const usageCount = img.usage_count || 0;
            return usageCount < 10; // Límite de uso
        });

        if (availableImages.length === 0) {
            return null;
        }

        const selectedImage = availableImages[0];
        const imageTags = (selectedImage.manual_tags || '').split(',').map(tag => tag.trim().toLowerCase());

        // Buscar texto coherente
        const coherentTexts = appState.data.texts.filter(text => {
            const textTags = (text.ai_tags || '').split(',').map(tag => tag.trim().toLowerCase());
            return textTags.some(tag => imageTags.includes(tag));
        });

        if (coherentTexts.length === 0) {
            return null;
        }

        return {
            text: coherentTexts[0],
            image: selectedImage
        };
    },
};

// Manejo de contenido
const ContentManager = {
    // Añadir texto manual
    async addManualText() {
        const content = document.getElementById('manual-text-input').value.trim();
        if (!content) {
            Utils.showNotification('Error', 'Por favor ingresa un texto válido', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const updatedTexts = await eel.add_manual_text(content)();
            appState.data.texts = updatedTexts;
            DataManager.updateTextsTable();
            DataManager.updateStats();
            document.getElementById('manual-text-input').value = '';
            Utils.showNotification('Texto añadido', 'El texto se agregó correctamente', 'success');
        } catch (error) {
            console.error('Error añadiendo texto:', error);
            Utils.showNotification('Error', 'No se pudo añadir el texto', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Generar textos con IA
    async generateAiTexts() {
        const topic = document.getElementById('ai-topic-input').value.trim();
        const count = parseInt(document.getElementById('ai-count-input').value) || 5;

        if (!topic) {
            Utils.showNotification('Error', 'Por favor ingresa un tema válido', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const updatedTexts = await eel.generate_ai_texts(topic, count)();
            appState.data.texts = updatedTexts;
            DataManager.updateTextsTable();
            DataManager.updateStats();
            document.getElementById('ai-topic-input').value = '';
            Utils.showNotification('Textos generados', `Se generaron ${count} textos con IA`, 'success');
        } catch (error) {
            console.error('Error generando textos:', error);
            Utils.showNotification('Error', 'No se pudieron generar los textos con IA', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Añadir imágenes
    async addImages() {
        const tags = document.getElementById('image-tags-input').value.trim();
        if (!tags) {
            Utils.showNotification('Error', 'Por favor ingresa etiquetas para las imágenes', 'warning');
            return;
        }

        try {
            // Mostrar inicio de proceso; el progreso detallado lo maneja Python via eel.update_upload_progress
            Utils.showNotification('Procesando', 'Procesando imágenes seleccionadas...', 'info');
            await eel.add_images(tags)();
            // La actualización de UI llegará a través de eel.update_data_view('images', ...)
            // No forzar tabla aquí para evitar condiciones de carrera
            document.getElementById('image-tags-input').value = '';
        } catch (error) {
            console.error('Error añadiendo imágenes:', error);
            Utils.showNotification('Error', 'No se pudieron añadir las imágenes', 'error');
        }
    }
};

// Manejo de destinos
const DestinationManager = {
    // Añadir grupo individual
    async addSingleGroup() {
        const url = document.getElementById('group-url-input').value.trim();
        const tags = document.getElementById('group-tags-single-input').value.trim();

        if (!url) {
            Utils.showNotification('Error', 'Por favor ingresa una URL válida', 'warning');
            return;
        }

        if (!Utils.isValidUrl(url)) {
            Utils.showNotification('Error', 'La URL ingresada no es válida', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const updatedGroups = await eel.add_group(url, tags)();
            appState.data.groups = updatedGroups;
            DataManager.updateGroupsTable();
            DataManager.updateStats();
            document.getElementById('group-url-input').value = '';
            document.getElementById('group-tags-single-input').value = '';
            Utils.showNotification('Grupo añadido', 'El grupo se agregó correctamente', 'success');
        } catch (error) {
            console.error('Error añadiendo grupo:', error);
            Utils.showNotification('Error', 'No se pudo añadir el grupo', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Importar grupos masivamente
    async importBulkGroups() {
        const urls = document.getElementById('bulk-groups-input').value.trim();
        const tags = document.getElementById('bulk-tags-input').value.trim();

        if (!urls) {
            Utils.showNotification('Error', 'Por favor ingresa URLs válidas', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const result = await eel.add_groups_bulk(urls, tags)();
            appState.data = result;
            DataManager.updateUI();
            document.getElementById('bulk-groups-input').value = '';
            document.getElementById('bulk-tags-input').value = '';
            Utils.showNotification('Importación completada', 'Los grupos se importaron correctamente', 'success');
        } catch (error) {
            console.error('Error importando grupos:', error);
            Utils.showNotification('Error', 'No se pudieron importar los grupos', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Añadir página
    async addPage() {
        const name = document.getElementById('page-name-input').value.trim();
        const url = document.getElementById('page-url-input').value.trim();

        if (!name || !url) {
            Utils.showNotification('Error', 'Por favor completa todos los campos', 'warning');
            return;
        }

        if (!Utils.isValidUrl(url)) {
            Utils.showNotification('Error', 'La URL ingresada no es válida', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const updatedPages = await eel.add_page(name, url)();
            appState.data.pages = updatedPages;
            DataManager.updatePagesTable();
            DataManager.updateStats();
            DataManager.updateSelects();
            document.getElementById('page-name-input').value = '';
            document.getElementById('page-url-input').value = '';
            Utils.showNotification('Página añadida', 'La página se agregó correctamente', 'success');
        } catch (error) {
            console.error('Error añadiendo página:', error);
            Utils.showNotification('Error', 'No se pudo añadir la página', 'error');
        } finally {
            Utils.showLoading(false);
        }
    }
};

// Manejo del programador
const SchedulerManager = {
    // Obtener sugerencia de contenido
    async getContentSuggestion() {
        const pageId = document.getElementById('schedule-page-select').value;
        if (!pageId) {
            Utils.showNotification('Error', 'Por favor selecciona una página', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const suggestion = await eel.get_content_suggestion(pageId, "")();

            if (suggestion.success) {
                document.getElementById('schedule-text-content').value = suggestion.text.content;
                document.getElementById('schedule-image-select').value = suggestion.image.id;
                Utils.showNotification('Contenido sugerido', 'Se ha sugerido contenido coherente', 'success');
            } else {
                Utils.showNotification('Sin sugerencias', suggestion.message, 'warning');
            }
        } catch (error) {
            console.error('Error obteniendo sugerencia:', error);
            Utils.showNotification('Error', 'No se pudo obtener una sugerencia', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Programar publicación
    async schedulePost() {
        const pageId = document.getElementById('schedule-page-select').value;
        const publishAt = document.getElementById('schedule-datetime').value;
        const textContent = document.getElementById('schedule-text-content').value.trim();
        const imageId = document.getElementById('schedule-image-select').value || null;

        if (!pageId) {
            Utils.showNotification('Error', 'Por favor selecciona una página', 'warning');
            return;
        }

        if (!publishAt) {
            Utils.showNotification('Error', 'Por favor selecciona fecha y hora', 'warning');
            return;
        }

        if (!textContent) {
            Utils.showNotification('Error', 'Por favor ingresa el contenido del texto', 'warning');
            return;
        }

        const data = {
            page_id: parseInt(pageId),
            publish_at: publishAt,
            text_content: textContent,
            image_id: imageId ? parseInt(imageId) : null
        };

        try {
            Utils.showLoading(true);
            const updatedScheduled = await eel.schedule_page_post(data)();
            appState.data.scheduled_posts = updatedScheduled;
            DataManager.updateScheduledPostsTable();
            DataManager.updateStats();

            // Limpiar formulario
            document.getElementById('schedule-page-select').value = '';
            document.getElementById('schedule-datetime').value = '';
            document.getElementById('schedule-text-content').value = '';
            document.getElementById('schedule-image-select').value = '';

            Utils.showNotification('Publicación programada', 'La publicación se programó correctamente', 'success');
        } catch (error) {
            console.error('Error programando publicación:', error);
            Utils.showNotification('Error', 'No se pudo programar la publicación', 'error');
        } finally {
            Utils.showLoading(false);
        }
    }
};

// Manejo de galería de imágenes
const GalleryManager = {
    // Filtrar imágenes por etiquetas
    filterImages(filterText) {
        const gallery = document.getElementById('image-gallery');
        const items = gallery.querySelectorAll('.gallery-item');

        if (!filterText.trim()) {
            items.forEach(item => item.style.display = 'block');
            return;
        }

        const filterTags = filterText.toLowerCase().split(',').map(tag => tag.trim());

        items.forEach(item => {
            const tags = Array.from(item.querySelectorAll('.gallery-item-tags .tag'))
                .map(tag => tag.textContent.toLowerCase());

            const matches = filterTags.some(filterTag =>
                tags.some(tag => tag.includes(filterTag))
            );

            item.style.display = matches ? 'block' : 'none';
        });
    },

    // Ordenar imágenes
    sortImages(sortBy) {
        const gallery = document.getElementById('image-gallery');
        const items = Array.from(gallery.querySelectorAll('.gallery-item'));

        items.sort((a, b) => {
            switch (sortBy) {
                case 'newest':
                    return parseInt(b.dataset.imageId) - parseInt(a.dataset.imageId);
                case 'oldest':
                    return parseInt(a.dataset.imageId) - parseInt(b.dataset.imageId);
                case 'usage':
                    const aUsage = parseInt(a.querySelector('.gallery-item-usage .tag').textContent) || 0;
                    const bUsage = parseInt(b.querySelector('.gallery-item-usage .tag').textContent) || 0;
                    return bUsage - aUsage;
                case 'name':
                    const aName = a.querySelector('.gallery-item-usage span').textContent;
                    const bName = b.querySelector('.gallery-item-usage span').textContent;
                    return aName.localeCompare(bName);
                default:
                    return 0;
            }
        });

        // Reorganizar elementos en el DOM
        items.forEach(item => gallery.appendChild(item));
    }
};

// Manejo de publicación en grupos
const GroupPublishingManager = {
    // Iniciar publicación en grupos
    async startGroupPublishing() {
        const groupTags = document.getElementById('group-tags-input').value.trim();
        const contentTags = document.getElementById('content-tags-input').value.trim();
        const publicationType = document.querySelector('input[name="publication-type"]:checked')?.value;

        if (!groupTags || !contentTags) {
            Utils.showNotification('Error', 'Por favor completa las etiquetas de grupos y contenido', 'warning');
            return;
        }

        // Añadir información del tipo de publicación a las etiquetas
        const enhancedContentTags = publicationType === 'text-only'
            ? `${contentTags},text-only`
            : `${contentTags},text-and-image`;

        try {
            Utils.showLoading(true);
            const result = await eel.start_group_publishing_process(groupTags, enhancedContentTags)();

            if (result.success) {
                appState.ui.isGroupPublishing = true;
                this.updatePublishingUI(true);
                Utils.showNotification('Publicación iniciada', result.message, 'success');
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error iniciando publicación:', error);
            Utils.showNotification('Error', 'No se pudo iniciar la publicación en grupos', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Detener publicación en grupos
    async stopGroupPublishing() {
        try {
            Utils.showLoading(true);
            const result = await eel.stop_group_publishing_process()();

            if (result.success) {
                appState.ui.isGroupPublishing = false;
                this.updatePublishingUI(false);
                Utils.showNotification('Publicación detenida', 'El proceso se detuvo correctamente', 'success');
            }
        } catch (error) {
            console.error('Error deteniendo publicación:', error);
            Utils.showNotification('Error', 'No se pudo detener la publicación', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Actualizar interfaz de publicación
    updatePublishingUI(isPublishing) {
        const startBtn = document.getElementById('start-group-publishing');
        const stopBtn = document.getElementById('stop-group-publishing');

        if (isPublishing) {
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-flex';
            startBtn.disabled = true;
        } else {
            startBtn.style.display = 'inline-flex';
            stopBtn.style.display = 'none';
            startBtn.disabled = false;
        }
    }
};

// Manejo de logs
const LogManager = {
    // Limpiar logs
    clearLogs() {
        const logPanel = document.getElementById('log-panel');
        logPanel.innerHTML = '<p class="log-info">Logs limpiados.</p>';
    },

    // Añadir log (esta función será llamada desde Python)
    addLog(message, type = 'info') {
        const logPanel = document.getElementById('log-panel');
        const logEntry = document.createElement('p');
        logEntry.className = `log-${type}`;
        logEntry.textContent = message;
        logPanel.appendChild(logEntry);
        logPanel.scrollTop = logPanel.scrollHeight;
    }
};

// Exponer función correctamente para que Python pueda llamarla
eel.expose(log_to_panel);
function log_to_panel(message) {
    LogManager.addLog(message);
}

// Manejo de interfaz
const UIManager = {
    // Inicializar interfaz
    init() {
        this.setupNavigation();
        this.setupTheme();
        this.setupMobileMenu();
        this.setupEventListeners();
        this.setupNotifications();
    },




    // Configurar navegación entre pestañas
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        const tabContents = document.querySelectorAll('.tab-content');

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();

                const tabId = link.dataset.tab;

                // Actualizar enlaces activos
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');

                // Actualizar contenido activo
                tabContents.forEach(t => t.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');

                appState.ui.currentTab = tabId;

                // Cerrar menú móvil
                if (window.innerWidth < 992) {
                    document.getElementById('sidebar').classList.remove('active');
                }
            });
        });
    },

    // Configurar tema
    setupTheme() {
        const themeToggle = document.getElementById('theme-toggle');
        const currentTheme = localStorage.getItem('theme') || 'dark';

        document.body.setAttribute('data-theme', currentTheme);
        themeToggle.innerHTML = currentTheme === 'dark' ?
            '<i class="fas fa-moon"></i>' :
            '<i class="fas fa-sun"></i>';

        themeToggle.addEventListener('click', () => {
            const current = document.body.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';

            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);

            themeToggle.innerHTML = newTheme === 'dark' ?
                '<i class="fas fa-moon"></i>' :
                '<i class="fas fa-sun"></i>';
        });
    },

    // Configurar menú móvil
    setupMobileMenu() {
        const mobileToggle = document.getElementById('mobile-menu-toggle');
        const sidebar = document.getElementById('sidebar');

        mobileToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });

        // Cerrar menú al hacer clic fuera
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 992 &&
                !sidebar.contains(e.target) &&
                !mobileToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    },

    // Configurar eventos de botones
    setupEventListeners() {
        // --- LÓGICA DEL MODAL ---
        const modal = document.getElementById('generic-modal');
        const closeBtn = modal.querySelector('.modal-close-btn');
        closeBtn.onclick = () => UIManager.closeModal();
        window.onclick = (event) => {
            if (event.target == modal) {
                UIManager.closeModal();
            }
        };

        // Botones de contenido
        document.getElementById('add-manual-text').addEventListener('click', ContentManager.addManualText);
        document.getElementById('generate-ai-texts').addEventListener('click', ContentManager.generateAiTexts);
        document.getElementById('add-images').addEventListener('click', ContentManager.addImages);

        // Botones de destinos
        document.getElementById('add-single-group').addEventListener('click', DestinationManager.addSingleGroup);
        document.getElementById('import-bulk-groups').addEventListener('click', DestinationManager.importBulkGroups);
        document.getElementById('add-page').addEventListener('click', DestinationManager.addPage);

        // Botones del programador
        document.getElementById('get-content-suggestion').addEventListener('click', SchedulerManager.getContentSuggestion);
        document.getElementById('schedule-post').addEventListener('click', SchedulerManager.schedulePost);

        // Botones de publicación
        document.getElementById('start-group-publishing').addEventListener('click', () => GroupPublishingManager.startGroupPublishing());
        document.getElementById('stop-group-publishing').addEventListener('click', () => GroupPublishingManager.stopGroupPublishing());

        // Botones de actualización
        document.getElementById('refresh-content').addEventListener('click', DataManager.loadInitialData);
        document.getElementById('refresh-destinations').addEventListener('click', DataManager.loadInitialData);
        document.getElementById('refresh-scheduler').addEventListener('click', DataManager.loadInitialData);

        // Botón de limpiar logs
        document.getElementById('clear-log').addEventListener('click', LogManager.clearLogs);

        // Envío con Enter en campos de texto
        document.getElementById('manual-text-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                ContentManager.addManualText();
            }
        });

        // NUEVOS EVENT LISTENERS PARA LAS MEJORAS

        // Opciones de publicación
        document.querySelectorAll('input[name="publication-type"]').forEach(radio => {
            radio.addEventListener('change', () => {
                DataManager.updatePublicationPreview();
            });
        });

        // Controles de galería
        document.getElementById('toggle-gallery-view')?.addEventListener('click', () => {
            document.getElementById('image-gallery').style.display = 'grid';
            document.getElementById('images-table-container').style.display = 'none';
            document.getElementById('toggle-gallery-view').classList.add('active');
            document.getElementById('toggle-table-view').classList.remove('active');
        });

        document.getElementById('toggle-table-view')?.addEventListener('click', () => {
            document.getElementById('image-gallery').style.display = 'none';
            document.getElementById('images-table-container').style.display = 'block';
            document.getElementById('toggle-table-view').classList.add('active');
            document.getElementById('toggle-gallery-view').classList.remove('active');
        });

        // Inicializar vista de galería por defecto
        document.getElementById('toggle-gallery-view')?.classList.add('active');

        // Filtros de galería
        document.getElementById('gallery-filter-tags')?.addEventListener('input', (e) => {
            GalleryManager.filterImages(e.target.value);
        });

        document.getElementById('gallery-sort')?.addEventListener('change', (e) => {
            GalleryManager.sortImages(e.target.value);
        });

        // Event listeners para sesiones
        document.getElementById('create-session-btn')?.addEventListener('click', () => {
            UIManager.showCreateSessionModal();
        });

        document.getElementById('create-session-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = document.getElementById('session-name').value.trim();
            const groupTags = document.getElementById('session-group-tags').value.trim();
            const contentTags = document.getElementById('session-content-tags').value.trim();
            const publicationType = document.querySelector('input[name="session-publication-type"]:checked')?.value;

            if (!name || !groupTags || !contentTags) {
                Utils.showNotification('Error', 'Por favor completa todos los campos', 'warning');
                return;
            }

            SessionManager.createSession(name, groupTags, contentTags, publicationType);
        });
    },

    async saveTextUpdate(id) {
        const newContent = document.getElementById('text-edit-textarea').value.trim();
        if (!newContent) {
            Utils.showNotification('Error', 'El contenido no puede estar vacío.', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const updatedTexts = await eel.update_text(id, newContent)();
            appState.data.texts = updatedTexts;
            this.updateTextsTable();
            UIManager.closeModal();
            Utils.showNotification('Texto actualizado', 'El texto y sus etiquetas IA se actualizaron correctamente.', 'success');
        } catch (error) {
            console.error('Error guardando texto:', error);
            Utils.showNotification('Error', 'No se pudo guardar el texto actualizado.', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async updateTextTags(id) {
        const newTags = document.getElementById('text-tags-input').value.trim();
        if (!newTags) {
            Utils.showNotification('Error', 'Las etiquetas no pueden estar vacías.', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const result = await eel.update_text_tags(id, newTags)();
            if (result.success) {
                // Recargar datos y actualizar tabla
                const allData = await eel.get_initial_data()();
                appState.data = allData;
                this.updateTextsTable();
                UIManager.closeModal();
                Utils.showNotification('Etiquetas actualizadas', result.message, 'success');
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error actualizando etiquetas del texto:', error);
            Utils.showNotification('Error', 'No se pudieron actualizar las etiquetas.', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async updateImageTags(id) {
        const newTags = document.getElementById('image-tags-input').value.trim();
        if (!newTags) {
            Utils.showNotification('Error', 'Las etiquetas no pueden estar vacías.', 'warning');
            return;
        }

        try {
            Utils.showLoading(true);
            const result = await eel.update_image_tags(id, newTags)();
            if (result.success) {
                // Recargar datos y actualizar tabla
                const allData = await eel.get_initial_data()();
                appState.data = allData;
                this.updateImagesTable();
                UIManager.closeModal();
                Utils.showNotification('Etiquetas actualizadas', result.message, 'success');
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error actualizando etiquetas de la imagen:', error);
            Utils.showNotification('Error', 'No se pudieron actualizar las etiquetas.', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    async regenerateTextTags(id) {
        try {
            Utils.showLoading(true);
            const result = await eel.regenerate_text_tags(id)();
            if (result.success) {
                // Recargar datos y actualizar tabla
                const allData = await eel.get_initial_data()();
                appState.data = allData;
                this.updateTextsTable();
                UIManager.closeModal();
                Utils.showNotification('Etiquetas regeneradas', result.message, 'success');
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error regenerando etiquetas del texto:', error);
            Utils.showNotification('Error', 'No se pudieron regenerar las etiquetas.', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    openModal() {
        document.getElementById('generic-modal').style.display = 'block';
    },

    closeModal() {
        document.getElementById('generic-modal').style.display = 'none';
        document.getElementById('modal-body').innerHTML = ''; // Limpiar contenido al cerrar
    },

    showImageModal(imagePath) {
        const modalBody = document.getElementById('modal-body');
        const imageSrc = Utils.getImageSrc(imagePath);
        modalBody.innerHTML = `<img src="${imageSrc}" alt="Vista previa de imagen" style="max-width: 100%; height: auto;">`;
        this.openModal();
    },

    showTextEditModal(id, content) {
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `
            <h3 style="margin-bottom: 15px;">Editar Texto</h3>
            <textarea id="text-edit-textarea" class="form-control" style="min-height: 250px;">${content}</textarea>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="UIManager.closeModal()">Cancelar</button>
                <button class="btn btn-primary" onclick="DataManager.saveTextUpdate(${id})">Guardar Cambios</button>
            </div>
        `;
        this.openModal();
    },

    showTextTagsEditModal(id, currentTags) {
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `
            <h3 style="margin-bottom: 15px;">Editar Etiquetas del Texto</h3>
            <div class="form-group">
                <label for="text-tags-input">Etiquetas (separadas por comas):</label>
                <input type="text" id="text-tags-input" class="form-control" value="${currentTags}" placeholder="ejemplo: marketing,ventas,oferta">
                <small class="form-text text-muted">Separa las etiquetas con comas. Las etiquetas se usarán para filtrar el contenido durante la publicación.</small>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="UIManager.closeModal()">Cancelar</button>
                <button class="btn btn-warning" onclick="DataManager.regenerateTextTags(${id})">Regenerar con IA</button>
                <button class="btn btn-primary" onclick="DataManager.updateTextTags(${id})">Guardar Cambios</button>
            </div>
        `;
        this.openModal();
    },

    showImageTagsEditModal(id, currentTags) {
        const modalBody = document.getElementById('modal-body');
        modalBody.innerHTML = `
            <h3 style="margin-bottom: 15px;">Editar Etiquetas de la Imagen</h3>
            <div class="form-group">
                <label for="image-tags-input">Etiquetas (separadas por comas):</label>
                <input type="text" id="image-tags-input" class="form-control" value="${currentTags}" placeholder="ejemplo: coche,ford,oferta">
                <small class="form-text text-muted">Separa las etiquetas con comas. Las etiquetas se usarán para filtrar el contenido durante la publicación.</small>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="UIManager.closeModal()">Cancelar</button>
                <button class="btn btn-primary" onclick="DataManager.updateImageTags(${id})">Guardar Cambios</button>
            </div>
        `;
        this.openModal();
    },

    // Configurar notificaciones
    setupNotifications() {
        const notification = document.getElementById('notification');
        const closeBtn = notification.querySelector('.notification-close');

        closeBtn.addEventListener('click', () => {
            notification.classList.remove('show');
        });
    },

    // Modal para crear sesión
    showCreateSessionModal() {
        document.getElementById('create-session-modal').style.display = 'block';
    },

    closeCreateSessionModal() {
        document.getElementById('create-session-modal').style.display = 'none';
        document.getElementById('create-session-form').reset();
    }
};

// Inicialización de la aplicación
document.addEventListener('DOMContentLoaded', () => {
    UIManager.init();
    DataManager.loadInitialData();

    // Configurar fecha y hora mínima para el programador (ahora)
    const now = new Date();
    const localISOTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById('schedule-datetime').min = localISOTime;
});

// Manejo de errores globales
window.addEventListener('error', (e) => {
    console.error('Error global:', e.error);
    Utils.showNotification('Error del sistema', 'Se ha producido un error inesperado', 'error');
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Promesa rechazada:', e.reason);
    Utils.showNotification('Error del sistema', 'Se ha producido un error de conexión', 'error');
});

// --- GESTOR DE SESIONES ---
const SessionManager = {
    // Crear nueva sesión
    async createSession(name, groupTags, contentTags, publicationType) {
        try {
            Utils.showLoading(true);
            const result = await eel.create_session(name, groupTags, contentTags, publicationType)();

            if (result.success) {
                Utils.showNotification('Sesión creada', result.message, 'success');
                await DataManager.loadSessions();
                UIManager.closeCreateSessionModal();
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error creando sesión:', error);
            Utils.showNotification('Error', 'No se pudo crear la sesión', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Iniciar sesión
    async startSession(sessionId) {
        try {
            Utils.showLoading(true);
            const result = await eel.start_session(sessionId)();

            if (result.success) {
                Utils.showNotification('Sesión iniciada', result.message, 'success');
                await DataManager.loadSessions();
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error iniciando sesión:', error);
            Utils.showNotification('Error', 'No se pudo iniciar la sesión', 'error');
        } finally {
            Utils.showLoading(false);
        }
    },

    // Pausar sesión
    async pauseSession(sessionId) {
        try {
            const result = await eel.pause_session(sessionId)();

            if (result.success) {
                Utils.showNotification('Sesión pausada', result.message, 'success');
                await DataManager.loadSessions();
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error pausando sesión:', error);
            Utils.showNotification('Error', 'No se pudo pausar la sesión', 'error');
        }
    },

    // Detener sesión
    async stopSession(sessionId) {
        try {
            const result = await eel.stop_session(sessionId)();

            if (result.success) {
                Utils.showNotification('Sesión detenida', result.message, 'success');
                await DataManager.loadSessions();
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error deteniendo sesión:', error);
            Utils.showNotification('Error', 'No se pudo detener la sesión', 'error');
        }
    },

    // Eliminar sesión
    async deleteSession(sessionId) {
        if (!confirm('¿Estás seguro de que quieres eliminar esta sesión? Esta acción no se puede deshacer.')) {
            return;
        }

        try {
            const result = await eel.delete_session(sessionId)();

            if (result.success) {
                Utils.showNotification('Sesión eliminada', result.message, 'success');
                await DataManager.loadSessions();
            } else {
                Utils.showNotification('Error', result.message, 'error');
            }
        } catch (error) {
            console.error('Error eliminando sesión:', error);
            Utils.showNotification('Error', 'No se pudo eliminar la sesión', 'error');
        }
    }
};

// Exponer función log_to_panel correctamente
eel.expose(log_to_panel);
function log_to_panel(message) {
    const logPanel = document.getElementById('log-panel');
    const logEntry = document.createElement('p');
    logEntry.className = 'log-info';
    logEntry.textContent = message;
    logPanel.appendChild(logEntry);
    logPanel.scrollTop = logPanel.scrollHeight;
}

// También exponer función de limpieza si la necesitas
eel.expose(clear_log_panel);
function clear_log_panel() {
    const logPanel = document.getElementById('log-panel');
    if (logPanel) {
        logPanel.innerHTML = '<p class="log-info">Logs limpiados.</p>';
    }
}

// Exponer funciones para mostrar progreso de subida de imágenes
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
    } catch (err) {
        console.error('Error actualizando progreso de subida:', err);
    }
}

eel.expose(hide_upload_progress);
function hide_upload_progress() {
    try {
        const progressContainer = document.getElementById('image-upload-progress');
        if (progressContainer) {
            const progressBar = progressContainer.querySelector('.progress');
            if (progressBar) progressBar.style.width = '0%';
            setTimeout(() => {
                progressContainer.style.display = 'none';
            }, 500);
        }
    } catch (err) {
        console.error('Error ocultando progreso de subida:', err);
    }
}

/**
 * Esta función es llamada desde Python para actualizar la UI del botón
 * de publicación en grupos (cambiar entre 'Iniciar' y 'Detener').
 * @param {boolean} isPublishing - True si el proceso ha comenzado, false si ha terminado o fallado.
 */
eel.expose(update_publishing_status);
function update_publishing_status(isPublishing) {
    // Registra en la consola del navegador para depuración
    console.log(`Señal desde Python: Estado de publicación es ahora ${isPublishing}`);

    // Actualiza el estado global de la aplicación en JavaScript
    appState.ui.isGroupPublishing = isPublishing;

    // Llama a la función del objeto GroupPublishingManager que se encarga de la lógica visual
    GroupPublishingManager.updatePublishingUI(isPublishing);
}

/**
 * Esta función es llamada desde los 'workers' de Python después de que
 * completan una tarea lenta (como añadir textos o imágenes).
 * Recibe los datos actualizados y refresca la parte correspondiente de la interfaz.
 * @param {string} dataType - El tipo de datos a actualizar ('texts', 'images', etc.).
 * @param {Array} data - El array de datos actualizado desde la base de datos.
 */
eel.expose(update_data_view);
function update_data_view(dataType, data) {
    // Registra en la consola del navegador para depuración
    console.log(`Recibiendo actualización de datos desde Python para: ${dataType}`);

    // Primero, actualiza el array de datos en el estado global de la aplicación
    if (appState.data.hasOwnProperty(dataType)) {
        appState.data[dataType] = data;
    } else {
        console.error(`El tipo de dato '${dataType}' no existe en appState.data`);
        return;
    }

    // Luego, llama a la función específica que redibuja esa parte de la UI
    switch (dataType) {
        case 'texts':
            DataManager.updateTextsTable();
            Utils.showNotification('Textos Actualizados', 'La lista de textos ha sido refrescada.', 'info');
            break;
        case 'images':
            DataManager.updateImagesTable();
            DataManager.updateSelects(); // Actualiza también los menús desplegables de imágenes
            Utils.showNotification('Imágenes Actualizadas', 'La lista de imágenes ha sido refrescada.', 'info');
            break;
        // Se pueden añadir más casos para otros tipos de datos en el futuro
        // case 'groups':
        //     DataManager.updateGroupsTable();
        //     break;
    }

    // Finalmente, actualiza los contadores y estadísticas generales
    DataManager.updateStats();
}