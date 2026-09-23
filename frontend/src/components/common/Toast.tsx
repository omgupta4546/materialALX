import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface ToastProps {
  className?: string;
  // Add props here
}

export const Toast: React.FC<ToastProps> = ({ className }) => {
  return (
    <div className={cn("p-4 border rounded-md shadow-sm bg-card", className)}>
      Toast Component
    </div>
  );
};
