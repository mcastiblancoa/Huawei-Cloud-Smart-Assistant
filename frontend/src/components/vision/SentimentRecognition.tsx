import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WebcamFeed } from "./WebcamFeed";
import { EmotionStatusCard } from "./EmotionCard";
import { EmotionCard } from "./EmotionCard";
import { EmotionChart } from "./EmotionChart";
import { Sparkles, RotateCcw, WifiOff } from "lucide-react";
import { analyzeSentiment } from "../../services/api";

const DEBOUNCE_MS = 500;
const MAX_CONSECUTIVE_ERRORS = 3;
const BACKOFF_MS = 5000;

export function SentimentRecognition({ language, theme }) {
  const [isActive, setIsActive] = useState(true);
  const [dominantEmotion, setDominantEmotion] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [allScores, setAllScores] = useState(null);
  const [faces, setFaces] = useState([]);
  const [faceCount, setFaceCount] = useState(0);
  const [latencyMs, setLatencyMs] = useState(null);
  const [backendDown, setBackendDown] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const lastSentRef = useRef(0);
  const abortRef = useRef(null);
  const consecutiveErrorsRef = useRef(0);
  const backoffTimerRef = useRef(null);
  const hasResultRef = useRef(false);

  const handleFrame = useCallback(async (blob) => {
    if (backendDown) return;

    const now = Date.now();
    if (now - lastSentRef.current < DEBOUNCE_MS) return;
    lastSentRef.current = now;

    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    if (!hasResultRef.current) {
      setStatusMessage("analyzing");
    }

    try {
      const result = await analyzeSentiment(blob, controller.signal);

      if (controller.signal.aborted) return;

      consecutiveErrorsRef.current = 0;
      setBackendDown(false);

      if (result.status === "success" && result.dominant_emotion) {
        hasResultRef.current = true;
        setStatusMessage(null);
        setDominantEmotion(result.dominant_emotion);
        setConfidence(result.confidence);
        setAllScores(result.all_scores);
        setFaces(result.faces || []);
        setFaceCount(result.face_count || 0);
        setLatencyMs(result.latency_ms);
      } else if (result.status === "no_face") {
        if (!hasResultRef.current) {
          setStatusMessage("no_face");
        }
      } else if (result.status === "error") {
        if (!hasResultRef.current) {
          setStatusMessage("error");
        }
      }
    } catch (err) {
      if (err.name === "AbortError") return;

      consecutiveErrorsRef.current += 1;

      if (consecutiveErrorsRef.current >= MAX_CONSECUTIVE_ERRORS) {
        setBackendDown(true);
        setStatusMessage("disconnected");

        if (backoffTimerRef.current) clearTimeout(backoffTimerRef.current);
        backoffTimerRef.current = setTimeout(() => {
          consecutiveErrorsRef.current = 0;
          setBackendDown(false);
          setStatusMessage(null);
        }, BACKOFF_MS);
        return;
      }

      if (!hasResultRef.current) {
        setStatusMessage("error");
      }
    }
  }, [backendDown]);

  const handleReset = useCallback(() => {
    if (backoffTimerRef.current) clearTimeout(backoffTimerRef.current);
    consecutiveErrorsRef.current = 0;
    hasResultRef.current = false;
    setBackendDown(false);
    setStatusMessage(null);
    setDominantEmotion(null);
    setConfidence(null);
    setAllScores(null);
    setFaces([]);
    setFaceCount(0);
    setLatencyMs(null);
  }, []);

  const hasResult = dominantEmotion != null;

  return (
    <div className="sentiment-layout">
      <div className="sentiment-video-section">
        <WebcamFeed
          onFrame={handleFrame}
          isActive={isActive}
          language={language}
        />
      </div>

      <div className="sentiment-results-section">
        {backendDown && (
          <motion.div
            className="backend-down-notice"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <WifiOff size={16} strokeWidth={1.5} />
            <span>
              {language === "es"
                ? "Backend no disponible. Reintentando en 5s..."
                : "Backend unavailable. Retrying in 5s..."}
            </span>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {statusMessage && !backendDown && !hasResult && (
            <EmotionStatusCard
              key={statusMessage}
              status={statusMessage}
              language={language}
            />
          )}
        </AnimatePresence>

        {hasResult && (
          <div className="sentiment-results-grid">
            <div className="sentiment-results-header">
              <Sparkles size={16} strokeWidth={1.5} className="sentiment-results-icon" />
              <span className="sentiment-results-title">
                {language === "es" ? "Resultado del análisis" : "Analysis result"}
              </span>
              {latencyMs != null && (
                <span className="sentiment-latency">{latencyMs} ms</span>
              )}
              {faceCount > 1 && (
                <span className="sentiment-face-count">
                  {faceCount} {language === "es" ? "rostros" : "faces"}
                </span>
              )}
            </div>

            {faces.length > 0 ? (
              faces.map((face) => (
                <EmotionCard
                  key={`face-${face.face_index}`}
                  emotion={face.dominant_emotion}
                  confidence={face.confidence}
                  faceIndex={face.face_index}
                  language={language}
                />
              ))
            ) : (
              <EmotionCard
                emotion={dominantEmotion}
                confidence={confidence}
                faceIndex={0}
                language={language}
              />
            )}

            <EmotionChart
              allScores={allScores || (faces[0]?.all_scores)}
              language={language}
            />

            <button
              className="sentiment-reset-btn"
              onClick={handleReset}
              type="button"
            >
              <RotateCcw size={12} />
              {language === "es" ? "Reiniciar" : "Reset"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
