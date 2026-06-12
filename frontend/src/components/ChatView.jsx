import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  TbSparkles,
  TbMessage2,
  TbActivity,
  TbCurrencyDollar,
  TbServer,
  TbGlobe,
  TbShield,
  TbDatabase,
  TbArchive,
  TbKey,
  TbLayersSubtract,
  TbCpu,
} from "react-icons/tb";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
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
import { sendChatMessage } from "../services/api";

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

const CHART_COLORS = [
  "#C7000B", "#2563eb", "#16a34a", "#f59e0b", "#8b5cf6",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1",
];

const KPI_ICON_MAP = [
  { pattern: /recurso|resource|total|instance|servidor|server/i, Icon: TbLayersSubtract },
  { pattern: /regi[oó]n|region|zona|zone|location/i, Icon: TbGlobe },
  { pattern: /cost|gasto|factur|billing|usd|precio|price/i, Icon: TbCurrencyDollar },
  { pattern: /ecs|compute|servidor|server/i, Icon: TbServer },
  { pattern: /vpc|red|network|subnet/i, Icon: TbActivity },
  { pattern: /security|segurid|firewall|sg-/i, Icon: TbShield },
  { pattern: /rds|database|base de datos|db/i, Icon: TbDatabase },
  { pattern: /obs|storage|almacen|bucket|object/i, Icon: TbArchive },
  { pattern: /key|clave|iam|credential/i, Icon: TbKey },
  { pattern: /image|imagen|ims|ami/i, Icon: TbCpu },
];

const extractNumber = (value) => {
  const normalized = String(value ?? "").replace(/[$%\s,]/g, "").replace(/[^\d.-]/g, "");
  if (!normalized || normalized === "-" || normalized === "." || normalized === "-.") return null;
  const number = Number(normalized);
  return Number.isFinite(number) ? number : null;
};

const extractKPIs = (content) => {
  const kpis = [];
  const patterns = [
    /(\d+)\s+recurso[s]?/gi,
    /(\d+)\s+resource[s]?/gi,
    /(\d+)\s+regi[oó]n(?:es)?/gi,
    /(\d+)\s+region[s]?/gi,
    /(\d+)\s+imagen(?:es)?/gi,
    /(\d+)\s+image[s]?/gi,
    /(\d+)\s+(?:grupo[s]?\s+de\s+)?seguridad/gi,
    /(\d+)\s+security\s+group[s]?/gi,
    /(\d+)\s+VPC[s]?/gi,
    /(\d+)\s+vpc[s]?/gi,
    /(\d+)\s+clave[s]?\s+de\s+acceso/gi,
    /(\d+)\s+access\s+key[s]?/gi,
    /(\d+)\s+servicio[s]?/gi,
    /(\d+)\s+service[s]?/gi,
    /(\d+)\s+instance[s]?/gi,
    /(?:costo|cost|gasto|total)\s*(?:total)?[:\s]*\$?([\d,.]+)/gi,
    /USD\s*([\d,.]+)/gi,
    /(\d+)\s+ECS/gi,
    /(\d+)\s+RDS/gi,
    /(\d+)\s+OBS/gi,
    /(\d+)\s+ELB/gi,
    /(\d+)\s+NAT/gi,
    /(\d+)\s+EIP/gi,
  ];

  const labelMap = {
    "recurso": { es: "Recursos", en: "Resources" },
    "resource": { es: "Recursos", en: "Resources" },
    "regi": { es: "Regiones", en: "Regions" },
    "region": { es: "Regiones", en: "Regions" },
    "imagen": { es: "Imágenes", en: "Images" },
    "image": { es: "Imágenes", en: "Images" },
    "seguridad": { es: "Grupos de Seguridad", en: "Security Groups" },
    "security": { es: "Grupos de Seguridad", en: "Security Groups" },
    "vpc": { es: "VPCs", en: "VPCs" },
    "clave": { es: "Claves de Acceso", en: "Access Keys" },
    "access": { es: "Claves de Acceso", en: "Access Keys" },
    "servicio": { es: "Servicios", en: "Services" },
    "service": { es: "Servicios", en: "Services" },
    "instance": { es: "Instancias", en: "Instances" },
    "costo": { es: "Costo Total", en: "Total Cost" },
    "cost": { es: "Costo Total", en: "Total Cost" },
    "gasto": { es: "Gasto Total", en: "Total Cost" },
    "usd": { es: "Costo USD", en: "Cost USD" },
    "ecs": { es: "ECS", en: "ECS" },
    "rds": { es: "RDS", en: "RDS" },
    "obs": { es: "OBS", en: "OBS" },
    "elb": { es: "ELB", en: "ELB" },
    "nat": { es: "NAT", en: "NAT" },
    "eip": { es: "EIP", en: "EIP" },
  };

  const seen = new Set();
  for (const pattern of patterns) {
    let match;
    const regex = new RegExp(pattern.source, pattern.flags);
    while ((match = regex.exec(content)) !== null) {
      const value = match[1].replace(/,/g, "");
      const num = Number(value);
      if (!Number.isFinite(num) || num === 0) continue;
      const matchText = match[0].toLowerCase();
      let label = { es: matchText, en: matchText };
      for (const [key, lbl] of Object.entries(labelMap)) {
        if (matchText.includes(key)) {
          label = lbl;
          break;
        }
      }
      const key = label.en.toLowerCase().replace(/\s+/g, "-");
      if (seen.has(key)) continue;
      seen.add(key);
      kpis.push({ value: num, label, key, isCurrency: /usd|\$|cost|gasto|factur/i.test(matchText) });
    }
  }
  return kpis.slice(0, 6);
};

