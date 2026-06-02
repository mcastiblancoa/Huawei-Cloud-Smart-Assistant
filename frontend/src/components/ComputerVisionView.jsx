import { motion } from "framer-motion";
import { TbCamera, TbAlertCircle } from "react-icons/tb";
import { SentimentRecognition } from "./vision/SentimentRecognition";
import { SafetyDetection } from "./vision/SafetyDetection";

export function ComputerVisionView({
  t,
  title,
  subtitle,
  language,
  theme,
  mode,
}) {
  const isFeelingsMode = mode === "feelings";
  const isSafetyMode = mode === "industrial-safety";
  const isActiveMode = isFeelingsMode || isSafetyMode;

  return (
    <motion.section
      className="view-shell"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        className="header"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <h1 className="app-title">{title}</h1>
        <p className="app-subtitle">{subtitle}</p>
      </motion.div>

      <div className="interactive-zone">
        {isFeelingsMode && (
          <motion.div
            className="sentiment-container"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            <SentimentRecognition language={language} theme={theme} />
          </motion.div>
        )}

        {isSafetyMode && (
          <motion.div
            className="safety-container"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            <SafetyDetection language={language} theme={theme} />
          </motion.div>
        )}

        {!isActiveMode && (
          <motion.div
            className="construction-container"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            <div className="construction-notice">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                className="construction-icon"
              >
                <TbAlertCircle size={48} className="text-hw-red" />
              </motion.div>
              <h2 className="construction-title">
                {language === "es" ? "En Construcción" : "Under Construction"}
              </h2>
              <p className="construction-text">
                {language === "es"
                  ? "Esta función está siendo desarrollada. Pronto estará disponible."
                  : "This feature is being developed. It will be available soon."}
              </p>
            </div>

            <motion.div
              className="camera-placeholder"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4 }}
            >
              <div className="camera-frame">
                <motion.div
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="camera-placeholder-content"
                >
                  <TbCamera size={64} className="camera-placeholder-icon" />
                  <p className="camera-placeholder-text">
                    {language === "es"
                      ? "Aquí irá la vista de la cámara"
                      : "Camera view will appear here"}
                  </p>
                </motion.div>
              </div>
            </motion.div>

            <motion.div
              className="info-box"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.4 }}
            >
              <p className="info-text">
                {language === "es"
                  ? "📹 Esta sección utilizará modelos de visión computacional para procesar imágenes de tu cámara web en tiempo real."
                  : "📹 This section will use computer vision models to process images from your webcam in real-time."}
              </p>
            </motion.div>
          </motion.div>
        )}
      </div>
    </motion.section>
  );
}
