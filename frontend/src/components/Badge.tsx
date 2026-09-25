import React from "react";

export const Badge = ({ children, variant = "default", className = "" }: { children: React.ReactNode; variant?: string; className?: string }) => {
  const baseStyle = "badge";
  const variantStyles: Record<string, string> = {
    default:  "badge-default",
    success:  "badge-success",
    warning:  "badge-warning",
    error:    "badge-error",
    danger:   "badge-error",
    info:     "badge-info",
  };

  const style = variantStyles[variant] || variantStyles.default;

  return (
    <span className={`${baseStyle} ${style} ${className}`}>
      {children}
    </span>
  );
};

