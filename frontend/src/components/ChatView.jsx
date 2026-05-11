import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { Sparkles, MessageSquare } from "lucide-react";
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
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ChatInput } from "./ChatInput";
import { ChatBubble, TypingIndicator, ChatEmptyState } from "./ChatComponents";
import { ScrollToBottom } from "./ScrollToBottom";
import { ScrollArea } from "./ui/ScrollArea";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const getRandomId = (prefix) => {
  const id = globalThis.crypto?.randomUUID?.() || `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${id}`;
};

const buildThreadTitle = (text, language) => {
  const cleanText = text.replace(/\s+/g, " ").trim();
  if (!cleanText) return language === "es" ? "Nuevo chat" : "New chat";
  const short = cleanText.split(" ").slice(0, 6).join(" ");
  return short.length > 42 ? `${short.slice(0, 39)}...` : short;
};

// Parser functions
const isTableSeparator = (line) => {
  const cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
};

const splitTableRow = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());

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
        while (reportIndex < reportLines.length && reportLines[reportIndex].trim() && !reportLines[reportIndex].includes("|") && !/^#{1,4}\s+/.test(reportLines[reportIndex])) {
          paragraphLines.push(reportLines[reportIndex]);
          reportIndex += 1;
        }
        blocks.push({ type: "text", text: paragraphLines.join("\n") });
      }
      return blocks;
    }
  }

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
  const normalized = String(value ?? "").replace(/[$%\s,]/g, "").replace(/[^\d.-]/g, "");
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
    return { kind: "single", data, series: [{ key: "value", label: column.label }] };
  }
  const seriesColumns = numericColumns.slice(0, 3);
  const data = table.rows.map((row) => {
    const item = { name: String(row[0] || labelHeader).slice(0, 28) };
    seriesColumns.forEach((column) => {
      item[column.key] = extractNumber(row[column.index]) ?? 0;
    });
    return item;
  });
  return { kind: "grouped", data, series: seriesColumns.map((column) => ({ key: column.key, label: column.label })) };
};

const formatCurrency = (value) => {
  if (!Number.isFinite(value)) return value;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
};

function DataTable({ table }) {
  return (
    <motion.div
      className="table-wrapper"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <table className="markdown-table">
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
    </motion.div>
  );
}

