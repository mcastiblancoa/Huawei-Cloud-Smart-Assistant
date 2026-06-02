import { useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, CameraOff, AlertTriangle } from "lucide-react";

const CAPTURE_WIDTH = 480;
const CAPTURE_HEIGHT = 360;
const JPEG_QUALITY = 0.8;

export function WebcamFeed({ onFrame, isActive, language }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const [cameraStatus, setCameraStatus] = useState("disconnected");
  const [errorMessage, setErrorMessage] = useState("");

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraStatus("connected");
      setErrorMessage("");
    } catch (err) {
      setCameraStatus("error");
      setErrorMessage(
        language === "es"
          ? "No se pudo acceder a la cámara. Verifica los permisos."
          : "Could not access camera. Please check permissions."
      );
    }
  }, [language]);

  const stopCamera = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraStatus("disconnected");
  }, []);

  useEffect(() => {
    if (isActive) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [isActive, startCamera, stopCamera]);

  useEffect(() => {
    if (cameraStatus !== "connected" || !canvasRef.current || !videoRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    canvas.width = CAPTURE_WIDTH;
    canvas.height = CAPTURE_HEIGHT;

    const captureFrame = () => {
      if (!videoRef.current || videoRef.current.readyState < 2) return;
      ctx.drawImage(videoRef.current, 0, 0, CAPTURE_WIDTH, CAPTURE_HEIGHT);
      canvas.toBlob(
        (blob) => {
          if (blob) onFrame(blob);
        },
        "image/jpeg",
        JPEG_QUALITY
      );
    };

    intervalRef.current = setInterval(captureFrame, 500);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [cameraStatus, onFrame]);

  return (
    <div className="webcam-container">
      <div className="webcam-frame">
        <video
          ref={videoRef}
          className="webcam-video"
          muted
          playsInline
          autoPlay
        />
        <canvas ref={canvasRef} className="webcam-canvas-hidden" />

        <AnimatePresence>
          {cameraStatus === "disconnected" && (
            <motion.div
              className="webcam-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <CameraOff size={40} strokeWidth={1.5} className="webcam-overlay-icon" />
              <p className="webcam-overlay-text">
                {language === "es" ? "Cámara desconectada" : "Camera disconnected"}
              </p>
            </motion.div>
          )}

          {cameraStatus === "error" && (
            <motion.div
              className="webcam-overlay webcam-overlay-error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <AlertTriangle size={40} strokeWidth={1.5} className="webcam-overlay-icon" />
              <p className="webcam-overlay-text">{errorMessage}</p>
            </motion.div>
          )}

          {cameraStatus === "connected" && (
            <motion.div
              className="webcam-live-badge"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            >
              <span className="webcam-live-dot" />
              LIVE
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="webcam-controls">
        {cameraStatus === "connected" ? (
          <button className="webcam-btn webcam-btn-stop" onClick={stopCamera} type="button">
            <CameraOff size={14} />
            {language === "es" ? "Detener" : "Stop"}
          </button>
        ) : (
          <button className="webcam-btn webcam-btn-start" onClick={startCamera} type="button">
            <Camera size={14} />
            {language === "es" ? "Iniciar cámara" : "Start camera"}
          </button>
        )}
      </div>
    </div>
  );
}
