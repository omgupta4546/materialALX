import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import { uploadFileFn, getJobFn } from '../api/upload';
import { cn } from '../components/common/MetricCard';

import { getCpsesFn } from '../api/cpses';

type Step = 'SELECT_CPSE' | 'UPLOAD' | 'MAP' | 'VALIDATE' | 'JOB';

interface MappingState {
  material_code: string;
  description: string;
  uom: string;
}

export const Upload: React.FC = () => {
  const [step, setStep] = useState<Step>('SELECT_CPSE');
  const [cpseCode, setCpseCode] = useState<string>('');
  const { data: orgs, isLoading: orgsLoading } = useQuery({
    queryKey: ['cpses'],
    queryFn: getCpsesFn
  });
  
  // File Parsing State
  const [_, setFile] = useState<File | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [rawRows, setRawRows] = useState<any[]>([]); // To build final CSV

  // Mapping State
  const [mapping, setMapping] = useState<MappingState>({ material_code: '', description: '', uom: '' });

  // Job State
  const [jobId, setJobId] = useState<string | null>(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    onDrop: (acceptedFiles) => handleFileDrop(acceptedFiles[0])
  });

  const uploadMutation = useMutation({
    mutationFn: (data: { file: File, cpseCode: string }) => uploadFileFn(data.file, data.cpseCode),
    onSuccess: (data) => {
      setJobId(data.job_id);
      setStep('JOB');
    }
  });

  const { data: jobData } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobFn(jobId!),
    enabled: !!jobId && step === 'JOB',
    refetchInterval: (query) => {
      // stop refetching if status is COMPLETED or FAILED
      const status = query.state.data?.status;
      if (status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED') return false;
      return 1000;
    }
  });

  const handleFileDrop = (file: File) => {
    if (!file) return;
    setFile(file);

    if (file.name.endsWith('.csv')) {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          if (results.meta.fields) {
            setHeaders(results.meta.fields);
            setPreviewRows(results.data.slice(0, 5));
            setRawRows(results.data);
            setStep('MAP');
          }
        }
      });
    } else if (file.name.endsWith('.xlsx')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(firstSheet);
        if (json.length > 0) {
          setHeaders(Object.keys(json[0] as object));
          setPreviewRows(json.slice(0, 5));
          setRawRows(json);
          setStep('MAP');
        }
      };
      reader.readAsArrayBuffer(file);
    }
  };

  const submitMapping = () => {
    // Generate clean CSV string from rawRows based on mapping
    const cleanData = rawRows.map(row => ({
      material_code: mapping.material_code ? row[mapping.material_code] : '',
      description: mapping.description ? row[mapping.description] : '',
      uom: mapping.uom ? row[mapping.uom] : ''
    }));

    const csvContent = Papa.unparse(cleanData);
    const cleanFile = new File([csvContent], "mapped_upload.csv", { type: "text/csv" });

    setStep('VALIDATE');
    uploadMutation.mutate({ file: cleanFile, cpseCode });
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-20">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Upload Catalog</h1>
        <div className="flex space-x-2 text-sm text-muted-foreground">
          <span className={cn(step === 'SELECT_CPSE' && 'text-primary font-bold')}>1. Setup</span>
          <span>→</span>
          <span className={cn(step === 'UPLOAD' && 'text-primary font-bold')}>2. Upload</span>
          <span>→</span>
          <span className={cn(step === 'MAP' && 'text-primary font-bold')}>3. Map</span>
          <span>→</span>
          <span className={cn(step === 'JOB' && 'text-primary font-bold')}>4. Process</span>
        </div>
      </div>

      {step === 'SELECT_CPSE' && (
        <div className="glass p-8 rounded-xl">
          <h2 className="text-lg font-medium mb-4">Select Target Organization</h2>
          <select 
            value={cpseCode}
            onChange={(e) => setCpseCode(e.target.value)}
            className="w-full p-3 rounded-md border border-border bg-background mb-6 focus:ring-primary focus:border-primary text-foreground"
            disabled={orgsLoading}
          >
            <option value="">-- Choose an Organization --</option>
            {orgs?.map(org => <option key={org.cpse_id} value={org.cpse_code}>{org.cpse_name}</option>)}
          </select>
          <button 
            disabled={!cpseCode}
            onClick={() => setStep('UPLOAD')}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 flex items-center"
          >
            Continue <ArrowRight size={16} className="ml-2" />
          </button>
        </div>
      )}

      {step === 'UPLOAD' && (
        <div 
          {...getRootProps()} 
          className={cn(
            "border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-colors glass",
            isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
          )}
        >
          <input {...getInputProps()} />
          <UploadCloud className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-1">Drag and drop your file here</h3>
          <p className="text-muted-foreground text-sm">Supports CSV, JSON, XLSX up to 50MB</p>
        </div>
      )}

      {step === 'MAP' && (
        <div className="space-y-6">
          <div className="glass p-6 rounded-xl">
            <h2 className="text-lg font-medium mb-4">Map Columns</h2>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <label className="block text-sm mb-1 text-muted-foreground">Target: Material Code</label>
                <select 
                  onChange={e => setMapping({...mapping, material_code: e.target.value})}
                  className="w-full p-2 rounded-md border border-border bg-background"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm mb-1 text-muted-foreground">Target: Description</label>
                <select 
                  onChange={e => setMapping({...mapping, description: e.target.value})}
                  className="w-full p-2 rounded-md border border-border bg-background"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm mb-1 text-muted-foreground">Target: UOM</label>
                <select 
                  onChange={e => setMapping({...mapping, uom: e.target.value})}
                  className="w-full p-2 rounded-md border border-border bg-background"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="glass p-6 rounded-xl overflow-auto">
            <h3 className="text-sm font-medium mb-4 text-muted-foreground">Data Preview</h3>
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 border-b border-border">
                <tr>
                  {headers.map(h => <th key={h} className="p-2 font-medium">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, i) => (
                  <tr key={i} className="border-b border-border/50">
                    {headers.map(h => <td key={h} className="p-2 text-muted-foreground">{row[h]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button 
            onClick={submitMapping}
            disabled={!mapping.material_code || !mapping.description}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50"
          >
            Validate & Submit
          </button>
        </div>
      )}

      {(step === 'VALIDATE' || step === 'JOB') && (
        <div className="glass p-8 rounded-xl text-center max-w-lg mx-auto">
          {uploadMutation.isPending ? (
            <div className="py-8">
              <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
              <p>Uploading mapped catalog...</p>
            </div>
          ) : jobData ? (
            <div className="py-8 space-y-4">
              {jobData.status === 'COMPLETED' ? (
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto" />
              ) : jobData.status === 'FAILED' ? (
                <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
              ) : (
                <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto" />
              )}
              
              <h2 className="text-xl font-bold">
                {jobData.status === 'COMPLETED' ? 'Processing Complete' : 
                 jobData.status === 'FAILED' ? 'Processing Failed' : 'Processing Background Job'}
              </h2>
              
              <div className="w-full bg-muted rounded-full h-3 mb-2 overflow-hidden border border-border">
                <div 
                  className={cn(
                    "h-full transition-all duration-500",
                    jobData.status === 'FAILED' ? "bg-destructive" : "bg-primary"
                  )} 
                  style={{ width: `${jobData.total_records > 0 ? (jobData.records_processed / jobData.total_records) * 100 : 0}%` }}
                ></div>
              </div>
              <p className="text-muted-foreground text-sm">
                Processed {jobData.records_processed} of {jobData.total_records} records.
              </p>

              {jobData.errors && (
                <div className="mt-4 p-4 bg-destructive/10 text-destructive text-sm rounded text-left">
                  {JSON.stringify(jobData.errors)}
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};
