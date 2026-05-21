import { motion, AnimatePresence } from "framer-motion";
import { Bot, Mic, X, Plus, MessageSquare, Trash2, Pencil, Cloud, ChevronDown, Eye, Smile, AlertTriangle } from "lucide-react";
import { ScrollArea } from "./ui/ScrollArea";
import huaweiLogo from "../img/huawei_logo.png";
import { useState } from "react";

export function Sidebar({
  activeView,
  onSelectView,
  language,
  theme,
  isOpen,
  onClose,
  chatThreads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  onRenameThread,
}) {
  const [infrastructureExpanded, setInfrastructureExpanded] = useState(true);
  const [cvExpanded, setCvExpanded] = useState(true);

  const HuaweiLogoIcon = () => (
    <img src={huaweiLogo} alt="Huawei Cloud" className="flex-shrink-0" style={{ width: "24px", height: "24px", objectFit: "contain" }} />
  );

  const infrastructureItems = [
    { id: "voice", label: language === "es" ? "Asistente de Voz" : "Voice Assistant", icon: Mic, category: "infrastructure" },
    { id: "chat", label: language === "es" ? "Asistente de Chat" : "Chat Assistant", icon: Bot, category: "infrastructure" },
  ];

  const cvItems = [
    { id: "feelings", label: language === "es" ? "Sentimientos" : "Feelings", icon: Smile, category: "cv" },
    { id: "industrial-safety", label: language === "es" ? "Seguridad Industrial" : "Industrial Safety", icon: AlertTriangle, category: "cv" },
  ];

  const infrastructureLabel = language === "es" ? "Infraestructura Huawei Cloud" : "Huawei Cloud Infrastructure";
  const cvLabel = language === "es" ? "Visión Artificial" : "Computer Vision";

  const t = {
    conversations: language === "es" ? "Conversaciones" : "Conversations",
    chatHistory: language === "es" ? "Historial de chat" : "Chat history",
    messages: language === "es" ? "mensajes" : "messages",
    newChat: language === "es" ? "Nuevo" : "New",
    deleteChat: language === "es" ? "Borrar chat" : "Delete chat",
    renameChat: language === "es" ? "Editar nombre" : "Edit name",
  };

  const showThreads = activeView === "chat" && chatThreads && chatThreads.length > 0;
  const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches;
  const sidebarStateClass = isMobile ? (isOpen ? "is-open" : "is-closed") : (!isOpen ? "is-collapsed" : "");

  return (
    <motion.aside
      className={`app-sidebar ${sidebarStateClass}`}
      animate={{
        width: isOpen && !isMobile ? "16rem" : undefined,
      }}
    >
      {/* Brand */}
      <div className="sidebar-brand">
        <motion.div
          className="sidebar-brand-mark"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <HuaweiLogoIcon />
        </motion.div>
        <div className="sidebar-brand-copy">
          <div className="sidebar-brand-title">Huawei Cloud</div>
          <div className="sidebar-brand-subtitle">Smart Assistant</div>
        </div>
        {isMobile && (
          <motion.button
            className="ml-auto p-2 hover:bg-huawei-gray-200 dark:hover:bg-huawei-gray-700 rounded-lg transition-colors"
            whileTap={{ scale: 0.95 }}
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X size={20} strokeWidth={1.5} />
          </motion.button>
        )}
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav" aria-label="Assistant views">
        {/* Infrastructure Category */}
        <motion.button
          className="sidebar-category-button"
          onClick={() => setInfrastructureExpanded(!infrastructureExpanded)}
          whileHover={{ x: 2 }}
          whileTap={{ scale: 0.98 }}
        >
          <Cloud size={18} strokeWidth={1.5} className="flex-shrink-0" />
          <span className="sidebar-category-label">{infrastructureLabel}</span>
          <motion.div
            animate={{ rotate: infrastructureExpanded ? 0 : -90 }}
            transition={{ duration: 0.2 }}
            className="ml-auto flex-shrink-0"
          >
            <ChevronDown size={18} strokeWidth={1.5} />
          </motion.div>
        </motion.button>

        {/* Infrastructure Items */}
        <AnimatePresence>
          {infrastructureExpanded && infrastructureItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <motion.button
                key={item.id}
                className={`sidebar-nav-item sidebar-nav-subitem ${isActive ? "active" : ""}`}
                onClick={() => {
                  onSelectView(item.id);
                  if (isMobile) {
                    onClose();
                  }
                }}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.98 }}
                aria-pressed={isActive}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <Icon size={20} strokeWidth={1.5} />
                <span>{item.label}</span>
              </motion.button>
            );
          })}
        </AnimatePresence>

        {/* Computer Vision Category */}
        <motion.button
          className="sidebar-category-button"
          onClick={() => setCvExpanded(!cvExpanded)}
          whileHover={{ x: 2 }}
          whileTap={{ scale: 0.98 }}
        >
          <Eye size={18} strokeWidth={1.5} className="flex-shrink-0" />
          <span className="sidebar-category-label">{cvLabel}</span>
          <motion.div
            animate={{ rotate: cvExpanded ? 0 : -90 }}
            transition={{ duration: 0.2 }}
            className="ml-auto flex-shrink-0"
          >
            <ChevronDown size={18} strokeWidth={1.5} />
          </motion.div>
        </motion.button>

        {/* Computer Vision Items */}
        <AnimatePresence>
          {cvExpanded && cvItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <motion.button
                key={item.id}
                className={`sidebar-nav-item sidebar-nav-subitem ${isActive ? "active" : ""}`}
                onClick={() => {
                  onSelectView(item.id);
                  if (isMobile) {
                    onClose();
                  }
                }}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.98 }}
                aria-pressed={isActive}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
              >
                <Icon size={20} strokeWidth={1.5} />
                <span>{item.label}</span>
              </motion.button>
            );
          })}
        </AnimatePresence>
      </nav>

      {/* Chat History */}
      {showThreads && (
        <div className="sidebar-threads">
          <div className="sidebar-threads-header">
            <span className="sidebar-threads-label">{t.chatHistory}</span>
            <motion.button
              className="sidebar-thread-new"
              onClick={onCreateThread}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              title={t.newChat}
            >
              <Plus size={16} strokeWidth={2} />
            </motion.button>
          </div>

          <ScrollArea className="flex-1">
            <div className="sidebar-threads-list pr-4">
              <AnimatePresence>
                {chatThreads.map((thread, index) => {
                  const isActive = thread.id === activeThreadId;
                  return (
                    <motion.div
                      key={thread.id}
                      className={`sidebar-thread-item ${isActive ? "active" : ""}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      transition={{ delay: index * 0.05 }}
                    >
                      <div className="sidebar-thread-actions">
                        <motion.button
                          type="button"
                          className="sidebar-thread-edit"
                          onClick={() => onRenameThread?.(thread.id)}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                          title={t.renameChat}
                        >
                          <Pencil size={14} strokeWidth={1.5} />
                        </motion.button>
                        <motion.button
                          type="button"
                          className="sidebar-thread-delete"
                          onClick={() => onDeleteThread(thread.id)}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                          title={t.deleteChat}
                        >
                          <Trash2 size={14} strokeWidth={1.5} />
                        </motion.button>
                      </div>
                      <button
                        type="button"
                        className="sidebar-thread-btn"
                        onClick={() => onSelectThread(thread.id)}
                      >
                        <MessageSquare size={16} strokeWidth={1.5} className="flex-shrink-0" />
                        <span className="sidebar-thread-name">{thread.title}</span>
                      </button>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          </ScrollArea>
        </div>
      )}
    </motion.aside>
  );
}
