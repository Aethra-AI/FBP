/**
 * Sistema de Onboarding - Tour Guiado para Nuevos Usuarios
 * Hace que la aplicación sea super intuitiva y fácil de usar
 */

class OnboardingTour {
    constructor() {
        this.currentStep = 0;
        this.isActive = false;
        this.steps = [];
        this.init();
    }

    init() {
        // Verificar si es la primera vez que el usuario abre la app
        const hasSeenTour = localStorage.getItem('hasSeenOnboardingTour');
        
        if (!hasSeenTour) {
            // Primera vez - mostrar bienvenida completa
            this.showWelcomeScreen();
        } else {
            // Usuario recurrente - solo mostrar botón de ayuda
            this.showHelpButton();
        }

        this.createOnboardingHTML();
        this.defineSteps();
    }

    showWelcomeScreen() {
        const welcomeHTML = `
            <div class="welcome-screen active">
                <div class="welcome-content">
                    <div class="welcome-icon">👋</div>
                    <h1 class="welcome-title">¡Bienvenido a Swiftly!</h1>
                    <p class="welcome-subtitle">
                        Tu asistente inteligente para automatizar publicaciones en Facebook
                    </p>

                    <div class="welcome-features">
                        <div class="welcome-feature">
                            <div class="welcome-feature-icon">🤖</div>
                            <div class="welcome-feature-text">
                                <strong>Chatbot con IA</strong>
                                Genera contenido profesional en segundos
                            </div>
                        </div>
                        <div class="welcome-feature">
                            <div class="welcome-feature-icon">🎯</div>
                            <div class="welcome-feature-text">
                                <strong>Categorización Inteligente</strong>
                                Empleos, Servicios y Ventas perfectamente separados
                            </div>
                        </div>
                        <div class="welcome-feature">
                            <div class="welcome-feature-icon">⚡</div>
                            <div class="welcome-feature-text">
                                <strong>Automatización Completa</strong>
                                Publica en múltiples grupos automáticamente
                            </div>
                        </div>
                    </div>

                    <div class="welcome-actions">
                        <button class="welcome-btn welcome-btn-tour" onclick="onboarding.startTour()">
                            🚀 Hacer Tour Guiado
                        </button>
                        <button class="welcome-btn welcome-btn-skip" onclick="onboarding.skipWelcome()">
                            Saltar y Explorar
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', welcomeHTML);
    }

    showHelpButton() {
        const helpButton = `
            <button class="start-tour-btn" onclick="onboarding.startTour()">
                <span class="icon">❓</span>
                <span>Tour Guiado</span>
            </button>
        `;
        document.body.insertAdjacentHTML('beforeend', helpButton);
    }

    createOnboardingHTML() {
        const onboardingHTML = `
            <div class="onboarding-overlay" id="onboarding-overlay"></div>
            <div class="onboarding-tooltip" id="onboarding-tooltip">
                <div class="onboarding-tooltip-header">
                    <div class="onboarding-tooltip-icon">👉</div>
                    <div class="onboarding-tooltip-title" id="onboarding-title">Título</div>
                </div>
                <div class="onboarding-tooltip-content" id="onboarding-content">
                    Contenido del paso
                </div>
                <div class="onboarding-tooltip-actions">
                    <div class="onboarding-progress" id="onboarding-progress">1/5</div>
                    <div class="onboarding-buttons">
                        <button class="onboarding-btn onboarding-btn-skip" onclick="onboarding.skipTour()">
                            Saltar
                        </button>
                        <button class="onboarding-btn onboarding-btn-prev" onclick="onboarding.prevStep()" id="btn-prev">
                            ← Anterior
                        </button>
                        <button class="onboarding-btn onboarding-btn-next" onclick="onboarding.nextStep()" id="btn-next">
                            Siguiente →
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', onboardingHTML);
    }

