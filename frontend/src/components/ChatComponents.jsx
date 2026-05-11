import { motion } from "framer-motion";

export function ChatBubble({ role, content }) {
  return (
    <div className={`chat-bubble-wrap ${role}`}>
      <div className={`chat-avatar ${role}`}>{role === "user" ? "You" : "HC"}</div>
      <div className={`chat-bubble ${role}`}>{content}</div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="chat-bubble typing">
      <div className="typing-dots" aria-label="Typing">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}

export function ChatEmptyState({ icon: Icon, title, subtitle }) {
  return (
    <motion.div
      className="chat-empty-state"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="chat-empty-icon">
        <Icon size={28} strokeWidth={1.5} />
      </div>
      <h2 className="chat-empty-title">{title}</h2>
      <p className="chat-empty-subtitle">{subtitle}</p>
    </motion.div>
  );
}
