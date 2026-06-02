import { motion, AnimatePresence } from "framer-motion";
import { Smile } from "lucide-react";

const EMOTION_CONFIG = {
  happy:    { emoji: "\u{1F600}", color: "#22c55e", labelEs: "Feliz",      labelEn: "Happy" },
  sad:      { emoji: "\u{1F622}", color: "#3b82f6", labelEs: "Triste",     labelEn: "Sad" },
  angry:    { emoji: "\u{1F620}", color: "#ef4444", labelEs: "Enojado",    labelEn: "Angry" },
  fear:     { emoji: "\u{1F628}", color: "#a855f7", labelEs: "Miedo",      labelEn: "Fear" },
  surprise: { emoji: "\u{1F62E}", color: "#f59e0b", labelEs: "Sorpresa",   labelEn: "Surprise" },
  disgust:  { emoji: "\u{1F922}", color: "#84cc16", labelEs: "Asco",       labelEn: "Disgust" },
  neutral:  { emoji: "\u{1F610}", color: "#6b7280", labelEs: "Neutral",    labelEn: "Neutral" },
};

export function EmotionCard({ emotion, confidence, faceIndex, language }) {
  const config = EMOTION_CONFIG[emotion] || EMOTION_CONFIG.neutral;
  const label = language === "es" ? config.labelEs : config.labelEn;

  return (
    <div className="emotion-card" key={`face-${faceIndex}`}>
      <div className="emotion-card-header">
        <motion.span
          className="emotion-emoji"
          key={emotion}
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
        >
          {config.emoji}
        </motion.span>
        <div className="emotion-card-info">
          <span className="emotion-label">{label}</span>
          {faceIndex > 0 && (
            <span className="emotion-face-index">
              {language === "es" ? `Rostro ${faceIndex + 1}` : `Face ${faceIndex + 1}`}
            </span>
          )}
        </div>
      </div>

      <div className="emotion-confidence-row">
        <div className="emotion-confidence-bar-track">
          <motion.div
            className="emotion-confidence-bar-fill"
            animate={{ width: `${Math.min(confidence, 100)}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            style={{ background: config.color }}
          />
        </div>
        <motion.span
          className="emotion-confidence-value"
          animate={{ color: config.color }}
          transition={{ duration: 0.3 }}
        >
          {confidence.toFixed(1)}%
        </motion.span>
      </div>
    </div>
  );
}

export function EmotionStatusCard({ status, language }) {
  const messages = {
    analyzing: { es: "Analizando...", en: "Analyzing..." },
    no_face: { es: "Rostro no detectado", en: "No face detected" },
    error: { es: "Error de procesamiento", en: "Processing error" },
    disconnected: { es: "Cámara desconectada", en: "Camera disconnected" },
  };

  const msg = messages[status];
  if (!msg) return null;

  return (
    <motion.div
      className="emotion-status-card"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      key={status}
    >
      <Smile size={18} strokeWidth={1.5} className="emotion-status-icon" />
      <span className="emotion-status-text">
        {language === "es" ? msg.es : msg.en}
      </span>
      {status === "analyzing" && (
        <motion.span
          className="emotion-status-dots"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity }}
        >
          ...
        </motion.span>
      )}
    </motion.div>
  );
}
