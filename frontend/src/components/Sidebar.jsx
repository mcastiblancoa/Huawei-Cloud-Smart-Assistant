import { Bot, Mic, X, Plus, MessageSquare, Trash2 } from "lucide-react";

export function Sidebar({ activeView, onSelectView, language, theme, isOpen, onClose, chatThreads, activeThreadId, onSelectThread, onCreateThread, onDeleteThread }) {
  const items = [
    { id: "voice", label: "Voice Assistant", icon: Mic },
    { id: "chat", label: "Chat Assistant", icon: Bot },
  ];

  const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches;
  const showThreads = activeView === "chat" && chatThreads && chatThreads.length > 0;

  const t = {
    conversations: language === "es" ? "Conversaciones" : "Conversations",
    chatHistory: language === "es" ? "Historial de chat" : "Chat history",
    messages: language === "es" ? "mensajes" : "messages",
    newChat: language === "es" ? "Nuevo" : "New",
    deleteChat: language === "es" ? "Borrar chat" : "Delete chat",
  };

  return (
    <aside className={`app-sidebar ${isOpen ? "is-open" : "is-closed"}`}>
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">HC</div>
        <div className="sidebar-brand-copy">
          <span className="sidebar-brand-title">Huawei Cloud</span>
          <span className="sidebar-brand-subtitle">Smart Assistant</span>
        </div>
        {isMobile && (
          <button className="sidebar-close" type="button" onClick={onClose} aria-label="Close sidebar">
            <X size={16} strokeWidth={1.5} />
          </button>
        )}
      </div>

      <nav className="sidebar-nav" aria-label="Assistant views">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              className={`sidebar-nav-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectView(item.id)}
              aria-pressed={isActive}
            >
              <Icon size={18} strokeWidth={1.5} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {showThreads && (
        <div className="sidebar-threads">
          <div className="sidebar-threads-header">
            <span className="sidebar-threads-label">{t.chatHistory}</span>
            <button className="sidebar-thread-new" type="button" onClick={onCreateThread} title={t.newChat}>
              <Plus size={14} strokeWidth={1.5} />
            </button>
          </div>
          <div className="sidebar-threads-list">
            {chatThreads.map((thread) => {
              const isActive = thread.id === activeThreadId;
              return (
                <div key={thread.id} className={`sidebar-thread-item ${isActive ? "active" : ""}`}>
                  <button type="button" className="sidebar-thread-btn" onClick={() => onSelectThread(thread.id)}>
                    <MessageSquare size={14} strokeWidth={1.5} />
                    <span className="sidebar-thread-name">{thread.title}</span>
                  </button>
                  <button
                    type="button"
                    className="sidebar-thread-delete"
                    onClick={() => onDeleteThread(thread.id)}
                    title={t.deleteChat}
                  >
                    <Trash2 size={12} strokeWidth={1.5} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </aside>
  );
}
