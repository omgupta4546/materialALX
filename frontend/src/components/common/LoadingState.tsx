import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface LoadingStateProps {
  className?: string;
  // Add props here
}

export const LoadingState: React.FC<LoadingStateProps> = ({ className }) => {
  return (
    <div className={cn("p-4 border rounded-md shadow-sm bg-card", className)}>
      LoadingState Component
    </div>
  );
};
