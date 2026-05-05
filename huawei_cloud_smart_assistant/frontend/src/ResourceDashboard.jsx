import { useMemo } from "react";
import { 
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";
import {
  Package,
  Server,
  Database,
  HardDrive,
  Activity,
  Globe,
  LayoutGrid,
  TrendingUp,
} from "lucide-react";
import "./ResourceDashboard.css";

const COLORS = ["#e60012", "#ff3333", "#cc0010", "#ff6666", "#b3000e", "#ff9999", "#99000c", "#ffcccc"];

const getResourceIcon = (type) => {
  const iconProps = { size: 18, strokeWidth: 1.5 };
  const iconMap = {
    cloudservers: <Server {...iconProps} />,
    rds: <Database {...iconProps} />,
    obs: <HardDrive {...iconProps} />,
    sis: <Activity {...iconProps} />,
    agents: <Activity {...iconProps} />,
    ecs: <Activity {...iconProps} />,
    buckets: <HardDrive {...iconProps} />,
    securitygroups: <LayoutGrid {...iconProps} />,
    vpcs: <Globe {...iconProps} />,
  };
  return iconMap[type?.toLowerCase()] || <Package {...iconProps} />;
};

const formatTypeName = (type) => {
  if (type?.toLowerCase() === 'agents') return 'ecs';
  return type;
};

const translations = {
  es: {
    title: "Recursos en la nube",
    subtitle: "Inventario de Huawei Cloud",
    totalLabel: "Total",
    typesLabel: "Tipos",
    regionsLabel: "Regiones",
    typeDistribution: "Distribución por tipo",
    regionDistribution: "Distribución por región",
    resourceTypes: "Tipos de recurso",
    regions: "Regiones",
    detailedList: "Listado detallado",
    resources: "recursos",
    name: "Nombre",
    type: "Tipo",
    region: "Región",
    provider: "Proveedor",
    created: "Creado",
    showing: "Mostrando",
    of: "de",
    loadingResources: "Cargando recursos...",
    noResourcesAvailable: "No hay recursos con información de estado disponible.",
  },
  en: {
    title: "Cloud Resources",
    subtitle: "Huawei Cloud Inventory",
    totalLabel: "Total",
    typesLabel: "Types",
    regionsLabel: "Regions",
    typeDistribution: "Distribution by Type",
    regionDistribution: "Distribution by Region",
    resourceTypes: "Resource Types",
    regions: "Regions",
    detailedList: "Detailed List",
    resources: "resources",
    name: "Name",
    type: "Type",
    region: "Region",
    provider: "Provider",
    created: "Created",
    showing: "Showing",
    of: "of",
    loadingResources: "Loading resources...",
    noResourcesAvailable: "No resources with state information available.",
  },
};

export function ResourceDashboard({ intentClassification, resourcesResponse, theme, language = "es" }) {
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
  if (!intentClassification) {
    return null;
  }

  if (!intentClassification.should_call_rms) {
    return null;
  }

  if (!resourcesResponse) {
    return (
      <div className="dash-container">
        <div className="dash-loading">{t.loadingResources}</div>
      </div>
    );
  }

  if (resourcesResponse.error) {
    return (
      <div className="dash-container">
        <div className="dash-error">{resourcesResponse.error}</div>
      </div>
    );
  }

  // Filter resources: only show those with valid state
  const allResources = resourcesResponse.resources || [];
  const validResources = allResources.filter(
    (r) => r.state && r.state.toLowerCase().trim() !== "unknown"
  );

  if (validResources.length === 0) {
    return (
      <div className="dash-container">
        <div className="dash-empty">
          <p>{t.noResourcesAvailable}</p>
        </div>
      </div>
    );
  }

  // Calculate metrics
  const metrics = useMemo(() => {
    const byType = {};
    const byRegion = {};

    validResources.forEach((resource) => {
      const type = formatTypeName(resource.type) || "Other";
      const region = resource.region_id || "Unknown";

      byType[type] = (byType[type] || 0) + 1;
      byRegion[region] = (byRegion[region] || 0) + 1;
    });

    return {
      total: validResources.length,
      typeCount: Object.keys(byType).length,
      regionCount: Object.keys(byRegion).length,
      byType,
      byRegion,
    };
  }, [validResources]);

  // Chart data - prepare for all three distributions
  const typeChartData = Object.entries(metrics.byType)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map((entry, index) => ({ ...entry, fill: COLORS[index % COLORS.length] }));

  const regionChartData = Object.entries(metrics.byRegion)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map((entry, index) => ({ ...entry, fill: COLORS[index % COLORS.length] }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="shadcn-tooltip" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="tooltip-color-indicator" style={{ backgroundColor: payload[0].payload.fill }}></div>
          <span className="tooltip-label">{payload[0].name}</span>
          <span className="tooltip-value">{payload[0].value}</span>
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
        </div>
      </div>

      {/* KPI Row */}
      <div className="dash-kpi-row" style={{ gap: "16px" }}>
        <div className="kpi-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="kpi-icon total">
            <Package size={20} strokeWidth={1.5} color={colors.primary} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label" style={{ color: colors.textSecondary }}>{t.totalLabel}</span>
            <span className="kpi-value">{metrics.total}</span>
          </div>
        </div>

        <div className="kpi-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="kpi-icon types">
            <LayoutGrid size={20} strokeWidth={1.5} color={colors.primary} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label" style={{ color: colors.textSecondary }}>{t.typesLabel}</span>
            <span className="kpi-value">{metrics.typeCount}</span>
          </div>
        </div>

        <div className="kpi-card" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border, color: colors.text }}>
          <div className="kpi-icon regions">
            <Globe size={20} strokeWidth={1.5} color={colors.primary} />
          </div>
          <div className="kpi-content">
            <span className="kpi-label" style={{ color: colors.textSecondary }}>{t.regionsLabel}</span>
            <span className="kpi-value">{metrics.regionCount}</span>
          </div>
        </div>
      </div>

      {/* Charts Grid - 3 columns on desktop */}
      <div className="dash-charts-row">
        {/* Chart 1: By Type */}
        <div className="dash-chart-card">
          <div className="dash-panel" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border }}>
            <div className="panel-header" style={{ borderBottomColor: colors.border }}>
              <h3 className="panel-title" style={{ color: colors.text }}>{t.typeDistribution}</h3>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={typeChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={0}
                    outerRadius={85}
                    paddingAngle={0}
                    dataKey="value"
                  >
                    {typeChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Chart 2: By Region */}
        <div className="dash-chart-card">
          <div className="dash-panel" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border }}>
            <div className="panel-header" style={{ borderBottomColor: colors.border }}>
              <h3 className="panel-title" style={{ color: colors.text }}>{t.regionDistribution}</h3>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={regionChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={0}
                    outerRadius={85}
                    paddingAngle={0}
                    dataKey="value"
                  >
                    {regionChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Breakdown Section */}
      <div className="dash-breakdown-grid" style={{ gridTemplateColumns: '1fr' }}>
        <div className="dash-breakdown-card">
          <div className="dash-panel" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border }}>
            <div className="panel-header" style={{ borderBottomColor: colors.border }}>
              <h3 className="panel-title" style={{ color: colors.text }}>{t.resourceTypes}</h3>
            </div>
            <div className="breakdown-list">
              {Object.entries(metrics.byType)
                .sort(([, a], [, b]) => b - a)
                .map(([type, count]) => (
                  <div key={type} className="breakdown-item" style={{ borderBottomColor: colors.border }}>
                    <div className="breakdown-icon">{getResourceIcon(type)}</div>
                    <div className="breakdown-info">
                      <span className="breakdown-name" style={{ color: colors.text }}>{type}</span>
                      <span className="breakdown-count" style={{ color: colors.textSecondary }}>{count} {t.resources}</span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>

      {/* Resources Table */}
      <div className="dash-table-section">
        <div className="dash-panel" style={{ backgroundColor: colors.bgSecondary, borderColor: colors.border }}>
          <div className="panel-header" style={{ borderBottomColor: colors.border }}>
            <h3 className="panel-title" style={{ color: colors.text }}>{t.detailedList}</h3>
            <span className="panel-meta" style={{ color: colors.textSecondary }}>{validResources.length} {t.resources}</span>
          </div>
          <div className="table-wrapper">
            <table className="dash-table" style={{ backgroundColor: colors.bg, color: colors.text }}>
              <thead style={{ backgroundColor: colors.bgTertiary, borderBottomColor: colors.border }}>
                <tr style={{ borderBottomColor: colors.border }}>
                  <th style={{ color: colors.text }}>{t.name}</th>
                  <th style={{ color: colors.text }}>{t.type}</th>
                  <th style={{ color: colors.text }}>{t.region}</th>
                  <th style={{ color: colors.text }}>{t.provider}</th>
                  <th style={{ color: colors.text }}>{t.created}</th>
                </tr>
              </thead>
              <tbody>
                {validResources.slice(0, 50).map((resource) => (
                  <tr key={resource.id}>
                    <td className="col-name">{resource.name || "—"}</td>
                    <td className="col-type">
                      <span className="type-badge">{formatTypeName(resource.type)}</span>
                    </td>
                    <td className="col-region">{resource.region_id || "—"}</td>
                    <td className="col-provider">{resource.provider || "—"}</td>
                    <td className="col-date">
                      {resource.created
                        ? new Date(resource.created).toLocaleDateString("es-ES", {
                            month: "short",
                            day: "numeric",
                            year: "2-digit",
                          })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {validResources.length > 50 && (
            <div className="table-footer" style={{ color: colors.textSecondary, borderTopColor: colors.border }}>{t.showing} 50 {t.of} {validResources.length} {t.resources}</div>
          )}
        </div>
      </div>
    </div>
  );
}
