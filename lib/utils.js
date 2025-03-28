import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

/**
 * Combines class names using clsx and tailwind-merge
 * @param {...string} inputs - Class names to combine
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Detects user's preferred color scheme
 * @returns {string} 'dark' or 'light'
 */
export function getSystemTheme() {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Smoothly scrolls to an element
 * @param {string} elementId - The ID of the element to scroll to
 * @param {Object} options - Scroll options
 */
export function smoothScrollTo(elementId, options = {}) {
  const defaultOptions = {
    behavior: 'smooth',
    offset: 0,
    duration: 500,
  };
  
  const { offset, duration } = { ...defaultOptions, ...options };
  
  if (typeof window === 'undefined') return;
  
  const element = document.getElementById(elementId);
  if (!element) return;
  
  const elementPosition = element.getBoundingClientRect().top + window.scrollY;
  const offsetPosition = elementPosition - offset;
  
  window.scrollTo({
    top: offsetPosition,
    behavior: 'smooth',
  });
}

/**
 * Format date to readable string
 * @param {Date|string} date - Date to format
 * @param {Object} options - Intl.DateTimeFormat options
 */
export function formatDate(date, options = {}) {
  const defaultOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  };
  
  const mergedOptions = { ...defaultOptions, ...options };
  const dateToFormat = typeof date === 'string' ? new Date(date) : date;
  
  return new Intl.DateTimeFormat('en-US', mergedOptions).format(dateToFormat);
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} length - Maximum length
 */
export function truncateText(text, length = 100) {
  if (!text || text.length <= length) return text;
  return `${text.slice(0, length)}...`;
}

/**
 * Create animation variants for framer-motion
 * @param {Object} options - Animation options
 */
export function createAnimationVariants({
  hidden = { opacity: 0 },
  visible = { 
    opacity: 1,
    transition: {
      duration: 0.5
    }
  }
} = {}) {
  return {
    hidden,
    visible
  };
}

/**
 * Animation variants for page transitions
 */
export const animationVariants = {
  fadeIn: createAnimationVariants(),
  slideUp: createAnimationVariants({
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  }),
  slideRight: createAnimationVariants({
    hidden: { opacity: 0, x: -20 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.5 } }
  }),
  scale: createAnimationVariants({
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.5 } }
  }),
  bounceIn: createAnimationVariants({
    hidden: { opacity: 0, scale: 0.8 },
    visible: { 
      opacity: 1, 
      scale: 1, 
      transition: { 
        type: "spring", 
        stiffness: 300, 
        damping: 25 
      } 
    }
  }),
  listItem: createAnimationVariants({
    hidden: { opacity: 0, x: -20 },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: { duration: 0.3 } 
    }
  })
};