const detectChartType = (table) => {
  if (!table?.headers?.length || !table?.rows?.length) return null;
  const numericColumns = [];
  table.headers.slice(1).forEach((header, offset) => {
    const index = offset + 1;
    const values = table.rows.map((row) => extractNumber(row[index])).filter((v) => v !== null);
    if (values.length > 0) {
      numericColumns.push({ index, key: `series-${offset}`, label: header, values });
    }
  });
  if (numericColumns.length === 0) return null;
  const rowCount = table.rows.length;
  const hasSingleNumeric = numericColumns.length === 1;
  const isDistribution = hasSingleNumeric && rowCount >= 2 && rowCount <= 10;
  const firstHeader = (table.headers[0] || "").toLowerCase();
  const isCategorical = /tipo|type|categor[ií]a|category|servicio|service|recurso|resource|regi[oó]n|region|estado|status|nombre|name/i.test(firstHeader);
  const isTimeSeries = /mes|month|fecha|date|a[oñ]|year|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec/i.test(firstHeader) ||
    table.rows.every((row) => /(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}[-\/]\d{2}|\d{2}[-\/]\d{4})/i.test(String(row[0])));
  if (isDistribution && isCategorical && !isTimeSeries) return "donut";
  if (isTimeSeries) return "bar";
  if (isDistribution) return "donut";
  return "bar";
};

const buildChartModel = (table, chartType) => {
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

  if (chartType === "donut") {
    const column = numericColumns[0];
    const data = table.rows
      .map((row) => ({
        name: String(row[0] || labelHeader).slice(0, 28),
        value: Math.abs(extractNumber(row[column.index]) ?? 0),
      }))
      .filter((row) => row.name.trim().length > 0 && row.value > 0);
    const total = data.reduce((sum, d) => sum + d.value, 0);
    return {
      kind: "donut",
      data: data.map((d) => ({ ...d, percent: total > 0 ? ((d.value / total) * 100).toFixed(1) : 0 })),
      total,
      series: [{ key: "value", label: column.label }],
    };
  }

  if (numericColumns.length === 1) {
    const column = numericColumns[0];
    const data = table.rows
      .map((row) => ({
        name: String(row[0] || labelHeader).slice(0, 28),
        value: extractNumber(row[column.index]) ?? 0,
      }))
      .filter((row) => row.name.trim().length > 0)
      .sort((left, right) => right.value - left.value)
      .slice(0, 12);
    return { kind: "single", data, series: [{ key: "value", label: column.label }] };
  }
  const seriesColumns = numericColumns.slice(0, 12);
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

const formatValue = (value, isCurrency) => {
  if (!Number.isFinite(value)) return String(value);
  if (isCurrency) return formatCurrency(value);
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return String(value);
};

function KPICards({ kpis, language }) {
  if (!kpis.length) return null;
  return (
    <div className="kpi-grid">
      {kpis.map((kpi) => {
        const matchedIcon = KPI_ICON_MAP.find(({ pattern }) => pattern.test(kpi.key) || pattern.test(kpi.label.en) || pattern.test(kpi.label.es));
        const Icon = matchedIcon?.Icon || TbActivity;
        const label = language === "es" ? kpi.label.es : kpi.label.en;
        return (
          <motion.div
            key={kpi.key}
            className="kpi-card"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="kpi-icon-wrap">
              <Icon size={16} strokeWidth={1.8} />
            </div>
            <div className="kpi-content">
              <span className="kpi-value">{kpi.isCurrency ? formatCurrency(kpi.value) : kpi.value}</span>
              <span className="kpi-label">{label}</span>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

function DataTable({ table }) {
  return (
    <motion.div
      className="table-wrapper"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <div className="table-scroll">
        <table className="markdown-table">
          <thead>
            <tr>
              {table.headers.map((header, index) => (
                <th key={`${header}-${index}`}><MarkdownRenderer content={header} /></th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`cell-${rowIndex}-${cellIndex}`}><MarkdownRenderer content={cell} /></td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

function DonutChartCard({ model, title }) {
  if (!model || model.kind !== "donut" || !model.data.length) return null;
  return (
    <motion.div
      className="chart-container"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <div className="chart-title">
        <TbSparkles size={16} className="inline mr-2" />
        {title}
      </div>
      <div className="donut-layout">
        <div className="donut-chart-wrap">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={model.data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
                dataKey="value"
                nameKey="name"
                stroke="none"
              >
                {model.data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value, name) => [formatValue(value, false), name]}
                contentStyle={{ borderRadius: 12, borderColor: "var(--border-light)", fontSize: "0.82rem", background: "var(--surface)" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="donut-legend">
          {model.data.map((item, index) => (
            <div key={`legend-${index}`} className="donut-legend-item">
              <span className="donut-legend-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
              <span className="donut-legend-name">{item.name}</span>
              <span className="donut-legend-value">{formatValue(item.value, false)}</span>
              <span className="donut-legend-pct">{item.percent}%</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function BarChartCard({ model, title, isCostData }) {
  if (!model || model.kind === "donut") return null;
  const colors = ["#C7000B", "#2563eb", "#16a34a", "#f59e0b", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1", "#14b8a6", "#e11d48"];
  return (
    <motion.div
      className="chart-container"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <div className="chart-title">
        <TbSparkles size={16} className="inline mr-2" />
        {title}
      </div>
      <div className="bar-chart-wrap">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={model.data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
            <XAxis dataKey="name" tick={false} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={(value) => (value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value)} />
            <Tooltip
              formatter={(value) => [isCostData ? formatCurrency(Number(value)) : formatValue(Number(value), false), ""]}
              contentStyle={{ borderRadius: 12, borderColor: "var(--border-light)", fontSize: "0.82rem", background: "var(--surface)" }}
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
  const kpis = useMemo(() => extractKPIs(content), [content]);
  const isCostContent = /gasto|cost|billing|factur|costos|\(USD\)|month|mayo|abril|statistics|resumen/i.test(content);
  const isResourceContent = /recurso|resource|desplegado|deployed|servicio|service|instance|imagen|image|vpc|security|segurid|clave|key|rds|obs|ecs|elb/i.test(content);
  const showVisuals = isCostContent || isResourceContent || tableBlocks.length > 0;

  const isBillingTable = useMemo(() => {
    return tableBlocks.map((block) => {
      const headers = block.table?.headers || [];
      return headers.some((h) => /\(USD\)/i.test(h));
    });
  }, [tableBlocks]);

  const chartModels = useMemo(() => {
    if (!showVisuals) return [];
    return tableBlocks.map((block, idx) => {
      if (isBillingTable[idx]) {
        const filteredTable = {
          headers: block.table.headers,
          rows: block.table.rows.filter((row) => !/^TOTAL$/i.test(String(row[0]).trim())),
        };
        const model = buildChartModel(filteredTable, "bar");
        return { chartType: "bar", model };
      }
      const chartType = detectChartType(block.table);
      if (!chartType) return null;
      return { chartType, model: buildChartModel(block.table, chartType) };
    });
  }, [tableBlocks, showVisuals, isBillingTable]);

  const getChartTitle = (chartType, index) => {
    if (isCostContent) {
      return language === "es" ? "Análisis de costos" : "Cost analysis";
    }
    if (chartType === "donut") {
      return language === "es" ? "Distribución" : "Distribution";
    }
    return language === "es" ? "Visualización de datos" : "Data visualization";
  };

  const durationLabel = Number.isFinite(durationMs)
    ? language === "es"
      ? `Respuesta en ${durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(1)} s`}`
      : `Response in ${durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(1)} s`}`
    : null;
  const textContent = textBlocks
    .map((block) => block.text)
    .filter((text) => !/^\*\*.+?\*\*\s*\(\d+\)\s*$/.test(text.trim()))
    .join("\n\n");

  const tableTitles = useMemo(() => {
    const titles = [];
    const lines = content.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const boldMatch = line.match(/^\*\*(.+?)\*\*\s*\((\d+)\)/);
      if (boldMatch) {
        let tableStart = i + 1;
        while (tableStart < lines.length && !lines[tableStart].trim()) tableStart++;
        if (tableStart < lines.length && lines[tableStart].includes("|")) {
          titles.push(boldMatch[1]);
        }
      }
    }
    return titles;
  }, [content]);

  const _MONTH_NAMES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  const _MONTH_NAMES_EN = ["January","February","March","April","May","June","July","August","September","October","November","December"];

  const _formatMonthLabel = (monthStr) => {
    const parts = monthStr.split("-");
    if (parts.length !== 2) return monthStr;
    const year = parts[0];
    const monthNum = parseInt(parts[1], 10);
    if (monthNum < 1 || monthNum > 12) return monthStr;
    const names = language === "es" ? _MONTH_NAMES_ES : _MONTH_NAMES_EN;
    return `${names[monthNum - 1]}-${year}`;
  };

  const billingTableTitle = useMemo(() => {
    if (!isCostContent) return null;
    const usdHeaders = tableBlocks.find((block) =>
      (block.table?.headers || []).some((h) => /\(USD\)/i.test(h))
    );
    if (!usdHeaders) return null;
    const months = (usdHeaders.table.headers || [])
      .filter((h) => /\(USD\)/i.test(h))
      .map((h) => h.replace(/\s*\(USD\)/, "").trim());
    if (months.length === 0) return null;
    const labeled = months.map(_formatMonthLabel);
    if (months.length === 1) {
      return language === "es" ? `Costos ${labeled[0]}` : `Costs ${labeled[0]}`;
    }
    return language === "es" ? `Comparativa ${labeled.join(" vs ")}` : `Comparison ${labeled.join(" vs ")}`;
  }, [content, isCostContent, tableBlocks, language]);

  return (
    <div className="space-y-3">
      {kpis.length > 0 && <KPICards kpis={kpis} language={language} />}
      {textContent && <MarkdownRenderer content={textContent} />}
      {tableBlocks.map((block, index) => (
        !isBillingTable[index] && (
          <div key={`table-${index}`}>
            {tableTitles[index] ? (
              <div className="resource-table-title">{tableTitles[index]}</div>
            ) : null}
            <DataTable table={block.table} />
          </div>
        )
      ))}
      {chartModels.map((cm, index) => {
        if (!cm?.model) return null;
        const title = isBillingTable[index] && billingTableTitle
          ? billingTableTitle
          : getChartTitle(cm.chartType, index);
        if (cm.chartType === "donut") {
          return <DonutChartCard key={`donut-${index}`} model={cm.model} title={title} />;
        }
        return <BarChartCard key={`bar-${index}`} model={cm.model} title={title} isCostData={isCostContent} />;
      })}
      {durationLabel && (
        <motion.div
          className="text-[10px] text-huawei-gray-500 dark:text-huawei-gray-400 pt-2 border-t border-huawei-gray-200 dark:border-huawei-gray-700"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {durationLabel}
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
  const [currentExampleIndex, setCurrentExampleIndex] = useState(0);
  const chatHistoryRef = useRef(null);
  const prevMsgCountRef = useRef(0);
  const justSentRef = useRef(false);
  const exampleCycleRef = useRef(null);

  const examplePrompts = [
    {
      en: "Deploy an ECS with the name ecs-web",
      es: "Despliega una ECS llamada ecs-web",
    },
    {
      en: "Show me what services I have deployed on Huawei Cloud",
      es: "Muéstrame qué servicios tengo desplegados en este momento",
    },
    {
      en: "Deploy a RDS with MySQL and password Huawei@123",
      es: "Despliega una RDS con MySQL y contraseña Huawei@123",
    },
  ];

  const currentExample = examplePrompts[currentExampleIndex]?.[language] || examplePrompts[0]?.[language];

  // Cycle through examples
  useEffect(() => {
    if (input.trim() !== "") return;
    
    exampleCycleRef.current = setInterval(() => {
      setCurrentExampleIndex((prev) => (prev + 1) % examplePrompts.length);
    }, 6000); // Change every 6 seconds (typing + pause + delete)

    return () => clearInterval(exampleCycleRef.current);
  }, [input, examplePrompts.length]);

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
      const data = await sendChatMessage(trimmed, threadSnapshot.sessionId);
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
  const messageCount = activeThread?.messages?.length || 0;
  const fewMessages = messageCount > 0 && messageCount < 3;

  return (
    <motion.section
      className="view-shell chat-shell"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="chat-workbench">
        <div className={`chat-panel ${!hasMessages ? "chat-panel-empty" : ""}`}>
          {!hasMessages && !isSending ? (
            <ChatEmptyState
              icon={TbSparkles}
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
                <div
                  className={`chat-history ${fewMessages ? "chat-history-few" : ""}`}
                  ref={chatHistoryRef}
                  onScroll={checkScrollPosition}
                >
                  <AnimatePresence mode="popLayout">
                    {activeThread?.messages.map((message, index) => (
                      <motion.div
                        key={message.id}
                        className={`chat-row ${message.role}`}
                        initial={{ opacity: 0, y: 16, scale: 0.98 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{
                          duration: 0.4,
                          ease: [0.25, 0.46, 0.45, 0.94],
                          delay: index * 0.03,
                        }}
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
                      <motion.div
                        key="typing"
                        className="chat-row assistant"
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                      >
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
            placeholder={language === "es" ? "Escribe tu mensaje..." : "Message Huawei Cloud Assistant..."}
            showTypingPlaceholder={!hasMessages && !isSending}
            typingText={currentExample}
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
