import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[var(--bg-secondary)] text-[var(--text-primary)]",
        subtle: "border-[var(--border-light)] text-[var(--text-secondary)]",
        success: "border-transparent bg-green-500/10 text-green-600",
        warning: "border-transparent bg-amber-500/10 text-amber-600",
        error: "border-transparent bg-[var(--hw-red-light)] text-[var(--hw-red)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

function Badge({ className, variant, ...props }) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge };
