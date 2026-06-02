import { motion } from "framer-motion";
import { TbCircleCheck, TbAlertCircle, TbClock, TbCircleX } from "react-icons/tb";

export function StatusBadge({ status = "pending", label = "", animated = true }) {
  const statusConfig = {
    success: { color: "text-green-600", bgColor: "bg-green-100", icon: TbCircleCheck, label: "Success" },
    error: { color: "text-red-600", bgColor: "bg-red-100", icon: TbCircleX, label: "Error" },
    warning: { color: "text-yellow-600", bgColor: "bg-yellow-100", icon: TbAlertCircle, label: "Warning" },
    pending: { color: "text-blue-600", bgColor: "bg-blue-100", icon: TbClock, label: "Pending" },
  };

  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;
  const displayLabel = label || config.label;

  return (
    <motion.div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${config.bgColor} ${config.color} border border-current border-opacity-20`}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      <motion.div animate={animated ? { rotate: status === "pending" ? 360 : 0 } : {}} transition={{ duration: 2, repeat: status === "pending" ? Infinity : 0 }}>
        <Icon size={14} />
      </motion.div>
      <span>{displayLabel}</span>
    </motion.div>
  );
}
