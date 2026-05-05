import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MessageSquare, Plus, Send, Sparkles, Trash2 } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const CHAT_THREADS_KEY = "koocliChatThreads";
const ACTIVE_THREAD_KEY = "koocliActiveChatId";

const getRandomId = (prefix) => {
  const id = globalThis.crypto?.randomUUID?.() || `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${id}`;
};

const safeParse = (value, fallback) => {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
};

const createWelcomeMessage = (language) => ({
  id: getRandomId("msg"),
  role: "assistant",
  content:
    language === "es"
      ? "Escribe una solicitud para consultar o ejecutar acciones de Huawei Cloud."
      : "Type a request to query or execute Huawei Cloud actions.",
  createdAt: Date.now(),
});

const buildThreadTitle = (text, language) => {
  const cleanText = text.replace(/\s+/g, " ").trim();
  if (!cleanText) {
    return language === "es" ? "Nuevo chat" : "New chat";
  }

  const short = cleanText.split(" ").slice(0, 6).join(" ");
  return short.length > 42 ? `${short.slice(0, 39)}...` : short;
};

const normalizeMessage = (message) => ({
  id: message.id || getRandomId("msg"),
  role: message.role === "user" ? "user" : "assistant",
  content: String(message.content ?? ""),
  createdAt: message.createdAt || Date.now(),
  durationMs: Number.isFinite(message.durationMs) ? message.durationMs : undefined,
});

const normalizeThread = (thread, language, fallbackSessionId) => {
  const messages = Array.isArray(thread.messages) && thread.messages.length > 0
    ? thread.messages.map(normalizeMessage)
    : [createWelcomeMessage(language)];
  const title = thread.title || buildThreadTitle(messages.find((item) => item.role === "user")?.content || "", language);

  return {
    id: thread.id || getRandomId("thread"),
    sessionId: thread.sessionId || fallbackSessionId || getRandomId("session"),
    title,
    createdAt: thread.createdAt || Date.now(),
    updatedAt: thread.updatedAt || Date.now(),
    messages,
  };
};

const createThread = (language, title) => ({
  id: getRandomId("thread"),
  sessionId: getRandomId("session"),
  title: title || (language === "es" ? "Nuevo chat" : "New chat"),
  createdAt: Date.now(),
  updatedAt: Date.now(),
  messages: [createWelcomeMessage(language)],
});

const isTableSeparator = (line) => {
  const cells = line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());

  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
};

const splitTableRow = (line) =>
  line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());

const isTableStart = (lines, index) => {
  const current = lines[index] || "";
  const next = lines[index + 1] || "";
  return current.includes("|") && next.includes("|") && isTableSeparator(next);
};

const parseMarkdownTable = (lines) => {
  if (lines.length < 2) return null;

  const headers = splitTableRow(lines[0]);
  const rows = [];

  for (let i = 2; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.trim() || !line.includes("|")) continue;
    rows.push(splitTableRow(line));
  }

  return { headers, rows };
};

