import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2, ArrowRight, FileText, Download, Info } from 'lucide-react';
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
  const [rawRows, setRawRows] = useState<any[]>([]);

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
    mutationFn: (data: { file: File; cpseCode: string }) => uploadFileFn(data.file, data.cpseCode),
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
    const cleanData = rawRows.map(row => ({
      material_code: mapping.material_code ? row[mapping.material_code] : '',
      description: mapping.description ? row[mapping.description] : '',
      uom: mapping.uom ? row[mapping.uom] : ''
    }));
    const csvContent = Papa.unparse(cleanData);
    const cleanFile = new File([csvContent], 'mapped_upload.csv', { type: 'text/csv' });
    setStep('VALIDATE');
    uploadMutation.mutate({ file: cleanFile, cpseCode });
  };

  const GUIDELINES = [
    'File must contain at least Material Code and Description columns.',
    'Ensure no duplicate material codes within the same file.',
    'UOM (Unit of Measure) column is optional but recommended.',
    'First row should be the column header row.',
    'Remove any summary or total rows before uploading.',
    'Accepted formats: CSV, XLSX, JSON (UTF-8 encoded).',
    'Maximum file size: 50 MB per upload.',
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-20">

      {/* ── Page header + stepper ── */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold font-heading">Upload Catalog</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Import material master data for your CPSE</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {(['SELECT_CPSE', 'UPLOAD', 'MAP', 'JOB'] as Step[]).map((s, i) => {
            const labels = ['1. Setup', '2. Upload', '3. Map', '4. Process'];
            const isActive = step === s;
            return (
              <React.Fragment key={s}>
                {i > 0 && <span className="text-border text-xs">→</span>}
                <span className={cn('transition-colors', isActive ? 'text-primary font-bold' : 'text-muted-foreground')}>
                  {labels[i]}
                </span>
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ══ STEP 1 — SELECT CPSE ══ */}
      {step === 'SELECT_CPSE' && (
        <div className="card p-8">
          <h2 className="text-lg font-semibold mb-4">Select Target Organization</h2>
          <select
            value={cpseCode}
            onChange={(e) => setCpseCode(e.target.value)}
            className="w-full p-3 rounded-lg border border-border bg-background mb-6 text-foreground transition-all outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/60"
            disabled={orgsLoading}
          >
            <option value="">-- Choose an Organization --</option>
            {orgs?.map(org => <option key={org.cpse_id} value={org.cpse_code}>{org.cpse_name}</option>)}
          </select>
          <button
            disabled={!cpseCode}
            onClick={() => setStep('UPLOAD')}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* ══ STEP 2 — UPLOAD (restyled) ══ */}
      {step === 'UPLOAD' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">

          {/* Left: dropzone 2/3 */}
          <div className="lg:col-span-2 space-y-4">

            {/* Drag-and-drop zone */}
            <div
              {...getRootProps()}
              className={cn(
                'relative rounded-2xl border-2 border-dashed p-14 text-center cursor-pointer transition-all duration-200 group select-none',
                isDragActive
                  ? 'border-primary bg-primary/8 scale-[1.01]'
                  : 'border-primary/35 bg-white hover:border-primary/65 hover:bg-primary/4'
              )}
              style={{ boxShadow: isDragActive ? '0 0 0 4px hsl(155 73% 21% / 0.10)' : '0 1px 4px rgba(0,0,0,0.04), 0 2px 8px hsl(155 73% 21% / 0.05)' }}
            >
              <input {...getInputProps()} />

              {/* Cloud icon chip */}
              <div
                className={cn(
                  'inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-5 mx-auto transition-all duration-200',
                  isDragActive ? 'bg-primary/18 scale-110' : 'bg-primary/8 group-hover:bg-primary/13'
                )}
              >
                <UploadCloud
                  size={32}
                  className={cn(
                    'transition-colors duration-200',
                    isDragActive ? 'text-primary' : 'text-primary/65 group-hover:text-primary'
                  )}
                />
              </div>

              {isDragActive ? (
                <p className="text-primary font-bold text-base">Release to upload!</p>
              ) : (
                <>
                  <h3 className="text-base font-semibold text-foreground mb-1.5">
                    Drag &amp; drop your file here
                  </h3>
                  <p className="text-sm text-muted-foreground mb-6">
                    or click anywhere, or use the button below
                  </p>

                  {/* Deep green Upload File button */}
                  <button
                    type="button"
                    className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-all duration-150 hover:-translate-y-px active:translate-y-0 focus:outline-none"
                    style={{
                      background: 'linear-gradient(135deg, hsl(155,73%,17%), hsl(155,62%,25%))',
                      boxShadow: '0 4px 14px hsl(155 73% 21% / 0.32)',
                    }}
                  >
                    <UploadCloud size={16} />
                    Upload File
                  </button>
                </>
              )}

              {/* Format badges */}
              <div className="mt-6 flex items-center justify-center gap-2 flex-wrap">
                {['CSV', 'XLSX', 'JSON'].map(fmt => (
                  <span
                    key={fmt}
                    className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                    style={{ background: 'hsl(155 73% 21% / 0.09)', color: 'hsl(155,62%,25%)' }}
                  >
                    {fmt}
                  </span>
                ))}
                <span className="text-[11px] text-muted-foreground">· Max 50 MB</span>
              </div>
            </div>

            {/* Privacy note */}
            <div
              className="flex items-start gap-3 px-4 py-3 rounded-xl text-sm"
              style={{ background: 'hsl(155 73% 21% / 0.06)', border: '1px solid hsl(155 73% 21% / 0.15)' }}
            >
              <Info size={15} className="text-primary shrink-0 mt-0.5" />
              <p className="text-primary/80 leading-relaxed">
                Files are parsed locally in your browser. Your data is never transmitted without your explicit confirmation at the next step.
              </p>
            </div>
          </div>

          {/* Right: Guidelines white card 1/3 */}
          <div className="card p-6 flex flex-col gap-5 h-fit">

            {/* Card header */}
            <div className="flex items-center gap-2.5">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: 'hsl(155 73% 21% / 0.10)' }}
              >
                <FileText size={16} className="text-primary" />
              </div>
              <h3 className="font-semibold text-sm text-foreground">File Guidelines</h3>
            </div>

            {/* Green bullet list */}
            <ul className="space-y-3">
              {GUIDELINES.map((tip, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-foreground/80 leading-snug">
                  <span
                    className="shrink-0 rounded-full"
                    style={{
                      width: '6px', height: '6px',
                      marginTop: '6px',
                      background: 'hsl(155,73%,25%)',
                      display: 'inline-block',
                    }}
                  />
                  {tip}
                </li>
              ))}
            </ul>

            {/* Divider */}
            <div className="h-px bg-border" />

            {/* Download template */}
            <a
              href="/template.csv"
              download
              className="inline-flex items-center gap-2 text-sm font-semibold transition-colors hover:underline"
              style={{ color: 'hsl(155,73%,21%)' }}
            >
              <Download size={15} />
              Download CSV template
            </a>
          </div>
        </div>
      )}

      {/* ══ STEP 3 — MAP COLUMNS (unchanged) ══ */}
      {step === 'MAP' && (
        <div className="space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-semibold mb-4">Map Columns</h2>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <label className="block text-sm mb-1 text-muted-foreground">Target: Material Code</label>
                <select
                  onChange={e => setMapping({ ...mapping, material_code: e.target.value })}
                  className="w-full p-2 rounded-md border border-border bg-background"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm mb-1 text-muted-foreground">Target: Description</label>
                <select
                  onChange={e => setMapping({ ...mapping, description: e.target.value })}
                  className="w-full p-2 rounded-md border border-border bg-background"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm mb-1 text-muted-foreground">Target: UOM</label>
                <select
                  onChange={e => setMapping({ ...mapping, uom: e.target.value })}
                  className="w-full p-2 rounded-md border border-border bg-background"
                >
                  <option value="">-- Select Column --</option>
                  {headers.map(h => <option key={h} value={h}>{h}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="card p-6 overflow-auto">
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
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Validate &amp; Submit
          </button>
        </div>
      )}

      {/* ══ STEP 4 — VALIDATE / JOB (unchanged) ══ */}
      {(step === 'VALIDATE' || step === 'JOB') && (
        <div className="card p-8 text-center max-w-lg mx-auto">
          {uploadMutation.isPending ? (
            <div className="py-8">
              <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
              <p>Uploading mapped catalog...</p>
            </div>
          ) : jobData ? (
            <div className="py-8 space-y-4">
              {jobData.status === 'COMPLETED' ? (
                <CheckCircle2 className="w-12 h-12 text-primary mx-auto" />
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
                  className={cn('h-full transition-all duration-500 rounded-full', jobData.status === 'FAILED' ? 'bg-destructive' : 'bg-primary')}
                  style={{ width: `${jobData.total_records > 0 ? (jobData.records_processed / jobData.total_records) * 100 : 0}%` }}
                />
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
