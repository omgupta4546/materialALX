import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface ErrorStateProps {
  className?: string;
  // Add props here
}

export const ErrorState: React.FC<ErrorStateProps> = ({ className }) => {
  return (
    <div className={cn("p-4 border rounded-md shadow-sm bg-card", className)}>
      ErrorState Component
    </div>
  );
};
