import { motion } from "framer-motion";
import { TbMicrophone, TbMicrophoneOff, TbVolume2 } from "react-icons/tb";

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
  agentReply,
  audioUrl,
  theme,
  language,
}) {
  const isRecording = status === "recording";
  const isProcessing = ["processing", "thinking", "generatingAudio"].includes(status);
  const isPlaying = status === "playing";

  const micColorClass = isRecording
    ? "mic-recording"
    : isProcessing
      ? "mic-processing"
      : isPlaying
        ? "mic-playing"
        : "";

  const MicIcon = isPlaying ? TbVolume2 : (isRecording ? TbMicrophoneOff : TbMicrophone);

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
          className={`mic-button ${micColorClass}`}
          onClick={toggleRecording}
          disabled={isProcessing}
          title={statusLabel}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
          whileHover={{ scale: isProcessing ? 1 : 1.05 }}
          whileTap={{ scale: isProcessing ? 1 : 0.95 }}
        >
          <MicIcon size={48} className="mic-icon" />
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

      {/* Voice Result Panel */}
      {(transcription || agentReply) && (
        <motion.div
          className="voice-result-panel"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          {/* Transcription subtitle */}
          {transcription && (
            <div className="voice-transcription-subtitle">
              <span className="voice-transcription-label">{t.transcription}</span>
              <p className="voice-transcription-text">{transcription}</p>
            </div>
          )}

          {/* Agent reply - shown as small subtitle, not main chat */}
          {agentReply && (
            <div className="voice-reply-subtitle">
              <span className="voice-reply-label">{t.agentReply}</span>
              <p className="voice-reply-text">{agentReply}</p>
            </div>
          )}

          {/* TTS Audio Player (hidden, auto-plays) */}
          {audioUrl && (
            <audio
              ref={(el) => { if (el && isPlaying) { el.play().catch(() => {}); } }}
              className="hidden"
              src={audioUrl}
            />
          )}
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
