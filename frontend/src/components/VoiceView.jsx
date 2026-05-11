import { motion } from "framer-motion";
import { Mic, MicOff } from "lucide-react";
import { ResourceDashboard } from "../ResourceDashboard";
import { BillingDashboard } from "../BillingDashboard";

export function VoiceView({
  t,
  status,
  statusLabel,
  toggleRecording,
  recordingLanguage,
  setRecordingLanguage,
  waveformData,
  errorMessage,
  transcription,
  audioUrl,
  intentClassification,
  resourcesResponse,
  billingResponse,
  theme,
  language,
}) {
  const isRecording = status === "recording";
  const isProcessing = status === "processing";

  return (
    <motion.section
      className="view-shell"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <motion.div
        className="header"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="app-title">{t.appTitle}</h1>
        <p className="app-subtitle">
          {language === "es" ? (
            <>Graba e interactúa con tus <span className="hw-red-text">servicios de Huawei Cloud</span></>
          ) : (
            <>Record and ask for your <span className="hw-red-text">Huawei Cloud services</span></>
          )}
        </p>
      </motion.div>

      {/* Interactive Zone */}
      <div className="interactive-zone">
        {/* Microphone Button */}
        <motion.button
          className={`mic-button ${isRecording ? "recording" : ""}`}
          onClick={toggleRecording}
          disabled={isProcessing}
          title={isProcessing ? t.transcribing : statusLabel}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          whileHover={{ scale: isProcessing ? 1 : 1.05 }}
          whileTap={{ scale: isProcessing ? 1 : 0.95 }}
        >
          {isRecording ? (
            <MicOff size={48} strokeWidth={1.5} className="mic-icon" />
          ) : (
            <Mic size={48} strokeWidth={1.5} className="mic-icon" />
          )}
        </motion.button>

        {/* Language Selector */}
        <motion.div
          className="recording-language-selector"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <p className="language-selector-label">{t.recordingLanguage}</p>
          <div className="language-buttons">
            {[
              { code: "en", label: t.english },
              { code: "es", label: t.spanish },
            ].map(({ code, label }) => (
              <motion.button
                key={code}
                className={`language-btn ${recordingLanguage === code ? "active" : ""}`}
                onClick={() => setRecordingLanguage(code)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {label}
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Status Indicator */}
        <motion.div
          className="status-indicator"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.3 }}
        >
          <span className={`status-dot ${status}`} />
          <p className={`status-text ${status}`}>{statusLabel}</p>
        </motion.div>

        {/* Waveform */}
        {waveformData.length > 0 && (
          <motion.div
            className="waveform-container"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <div className="waveform">
              {waveformData.map((value, idx) => (
                <motion.div
                  key={idx}
                  className="waveform-bar"
                  style={{ height: `${value * 100}%` }}
                  animate={{ height: `${value * 100}%` }}
                  transition={{ duration: 0.1 }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <motion.div
          className="error-box max-w-2xl mx-auto"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
        >
          <p className="error-text">{errorMessage}</p>
        </motion.div>
      )}

      {/* Transcription Result */}
      {transcription && (
        <motion.div
          className="transcription-panel"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <h2 className="result-title">{t.transcription}</h2>
          <p className="result-text">{transcription}</p>
          {audioUrl && (
            <div className="audio-player-wrapper">
              <audio controls className="audio-player" src={audioUrl}>
                <track kind="captions" />
              </audio>
            </div>
          )}
        </motion.div>
      )}

      {/* Resource Dashboard */}
      {intentClassification?.should_call_rms && (
        <motion.div
          className="w-full"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <ResourceDashboard
            intentClassification={intentClassification}
            resourcesResponse={resourcesResponse}
            theme={theme}
            language={language}
          />
        </motion.div>
      )}

      {/* Billing Dashboard */}
      {intentClassification?.should_call_bss && (
        <motion.div
          className="w-full"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <BillingDashboard
            intentClassification={intentClassification}
            billingResponse={billingResponse}
            theme={theme}
            language={language}
          />
        </motion.div>
      )}

      {/* Helper Text */}
      {!transcription && status !== "idle" && status !== "recording" && !errorMessage && (
        <motion.p
          className="text-center text-sm text-huawei-gray-500 dark:text-huawei-gray-400"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {t.yourTranscriptionWillAppear}
        </motion.p>
      )}
    </motion.section>
  );
}
