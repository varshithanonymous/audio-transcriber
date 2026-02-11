/**
 * SERP HAWK - THE LIVING MASCOT
 * A fully animated, interactive character that brings the app to life
 */

class SerpHawkMascot {
    constructor(selector) {
        this.mascot = document.querySelector(selector);
        if (!this.mascot) {
            console.warn("Serp Hawk mascot element not found");
            return;
        }
        
        this.container = this.mascot.parentElement;
        this.currentMood = 'idle';
        this.isAnimating = false;
        this.behaviors = ['fly', 'celebrate', 'peek', 'sleep', 'wake', 'dance'];
        
        this.init();
    }

    init() {
        console.log("🦅 SERP HAWK IS ALIVE!");
        
        // Add speech bubble element
        this.addSpeechBubble();
        
        // Make mascot clickable
        this.mascot.style.cursor = 'pointer';
        this.mascot.addEventListener('click', () => this.onClick());
        
        // Mouse tracking with smoothing
        document.addEventListener('mousemove', (e) => this.trackMouse(e));
        
        // Random autonomous behaviors
        this.startAutonomousBehavior();
        
        // React to user inputs
        this.setupInputReactions();
        
        // Welcome animation
        setTimeout(() => this.playAnimation('wake'), 500);
    }

    addSpeechBubble() {
        if (!document.querySelector('.hawk-speech')) {
            const bubble = document.createElement('div');
            bubble.className = 'hawk-speech';
            bubble.style.cssText = `
                position: absolute;
                top: -70px;
                left: 50%;
                transform: translateX(-50%) scale(0);
                background: white;
                padding: 12px 18px;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                font-weight: 600;
                color: #0F172A;
                white-space: nowrap;
                opacity: 0;
                transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                pointer-events: none;
                z-index: 1000;
            `;
            this.container.style.position = 'relative';
            this.container.appendChild(bubble);
            this.speechBubble = bubble;
        }
    }

    speak(text, duration = 3000) {
        if (!this.speechBubble) return;
        
        this.speechBubble.textContent = text;
        this.speechBubble.style.opacity = '1';
        this.speechBubble.style.transform = 'translateX(-50%) scale(1)';
        
        // Animate mascot while speaking
        this.mascot.style.animation = 'hawkTalk 0.3s ease-in-out infinite';
        
        setTimeout(() => {
            this.speechBubble.style.opacity = '0';
            this.speechBubble.style.transform = 'translateX(-50%) scale(0)';
            this.mascot.style.animation = '';
        }, duration);
    }

    trackMouse(e) {
        if (this.isAnimating) return;
        
        const rect = this.mascot.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const deltaX = e.clientX - centerX;
        const deltaY = e.clientY - centerY;
        
        // Smoother, more natural tracking
        const rotateY = Math.min(Math.max(deltaX / 20, -25), 25);
        const rotateX = Math.min(Math.max(-deltaY / 20, -20), 20);
        
        this.mascot.style.transform = `
            perspective(800px)
            rotateY(${rotateY}deg)
            rotateX(${rotateX}deg)
            scale(1)
        `;
    }

    playAnimation(animationType) {
        if (this.isAnimating) return;
        
        this.isAnimating = true;
        this.mascot.classList.remove('idle', 'fly', 'celebrate', 'peek', 'sleep', 'wake', 'dance');
        this.mascot.classList.add(animationType);
        
        const messages = {
            fly: ["I can fly! 🦅", "Wheee!", "Up up and away!"],
            celebrate: ["YES! 🎉", "Amazing work!", "You're crushing it!"],
            peek: ["Psst... keep going! 👀", "I'm watching..."],
            sleep: ["Zzz... 💤", "Time for a nap"],
            wake: ["Good morning! ☀️", "Let's learn!", "Ready to go!"],
            dance: ["Let's dance! 💃", "Feeling the rhythm!"],
            think: ["Hmm... 🤔", "Interesting..."]
        };
        
        if (messages[animationType]) {
            const msg = messages[animationType][Math.floor(Math.random() * messages[animationType].length)];
            this.speak(msg);
        }
        
        setTimeout(() => {
            this.isAnimating = false;
            this.mascot.classList.remove(animationType);
            this.mascot.classList.add('idle');
        }, 3000);
    }

    onClick() {
        const reactions = ['celebrate', 'dance', 'fly', 'peek'];
        const random = reactions[Math.floor(Math.random() * reactions.length)];
        this.playAnimation(random);
    }

    startAutonomousBehavior() {
        // Random autonomous actions every 8-15 seconds
        setInterval(() => {
            if (!this.isAnimating && Math.random() > 0.6) {
                const behavior = this.behaviors[Math.floor(Math.random() * this.behaviors.length)];
                this.playAnimation(behavior);
            }
        }, 10000);
        
        // Occasional random speech
        setInterval(() => {
            if (!this.isAnimating && Math.random() > 0.7) {
                const randomMessages = [
                    "Keep up the great work! 💪",
                    "You're doing amazing!",
                    "Practice makes perfect!",
                    "I believe in you! ✨",
                    "Let's reach that goal!",
                    "You've got this! 🎯"
                ];
                this.speak(randomMessages[Math.floor(Math.random() * randomMessages.length)]);
            }
        }, 15000);
    }

    setupInputReactions() {
        // React to form inputs
        document.querySelectorAll('input, textarea').forEach(input => {
            input.addEventListener('focus', () => {
                if (!this.isAnimating) {
                    this.speak("I'm listening! 👂");
                    this.mascot.style.filter = 'brightness(1.1)';
                }
            });
            
            input.addEventListener('blur', () => {
                this.mascot.style.filter = 'brightness(1)';
            });
            
            // Celebrate when user types
            let typingTimeout;
            input.addEventListener('input', () => {
                clearTimeout(typingTimeout);
                // Subtle bob while typing
                this.mascot.style.animation = 'hawkBob 0.5s ease';
                
                typingTimeout = setTimeout(() => {
                    this.mascot.style.animation = '';
                }, 500);
            });
        });
        
        // React to button clicks
        document.querySelectorAll('button, .btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (!this.isAnimating && Math.random() > 0.5) {
                    this.playAnimation('celebrate');
                }
            });
        });
    }

    // Call this when user achieves something
    celebrate() {
        this.playAnimation('celebrate');
    }
    
    // Call when user makes a mistake
    encourage() {
        this.speak("Don't worry! Try again! 💪", 4000);
    }
}

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
    const hawk = new SerpHawkMascot('.hawk-mascot-interactive');
    
    // Make globally accessible
    window.serpHawk = hawk;
});
