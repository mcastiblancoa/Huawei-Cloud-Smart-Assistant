import { motion } from "framer-motion";
import { ArrowDown } from "lucide-react";

export function ScrollToBottom({ onClick }) {
  return (
    <motion.button
      type="button"
      className="scroll-to-bottom-btn"
      onClick={onClick}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.95 }}
      aria-label="Scroll to bottom"
    >
      <ArrowDown size={16} strokeWidth={1.5} />
    </motion.button>
  );
}
