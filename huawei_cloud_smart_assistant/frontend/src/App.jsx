import { useMemo, useRef, useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { VoiceView } from "./components/VoiceView";
import { ChatView } from "./components/ChatView";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Translations
const translations = {
  en: {
    appTitle: "Voice Assistant",
    appSubtitle: "Record and ask for your Huawei Cloud services",
    clickToStart: "Click to start recording",
    recording: "Recording...",
    transcribing: "Transcribing...",
    done: "Done",
    errorOccurred: "Error occurred",
    microphoneError: "Microphone access denied. Please allow microphone permission.",
    noTextError: "I can't understand, please record your audio again.",
    transcriptionFailed: "Transcription failed.",
    transcription: "Transcription",
    yourTranscriptionWillAppear: "Your transcription will appear here",
    recordingLanguage: "Recording language",
    english: "English",
    spanish: "Spanish",
    spanishNotAvailable: "Spanish recording not available yet",
    feature1Title: "1. Active Resources",
    feature1Desc: "Smart voice assistant that allows users to manage, query, and understand their active resources on Huawei Cloud. By centralizing information in an interactive visual panel, it significantly simplifies cloud monitoring, avoiding the need to navigate through the console.",
    feature1Example: 'Try: "Show me a summary of my services right now, please"',
    feature2Title: "2. Monthly Billing",
    feature2Desc: "Query and understand your monthly billing on Huawei Cloud using english voice commands. A direct way to track and control expenses via the same interactive interface.",
    feature2Example: 'Try: "How much money I spent on April 2026"',
    chatTitle: "Chat Assistant",
    chatSubtitle: "Interact with your Huawei Cloud services through chat.",
    conversations: "Conversations",
    chatHistory: "Chat history",
    messages: "messages",
    typing: "Typing...",
    send: "Send",
    transcription: "Transcription",
  },
  es: {
    appTitle: "Asistente de Voz",
    appSubtitle: "Graba e interactúa con tus servicios de Huawei Cloud",
    clickToStart: "Haz clic para comenzar a grabar",
    recording: "Grabando...",
    transcribing: "Transcribiendo...",
    done: "Listo",
    errorOccurred: "Ocurrió un error",
    microphoneError: "Acceso al micrófono denegado. Por favor, permite el acceso al micrófono.",
    noTextError: "No puedo entender, por favor graba tu audio de nuevo.",
    transcriptionFailed: "Falló la transcripción.",
    transcription: "Transcripción",
    yourTranscriptionWillAppear: "Tu transcripción aparecerá aquí",
    recordingLanguage: "Idioma de grabación",
    english: "Inglés",
    spanish: "Español",
    spanishNotAvailable: "La grabación en español aún no está disponible",
    feature1Title: "1. Recursos activos",
    feature1Desc: "Asistente inteligente que te permite administrar y consultar tus recursos activos en Huawei Cloud. Centraliza la información en un panel interactivo y simplifica el monitoreo evitando navegar por la consola.",
    feature1Example: 'Ej: "Show me a summary of my services right now, please"',
    feature2Title: "2. Facturación mensual",
    feature2Desc: "Comprende tu facturación mensual utilizando comandos de voz en inglés. Una forma directa de controlar tus gastos centralizados en una misma interfaz gráfica fácil de leer.",
    feature2Example: 'Ej: "How much money I spent on April 2026"',
    chatTitle: "Asistente de Chat",
    chatSubtitle: "Interactúa con tus servicios de Huawei Cloud a través de chat.",
    conversations: "Conversaciones",
    chatHistory: "Historial de chat",
    messages: "mensajes",
    typing: "Escribiendo...",
    send: "Enviar",
    transcription: "Transcripción",
  },
};

function App() {
  const [activeView, setActiveView] = useState("voice");
  const [sidebarOpen, setSidebarOpen] = useState(() =>
    typeof window !== "undefined" ? !window.matchMedia("(max-width: 768px)").matches : true
  );
  const [status, setStatus] = useState("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [transcription, setTranscription] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [waveformData, setWaveformData] = useState([]);
  const [language, setLanguage] = useState(() => localStorage.getItem("language") || "en");
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "light");
  const [recordingLanguage, setRecordingLanguage] = useState(() => localStorage.getItem("recordingLanguage") || "en");
  const [intentClassification, setIntentClassification] = useState(null);
  const [resourcesResponse, setResourcesResponse] = useState(null);
  const [billingResponse, setBillingResponse] = useState(null);

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const chunksRef = useRef([]);
  const analyzerRef = useRef(null);
  const animationIdRef = useRef(null);
  const audioContextRef = useRef(null);
  const waveformSmoothingRef = useRef(new Array(64).fill(0));

  const t = translations[language];

  // Apply theme on mount and when it changes
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Save language to localStorage
  useEffect(() => {
    localStorage.setItem("language", language);
  }, [language]);

  // Save recording language to localStorage
  useEffect(() => {
    localStorage.setItem("recordingLanguage", recordingLanguage);
  }, [recordingLanguage]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 768px)");

    const syncSidebarState = () => {
      setSidebarOpen(!mediaQuery.matches);
    };

    syncSidebarState();
    mediaQuery.addEventListener("change", syncSidebarState);

    return () => mediaQuery.removeEventListener("change", syncSidebarState);
  }, []);

  const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches;

  const handleSelectView = (view) => {
    setActiveView(view);
    if (isMobile) setSidebarOpen(false);
  };

  const statusLabel = useMemo(() => {
    const labels = {
      idle: t.clickToStart,
      recording: t.recording,
      processing: t.transcribing,
      success: t.done,
      error: t.errorOccurred,
    };
    return labels[status];
  }, [status, t]);

  const resetOutput = () => {
    setTranscription("");
    setErrorMessage("");
    setWaveformData([]);
    setIntentClassification(null);
    setResourcesResponse(null);
    setBillingResponse(null);
  };

  const updateWaveform = () => {
    if (!analyzerRef.current) return;

    const dataArray = new Uint8Array(analyzerRef.current.frequencyBinCount);
    analyzerRef.current.getByteFrequencyData(dataArray);

    // Use logarithmic frequency bucketing for more natural visualization
    const bars = 64;
    const smoothedData = new Array(bars).fill(0);
    const binSpacing = Math.floor(dataArray.length / bars);

    for (let i = 0; i < bars; i++) {
      const index = i * binSpacing;
      const value = dataArray[index] / 255;
      
      // Apply exponential smoothing for natural movement
      const smoothingFactor = 0.3;
      waveformSmoothingRef.current[i] = 
        waveformSmoothingRef.current[i] * (1 - smoothingFactor) + value * smoothingFactor;
      
      smoothedData[i] = Math.pow(waveformSmoothingRef.current[i], 0.8);
    }

    setWaveformData(smoothedData);
    animationIdRef.current = requestAnimationFrame(updateWaveform);
  };

  const startRecording = async () => {
    resetOutput();
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl("");
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;
      const analyzer = audioContext.createAnalyser();
      analyzer.fftSize = 256;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyzer);
      analyzerRef.current = analyzer;

      const preferredMimeTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg"];
      const mimeType = preferredMimeTypes.find((type) => MediaRecorder.isTypeSupported(type)) || "";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        if (animationIdRef.current) {
          cancelAnimationFrame(animationIdRef.current);
        }
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        setWaveformData([]);
        await uploadAndTranscribe(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
      updateWaveform();
    } catch (error) {
      setStatus("error");
      setErrorMessage(t.microphoneError);
      console.error(error);
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    recorder.stop();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    setStatus("processing");
  };

  const uploadAndTranscribe = async (blob) => {
    setStatus("processing");
    setErrorMessage("");

    const extension = blob.type.includes("ogg") ? "ogg" : "webm";
    const file = new File([blob], `recording.${extension}`, { type: blob.type || "audio/webm" });
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", recordingLanguage);

    try {
      const response = await fetch(`${API_BASE_URL}/transcribe`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let detail = `Backend error (${response.status}).`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch {
          // Keep fallback message.
        }
        throw new Error(detail);
      }

      const data = await response.json();
      
      if (!data.text || data.text.trim() === "") {
        throw new Error(t.noTextError);
      }
      
      setTranscription(data.text);
      
      // Store intent classification if available
      if (data.intent_classification) {
        setIntentClassification(data.intent_classification);
      }
      
      // Store resources response if available
      if (data.resources_response) {
        setResourcesResponse(data.resources_response);
      }
      
      // Store billing response if available
      if (data.billing_response) {
        setBillingResponse(data.billing_response);
      }
      
      setStatus("success");
    } catch (error) {
      setStatus("error");
      setErrorMessage(error.message || t.transcriptionFailed);
      console.error(error);
    }
  };

  const toggleRecording = () => {
    if (status === "idle" || status === "success" || status === "error") {
      startRecording();
    } else if (status === "recording") {
      stopRecording();
    }
  };

  return (
    <main className="app-container app-shell">
      <Sidebar
        activeView={activeView}
        onSelectView={handleSelectView}
        language={language}
        theme={theme}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="app-main">
        <div className="top-bar">
          <button
            className="sidebar-toggle"
            type="button"
            onClick={() => setSidebarOpen((current) => !current)}
            aria-label="Toggle sidebar"
          >
            ☰
          </button>

          <div className="lang-switch">
            <span className="lang-switch-label">{language === "es" ? "ES" : "EN"}</span>
            <div
              className="lang-switch-track"
              role="switch"
              aria-checked={language === "es"}
              aria-label={language === "es" ? "Cambiar a inglés" : "Switch to Spanish"}
              tabIndex={0}
              onClick={() => setLanguage(language === "es" ? "en" : "es")}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setLanguage(language === "es" ? "en" : "es"); } }}
            >
              <div className="lang-switch-thumb" />
            </div>
            <span className="lang-switch-label">{language === "es" ? "EN" : "ES"}</span>
          </div>

          <div className="theme-switch">
            <svg className="theme-switch-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
            <div
              className="theme-switch-track"
              role="switch"
              aria-checked={theme === "dark"}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              tabIndex={0}
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setTheme(theme === "dark" ? "light" : "dark"); } }}
            >
              <div className="theme-switch-thumb" />
            </div>
            <svg className="theme-switch-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
          </div>
        </div>

        <div style={{ display: activeView === "voice" ? "block" : "none", height: "100%" }}>
          <VoiceView
            t={t}
            status={status}
            statusLabel={statusLabel}
            toggleRecording={toggleRecording}
            recordingLanguage={recordingLanguage}
            setRecordingLanguage={setRecordingLanguage}
            waveformData={waveformData}
            errorMessage={errorMessage}
            transcription={transcription}
            audioUrl={audioUrl}
            intentClassification={intentClassification}
            resourcesResponse={resourcesResponse}
            billingResponse={billingResponse}
            theme={theme}
            language={language}
          />
        </div>
        
        <div style={{ display: activeView === "chat" ? "block" : "none", height: "100%" }}>
          <ChatView theme={theme} language={language} t={t} />
        </div>
      </div>
    </main>
  );
}

export default App;
