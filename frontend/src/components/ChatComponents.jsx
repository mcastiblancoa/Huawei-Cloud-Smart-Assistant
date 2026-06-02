import { motion } from "framer-motion";
import { User, Sparkles } from "lucide-react";

export function ChatBubble({ role, content }) {
  return (
    <motion.div
      className={`chat-bubble-wrap ${role}`}
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {role === "assistant" && (
        <div className="chat-avatar assistant">
          <Sparkles size={16} strokeWidth={2} />
        </div>
      )}
      <div className={`chat-bubble ${role}`}>{content}</div>
      {role === "user" && (
        <div className="chat-avatar user">
          <User size={16} strokeWidth={2} />
        </div>
      )}
    </motion.div>
  );
}

export function TypingIndicator() {
  return (
    <motion.div
      className="chat-bubble typing"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div className="typing-dots" aria-label="Typing">
        <motion.span
          className="dot"
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity }}
        />
        <motion.span
          className="dot"
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: 0.15 }}
        />
        <motion.span
          className="dot"
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: 0.3 }}
        />
      </div>
    </motion.div>
  );
}

export function ChatEmptyState({ icon: Icon, title, subtitle }) {
  return (
    <motion.div
      className="chat-empty-state"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <motion.div
        className="chat-empty-icon"
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      >
        <Icon size={36} strokeWidth={1.5} />
      </motion.div>
      <motion.h2
        className="chat-empty-title"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.4 }}
      >
        {title}
      </motion.h2>
      <motion.p
        className="chat-empty-subtitle"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.4 }}
      >
        {subtitle}
      </motion.p>
    </motion.div>
  );
}
