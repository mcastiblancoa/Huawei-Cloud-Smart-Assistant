import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hw-red)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-[var(--hw-red)] text-white shadow-md hover:bg-[var(--hw-red-bright)]",
        secondary: "bg-[var(--bg-secondary)] text-[var(--text-primary)] border border-[var(--border-light)] hover:bg-[var(--surface-hover)]",
        outline: "border border-[var(--border-light)] text-[var(--text-primary)] hover:bg-[var(--surface-hover)]",
        ghost: "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]",
        destructive: "bg-[var(--hw-red)] text-white hover:bg-[var(--hw-red-bright)]",
      },
      size: {
        sm: "h-8 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-6",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
      },
    },
    defaultVariants: {
      variant: "secondary",
      size: "md",
    },
  }
);

const Button = React.forwardRef(function Button(
  { className, variant, size, type = "button", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
});

export { Button, buttonVariants };
