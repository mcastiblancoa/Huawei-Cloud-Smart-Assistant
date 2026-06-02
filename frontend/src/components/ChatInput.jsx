import { useEffect, useRef, useState } from "react";
import { TbSend, TbPaperclip } from "react-icons/tb";
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
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    const nextHeight = Math.min(el.scrollHeight, 180);
    el.style.height = `${nextHeight}px`;
  }, [value]);

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
        setIsDeleting(false);
        timeout = setTimeout(() => {}, 500);
      }
    }

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, showTypingPlaceholder, typingText, value]);

  const displayPlaceholder = value.trim() === "" && showTypingPlaceholder ? displayText : placeholder;

  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <motion.div
        className={`chat-input-wrapper ${isFocused ? "focused" : ""}`}
        animate={{
          boxShadow: isFocused
            ? "0 0 0 2px rgba(199, 0, 11, 0.12), 0 4px 16px rgba(0,0,0,0.08)"
            : "0 2px 8px rgba(0,0,0,0.04)",
        }}
        transition={{ duration: 0.2 }}
      >
        <div className="chat-input-container">
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={value}
            onChange={onChange}
            onKeyDown={onKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={displayPlaceholder}
            rows={1}
            spellCheck="true"
            aria-label={language === "es" ? "Mensaje" : "Message"}
          />
          {showTypingPlaceholder && value.trim() === "" && displayText && (
            <div className="chat-input-typing-indicator">
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                ▊
              </motion.span>
            </div>
          )}
        </div>
        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button
            type="submit"
            size="icon"
            variant="primary"
            className="chat-send-button"
            disabled={isLoading || !value.trim()}
            aria-label={language === "es" ? "Enviar mensaje" : "Send message"}
          >
            <TbSend size={16} />
          </Button>
        </motion.div>
      </motion.div>
      <p className="chat-disclaimer">
        {language === "es"
          ? "Huawei Cloud Smart Assistant puede cometer errores. Verifica la información importante."
          : "Huawei Cloud Smart Assistant can make mistakes. Check important info."}
      </p>
    </form>
  );
}
