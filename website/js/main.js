// Mobile navigation toggle
const navToggle = document.getElementById('navToggle');
const navMenu = document.querySelector('.nav-menu');

if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
    });
}

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
            // Close mobile menu if open
            if (navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
            }
        }
    });
});

// Add scroll effect to navbar
let lastScroll = 0;
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll <= 0) {
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.3)';
    } else {
        navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.5)';
    }
    
    lastScroll = currentScroll;
});

// Intersection Observer for fade-in animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe all sections for animations
document.querySelectorAll('.section').forEach(section => {
    section.style.opacity = '0';
    section.style.transform = 'translateY(30px)';
    section.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(section);
});

// Copy contract address to clipboard (when addresses are added)
document.querySelectorAll('.contract-address code').forEach(code => {
    code.style.cursor = 'pointer';
    code.addEventListener('click', function() {
        const text = this.textContent;
        if (text !== 'Coming soon...') {
            // Check if clipboard API is available
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).then(() => {
                    // Show copied feedback
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy:', err);
                });
            } else {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                try {
                    document.execCommand('copy');
                    const originalText = this.textContent;
                    this.textContent = 'Copied!';
                    setTimeout(() => {
                        this.textContent = originalText;
                    }, 2000);
                } catch (err) {
                    console.error('Fallback copy failed:', err);
                }
                document.body.removeChild(textarea);
            }
        }
    });
});

// Add particles effect to hero section (optional enhancement)
function createParticle() {
    const hero = document.querySelector('.hero');
    if (!hero) return;
    
    const particle = document.createElement('div');
    particle.className = 'particle';
    
    const randomX = Math.random() * 100;
    const randomDuration = 5 + Math.random() * 10;
    const randomDelay = Math.random() * 2;
    const randomEndX = Math.random() * 100 - 50;
    
    particle.style.cssText = `
        position: absolute;
        width: 5px;
        height: 5px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        pointer-events: none;
        left: ${randomX}%;
        top: 100%;
        animation: float-particle-${Date.now()} ${randomDuration}s linear ${randomDelay}s forwards;
    `;
    
    // Create unique animation for this particle
    const styleId = `particle-anim-${Date.now()}`;
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
        @keyframes float-particle-${Date.now()} {
            0% {
                transform: translateY(0) translateX(0);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(-100vh) translateX(${randomEndX}px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    hero.appendChild(particle);
    
    // Remove particle and style after animation
    setTimeout(() => {
        particle.remove();
        document.getElementById(styleId)?.remove();
    }, (randomDuration + randomDelay) * 1000 + 1000);
}

// Create particles periodically
setInterval(createParticle, 500);

// Console easter egg
console.log('%c🚀 MEMECOIN 🚀', 'color: #667eea; font-size: 24px; font-weight: bold;');
console.log('%cTo the moon! 🌙', 'color: #fd79a8; font-size: 16px;');
console.log('%cInterested in contributing? Check out our GitHub!', 'color: #00b894; font-size: 12px;');
