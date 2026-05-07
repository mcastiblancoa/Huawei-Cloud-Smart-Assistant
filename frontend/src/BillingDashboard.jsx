import { useMemo } from "react";
import { 
  PieChart, Pie, Cell,
  Tooltip, Legend, ResponsiveContainer
} from "recharts";
import {
  DollarSign,
  Calendar,
} from "lucide-react";
import "./ResourceDashboard.css";

const COLORS = ["#e60012", "#ff3333", "#cc0010", "#ff6666", "#b3000e", "#ff9999", "#99000c", "#ffcccc"];

const translations = {
  es: {
    title: "Resumen de Facturación",
    subtitle: "Gasto mensual de Huawei Cloud",
    totalSpend: "Gasto Total",
    currency: "Moneda",
    month: "Mes",
    services: "Servicios",
    amount: "Monto",
    loadingBilling: "Cargando facturación...",
    noBillingData: "No hay datos de facturación disponibles para este período.",
    spendingBreakdown: "Desglose de Gasto por Servicio",
    spendingDistribution: "Distribución de Gasto",
    serviceName: "Servicio",
    cost: "Costo",
  },
  en: {
    title: "Billing Summary",
    subtitle: "Huawei Cloud Monthly Spend",
    totalSpend: "Total Spend",
    currency: "Currency",
    month: "Month",
    services: "Services",
    amount: "Amount",
    loadingBilling: "Loading billing data...",
    noBillingData: "No billing data available for this period.",
    spendingBreakdown: "Spending Breakdown by Service",
    spendingDistribution: "Spending Distribution",
    serviceName: "Service",
    cost: "Cost",
  },
};

export function BillingDashboard({ intentClassification, billingResponse, theme, language = "es" }) {
  const t = translations[language] || translations.es;
  
  // Color scheme based on theme
  const colors = {
    text: theme === "dark" ? "#f5f5f5" : "#1a1a1a",
    textSecondary: theme === "dark" ? "#b0b0b0" : "#6b7280",
    border: theme === "dark" ? "#333333" : "#e5e7eb",
    bg: theme === "dark" ? "#0a0a0a" : "#ffffff",
    bgSecondary: theme === "dark" ? "#1a1a1a" : "#f9fafb",
    bgTertiary: theme === "dark" ? "#0f1419" : "#fafbfc",
    primary: "white",
    chart: theme === "dark" ? "#88ccee" : "#1a1a1a",
  };

  if (!intentClassification || !intentClassification.should_call_bss) {
    return null;
  }

  if (!billingResponse) {
    return (
      <div className="dash-container">
        <div className="dash-loading">{t.loadingBilling}</div>
      </div>
    );
  }

  if (billingResponse.error) {
    return (
      <div className="dash-container">
        <div className="dash-error">{billingResponse.error}</div>
      </div>
    );
  }

  const { total, currency, month, services, natural_response } = billingResponse;

  if (!services || services.length === 0) {
    return (
      <div className="dash-container">
        <div className="dash-empty">
          <p>{t.noBillingData}</p>
        </div>
      </div>
    );
  }

  const chartData = services.map((s, index) => ({
    name: s.name,
    amount: s.amount,
    fill: COLORS[index % COLORS.length]
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="shadcn-tooltip" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="tooltip-color-indicator" style={{ backgroundColor: payload[0].payload.fill }}></div>
          <span className="tooltip-label">{payload[0].name}</span>
          <span className="tooltip-value">{payload[0].value} {currency}</span>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="dash-container">
      {/* Header */}
      <div className="dash-header">
        <div className="dash-header-content">
          <h2 className="dash-title">{t.title}</h2>
          <p className="dash-subtitle">{t.subtitle}</p>
          {natural_response && (
            <p className="dash-subtitle" style={{ marginTop: '8px', fontStyle: 'italic', color: colors.text }}>
              "{natural_response}"
            </p>
          )}
        </div>
      </div>

      {/* KPI Row */}
      <div className="dash-kpi-row">
        <div className="kpi-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="kpi-icon total">
            <DollarSign size={20} strokeWidth={1.5} color={colors.primary} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label" style={{ color: colors.textSecondary }}>{t.totalSpend}</span>
            <span className="kpi-value">{total} <span style={{ fontSize: '0.5em', color: colors.textSecondary }}>{currency}</span></span>
          </div>
        </div>

        <div className="kpi-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="kpi-icon types">
            <Calendar size={20} strokeWidth={1.5} color={colors.primary} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label" style={{ color: colors.textSecondary }}>{t.month}</span>
            <span className="kpi-value">{month}</span>
          </div>
        </div>
      </div>

      {/* Charts & Table Row */}
      <div className="dash-charts-row">
        
        {/* Pie Chart */}
        <div className="dash-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border }}>
          <div className="card-header">
            <h3 className="card-title" style={{ color: colors.text }}>{t.spendingDistribution}</h3>
          </div>
          <div className="card-content" style={{ height: "300px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={0}
                  outerRadius={80}
                  paddingAngle={0}
                  dataKey="amount"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Services List Table */}
        <div className="dash-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border }}>
          <div className="card-header">
            <h3 className="card-title" style={{ color: colors.text }}>{t.services}</h3>
        </div>
        <div className="card-content" style={{ padding: 0 }}>
          <div className="dash-table-wrapper">
            <table className="dash-table">
              <thead>
                <tr>
                  <th style={{ color: colors.textSecondary, borderColor: colors.border }}>{t.serviceName}</th>
                  <th style={{ color: colors.textSecondary, borderColor: colors.border, textAlign: 'right' }}>{t.amount}</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service, index) => (
                  <tr key={index} className="dash-tr">
                    <td style={{ color: colors.text, borderColor: colors.border }}>
                      <div className="table-cell-content">
                        <span className="font-medium">{service.name}</span>
                      </div>
                    </td>
                    <td style={{ color: colors.text, borderColor: colors.border, textAlign: 'right' }}>
                      {service.amount} <span style={{ fontSize: '0.8em', color: colors.textSecondary }}>{currency}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}