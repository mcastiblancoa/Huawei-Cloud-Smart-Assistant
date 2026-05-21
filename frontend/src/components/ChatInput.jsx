import { useEffect, useRef, useState } from "react";
import { Mic, Send } from "lucide-react";
import { Button } from "./ui/Button";
import { motion } from "framer-motion";

export function ChatInput({
  value,
  onChange,
  onKeyDown,
  onSubmit,
  isLoading,
  language,
  placeholder,
  showTypingPlaceholder,
  typingText,
}) {
  const textareaRef = useRef(null);
  const prevTypingTextRef = useRef(typingText);
  const [displayText, setDisplayText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const typingSpeedRef = useRef(60);
  const deletingSpeedRef = useRef(30);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    const nextHeight = Math.min(el.scrollHeight, 160);
    el.style.height = `${nextHeight}px`;
  }, [value]);

  // When typingText changes, trigger deletion of current text
  useEffect(() => {
    if (typingText !== prevTypingTextRef.current && showTypingPlaceholder && value.trim() === "") {
      prevTypingTextRef.current = typingText;
      if (displayText.length > 0) {
        setIsDeleting(true);
      } else {
        setDisplayText("");
        setIsDeleting(false);
      }
    }
  }, [typingText, showTypingPlaceholder, value]);

  // Typing placeholder effect
  useEffect(() => {
    if (!showTypingPlaceholder || !typingText || value.trim() !== "") {
      setDisplayText("");
      return;
    }

    let timeout;
    const targetText = typingText;

    if (!isDeleting) {
      if (displayText.length < targetText.length) {
        timeout = setTimeout(() => {
          setDisplayText(targetText.slice(0, displayText.length + 1));
        }, typingSpeedRef.current);
      } else {
        // Pause at end before deleting
        timeout = setTimeout(() => {
          setIsDeleting(true);
        }, 2000);
      }
    } else {
      if (displayText.length > 0) {
        timeout = setTimeout(() => {
          setDisplayText(displayText.slice(0, -1));
        }, deletingSpeedRef.current);
      } else {
        // Pause before typing next one
        setIsDeleting(false);
        timeout = setTimeout(() => {}, 500);
      }
    }

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, showTypingPlaceholder, typingText, value]);

  const displayPlaceholder = value.trim() === "" && showTypingPlaceholder ? displayText : placeholder;

  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <div className="chat-input-wrapper">
        <div className="chat-input-container">
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={value}
            onChange={onChange}
            onKeyDown={onKeyDown}
            placeholder={displayPlaceholder}
            rows={1}
          />
          {showTypingPlaceholder && value.trim() === "" && displayText && (
            <div className="chat-input-typing-indicator">
              <motion.span
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                ▊
              </motion.span>
            </div>
          )}
        </div>
        <Button
          type="submit"
          size="icon"
          variant="primary"
          className="chat-send-button"
          disabled={isLoading || !value.trim()}
          aria-label={language === "es" ? "Enviar mensaje" : "Send message"}
        >
          <Send size={16} strokeWidth={1.5} />
        </Button>
      </div>
    </form>
  );
}
