import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface ConfirmationDialogProps {
  className?: string;
  // Add props here
}

export const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({ className }) => {
  return (
    <div className={cn("p-4 border rounded-md shadow-sm bg-card", className)}>
      ConfirmationDialog Component
    </div>
  );
};