    defineSteps() {
        this.steps = [
            {
                target: '.chatbot-toggle',
                title: '💬 Tu Asistente Personal con IA',
                content: 'Este es el <strong>Chatbot Inteligente</strong>. Haz clic aquí para generar contenido, añadir textos, o pedir ideas. Es como tener a ChatGPT integrado en tu app.',
                icon: '🤖',
                position: 'left'
            },
            {
                target: '[data-tab="content"]',
                title: '📚 Biblioteca de Contenido',
                content: 'Aquí se almacenan tus <strong>textos e imágenes</strong>. Todo está organizado por categorías (Empleos, Servicios, Ventas) automáticamente.',
                icon: '📚',
                position: 'bottom'
            },
            {
                target: '[data-tab="groups"]',
                title: '👥 Gestión de Grupos',
                content: 'Agrega los grupos de Facebook donde quieres publicar. Asigna <strong>etiquetas</strong> para organizar (ej: "empleos", "honduras").',
                icon: '👥',
                position: 'bottom'
            },
            {
                target: '[data-tab="automation"]',
                title: '⚡ Automatización',
                content: 'Crea <strong>sesiones automáticas</strong>. El sistema seleccionará el contenido perfecto para cada grupo basándose en categorías.',
                icon: '⚡',
                position: 'bottom'
            },
            {
                target: '.chatbot-toggle',
                title: '🎉 ¡Listo para Empezar!',
                content: '<strong>Prueba ahora:</strong><br><br>1. Haz clic en el chatbot 💬<br>2. Escribe "Genera un post sobre empleos"<br>3. Guarda los textos generados<br><br>¡Es así de fácil!',
                icon: '🚀',
                position: 'left'
            }
        ];
    }

    skipWelcome() {
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.classList.remove('active');
            setTimeout(() => welcomeScreen.remove(), 500);
        }
        localStorage.setItem('hasSeenOnboardingTour', 'true');
        this.showHelpButton();
    }

    startTour() {
        // Ocultar pantalla de bienvenida si está activa
        this.skipWelcome();

        this.isActive = true;
        this.currentStep = 0;
        this.showStep(this.currentStep);

        // Activar overlay
        document.getElementById('onboarding-overlay').classList.add('active');
    }

    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) return;

        const step = this.steps[stepIndex];
        const target = document.querySelector(step.target);

        if (!target) {
            console.warn(`Target not found: ${step.target}`);
            this.nextStep();
            return;
        }

        // Actualizar contenido del tooltip
        document.getElementById('onboarding-title').textContent = step.title;
        document.getElementById('onboarding-content').innerHTML = step.content;
        document.querySelector('.onboarding-tooltip-icon').textContent = step.icon;
        document.getElementById('onboarding-progress').textContent = `${stepIndex + 1}/${this.steps.length}`;

        // Mostrar/ocultar botón anterior
        const btnPrev = document.getElementById('btn-prev');
        if (stepIndex === 0) {
            btnPrev.style.display = 'none';
        } else {
            btnPrev.style.display = 'block';
        }

        // Cambiar texto del botón siguiente en el último paso
        const btnNext = document.getElementById('btn-next');
        if (stepIndex === this.steps.length - 1) {
            btnNext.textContent = '¡Empezar! 🎉';
        } else {
            btnNext.textContent = 'Siguiente →';
        }

        // Highlight del elemento
        this.highlightElement(target);

        // Posicionar tooltip
        this.positionTooltip(target, step.position);

        // Activar tooltip
        document.getElementById('onboarding-tooltip').classList.add('active');
    }

    highlightElement(element) {
        // Remover highlights anteriores
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });

        // Agregar highlight al nuevo elemento
        element.classList.add('onboarding-highlight');

        // Scroll al elemento si es necesario
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    positionTooltip(target, position) {
        const tooltip = document.getElementById('onboarding-tooltip');
        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let top, left;

        switch (position) {
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left - tooltipRect.width - 20;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + 20;
                break;
            case 'top':
                top = rect.top - tooltipRect.height - 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
            default:
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
        }

        // Asegurar que el tooltip no se salga de la pantalla
        top = Math.max(20, Math.min(top, window.innerHeight - tooltipRect.height - 20));
        left = Math.max(20, Math.min(left, window.innerWidth - tooltipRect.width - 20));

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }

    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.showStep(this.currentStep);
        } else {
            // Último paso - finalizar tour
            this.endTour();
        }
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.showStep(this.currentStep);
        }
    }

    skipTour() {
        this.endTour();
    }

    endTour() {
        this.isActive = false;

        // Desactivar overlay y tooltip
        document.getElementById('onboarding-overlay').classList.remove('active');
        document.getElementById('onboarding-tooltip').classList.remove('active');

        // Remover highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });

        // Marcar como visto
        localStorage.setItem('hasSeenOnboardingTour', 'true');

        // Mostrar mensaje de éxito
        if (this.currentStep === this.steps.length - 1) {
            // Completó el tour
            setTimeout(() => {
                alert('¡Perfecto! 🎉\n\nYa estás listo para usar Swiftly.\n\nPrueba el chatbot haciendo clic en el botón 💬');
            }, 500);
        }
    }
}

// Inicializar el tour cuando el DOM esté listo
let onboarding;
document.addEventListener('DOMContentLoaded', () => {
    onboarding = new OnboardingTour();
});
