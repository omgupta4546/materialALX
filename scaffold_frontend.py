import os

base_dir = "frontend/src"
folders = [
    "components/common",
    "layouts",
    "pages",
    "api",
    "store",
    "hooks"
]

for folder in folders:
    os.makedirs(os.path.join(base_dir, folder), exist_ok=True)

components = [
    "MetricCard", "DataTable", "FilterPanel", "SearchBar", "StatusBadge",
    "ConfidenceBadge", "AttributeTable", "ComparisonTable", "ChartCard",
    "Modal", "Drawer", "Toast", "Pagination", "LoadingState", "ErrorState",
    "EmptyState", "ConfirmationDialog", "AuditTimeline"
]

component_template = """import React from 'react';
import {{ clsx, type ClassValue }} from 'clsx';
import {{ twMerge }} from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {{
  return twMerge(clsx(inputs));
}}

export interface {name}Props {{
  className?: string;
  // Add props here
}}

export const {name}: React.FC<{name}Props> = ({{ className }}) => {{
  return (
    <div className={{cn("p-4 border rounded-md shadow-sm bg-card", className)}}>
      {name} Component
    </div>
  );
}};
"""

for comp in components:
    path = os.path.join(base_dir, "components/common", f"{comp}.tsx")
    with open(path, "w") as f:
        f.write(component_template.format(name=comp))

layouts = ["AppShell", "Sidebar", "Topbar"]
layout_template = """import React from 'react';
import {{ Outlet, Link }} from 'react-router-dom';
import {{ cn }} from '../components/common/MetricCard'; // reuse cn

export const {name}: React.FC = () => {{
  return (
    <div className="flex h-screen w-full bg-background">
      {name}
    </div>
  );
}};
"""
for layout in layouts:
    path = os.path.join(base_dir, "layouts", f"{layout}.tsx")
    with open(path, "w") as f:
        f.write(layout_template.format(name=layout))

pages = ["Dashboard", "Materials", "Approvals", "Analytics", "Login"]
page_template = """import React from 'react';

export const {name}: React.FC = () => {{
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">{name} Page</h1>
      <p className="text-muted-foreground">Placeholder for {name} content.</p>
    </div>
  );
}};
"""
for page in pages:
    path = os.path.join(base_dir, "pages", f"{page}.tsx")
    with open(path, "w") as f:
        f.write(page_template.format(name=page))

print("Scaffolding complete.")
