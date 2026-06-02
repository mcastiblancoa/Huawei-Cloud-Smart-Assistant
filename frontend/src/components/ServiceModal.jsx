import { motion, AnimatePresence } from "framer-motion";
import { TbX } from "react-icons/tb";
import { useEffect } from "react";

export function ServiceModal({ isOpen, onClose, activeView, language, theme }) {
  // Prevenir scroll cuando el modal está abierto
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }
  const content = {
    voice: {
      en: {
        title: "Voice Assistant",
        instruction: "Tap the microphone to start interacting with the agent. You can ask it to:",
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
        title: "Asistente de Voz",
        instruction: "Toca el micrófono para empezar a interactuar con el agente. Puedes pedirle que:",
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
  };

  const activeContent = content[activeView] || content.chat;
  const localized = activeContent[language];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="service-modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            className="service-modal"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
          >
            {/* Header */}
            <div className="service-modal-header">
              <h2 className="service-modal-title">{localized.title}</h2>
              <button
                type="button"
                className="service-modal-close"
                onClick={onClose}
                aria-label={language === "es" ? "Cerrar" : "Close"}
              >
                <TbX size={24} />
              </button>
            </div>

            {/* Content */}
            <div className="service-modal-content">
              {/* Instruction */}
              <motion.p
                className="service-modal-instruction"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                {localized.instruction}
              </motion.p>

              {/* Examples */}
              <div className="service-modal-examples">
                {localized.tips.map((tip, idx) => (
                  <motion.div
                    key={idx}
                    className="service-modal-example"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.15 + idx * 0.05 }}
                  >
                    <div className="service-modal-bullet" />
                    <p className="service-modal-example-text">{tip}</p>
                  </motion.div>
                ))}
              </div>

              {/* Info Box */}
              <motion.div
                className="service-modal-info-box"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <p className="service-modal-info-text">
                  {language === "es"
                    ? "💡 Usa comandos naturales para interactuar con tus servicios de Huawei Cloud"
                    : "💡 Use natural commands to interact with your Huawei Cloud services"}
                </p>
              </motion.div>
            </div>

            {/* Footer - Close Button */}
            <div className="service-modal-footer">
              <button
                type="button"
                className="service-modal-action-button"
                onClick={onClose}
              >
                {language === "es" ? "Entendido" : "Got it"}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
