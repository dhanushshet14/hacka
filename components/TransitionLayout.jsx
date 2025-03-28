import React from 'react';
import { motion } from 'framer-motion';
import { animationVariants } from '@/lib/utils';

/**
 * TransitionLayout component for page transitions
 * @param {ReactNode} children - Child components to render
 * @param {string} variant - Animation variant to use
 * @param {number} duration - Animation duration in seconds
 */
const TransitionLayout = ({ 
  children, 
  variant = 'fadeIn',
  duration = 0.3
}) => {
  // Get animation variants from utils or use fadeIn as default
  const variants = animationVariants[variant] || animationVariants.fadeIn;
  
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="hidden"
      variants={variants}
      transition={{ duration }}
    >
      {children}
    </motion.div>
  );
};

export default TransitionLayout; 