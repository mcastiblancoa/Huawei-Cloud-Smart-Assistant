import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export function RightSidebar({ isOpen, onClose, activeView, language, theme }) {
  const content = {
    voice: {
      en: {
        title: "Voice Assistant",
        instruction: "Tap the microphone to start interacting with the agent. You can ask it to:",
        tips: [
          "Tell me how much I spent in May 2026 on Huawei Cloud",
          "Deploy an ECS instance with Ubuntu named ecs-test",
          "List all my active RDS databases",
          "Create a new VPC with CIDR 10.0.0.0/16",
          "How many resources do I have deployed right now?"
        ],
      },
      es: {
        title: "Asistente de Voz",
        instruction: "Toca el micrófono para empezar a interactuar con el agente. Puedes pedirle que:",
        tips: [
          "Dime cuánto he gastado en Mayo de 2026 en Huawei Cloud",
          "Despliega una ECS con Ubuntu llamada ecs-test",
          "Enumera todas mis bases de datos RDS activas",
          "Crea una nueva VPC con CIDR 10.0.0.0/16",
          "¿Cuántos recursos tengo desplegados en este momento?"
        ],
      },
    },
    chat: {
      en: {
        title: "Chat Assistant",
        instruction: "Ask the agent what you want to do:",
        tips: [
          "Show me how much I spent in May 2026 on Huawei Cloud",
          "Deploy an ECS instance with Ubuntu named ecs-test",
          "List all my active RDS databases",
          "Create a new VPC with CIDR 10.0.0.0/16",
          "How many resources do I have deployed right now?",
          "Show me the billing details for ECS services",
        ],
      },
      es: {
        title: "Asistente de Chat",
        instruction: "Pídele al agente qué quieres hacer:",
        tips: [
          "Muéstrame cuánto he gastado en Mayo de 2026 en Huawei Cloud",
          "Despliega una ECS con Ubuntu llamada ecs-test",
          "Enumera todas mis bases de datos RDS activas",
          "Crea una nueva VPC con CIDR 10.0.0.0/16",
          "¿Cuántos recursos tengo desplegados en este momento?",
          "Muéstrame los detalles de facturación para servicios ECS",
        ],
      },
    },
    feelings: {
      en: {
        title: "Feelings Recognition",
        tips: [
          "Coming soon - Computer Vision feature",
          "Real-time emotion detection from camera",
          "AI-powered sentiment analysis",
          "Integration with Huawei Cloud services",
        ],
      },
      es: {
        title: "Reconocimiento de Sentimientos",
        tips: [
          "Próximamente - Función de Visión Computacional",
          "Detección de emociones en tiempo real desde la cámara",
          "Análisis de sentimientos impulsado por IA",
          "Integración con servicios de Huawei Cloud",
        ],
      },
    },
    "industrial-safety": {
      en: {
        title: "Industrial Safety",
        tips: [
          "Coming soon - Computer Vision feature",
          "Safety detection in industrial environments",
          "Real-time alerts and monitoring",
          "AI-powered risk assessment",
        ],
      },
      es: {
        title: "Seguridad Industrial",
        tips: [
          "Próximamente - Función de Visión Computacional",
          "Detección de seguridad en entornos industriales",
          "Alertas y monitoreo en tiempo real",
          "Evaluación de riesgos impulsada por IA",
        ],
      },
    },
  };

  const activeContent = content[activeView] || content.chat;
  const localized = activeContent[language];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="right-sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Sidebar */}
          <motion.aside
            className="right-sidebar"
            initial={{ x: 360, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 360, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            {/* Header */}
            <div className="right-sidebar-header">
              <h2 className="right-sidebar-title">{localized.title}</h2>
              <button
                type="button"
                className="right-sidebar-close"
                onClick={onClose}
                aria-label={language === "es" ? "Cerrar" : "Close"}
              >
                <X size={20} strokeWidth={1.5} />
              </button>
            </div>

            {/* Content */}
            <div className="right-sidebar-content">
              {/* Instruction */}
              {localized.instruction && (
                <motion.p
                  className="tips-instruction"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  {localized.instruction}
                </motion.p>
              )}

              {/* Examples Section */}
              <div className="tips-section">
                <div className="tips-examples-container">
                  {localized.tips.map((tip, idx) => (
                    <motion.div
                      key={idx}
                      className="tips-example"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.15 + idx * 0.05 }}
                    >
                      <p className="tips-example-text">{tip}</p>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Info Box */}
              <motion.div
                className="info-box"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <p className="info-text">
                  {language === "es"
                    ? "💡 Usa comandos naturales para interactuar con tus servicios de Huawei Cloud"
                    : "💡 Use natural commands to interact with your Huawei Cloud services"}
                </p>
              </motion.div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
