import React, { useState } from 'react';
import { Download, FileSpreadsheet, Loader2, FileText } from 'lucide-react';
import { Card } from './Card';
import { Badge } from './Badge';

const EXPORTS = [
  { id: 'cpse-mapping', name: 'CPSE Mapping Report', desc: 'All approved mappings linking Legacy codes to National codes.' },
  { id: 'duplicate-report', name: 'Duplicate Report', desc: 'All identified NEAR_DUPLICATE match results.' },
  { id: 'material-master', name: 'Material Master', desc: 'Complete dump of all National Materials.' },
  { id: 'migration-report', name: 'Migration Report', desc: 'Status of processing jobs and data readiness.' },
  { id: 'procurement-opportunity', name: 'Procurement Opportunities', desc: 'Procurement intelligence per National Material.' },
  { id: 'audit-report', name: 'Audit Report', desc: 'Complete audit log for governance tracking.' },
  { id: 'data-quality-report', name: 'Data Quality Report', desc: 'Data quality metrics per material.' },
];

export function DataExportsSection({ headers }: { headers: any }) {
  const [downloading, setDownloading] = useState<string | null>(null);
  
  const handleDownload = async (reportId: string, format: 'csv' | 'xlsx') => {
    try {
      setDownloading(`${reportId}-${format}`);
      const token = headers.Authorization.split(' ')[1];
      const url = `http://localhost:8000/api/v1/exports/${reportId}?format=${format}`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${reportId}_report.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error(err);
      alert('Failed to download report.');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4 border-b border-gray-800 pb-4">
        <Download className="w-5 h-5 text-indigo-400" />
        <div>
          <h2 className="text-lg font-medium text-gray-200">Data Exports</h2>
          <p className="text-sm text-gray-500">Download system data and analytical reports in CSV or XLSX format.</p>
        </div>
      </div>
      
      <div className="grid gap-4">
        {EXPORTS.map(exp => (
          <div key={exp.id} className="flex items-center justify-between p-4 bg-gray-950/50 border border-gray-800 rounded-lg hover:border-gray-700 transition-colors">
            <div>
              <h3 className="font-medium text-gray-200 flex items-center gap-2">
                {exp.name}
              </h3>
              <p className="text-sm text-gray-500 mt-1">{exp.desc}</p>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleDownload(exp.id, 'csv')}
                disabled={downloading !== null}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-900 border border-gray-700 hover:border-gray-500 rounded text-gray-300 disabled:opacity-50"
              >
                {downloading === `${exp.id}-csv` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 text-gray-400" />}
                CSV
              </button>
              <button
                onClick={() => handleDownload(exp.id, 'xlsx')}
                disabled={downloading !== null}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-indigo-900/30 border border-indigo-800 hover:border-indigo-600 rounded text-indigo-300 disabled:opacity-50"
              >
                {downloading === `${exp.id}-xlsx` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 text-indigo-400" />}
                XLSX
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
