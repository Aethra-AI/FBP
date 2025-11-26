/**
 * Chatbot Asistente - Sistema de IA para generación de contenido
 * Maneja la interfaz y comunicación con el chatbot backend
 */

class ChatbotUI {
    constructor() {
        this.isOpen = false;
        this.currentCategory = null;
        this.conversationHistory = [];
        this.init();
    }

    init() {
        this.createChatbotHTML();
        this.attachEventListeners();
    }

    createChatbotHTML() {
        const chatbotHTML = `
            <!-- Botón flotante para abrir chatbot -->
            <button id="chatbot-toggle" class="chatbot-toggle" title="Asistente de IA">
                💬
            </button>

            <!-- Panel del chatbot -->
            <div id="chatbot-panel" class="chatbot-panel">
                <div class="chatbot-header">
                    <div class="chatbot-header-title">
                        <span class="chatbot-icon">🤖</span>
                        <span>Asistente de Contenido</span>
                    </div>
                    <div class="chatbot-header-actions">
                        <button id="chatbot-clear" class="chatbot-btn-icon" title="Limpiar conversación">
                            🗑️
                        </button>
                        <button id="chatbot-close" class="chatbot-btn-icon" title="Cerrar">
                            ✕
                        </button>
                    </div>
                </div>

                <div class="chatbot-category-selector">
                    <label>Categoría:</label>
                    <select id="chatbot-category">
                        <option value="">Seleccionar categoría</option>
                        <option value="EMPLEOS">💼 Empleos</option>
                        <option value="SERVICIOS">🔧 Servicios</option>
                        <option value="VENTAS">🛒 Ventas</option>
                    </select>
                </div>

                <div id="chatbot-messages" class="chatbot-messages">
                    <div class="chatbot-message bot-message">
                        <div class="message-avatar">🤖</div>
                        <div class="message-content">
                            <p>¡Hola! Soy tu asistente para crear contenido de Facebook. 👋</p>
                            <p>Puedo ayudarte a:</p>
                            <ul>
                                <li>📝 Generar textos para publicaciones</li>
                                <li>🔄 Crear variaciones de un ejemplo</li>
                                <li>✨ Optimizar contenido existente</li>
                                <li>💡 Sugerirte ideas de contenido</li>
                            </ul>
                            <p>¿En qué puedo ayudarte hoy?</p>
                        </div>
                    </div>
                </div>

                <div class="chatbot-quick-actions" id="chatbot-quick-actions">
                    <button class="quick-action-btn" data-action="generate">
                        📝 Generar Post
                    </button>
                    <button class="quick-action-btn" data-action="add">
                        ➕ Añadir Texto
                    </button>
                    <button class="quick-action-btn" data-action="ideas">
                        💡 Dame Ideas
                    </button>
                    <button class="quick-action-btn" data-action="stats">
                        📊 Ver Estadísticas
                    </button>
                </div>

                <div class="chatbot-input-container">
                    <textarea 
                        id="chatbot-input" 
                        class="chatbot-input" 
                        placeholder="Escribe tu mensaje aquí..."
                        rows="2"
                    ></textarea>
                    <button id="chatbot-send" class="chatbot-send-btn" title="Enviar">
                        ➤
                    </button>
                </div>

                <div class="chatbot-typing-indicator" id="chatbot-typing" style="display: none;">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;

        // Agregar al body
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
    }

    attachEventListeners() {
        // Toggle chatbot
        document.getElementById('chatbot-toggle').addEventListener('click', () => {
            this.toggleChatbot();
        });

        // Close chatbot
        document.getElementById('chatbot-close').addEventListener('click', () => {
            this.toggleChatbot();
        });

        // Clear conversation
        document.getElementById('chatbot-clear').addEventListener('click', () => {
            this.clearConversation();
        });

        // Category selection
        document.getElementById('chatbot-category').addEventListener('change', (e) => {
            this.currentCategory = e.target.value || null;
        });

        // Send message
        document.getElementById('chatbot-send').addEventListener('click', () => {
            this.sendMessage();
        });

        // Send on Enter (Shift+Enter for new line)
        document.getElementById('chatbot-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Quick actions
        document.querySelectorAll('.quick-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.handleQuickAction(action);
            });
        });
    }

    toggleChatbot() {
        this.isOpen = !this.isOpen;
        const panel = document.getElementById('chatbot-panel');
        const toggle = document.getElementById('chatbot-toggle');
        
        if (this.isOpen) {
            panel.classList.add('active');
            toggle.classList.add('active');
        } else {
            panel.classList.remove('active');
            toggle.classList.remove('active');
        }
    }

    async sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();

        if (!message) return;

        // Mostrar mensaje del usuario
        this.addMessage(message, 'user');
        input.value = '';

        // Mostrar indicador de escritura
        this.showTyping();

        try {
            // Enviar al backend
            const response = await eel.chat_with_assistant(message, this.currentCategory)();
            
            this.hideTyping();

            // Mostrar respuesta del bot
            this.addMessage(response.response, 'bot', response);

            // Manejar datos adicionales según la acción
            if (response.action === 'generate' && response.data.texts) {
                this.showGeneratedContent(response.data);
            } else if (response.action === 'add_text' && response.data.text_to_add) {
                // Llamar a add_manual_text con el texto proporcionado
                this.addTextToContent(response.data.text_to_add);
            }

            // Actualizar sugerencias
            if (response.suggestions && response.suggestions.length > 0) {
                this.updateQuickActions(response.suggestions);
            }

        } catch (error) {
            this.hideTyping();
            this.addMessage(
                '❌ Error al procesar tu mensaje. Por favor intenta de nuevo.',
                'bot'
            );
            console.error('Error en chatbot:', error);
        }
    }

    addMessage(content, type = 'bot', metadata = {}) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chatbot-message ${type}-message`;

        const avatar = type === 'user' ? '👤' : '🤖';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                ${this.formatMessage(content)}
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        // Guardar en historial
        this.conversationHistory.push({
            type,
            content,
            metadata,
            timestamp: new Date()
        });
    }

