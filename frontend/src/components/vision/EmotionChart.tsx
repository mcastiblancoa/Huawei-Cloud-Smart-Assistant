import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const EMOTION_COLORS = {
  happy: "#22c55e",
  sad: "#3b82f6",
  angry: "#ef4444",
  fear: "#a855f7",
  surprise: "#f59e0b",
  disgust: "#84cc16",
  neutral: "#6b7280",
};

const EMOTION_LABELS = {
  happy: { es: "Feliz", en: "Happy" },
  sad: { es: "Triste", en: "Sad" },
  angry: { es: "Enojado", en: "Angry" },
  fear: { es: "Miedo", en: "Fear" },
  surprise: { es: "Sorpresa", en: "Surprise" },
  disgust: { es: "Asco", en: "Disgust" },
  neutral: { es: "Neutral", en: "Neutral" },
};

export function EmotionChart({ allScores, language }) {
  if (!allScores) return null;

  const data = Object.entries(allScores)
    .map(([key, value]) => ({
      name: EMOTION_LABELS[key]?.[language === "es" ? "es" : "en"] || key,
      value: Number(value),
      fill: EMOTION_COLORS[key] || "#6b7280",
      key,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="emotion-chart-container">
      <div className="emotion-chart-title">
        {language === "es" ? "Distribución de emociones" : "Emotion distribution"}
      </div>
      <div className="emotion-chart-wrap">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 40, left: 4, bottom: 4 }}
          >
            <XAxis
              type="number"
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 10 }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={70}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              formatter={(value) => [`${Number(value).toFixed(1)}%`, ""]}
              contentStyle={{
                borderRadius: 10,
                borderColor: "var(--border-light)",
                fontSize: "0.78rem",
                background: "var(--surface)",
              }}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={18} isAnimationActive={true} animationDuration={400}>
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
