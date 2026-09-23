import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface ConfidenceBadgeProps {
  className?: string;
  // Add props here
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ className }) => {
  return (
    <div className={cn("p-4 border rounded-md shadow-sm bg-card", className)}>
      ConfidenceBadge Component
    </div>
  );
};