    formatMessage(content) {
        // Convertir markdown básico a HTML
        let formatted = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // **bold**
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // *italic*
            .replace(/\n/g, '<br>'); // saltos de línea

        return `<p>${formatted}</p>`;
    }

    showGeneratedContent(data) {
        const texts = data.texts || [];
        const category = data.category || '';

        if (texts.length === 0) return;

        // Crear panel con los textos generados
        const contentDiv = document.createElement('div');
        contentDiv.className = 'generated-content-panel';

        let html = `
            <div class="generated-content-header">
                <h4>Textos Generados (${category})</h4>
            </div>
        `;

        texts.forEach((text, index) => {
            html += `
                <div class="generated-text-item">
                    <div class="generated-text-content">${text}</div>
                    <div class="generated-text-actions">
                        <button class="btn-save-text" data-text="${this.escapeHtml(text)}" data-category="${category}">
                            ✅ Guardar
                        </button>
                        <button class="btn-copy-text" data-text="${this.escapeHtml(text)}">
                            📋 Copiar
                        </button>
                    </div>
                </div>
            `;
        });

        html += `
            <div class="generated-content-actions">
                <button class="btn-save-all-texts" data-category="${category}">
                    💾 Guardar Todos
                </button>
            </div>
        `;

        contentDiv.innerHTML = html;

        // Agregar al chat
        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.appendChild(contentDiv);
        this.scrollToBottom();

        // Attach event listeners para los botones
        this.attachGeneratedContentListeners(contentDiv, texts, category);
    }

    attachGeneratedContentListeners(container, texts, category) {
        // Guardar texto individual
        container.querySelectorAll('.btn-save-text').forEach(btn => {
            btn.addEventListener('click', async () => {
                const text = btn.dataset.text;
                await this.saveTexts([text], category);
            });
        });

        // Copiar texto
        container.querySelectorAll('.btn-copy-text').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.dataset.text;
                navigator.clipboard.writeText(text);
                btn.textContent = '✅ Copiado';
                setTimeout(() => {
                    btn.textContent = '📋 Copiar';
                }, 2000);
            });
        });

        // Guardar todos
        container.querySelector('.btn-save-all-texts')?.addEventListener('click', async () => {
            await this.saveTexts(texts, category);
        });
    }

    async saveTexts(texts, category) {
        try {
            this.showTyping();
            const result = await eel.save_generated_texts(texts, category)();
            this.hideTyping();

            if (result.success) {
                this.addMessage(result.message, 'bot');
                
                // Recargar datos si estamos en la pestaña de contenido
                if (typeof loadAllData === 'function') {
                    loadAllData();
                }
            } else {
                this.addMessage(`❌ ${result.message}`, 'bot');
            }
        } catch (error) {
            this.hideTyping();
            this.addMessage('❌ Error al guardar los textos', 'bot');
            console.error(error);
        }
    }

    async addTextToContent(text) {
        try {
            // Llamar a add_manual_text (función existente que ya genera etiquetas)
            await eel.add_manual_text(text)();
            
            // Esperar un momento para que se procese
            setTimeout(() => {
                this.addMessage('✅ ¡Texto guardado exitosamente con etiquetas generadas automáticamente!\n\nYa está disponible en tu biblioteca de contenido.', 'bot');
                
                // Recargar datos si estamos en la pestaña de contenido
                if (typeof loadAllData === 'function') {
                    loadAllData();
                }
            }, 1500);
            
        } catch (error) {
            this.addMessage('❌ Error al guardar el texto', 'bot');
            console.error(error);
        }
    }

    handleQuickAction(action) {
        const messages = {
            'generate': '📝 Quiero generar un post para publicar',
            'ideas': '💡 Dame ideas de contenido',
            'stats': '📊 Muéstrame estadísticas de mi contenido',
            'add': '➕ Quiero añadir un texto al contenido'
        };

        const input = document.getElementById('chatbot-input');
        input.value = messages[action] || '';
        this.sendMessage();
    }

    updateQuickActions(suggestions) {
        const container = document.getElementById('chatbot-quick-actions');
        container.innerHTML = '';

        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'quick-action-btn';
            btn.textContent = suggestion;
            btn.addEventListener('click', () => {
                document.getElementById('chatbot-input').value = suggestion;
                this.sendMessage();
            });
            container.appendChild(btn);
        });
    }

    showTyping() {
        document.getElementById('chatbot-typing').style.display = 'flex';
        this.scrollToBottom();
    }

    hideTyping() {
        document.getElementById('chatbot-typing').style.display = 'none';
    }

    scrollToBottom() {
        const container = document.getElementById('chatbot-messages');
        container.scrollTop = container.scrollHeight;
    }

    async clearConversation() {
        if (!confirm('¿Estás seguro de que quieres limpiar la conversación?')) {
            return;
        }

        try {
            await eel.clear_chat_history()();
            
            // Limpiar UI
            const messagesContainer = document.getElementById('chatbot-messages');
            messagesContainer.innerHTML = `
                <div class="chatbot-message bot-message">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        <p>Conversación limpiada. ¿En qué puedo ayudarte? 😊</p>
                    </div>
                </div>
            `;

            this.conversationHistory = [];
        } catch (error) {
            console.error('Error limpiando historial:', error);
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar chatbot cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new ChatbotUI();
});
