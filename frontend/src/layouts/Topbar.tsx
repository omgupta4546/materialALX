import React from 'react';
import { Bell, Search } from 'lucide-react';

export const Topbar: React.FC = () => {
  return (
    <header className="h-16 border-b border-border bg-card flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center w-96 relative text-muted-foreground focus-within:text-foreground">
        <Search size={18} className="absolute left-3" />
        <input 
          type="text" 
          placeholder="Search materials globally..." 
          className="w-full pl-10 pr-4 py-2 rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 transition-shadow"
        />
      </div>
      <div className="flex items-center space-x-4 text-muted-foreground">
        <button className="hover:text-foreground transition-colors p-2 rounded-full hover:bg-accent relative">
          <Bell size={20} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full"></span>
        </button>
        <div className="flex items-center space-x-2 border-l border-border pl-4">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
            A
          </div>
          <span className="text-sm font-medium text-foreground">Admin User</span>
        </div>
      </div>
    </header>
  );
};
