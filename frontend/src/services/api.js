const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8003";

export async function sendChatMessage(message, sessionId) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    let detail = `Backend error (${response.status}).`;
    try { const body = await response.json(); detail = body.detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

export async function sendVoiceAudio(audioBlob, language, sessionId, voice, speed) {
  const extension = audioBlob.type.includes("ogg") ? "ogg" : "webm";
  const file = new File([audioBlob], `recording.${extension}`, { type: audioBlob.type || "audio/webm" });
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language);
  if (sessionId) formData.append("session_id", sessionId);
  if (voice) formData.append("voice", voice);
  if (speed) formData.append("speed", speed);

  const response = await fetch(`${API_BASE_URL}/voice`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    let detail = `Backend error (${response.status}).`;
    try { const body = await response.json(); detail = body.detail || detail; } catch {}
    throw new Error(detail);
  }

  const data = await response.json();
  let ttsAudioBlob = null;

  if (data.audio_base64) {
    try {
      const byteCharacters = atob(data.audio_base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const mimeType = data.audio_format === "mp3" ? "audio/mpeg" : `audio/${data.audio_format || "mpeg"}`;
      ttsAudioBlob = new Blob([byteArray], { type: mimeType });
    } catch (decodeError) {
      console.error("Failed to decode TTS audio:", decodeError);
    }
  }

  return { json: data, audio: ttsAudioBlob };
}

export async function analyzeSentiment(imageBlob, signal) {
  const formData = new FormData();
  formData.append("file", imageBlob, "frame.jpg");

  const response = await fetch(`${API_BASE_URL}/vision/sentiment`, {
    method: "POST",
    body: formData,
    signal,
  });
  if (!response.ok) {
    let detail = `Vision error (${response.status}).`;
    try { const body = await response.json(); detail = body.detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

export async function analyzeSafety(imageBlob, signal) {
  const formData = new FormData();
  formData.append("file", imageBlob, "frame.jpg");

  const response = await fetch(`${API_BASE_URL}/vision/safety`, {
    method: "POST",
    body: formData,
    signal,
  });
  if (!response.ok) {
    let detail = `Safety error (${response.status}).`;
    try { const body = await response.json(); detail = body.detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

export { API_BASE_URL };