const parseAssistantContent = (content) => {
  const fullContent = String(content);
  const lines = fullContent.split(/\r?\n/);
  const blocks = [];
  let index = 0;

  // Detectar marcador de reporte especial
  if (fullContent.includes(":::REPORTE_RECURSOS:::")) {
    const reportMatch = fullContent.match(/:::REPORTE_RECURSOS:::\s*([\s\S]*)/);
    if (reportMatch) {
      blocks.push({ type: "report-header" });
      const reportContent = reportMatch[1];
      const reportLines = reportContent.split(/\r?\n/);
      let reportIndex = 0;

      while (reportIndex < reportLines.length) {
        const line = reportLines[reportIndex];
        if (!line.trim()) {
          reportIndex += 1;
          continue;
        }

        if (line.includes("|") && reportIndex + 1 < reportLines.length && reportLines[reportIndex + 1].includes("|")) {
          const tableLines = [line, reportLines[reportIndex + 1]];
          reportIndex += 2;

          while (reportIndex < reportLines.length && reportLines[reportIndex].trim() && reportLines[reportIndex].includes("|")) {
            tableLines.push(reportLines[reportIndex]);
            reportIndex += 1;
          }

          const table = parseMarkdownTable(tableLines);
          if (table) {
            blocks.push({ type: "table", table });
          }
          continue;
        }

        if (/^#{1,4}\s+/.test(line)) {
          const level = line.match(/^#{1,4}/)?.[0].length || 1;
          blocks.push({ type: "heading", level, text: line.replace(/^#{1,4}\s+/, "") });
          reportIndex += 1;
          continue;
        }

        const paragraphLines = [line];
        reportIndex += 1;

        while (reportIndex < reportLines.length && reportLines[reportIndex].trim() && 
               !reportLines[reportIndex].includes("|") && !/^#{1,4}\s+/.test(reportLines[reportIndex])) {
          paragraphLines.push(reportLines[reportIndex]);
          reportIndex += 1;
        }

        blocks.push({ type: "text", text: paragraphLines.join("\n") });
      }
      return blocks;
    }
  }

  // Parseo normal sin reporte especial
  while (index < lines.length) {
    if (isTableStart(lines, index)) {
      const tableLines = [lines[index], lines[index + 1]];
      index += 2;

      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
        tableLines.push(lines[index]);
        index += 1;
      }

      const table = parseMarkdownTable(tableLines);
      if (table) {
        blocks.push({ type: "table", table });
      }
      continue;
    }

    if (!lines[index].trim()) {
      index += 1;
      continue;
    }

    const paragraphLines = [lines[index]];
    index += 1;

    while (index < lines.length && lines[index].trim() && !isTableStart(lines, index)) {
      paragraphLines.push(lines[index]);
      index += 1;
    }

    blocks.push({ type: "text", text: paragraphLines.join("\n") });
  }

  return blocks;
};

const extractNumber = (value) => {
  const normalized = String(value ?? "")
    .replace(/[$%\s,]/g, "")
    .replace(/[^\d.-]/g, "");

  if (!normalized || normalized === "-" || normalized === "." || normalized === "-.") return null;
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
};

const buildChartModel = (table) => {
  if (!table?.headers?.length || !table?.rows?.length) return null;

  const labelHeader = table.headers[0] || "Item";
  const numericColumns = [];

  table.headers.slice(1).forEach((header, offset) => {
    const index = offset + 1;
    const values = table.rows.map((row) => extractNumber(row[index])).filter((value) => value !== null);
    if (values.length > 0) {
      numericColumns.push({ index, key: `series-${offset}`, label: header, values });
    }
  });

  if (numericColumns.length === 0) return null;

  if (numericColumns.length === 1) {
    const column = numericColumns[0];
    const data = table.rows
      .map((row) => ({
        name: String(row[0] || labelHeader).slice(0, 28),
        value: extractNumber(row[column.index]) ?? 0,
      }))
      .filter((row) => row.name.trim().length > 0)
      .sort((left, right) => right.value - left.value)
      .slice(0, 8);

    return {
      kind: "single",
      data,
      series: [{ key: "value", label: column.label }],
    };
  }

  const seriesColumns = numericColumns.slice(0, 3);
  const data = table.rows.map((row) => {
    const item = { name: String(row[0] || labelHeader).slice(0, 28) };

    seriesColumns.forEach((column) => {
      item[column.key] = extractNumber(row[column.index]) ?? 0;
    });

    return item;
  });

  return {
    kind: "grouped",
    data,
    series: seriesColumns.map((column) => ({ key: column.key, label: column.label })),
  };
};

const formatCurrency = (value) => {
  if (!Number.isFinite(value)) return value;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
};

function ReportHeader() {
  return (
    <div className="chat-report-header">
      <div className="chat-report-badge">📊 REPORTE DE RECURSOS</div>
    </div>
  );
}

function MarkdownBlock({ text }) {
  const lines = String(text).split(/\r?\n/);
  const blocks = [];
  let currentParagraph = [];

  const flushParagraph = () => {
    if (!currentParagraph.length) return;
    blocks.push({ type: "paragraph", text: currentParagraph.join(" ") });
    currentParagraph = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      return;
    }

    if (/^#{1,3}\s+/.test(trimmed)) {
      flushParagraph();
      const level = trimmed.match(/^#{1,3}/)?.[0].length || 1;
      blocks.push({ type: "heading", level, text: trimmed.replace(/^#{1,3}\s+/, "") });
      return;
    }

    if (/^(?:[-*]|\d+\.)\s+/.test(trimmed)) {
      flushParagraph();
      blocks.push({ type: "list-item", text: trimmed.replace(/^(?:[-*]|\d+\.)\s+/, "") });
      return;
    }

    currentParagraph.push(trimmed);
  });

  flushParagraph();

  const renderHTMLContent = (content) => {
    return (
      <span dangerouslySetInnerHTML={{ __html: content }} />
    );
  };

  return (
    <div className="chat-text-block">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const HeadingTag = block.level === 1 ? "h3" : block.level === 2 ? "h4" : "h5";
          const cleanText = block.text.replace(/\*\*(.*?)\*\*/g, "$1");
          return (
            <HeadingTag className={`chat-heading level-${block.level}`} key={`${block.type}-${index}`}>
              {renderHTMLContent(cleanText)}
            </HeadingTag>
          );
        }

        if (block.type === "list-item") {
          const cleanText = block.text.replace(/\*\*(.*?)\*\*/g, "$1");
          return (
            <div className="chat-list-item" key={`${block.type}-${index}`}>
              <span className="chat-list-bullet">•</span>
              <span>{renderHTMLContent(cleanText)}</span>
            </div>
          );
        }

        const cleanText = block.text.replace(/\*\*(.*?)\*\*/g, "$1");
        return (
          <p className="chat-paragraph" key={`${block.type}-${index}`}>
            {renderHTMLContent(cleanText)}
          </p>
        );
      })}
    </div>
  );
}

function DataTable({ table }) {
  return (
    <div className="chat-table-wrap">
      <table className="chat-table">
        <thead>
          <tr>
            {table.headers.map((header, index) => (
              <th key={`${header}-${index}`}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`cell-${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChartCard({ model, title }) {
  if (!model) return null;

  const colors = ["#e60012", "#2563eb", "#16a34a"];

  const topItem = model.data.reduce(
    (best, item) => {
      const total = model.kind === "single"
        ? item.value
        : model.series.reduce((sum, series) => sum + (Number(item[series.key]) || 0), 0);

      if (total > best.total) {
        return { label: item.name, total };
      }

      return best;
    },
    { label: "", total: 0 }
  );

  return (
    <div className="chat-visual-card">
      <div className="chat-visual-header">
        <div>
          <div className="chat-visual-title">
            <Sparkles size={14} />
            {title || "Visualization"}
          </div>
          <div className="chat-visual-subtitle">
            {model.kind === "single" ? "Ranking of amounts" : "Comparison across categories"}
          </div>
        </div>
        <div className="chat-visual-metrics">
          {topItem.label && (
            <span className="chat-metric-pill">
              Top: {topItem.label} · {formatCurrency(topItem.total)}
            </span>
          )}
        </div>
      </div>

      <div className="chat-chart">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={model.data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.2)" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} interval={0} height={60} />
            <YAxis tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value)} />
            <Tooltip
              formatter={(value, name) => [formatCurrency(Number(value)), name]}
              contentStyle={{ borderRadius: 12, borderColor: "#e5e7eb" }}
            />
            <Legend />
            {model.kind === "single" ? (
              <Bar dataKey="value" name={model.series[0].label} fill="#e60012" radius={[8, 8, 0, 0]} />
            ) : (
              model.series.map((series, index) => (
                <Bar
                  key={series.key}
                  dataKey={series.key}
                  name={series.label}
                  fill={colors[index % colors.length]}
                  radius={[8, 8, 0, 0]}
                />
              ))
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function AssistantMessage({ content, durationMs, language }) {
  const blocks = useMemo(() => parseAssistantContent(content), [content]);
  const reportHeaderBlock = blocks.find((block) => block.type === "report-header");
  const tableBlocks = blocks.filter((block) => block.type === "table");
  const textBlocks = blocks.filter((block) => block.type !== "table" && block.type !== "report-header");
  const chartModel = useMemo(() => buildChartModel(tableBlocks[0]?.table), [tableBlocks]);
  const hasCostLanguage = /gasto|cost|billing|factur|costos|usd|month|mayo|abril|statistics|resumen/i.test(content);

  const tableLabel = language === "es" ? "Tabla estructurada" : "Structured table";
  const chartTitle = language === "es" ? "Análisis de costos" : "Cost analysis";

  const durationLabel = Number.isFinite(durationMs)
    ? language === "es"
      ? `Respuesta en ${durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(1)} s`}`
      : `Response in ${durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(1)} s`}`
    : null;

  return (
    <div className="chat-rendered-message">
      {reportHeaderBlock && <ReportHeader />}
      
      {textBlocks.map((block, index) => (
        <MarkdownBlock key={`${block.type}-${index}`} text={block.text} />
      ))}

      {tableBlocks.map((block, index) => (
        <div className="chat-table-card" key={`table-${index}`}>
          <div className="chat-table-card-title">
            <MessageSquare size={14} />
            {tableLabel}
          </div>
          <DataTable table={block.table} />
        </div>
      ))}

      {chartModel && hasCostLanguage && <ChartCard model={chartModel} title={chartTitle} />}

      {durationLabel && (
        <div className="chat-response-time">
          {durationLabel}
        </div>
      )}
    </div>
  );
}

function ChatThreadList({ threads, activeThreadId, onSelectThread, onCreateThread, onDeleteThread, language, t, isMobileVisible }) {
  return (
    <aside className={`chat-thread-panel ${isMobileVisible ? "is-visible" : "is-hidden"}`}>
      <div className="chat-thread-header">
        <div>
          <div className="chat-thread-eyebrow">{t.conversations}</div>
          <h2 className="chat-thread-title">{t.chatHistory}</h2>
        </div>
        <button className="chat-thread-new" type="button" onClick={onCreateThread} title={language === "es" ? "Nuevo chat" : "New chat"}>
          <Plus size={16} />
          {language === "es" ? "Nuevo" : "New"}
        </button>
      </div>

      <div className="chat-thread-list">
        {threads.map((thread) => {
          const isActive = thread.id === activeThreadId;
          return (
            <div key={thread.id} className={`chat-thread-item ${isActive ? "active" : ""}`}>
              <button type="button" className="chat-thread-main" onClick={() => onSelectThread(thread.id)}>
                <div className="chat-thread-main-icon">
                  <MessageSquare size={16} />
                </div>
                <div className="chat-thread-copy">
                  <div className="chat-thread-name">{thread.title}</div>
                  <div className="chat-thread-meta">
                    {thread.messages.length} {t.messages} · {new Intl.DateTimeFormat(language === "es" ? "es-ES" : "en-US", { month: "short", day: "numeric" }).format(new Date(thread.updatedAt))}
                  </div>
                </div>
              </button>
              <button
                type="button"
                className="chat-thread-delete"
                onClick={() => onDeleteThread(thread.id)}
                title={language === "es" ? "Borrar chat" : "Delete chat"}
              >
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

export function ChatView({ theme, language, t }) {
  const [threads, setThreads] = useState(() => {
    const persistedThreads = safeParse(localStorage.getItem(CHAT_THREADS_KEY), null);
    if (Array.isArray(persistedThreads) && persistedThreads.length > 0) {
      const legacySessionId = localStorage.getItem("koocliChatSessionId") || undefined;
      return persistedThreads.map((thread) => normalizeThread(thread, language, legacySessionId));
    }

    const legacyMessages = safeParse(localStorage.getItem("koocliChatMessages"), null);
    const legacySessionId = localStorage.getItem("koocliChatSessionId") || getRandomId("session");
    if (Array.isArray(legacyMessages) && legacyMessages.length > 0) {
      const normalizedMessages = legacyMessages.map(normalizeMessage);
      return [
        normalizeThread(
          {
            id: getRandomId("thread"),
            sessionId: legacySessionId,
            title: buildThreadTitle(normalizedMessages.find((message) => message.role === "user")?.content || "", language),
            messages: normalizedMessages,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          },
          language,
          legacySessionId,
        ),
      ];
    }

    return [createThread(language)];
  });
  const [activeThreadId, setActiveThreadId] = useState(() => localStorage.getItem(ACTIVE_THREAD_KEY) || null);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [showMobileHistory, setShowMobileHistory] = useState(false);
  const bottomRef = useRef(null);
  const chatHistoryRef = useRef(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const prevMsgCountRef = useRef(0);
  const justSentRef = useRef(false);

  /* ── Scroll-to-bottom button visibility ── */
  const checkScrollPosition = () => {
    const el = chatHistoryRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setShowScrollBtn(!atBottom);
  };

  const scrollToBottom = () => {
    const el = chatHistoryRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  };

  useEffect(() => {
    if (!threads.length) {
      const nextThread = createThread(language);
      setThreads([nextThread]);
      setActiveThreadId(nextThread.id);
    }
  }, [language, threads.length]);

  useEffect(() => {
    if (!activeThreadId && threads[0]) {
      setActiveThreadId(threads[0].id);
    }
  }, [threads, activeThreadId]);

  useEffect(() => {
    localStorage.setItem(CHAT_THREADS_KEY, JSON.stringify(threads));
    if (activeThreadId) {
      localStorage.setItem(ACTIVE_THREAD_KEY, activeThreadId);
    }
  }, [threads, activeThreadId]);

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) || threads[0] || null,
    [threads, activeThreadId]
  );

  /* ── Auto-scroll only after sending a new message ── */
  useEffect(() => {
    const msgCount = activeThread?.messages?.length || 0;
    if (justSentRef.current && msgCount > prevMsgCountRef.current) {
      scrollToBottom();
      justSentRef.current = false;
    }
    prevMsgCountRef.current = msgCount;
  }, [activeThread?.messages, isSending]);

  const colors = useMemo(
    () => ({
      shell: theme === "dark" ? "#0a0a0a" : "#ffffff",
      border: theme === "dark" ? "#2a2a2a" : "#e5e7eb",
      assistant: theme === "dark" ? "#171717" : "#f8fafc",
      user: "#e60012",
      text: theme === "dark" ? "#f5f5f5" : "#111827",
      muted: theme === "dark" ? "#9ca3af" : "#6b7280",
    }),
    [theme]
  );

  const updateThread = (threadId, updater) => {
    setThreads((currentThreads) =>
      currentThreads.map((thread) => {
        if (thread.id !== threadId) return thread;
        const updated = typeof updater === "function" ? updater(thread) : updater;
        return {
          ...thread,
          ...updated,
          updatedAt: Date.now(),
        };
      })
    );
  };

  const createNewThread = () => {
    const nextThread = createThread(language);
    setThreads((currentThreads) => [nextThread, ...currentThreads]);
    setActiveThreadId(nextThread.id);
    setError("");
    setInput("");
  };

  const selectThread = (threadId) => {
    setActiveThreadId(threadId);
    setError("");
    setInput("");
  };

  const deleteThread = (threadId) => {
    setThreads((currentThreads) => {
      const remaining = currentThreads.filter((thread) => thread.id !== threadId);

      if (remaining.length === 0) {
        const replacement = createThread(language);
        setActiveThreadId(replacement.id);
        return [replacement];
      }

      if (activeThreadId === threadId) {
        setActiveThreadId(remaining[0].id);
      }

      return remaining;
    });
    setError("");
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isSending || !activeThread) return;

    const userMessage = {
      id: getRandomId("msg"),
      role: "user",
      content: trimmed,
      createdAt: Date.now(),
    };

    const threadSnapshot = activeThread;
    const userMessageCountBeforeSend = threadSnapshot.messages.filter((message) => message.role === "user").length;
    const startedAt = performance.now();

    updateThread(threadSnapshot.id, (thread) => ({
      messages: [...thread.messages, userMessage],
      title:
        thread.title === (language === "es" ? "Nuevo chat" : "New chat") || userMessageCountBeforeSend === 0
          ? buildThreadTitle(trimmed, language)
          : thread.title,
    }));

    setInput("");
    setError("");
    setIsSending(true);
    justSentRef.current = true;

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
          session_id: threadSnapshot.sessionId,
        }),
      });

      if (!response.ok) {
        let detail = `Backend error (${response.status}).`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch {
          // keep fallback
        }
        throw new Error(detail);
      }

      const data = await response.json();
      const assistantReply = String(data.reply || "No response generated.").trim();
      const durationMs = Math.max(0, Math.round(performance.now() - startedAt));

      updateThread(threadSnapshot.id, (thread) => ({
        messages: [
          ...thread.messages,
          {
            id: getRandomId("msg"),
            role: "assistant",
            content: assistantReply,
            createdAt: Date.now(),
            durationMs,
          },
        ],
      }));
    } catch (chatError) {
      setError(chatError.message || "Chat request failed.");
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    sendMessage();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <section className="view-shell chat-shell">
      <div className="header chat-header" style={{ position: "relative" }}>
        <h1 className="app-title">{t.chatTitle}</h1>
        <p className="app-subtitle">{t.chatSubtitle}</p>
        
        {/* Solo visible en mobile via CSS */}
        <button 
          className="mobile-history-toggle"
          onClick={() => setShowMobileHistory(!showMobileHistory)}
          aria-label="Toggle history"
        >
          <MessageSquare size={18} />
          {showMobileHistory ? (language === "es" ? "Ocultar historial" : "Hide history") : (language === "es" ? "Ver historial" : "View history")}
        </button>
      </div>

      <div className="chat-workbench">
        <ChatThreadList
          threads={threads}
          activeThreadId={activeThreadId}
          onSelectThread={(id) => {
            selectThread(id);
            setShowMobileHistory(false);
          }}
          onCreateThread={() => {
            createNewThread();
            setShowMobileHistory(false);
          }}
          onDeleteThread={deleteThread}
          language={language}
          t={t}
          isMobileVisible={showMobileHistory}
        />

        <div className="chat-panel" style={{ backgroundColor: colors.shell, borderColor: colors.border }}>
          <div className="chat-history" ref={chatHistoryRef} onScroll={checkScrollPosition}>
            {activeThread?.messages.map((message) => (
              <div key={message.id} className={`chat-row ${message.role}`}>
                <div
                  className={`chat-bubble ${message.role}`}
                  style={{
                    borderColor: colors.border,
                    color: message.role === "user" ? "#fff" : colors.text,
                    backgroundColor: message.role === "user" ? colors.user : colors.assistant,
                  }}
                >
                  {message.role === "assistant" ? (
                    <AssistantMessage content={message.content} durationMs={message.durationMs} language={language} />
                  ) : (
                    <div className="chat-user-text">{message.content}</div>
                  )}
                </div>
              </div>
            ))}

            {isSending && (
              <div className="chat-row assistant">
                <div className="chat-bubble assistant typing" style={{ borderColor: colors.border }}>
                  <span className="typing-dots">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {showScrollBtn && (
            <button
              className="scroll-to-bottom-btn"
              onClick={scrollToBottom}
              aria-label={language === "es" ? "Ir al final" : "Scroll to bottom"}
              type="button"
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 4v12M5 11l5 5 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          )}

          <form className="chat-composer" onSubmit={handleSubmit}>
            <textarea
              className="chat-input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={language === "es" ? "Escribe tu mensaje..." : "Type your message..."}
              rows={2}
              disabled={isSending}
            />
            <button className="chat-send-button" type="submit" disabled={isSending || !input.trim()}>
              <Send size={20} strokeWidth={2.5} />
              {t.send}
            </button>
          </form>

          {error && <div className="chat-error">{error}</div>}
          <div className="chat-footer-note" style={{ color: colors.muted }}>
            {t.session} {activeThread?.sessionId?.slice(0, 8) || "----"} · {t.langGraphMemory}
          </div>
        </div>
      </div>
    </section>
  );
}