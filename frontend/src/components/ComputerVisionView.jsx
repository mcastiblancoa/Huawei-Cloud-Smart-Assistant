import { motion } from "framer-motion";
import { Camera, AlertCircle } from "lucide-react";

export function ComputerVisionView({
  t,
  title,
  subtitle,
  language,
  theme,
}) {
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
        <h1 className="app-title">{title}</h1>
        <p className="app-subtitle">{subtitle}</p>
      </motion.div>

      {/* Interactive Zone */}
      <div className="interactive-zone">
        {/* Construction Notice */}
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
              <AlertCircle size={48} strokeWidth={1.5} className="text-hw-red" />
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

          {/* Camera Preview Placeholder */}
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
                <Camera size={64} strokeWidth={1.5} className="camera-placeholder-icon" />
                <p className="camera-placeholder-text">
                  {language === "es"
                    ? "Aquí irá la vista de la cámara"
                    : "Camera view will appear here"}
                </p>
              </motion.div>
            </div>
          </motion.div>

          {/* Info Box */}
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
      </div>
    </motion.section>
  );
}
