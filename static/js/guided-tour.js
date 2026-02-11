/**
 * LinguaVoice Guided Tour System
 * Elegant onboarding tour for new users
 */

class GuidedTour {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
        this.isActive = false;
    }

    /**
     * Initialize the tour with steps
     * @param {Array} steps - Array of tour step objects
     */
    init(steps) {
        this.steps = steps;
        this.createOverlay();
        this.createSpotlight();
        this.createTooltip();
    }

    /**
     * Create the dark overlay
     */
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.id = 'tour-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(47, 47, 47, 0.85);
            z-index: 9998;
            opacity: 0;
            transition: opacity 0.4s ease;
            backdrop-filter: blur(3px);
        `;
        document.body.appendChild(this.overlay);
    }

    /**
     * Create the spotlight circle
     */
    createSpotlight() {
        this.spotlight = document.createElement('div');
        this.spotlight.id = 'tour-spotlight';
        this.spotlight.style.cssText = `
            position: fixed;
            border-radius: 12px;
            box-shadow: 0 0 0 9999px rgba(47, 47, 47, 0.85), 0 0 30px rgba(139, 69, 19, 0.5);
            z-index: 9999;
            pointer-events: none;
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        document.body.appendChild(this.spotlight);
    }

    /**
     * Create the tooltip/info box
     */
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.id = 'tour-tooltip';
        this.tooltip.style.cssText = `
            position: fixed;
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 380px;
            z-index: 10000;
            box-shadow: 0 20px 25px -5px rgba(61, 90, 76, 0.25), 0 10px 10px -5px rgba(61, 90, 76, 0.12);
            border: 2px solid #8B4513;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        `;
        
        this.tooltip.innerHTML = `
            <div class="tour-tooltip-content">
                <h3 style="font-family: 'Merriweather', serif; color: #3d5a4c; margin: 0 0 12px 0; font-size: 1.5rem;"></h3>
                <p style="color: #4A4A4A; line-height: 1.7; margin: 0 0 20px 0; font-size: 1rem;"></p>
                <div class="tour-tooltip-footer" style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="tour-progress" style="font-size: 0.875rem; color: #4A4A4A; font-weight: 600;">
                        <span class="current-step">1</span> / <span class="total-steps">1</span>
                    </div>
                    <div class="tour-buttons" style="display: flex; gap: 12px;">
                        <button class="tour-btn-skip" style="background: transparent; border: 2px solid #8B4513; color: #8B4513; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s;">
                            Skip Tour
                        </button>
                        <button class="tour-btn-next" style="background: #8B4513; border: none; color: white; padding: 8px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.3s;">
                            Next
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.tooltip);
        
        // Add event listeners
        this.tooltip.querySelector('.tour-btn-next').addEventListener('click', () => this.next());
        this.tooltip.querySelector('.tour-btn-skip').addEventListener('click', () => this.end());

        // Add hover effects
        const skipBtn = this.tooltip.querySelector('.tour-btn-skip');
        const nextBtn = this.tooltip.querySelector('.tour-btn-next');
        
        skipBtn.addEventListener('mouseenter', () => {
            skipBtn.style.background = '#F4F1E8';
        });
        skipBtn.addEventListener('mouseleave', () => {
            skipBtn.style.background = 'transparent';
        });
        
        nextBtn.addEventListener('mouseenter', () => {
            nextBtn.style.background = '#A0522D';
            nextBtn.style.transform = 'translateY(-2px)';
        });
        nextBtn.addEventListener('mouseleave', () => {
            nextBtn.style.background = '#8B4513';
            nextBtn.style.transform = 'translateY(0)';
        });
    }

    /**
     * Start the tour
     */
    start() {
        if (this.steps.length === 0) {
            console.warn('No tour steps defined');
            return;
        }

        this.isActive = true;
        this.currentStep = 0;
        
        // Fade in overlay
        setTimeout(() => {
            this.overlay.style.opacity = '1';
        }, 10);
        
        // Show first step
        setTimeout(() => {
            this.showStep(this.currentStep);
        }, 400);
    }

    /**
     * Show a specific step
     */
    showStep(stepIndex) {
        if (stepIndex >= this.steps.length) {
            this.end();
            return;
        }

        const step = this.steps[stepIndex];
        const element = document.querySelector(step.element);

        if (!element) {
            console.warn(`Element not found: ${step.element}`);
            this.next();
            return;
        }

        // Scroll element into view
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });

        setTimeout(() => {
            // Position spotlight
            const rect = element.getBoundingClientRect();
            const padding = step.padding || 8;
            
            this.spotlight.style.top = `${rect.top - padding}px`;
            this.spotlight.style.left = `${rect.left - padding}px`;
            this.spotlight.style.width = `${rect.width + (padding * 2)}px`;
            this.spotlight.style.height = `${rect.height + (padding * 2)}px`;

            // Update tooltip content
            this.tooltip.querySelector('h3').textContent = step.title;
            this.tooltip.querySelector('p').textContent = step.description;
            this.tooltip.querySelector('.current-step').textContent = stepIndex + 1;
            this.tooltip.querySelector('.total-steps').textContent = this.steps.length;

            // Update button text for last step
            const nextBtn = this.tooltip.querySelector('.tour-btn-next');
            nextBtn.textContent = stepIndex === this.steps.length - 1 ? 'Finish' : 'Next';

            // Position tooltip
            this.positionTooltip(rect, step.tooltipPosition || 'bottom');

            // Show tooltip
            setTimeout(() => {
                this.tooltip.style.opacity = '1';
                this.tooltip.style.transform = 'translateY(0)';
            }, 100);
        }, 500);
    }

    /**
     * Position the tooltip relative to the element
     */
    positionTooltip(rect, position) {
        const tooltipWidth = 380;
        const spacing = 20;

        // Reset transform
        this.tooltip.style.transform = 'translateY(0)';

        switch (position) {
            case 'top':
                this.tooltip.style.top = `${rect.top - this.tooltip.offsetHeight - spacing}px`;
                this.tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltipWidth / 2)}px`;
                this.tooltip.style.transform = 'translateY(20px)';
                break;
            case 'bottom':
                this.tooltip.style.top = `${rect.bottom + spacing}px`;
                this.tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltipWidth / 2)}px`;
                this.tooltip.style.transform = 'translateY(-20px)';
                break;
            case 'left':
                this.tooltip.style.top = `${rect.top + (rect.height / 2) - (this.tooltip.offsetHeight / 2)}px`;
                this.tooltip.style.left = `${rect.left - tooltipWidth - spacing}px`;
                break;
            case 'right':
                this.tooltip.style.top = `${rect.top + (rect.height / 2) - (this.tooltip.offsetHeight / 2)}px`;
                this.tooltip.style.left = `${rect.right + spacing}px`;
                break;
            default:
                this.tooltip.style.top = `${rect.bottom + spacing}px`;
                this.tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltipWidth / 2)}px`;
        }

        // Ensure tooltip stays within viewport
        const tooltipRect = this.tooltip.getBoundingClientRect();
        if (tooltipRect.right > window.innerWidth) {
            this.tooltip.style.left = `${window.innerWidth - tooltipWidth - 20}px`;
        }
        if (tooltipRect.left < 0) {
            this.tooltip.style.left = '20px';
        }
    }

    /**
     * Go to next step
     */
    next() {
        // Hide current tooltip
        this.tooltip.style.opacity = '0';
        this.tooltip.style.transform = 'translateY(20px)';

        setTimeout(() => {
            this.currentStep++;
            if (this.currentStep >= this.steps.length) {
                this.end();
            } else {
                this.showStep(this.currentStep);
            }
        }, 300);
    }

    /**
     * End the tour
     */
    end() {
        this.isActive = false;
        
        // Fade out
        this.tooltip.style.opacity = '0';
        this.tooltip.style.transform = 'translateY(20px)';
        this.overlay.style.opacity = '0';

        setTimeout(() => {
            this.overlay.remove();
            this.spotlight.remove();
            this.tooltip.remove();
            
            // Store that user has completed the tour
            localStorage.setItem('linguavoice_tour_completed', 'true');
        }, 400);
    }

    /**
     * Check if user has completed the tour
     */
    static hasCompletedTour() {
        return localStorage.getItem('linguavoice_tour_completed') === 'true';
    }

    /**
     * Reset tour completion status
     */
    static resetTour() {
        localStorage.removeItem('linguavoice_tour_completed');
    }
}

// Export for use in templates
window.GuidedTour = GuidedTour;
