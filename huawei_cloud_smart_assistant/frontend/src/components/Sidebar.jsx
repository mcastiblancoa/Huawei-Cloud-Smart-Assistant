import { Bot, Mic } from "lucide-react";

export function Sidebar({ activeView, onSelectView, language, theme, isOpen, onClose }) {
  const items = [
    { id: "voice", label: "Voice Assistant", icon: Mic },
    { id: "chat", label: "Chat Assistant", icon: Bot },
  ];

  return (
    <aside className={`app-sidebar ${isOpen ? "is-open" : "is-closed"}`}>
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">HC</div>
        <div className="sidebar-brand-copy">
          <span className="sidebar-brand-title">Huawei Cloud</span>
          <span className="sidebar-brand-subtitle">Smart Assistant</span>
        </div>
        <button className="sidebar-close" type="button" onClick={onClose} aria-label="Close sidebar">
          ×
        </button>
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
              <Icon size={18} strokeWidth={1.8} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-meta">
          <span className="sidebar-meta-label">Language</span>
          <span className="sidebar-meta-value">{language === "es" ? "ES" : "EN"}</span>
        </div>
        <div className="sidebar-meta">
          <span className="sidebar-meta-label">Theme</span>
          <span className="sidebar-meta-value">{theme}</span>
        </div>
      </div>
    </aside>
  );
}