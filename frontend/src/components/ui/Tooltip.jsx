import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

export function Tooltip({ children, content, side = "top", delay = 0.3 }) {
  const [isVisible, setIsVisible] = useState(false);

  const positionClasses = {
    top: "bottom-full mb-2",
    bottom: "top-full mt-2",
    left: "right-full mr-2",
    right: "left-full ml-2",
  };

  const arrowClasses = {
    top: "top-full left-1/2 transform -translate-x-1/2 border-t-2 border-t-surface border-l-2 border-l-transparent border-r-2 border-r-transparent",
    bottom: "bottom-full left-1/2 transform -translate-x-1/2 border-b-2 border-b-surface border-l-2 border-l-transparent border-r-2 border-r-transparent",
    left: "left-full top-1/2 transform -translate-y-1/2 border-l-2 border-l-surface border-t-2 border-t-transparent border-b-2 border-b-transparent",
    right: "right-full top-1/2 transform -translate-y-1/2 border-r-2 border-r-surface border-t-2 border-t-transparent border-b-2 border-b-transparent",
  };

  return (
    <div className="relative inline-block" onMouseEnter={() => setIsVisible(true)} onMouseLeave={() => setIsVisible(false)}>
      {children}
      <AnimatePresence>
        {isVisible && (
          <motion.div
            className={`absolute ${positionClasses[side]} z-50 whitespace-nowrap pointer-events-none`}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15, delay }}
          >
            <div className="px-3 py-2 bg-surface border border-border-light rounded-lg shadow-lg text-text-primary text-xs font-medium">
              {content}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
