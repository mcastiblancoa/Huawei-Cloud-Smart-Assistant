import { useEffect, useRef } from "react";
import { Mic, Send } from "lucide-react";
import { Button } from "./ui/Button";

export function ChatInput({
  value,
  onChange,
  onKeyDown,
  onSubmit,
  isLoading,
  language,
  placeholder,
}) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "0px";
    const nextHeight = Math.min(el.scrollHeight, 160);
    el.style.height = `${nextHeight}px`;
  }, [value]);

  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <div className="chat-input-wrapper">
        <button
          type="button"
          className="chat-action-btn"
          aria-label={language === "es" ? "Entrada por voz" : "Voice input"}
          title={language === "es" ? "Entrada por voz" : "Voice input"}
          disabled
        >
          <Mic size={16} strokeWidth={1.5} />
        </button>
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={1}
        />
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
