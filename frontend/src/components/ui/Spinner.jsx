import { cn } from "../lib/utils";

export function Spinner({ className, size = "md" }) {
  const sizes = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  };

  return (
    <div
      className={cn(
        "animate-spin rounded-full border-2 border-[var(--border-light)] border-t-[var(--hw-red)]",
        sizes[size],
        className
      )}
    />
  );
}
