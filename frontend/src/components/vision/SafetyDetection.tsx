import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WebcamFeed } from "./WebcamFeed";
import { PPEStatusGrid, PersonComplianceList } from "./PPEBadge";
import { ComplianceChart } from "./ComplianceChart";
import { TbShieldCheck, TbShieldExclamation, TbRefresh, TbWifiOff, TbUsers, TbCircleCheck, TbCircleX } from "react-icons/tb";
import { analyzeSafety } from "../../services/api";

const DEBOUNCE_MS = 500;
const MAX_CONSECUTIVE_ERRORS = 3;
const BACKOFF_MS = 5000;

export function SafetyDetection({ language, theme }) {
  const [isActive, setIsActive] = useState(true);
  const [totalPersons, setTotalPersons] = useState(0);
  const [compliantPersons, setCompliantPersons] = useState(0);
  const [complianceRate, setComplianceRate] = useState(null);
  const [persons, setPersons] = useState([]);
  const [ppeSummary, setPpeSummary] = useState(null);
  const [allDetections, setAllDetections] = useState([]);
  const [latencyMs, setLatencyMs] = useState(null);
  const [backendDown, setBackendDown] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [modelSource, setModelSource] = useState(null);
  const [isCocoFallback, setIsCocoFallback] = useState(false);

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
      const result = await analyzeSafety(blob, controller.signal);

      if (controller.signal.aborted) return;

      consecutiveErrorsRef.current = 0;
      setBackendDown(false);

      if (result.status === "success") {
        hasResultRef.current = true;
        setStatusMessage(null);
        setTotalPersons(result.total_persons);
        setCompliantPersons(result.compliant_persons);
        setComplianceRate(result.compliance_rate);
        setPersons(result.persons || []);
        setPpeSummary(result.ppe_summary || {});
        setAllDetections(result.all_detections || []);
        setLatencyMs(result.latency_ms);
        setModelSource(result.model_source || null);
        setIsCocoFallback(result.is_coco_fallback || false);
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
    setTotalPersons(0);
    setCompliantPersons(0);
    setComplianceRate(null);
    setPersons([]);
    setPpeSummary(null);
    setAllDetections([]);
    setLatencyMs(null);
  }, []);

  const hasResult = hasResultRef.current && complianceRate != null;
  const isEs = language === "es";

  return (
    <div className="safety-layout">
      <div className="safety-video-section">
        <WebcamFeed
          onFrame={handleFrame}
          isActive={isActive}
          language={language}
        />
      </div>

      <div className="safety-results-section">
        {backendDown && (
          <motion.div
            className="backend-down-notice"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <TbWifiOff size={16} />
            <span>
              {isEs ? "Backend no disponible. Reintentando en 5s..." : "Backend unavailable. Retrying in 5s..."}
            </span>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {statusMessage && !backendDown && !hasResult && (
            <motion.div
              className="safety-status-card"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              key={statusMessage}
            >
              <TbShieldExclamation size={18} className="safety-status-icon" />
              <span>
                {statusMessage === "analyzing" && (isEs ? "Analizando..." : "Analyzing...")}
                {statusMessage === "error" && (isEs ? "Error de procesamiento" : "Processing error")}
                {statusMessage === "disconnected" && (isEs ? "Cámara desconectada" : "Camera disconnected")}
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {hasResult && (
          <div className="safety-results-grid">
            <div className="safety-results-header">
              <TbShieldCheck size={16} className="safety-results-icon" />
              <span className="safety-results-title">
                {isEs ? "Análisis de seguridad" : "Safety analysis"}
              </span>
              {latencyMs != null && (
                <span className="safety-latency">{latencyMs} ms</span>
              )}
            </div>

            {isCocoFallback && (
              <div className="safety-fallback-notice">
                <TbShieldExclamation size={14} />
                <span>
                  {isEs
                    ? "Modo heurístico: detección por color (modelo PPE no disponible). Para mejor precisión, ejecute: python download_ppe_model.py"
                    : "Heuristic mode: color-based detection (PPE model not available). For better accuracy, run: python download_ppe_model.py"}
                </span>
              </div>
            )}

            <div className="safety-kpi-row">
              <div className="safety-kpi-card">
                <TbUsers size={18} className="safety-kpi-icon" />
                <div className="safety-kpi-content">
                  <span className="safety-kpi-value">{totalPersons}</span>
                  <span className="safety-kpi-label">{isEs ? "Personas" : "Persons"}</span>
                </div>
              </div>
              <div className="safety-kpi-card">
                <TbCircleCheck size={18} className="safety-kpi-icon safety-kpi-icon-ok" />
                <div className="safety-kpi-content">
                  <span className="safety-kpi-value">{compliantPersons}</span>
                  <span className="safety-kpi-label">{isEs ? "Cumplen" : "Compliant"}</span>
                </div>
              </div>
              <div className="safety-kpi-card">
                <TbCircleX size={18} className="safety-kpi-icon safety-kpi-icon-fail" />
                <div className="safety-kpi-content">
                  <span className="safety-kpi-value">{totalPersons - compliantPersons}</span>
                  <span className="safety-kpi-label">{isEs ? "No cumplen" : "Non-compliant"}</span>
                </div>
              </div>
              <div className={`safety-kpi-card safety-compliance-rate ${complianceRate >= 80 ? "rate-ok" : complianceRate >= 50 ? "rate-warn" : "rate-fail"}`}>
                <span className="safety-rate-value">{complianceRate.toFixed(0)}%</span>
                <span className="safety-rate-label">{isEs ? "Cumplimiento" : "Compliance"}</span>
              </div>
            </div>

            <PPEStatusGrid ppeSummary={ppeSummary} persons={persons} language={language} />

            {persons.length > 0 && (
              <PersonComplianceList persons={persons} language={language} />
            )}

            <ComplianceChart ppeSummary={ppeSummary} language={language} />

            <button className="safety-reset-btn" onClick={handleReset} type="button">
              <TbRefresh size={12} />
              {isEs ? "Reiniciar" : "Reset"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
