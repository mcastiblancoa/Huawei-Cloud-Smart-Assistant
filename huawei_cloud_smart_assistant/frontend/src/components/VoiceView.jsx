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
  return (
    <section className="view-shell">
      <div className="header">
        <h1 className="app-title">{t.appTitle}</h1>
        <p className="app-subtitle">{t.appSubtitle}</p>
      </div>

      <div className="interactive-zone">
        <button
          className={`mic-button ${status === "recording" ? "recording" : ""}`}
          onClick={toggleRecording}
          disabled={status === "processing"}
          title={status === "processing" ? t.transcribing : statusLabel}
        >
          <svg className="mic-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v12a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
        </button>

        <div className="recording-language-selector">
          <p className="language-selector-label">{t.recordingLanguage}</p>
          <div className="language-buttons">
            <button
              className={`language-btn ${recordingLanguage === "en" ? "active" : ""}`}
              onClick={() => setRecordingLanguage("en")}
              title={t.english}
            >
              {t.english}
            </button>
            <button
              className={`language-btn ${recordingLanguage === "es" ? "active" : ""}`}
              onClick={() => setRecordingLanguage("es")}
              title={t.spanish}
            >
              {t.spanish}
            </button>
          </div>
        </div>

        <div className="status-indicator">
          <span className={`status-dot ${status}`}></span>
          <p className={`status-text ${status}`}>{statusLabel}</p>
        </div>

        {waveformData.length > 0 && (
          <div className="waveform-container">
            <div className="waveform">
              {waveformData.map((value, idx) => (
                <div key={idx} className="waveform-bar" style={{ height: `${value * 100}%` }}></div>
              ))}
            </div>
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="error-box">
          <p className="error-text">{errorMessage}</p>
        </div>
      )}

      {transcription && (
        <div className="transcription-panel">
          <h2 className="result-title">{t.transcription}</h2>
          <p className="result-text">{transcription}</p>
          {audioUrl && (
            <div className="audio-player-wrapper">
              <audio controls className="audio-player" src={audioUrl}>
                <track kind="captions" />
              </audio>
            </div>
          )}
        </div>
      )}

      {intentClassification?.should_call_rms && (
        <div className="dashboard-wrapper">
          <ResourceDashboard
            intentClassification={intentClassification}
            resourcesResponse={resourcesResponse}
            theme={theme}
            language={language}
          />
        </div>
      )}

      {intentClassification?.should_call_bss && (
        <div className="dashboard-wrapper">
          <BillingDashboard
            intentClassification={intentClassification}
            billingResponse={billingResponse}
            theme={theme}
            language={language}
          />
        </div>
      )}

      {!transcription && status !== "idle" && status !== "recording" && !errorMessage && (
        <p className="helper-text">{t.yourTranscriptionWillAppear}</p>
      )}
    </section>
  );
}