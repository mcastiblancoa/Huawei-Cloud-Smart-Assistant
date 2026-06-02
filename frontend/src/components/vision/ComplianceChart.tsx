import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const PPE_COLORS = {
  hardhat: "#22c55e",
  helmet: "#22c55e",
  safety_vest: "#3b82f6",
  vest: "#3b82f6",
  goggles: "#a855f7",
  glasses: "#a855f7",
  face_shield: "#f59e0b",
  mask: "#06b6d4",
  gloves: "#84cc16",
  safety_boots: "#ec4899",
  boots: "#ec4899",
};

const PPE_LABELS = {
  hardhat: { es: "Casco", en: "Hardhat" },
  helmet: { es: "Casco", en: "Helmet" },
  safety_vest: { es: "Chaleco", en: "Safety Vest" },
  vest: { es: "Chaleco", en: "Vest" },
  goggles: { es: "Gafas", en: "Goggles" },
  glasses: { es: "Gafas", en: "Glasses" },
  face_shield: { es: "Prot. facial", en: "Face Shield" },
  mask: { es: "Mascarilla", en: "Mask" },
  gloves: { es: "Guantes", en: "Gloves" },
  safety_boots: { es: "Botas", en: "Safety Boots" },
  boots: { es: "Botas", en: "Boots" },
};

export function ComplianceChart({ ppeSummary, language }) {
  if (!ppeSummary || Object.keys(ppeSummary).length === 0) return null;

  const data = Object.entries(ppeSummary)
    .map(([key, count]) => ({
      name: PPE_LABELS[key]?.[language === "es" ? "es" : "en"] || key,
      value: Number(count),
      fill: PPE_COLORS[key] || "#6b7280",
      key,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="compliance-chart-container">
      <div className="compliance-chart-title">
        {language === "es" ? "Equipamiento detectado" : "Equipment detected"}
      </div>
      <div className="compliance-chart-wrap">
        <ResponsiveContainer width="100%" height={180}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 30, left: 4, bottom: 4 }}
          >
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} />
            <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value) => [value, ""]}
              contentStyle={{
                borderRadius: 10,
                borderColor: "var(--border-light)",
                fontSize: "0.78rem",
                background: "var(--surface)",
              }}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16} isAnimationActive={true} animationDuration={400}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
