const PPE_CONFIG = {
  hardhat:      { icon: "⛑️", labelEs: "Casco",        labelEn: "Hardhat",       color: "#22c55e" },
  helmet:       { icon: "⛑️", labelEs: "Casco",        labelEn: "Helmet",        color: "#22c55e" },
  safety_vest:  { icon: "🦺", labelEs: "Chaleco",      labelEn: "Safety Vest",   color: "#3b82f6" },
  vest:         { icon: "🦺", labelEs: "Chaleco",      labelEn: "Vest",          color: "#3b82f6" },
  goggles:      { icon: "🥽", labelEs: "Gafas",        labelEn: "Goggles",       color: "#a855f7" },
  glasses:      { icon: "🥽", labelEs: "Gafas",        labelEn: "Glasses",       color: "#a855f7" },
  face_shield:  { icon: "🛡️", labelEs: "Prot. facial", labelEn: "Face Shield",   color: "#f59e0b" },
  mask:         { icon: "😷", labelEs: "Mascarilla",   labelEn: "Mask",          color: "#06b6d4" },
  gloves:       { icon: "🧤", labelEs: "Guantes",      labelEn: "Gloves",        color: "#84cc16" },
  safety_boots: { icon: "🥾", labelEs: "Botas",        labelEn: "Safety Boots",  color: "#ec4899" },
  boots:        { icon: "🥾", labelEs: "Botas",        labelEn: "Boots",         color: "#ec4899" },
};

const REQUIRED_PPE = ["hardhat", "safety_vest"];

export function PPEStatusGrid({ ppeSummary, persons, language }) {
  const isEs = language === "es";

  const detectedPPE = Object.keys(ppeSummary || {});
  const allPPE = [...new Set([...REQUIRED_PPE, ...detectedPPE])];

  return (
    <div className="ppe-grid">
      {allPPE.map((key) => {
        const config = PPE_CONFIG[key] || { icon: "📦", labelEs: key, labelEn: key, color: "#6b7280" };
        const count = ppeSummary?.[key] || 0;
        const isRequired = REQUIRED_PPE.includes(key);
        const isMissing = isRequired && count === 0;

        return (
          <div
            key={key}
            className={`ppe-badge ${isMissing ? "ppe-badge-missing" : count > 0 ? "ppe-badge-detected" : "ppe-badge-optional"}`}
          >
            <span className="ppe-badge-icon">{config.icon}</span>
            <div className="ppe-badge-info">
              <span className="ppe-badge-label">{isEs ? config.labelEs : config.labelEn}</span>
              <span className="ppe-badge-count">
                {count > 0
                  ? (isEs ? `${count} detectado${count > 1 ? "s" : ""}` : `${count} detected`)
                  : isMissing
                    ? (isEs ? "Falta" : "Missing")
                    : (isEs ? "No detectado" : "Not detected")}
              </span>
            </div>
            {isRequired && (
              <span className={`ppe-badge-required ${isMissing ? "ppe-required-missing" : "ppe-required-ok"}`}>
                {isEs ? "OBLIGATORIO" : "REQUIRED"}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function PersonComplianceList({ persons, language }) {
  if (!persons || persons.length === 0) return null;
  const isEs = language === "es";

  return (
    <div className="person-compliance-list">
      {persons.map((person) => (
        <div key={`person-${person.person_index}`} className={`person-compliance-card ${person.compliant ? "person-compliant" : "person-non-compliant"}`}>
          <div className="person-compliance-header">
            <span className="person-compliance-status-dot" />
            <span className="person-compliance-label">
              {isEs ? `Persona ${person.person_index + 1}` : `Person ${person.person_index + 1}`}
            </span>
            <span className={`person-compliance-badge ${person.compliant ? "badge-ok" : "badge-fail"}`}>
              {person.compliant
                ? (isEs ? "Cumple" : "Compliant")
                : (isEs ? "No cumple" : "Non-compliant")}
            </span>
          </div>
          {person.missing_ppe.length > 0 && (
            <div className="person-missing-ppe">
              <span className="person-missing-label">
                {isEs ? "Falta: " : "Missing: "}
              </span>
              {person.missing_ppe.join(", ")}
            </div>
          )}
          {person.ppe.length > 0 && (
            <div className="person-detected-ppe">
              {person.ppe.map((item, i) => (
                <span key={i} className="person-ppe-tag">
                  {item.class_name} {item.confidence.toFixed(0)}%
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
