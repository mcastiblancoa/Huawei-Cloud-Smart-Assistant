import { motion } from "framer-motion";
import { TbArrowDown } from "react-icons/tb";

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
      <TbArrowDown size={16} />
    </motion.button>
  );
}