function ChartCard({ model, title }) {
  if (!model) return null;
  const colors = ["#C7000B", "#2563eb", "#16a34a"];
  const topItem = model.data.reduce(
    (best, item) => {
      const total =
        model.kind === "single"
          ? item.value
          : model.series.reduce((sum, series) => sum + (Number(item[series.key]) || 0), 0);
      if (total > best.total) return { label: item.name, total };
      return best;
    },
    { label: "", total: 0 }
  );

  return (
    <motion.div
      className="chart-container"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <div className="chart-title">
        <Sparkles size={16} strokeWidth={1.5} className="inline mr-2" />
        {title}
      </div>
      <div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={model.data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} height={60} />
            <YAxis tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value)} />
            <Tooltip
              formatter={(value) => [formatCurrency(Number(value)), ""]}
              contentStyle={{ borderRadius: 12, borderColor: "#e5e5e5", fontSize: "0.82rem" }}
            />
            <Legend />
            {model.kind === "single" ? (
              <Bar dataKey="value" name={model.series[0].label} fill="#C7000B" radius={[6, 6, 0, 0]} />
            ) : (
              model.series.map((series, index) => (
                <Bar key={series.key} dataKey={series.key} name={series.label} fill={colors[index % colors.length]} radius={[6, 6, 0, 0]} />
              ))
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

function AssistantMessage({ content, durationMs, language }) {
  const blocks = useMemo(() => parseAssistantContent(content), [content]);
  const reportHeaderBlock = blocks.find((block) => block.type === "report-header");
  const tableBlocks = blocks.filter((block) => block.type === "table");
  const textBlocks = blocks.filter((block) => block.type !== "table" && block.type !== "report-header");
  const chartModel = useMemo(() => buildChartModel(tableBlocks[0]?.table), [tableBlocks]);
  const hasCostLanguage = /gasto|cost|billing|factur|costos|usd|month|mayo|abril|statistics|resumen/i.test(content);
  const chartTitle = language === "es" ? "Análisis de costos" : "Cost analysis";
  const durationLabel = Number.isFinite(durationMs)
    ? language === "es"
      ? `Respuesta en ${durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(1)} s`}`
      : `Response in ${durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(1)} s`}`
    : null;
  const textContent = textBlocks.map((block) => block.text).join("\n\n");

  return (
    <div className="space-y-3">
      {textContent && <MarkdownRenderer content={textContent} />}
      {tableBlocks.map((block, index) => (
        <div key={`table-${index}`}>
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-huawei-gray-600 dark:text-huawei-gray-400">
            <MessageSquare size={14} />
            {language === "es" ? "Tabla estructurada" : "Structured table"}
          </div>
          <DataTable table={block.table} />
        </div>
      ))}
      {chartModel && hasCostLanguage && <ChartCard model={chartModel} title={chartTitle} />}
      {durationLabel && (
        <motion.div
          className="text-xs text-huawei-gray-500 dark:text-huawei-gray-400 pt-2 border-t border-huawei-gray-200 dark:border-huawei-gray-700"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          ⚡ {durationLabel}
        </motion.div>
      )}
    </div>
  );
}

export function ChatView({ theme, language, t, threads, setThreads, activeThreadId, setActiveThreadId }) {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const chatHistoryRef = useRef(null);
  const prevMsgCountRef = useRef(0);
  const justSentRef = useRef(false);

  const activeThread = useMemo(
    () => threads.find((thread) => thread.id === activeThreadId) || threads[0] || null,
    [threads, activeThreadId]
  );

  const checkScrollPosition = () => {
    const el = chatHistoryRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setShowScrollBtn(!atBottom);
  };

  const scrollToBottom = () => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTo({ top: chatHistoryRef.current.scrollHeight, behavior: "smooth" });
    }
  };

  useEffect(() => {
    const msgCount = activeThread?.messages?.length || 0;
    if (justSentRef.current && msgCount > prevMsgCountRef.current) {
      scrollToBottom();
      justSentRef.current = false;
    }
    prevMsgCountRef.current = msgCount;
  }, [activeThread?.messages, isSending]);

  const updateThread = (threadId, updater) => {
    setThreads((currentThreads) =>
      currentThreads.map((thread) => {
        if (thread.id !== threadId) return thread;
        const updated = typeof updater === "function" ? updater(thread) : updater;
        return { ...thread, ...updated, updatedAt: Date.now() };
      })
    );
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isSending || !activeThread) return;

    const userMessage = { id: getRandomId("msg"), role: "user", content: trimmed, createdAt: Date.now() };
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, session_id: threadSnapshot.sessionId }),
      });

      if (!response.ok) {
        let detail = `Backend error (${response.status}).`;
        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch {}
        throw new Error(detail);
      }

      const data = await response.json();
      const assistantReply = String(data.reply || "No response generated.").trim();
      const durationMs = Math.max(0, Math.round(performance.now() - startedAt));

      updateThread(threadSnapshot.id, (thread) => ({
        messages: [...thread.messages, { id: getRandomId("msg"), role: "assistant", content: assistantReply, createdAt: Date.now(), durationMs }],
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

  const hasMessages = activeThread?.messages && activeThread.messages.length > 0;

  return (
    <motion.section
      className="view-shell chat-shell"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="chat-workbench">
        <div className="chat-panel">
          {!hasMessages && !isSending ? (
            <ChatEmptyState
              icon={Sparkles}
              title={t.chatTitle}
              subtitle={
                language === "es"
                  ? "Interactúa con tus servicios de Huawei Cloud a través de chat."
                  : "Interact with your Huawei Cloud services through chat."
              }
            />
          ) : (
            <>
              <ScrollArea className="flex-1">
                <div className="chat-history" ref={chatHistoryRef} onScroll={checkScrollPosition}>
                  <AnimatePresence>
                    {activeThread?.messages.map((message, index) => (
                      <motion.div
                        key={message.id}
                        className={`chat-row ${message.role}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05, duration: 0.3 }}
                      >
                        <ChatBubble
                          role={message.role}
                          content={
                            message.role === "assistant" ? (
                              <AssistantMessage content={message.content} durationMs={message.durationMs} language={language} />
                            ) : (
                              <div>{message.content}</div>
                            )
                          }
                        />
                      </motion.div>
                    ))}

                    {isSending && (
                      <motion.div key="typing" className="chat-row assistant">
                        <TypingIndicator />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </ScrollArea>

              {showScrollBtn && hasMessages && (
                <ScrollToBottom onClick={scrollToBottom} />
              )}
            </>
          )}

          <ChatInput
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onSubmit={handleSubmit}
            isLoading={isSending}
            language={language}
            placeholder={language === "es" ? "Escribe tu mensaje..." : "Type your message..."}
          />

          {error && (
            <motion.div
              className="error-box mx-6 mb-4"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <p className="error-text">{error}</p>
            </motion.div>
          )}
        </div>
      </div>
    </motion.section>
  );
}
