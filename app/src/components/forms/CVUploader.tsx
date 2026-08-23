import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, X, AlertCircle, Users, CheckCircle2, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useLanguage } from '@/hooks/use-language';
import { CandidateItem } from '@/types';

interface CVUploaderProps {
  candidates: CandidateItem[];
  onAddFiles: (files: File[]) => void;
  onRemoveCandidate: (index: number) => void;
  onUpdateCandidateName?: (index: number, name: string) => void;
}

export const CVUploader: React.FC<CVUploaderProps> = ({
  candidates,
  onAddFiles,
  onRemoveCandidate,
  onUpdateCandidateName,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const { t } = useLanguage();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(Array.from(e.target.files));
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const processFiles = (files: File[]) => {
    setUploadError(null);
    const validFiles: File[] = [];

    for (const file of files) {
      const isExtensionValid = /\.(pdf|docx|doc|txt)$/i.test(file.name);
      if (!isExtensionValid) {
        setUploadError(t.cvUploader.invalidType);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setUploadError(t.cvUploader.sizeError);
        return;
      }
      validFiles.push(file);
    }

    if (validFiles.length > 0) {
      onAddFiles(validFiles);
    }
  };

  const handleDownload = (cand: CandidateItem) => {
    if (cand.file) {
      const url = URL.createObjectURL(cand.file);
      const a = document.createElement('a');
      a.href = url;
      a.download = cand.cvFileName || cand.file.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else {
      const content =
        `===================================================\n` +
        `CANDIDATE CURRICULUM VITAE\n` +
        `===================================================\n` +
        `Name: ${cand.name}\n` +
        `File: ${cand.cvFileName || `${cand.name.replace(/\s+/g, '_')}_CV.txt`}\n` +
        `---------------------------------------------------\n\n` +
        `${cand.cvRawText || 'No resume content available.'}\n`;

      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const downloadName = cand.cvFileName
        ? cand.cvFileName.replace(/\.pdf$/i, '.txt')
        : `${cand.name.replace(/\s+/g, '_')}_CV.txt`;
      a.download = downloadName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="space-y-3">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.docx,.doc,.txt"
        multiple
        className="hidden"
      />

      {uploadError && (
        <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
          <button
            type="button"
            onClick={() => setUploadError(null)}
            className="text-destructive hover:opacity-70 cursor-pointer"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Multi-file Dropzone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-4 sm:p-5 text-center transition-all ${
          isDragging
            ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
            : 'border-border/80 hover:border-primary/50 hover:bg-muted/30'
        }`}
      >
        <div className="mb-2 flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-full bg-blue-500/15 text-blue-500 dark:text-blue-400 border border-blue-500/30 shadow-2xs">
          <UploadCloud className="h-4.5 w-4.5 sm:h-5 sm:w-5" />
        </div>
        <p className="text-xs sm:text-sm font-medium text-foreground">
          {t.cvUploader.dragPrompt}{' '}
          <span className="text-primary underline">{t.cvUploader.browse}</span>
        </p>
        <p className="mt-0.5 text-[11px] sm:text-xs text-muted-foreground">
          {t.cvUploader.supportedTypes}
        </p>
      </div>

      {/* Queue list of candidates */}
      {candidates.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
              <Users className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400" />
              <span>{t.form.candidatePoolTitle}</span>
            </div>
            <Badge variant="secondary" className="text-[10px] font-mono h-5 px-1.5 select-none">
              {candidates.length} {t.form.candidateCount}
            </Badge>
          </div>

          <div className="grid grid-cols-1 gap-1.5 max-h-56 overflow-y-auto pr-1">
            {candidates.map((cand, idx) => (
              <div
                key={cand.id || idx}
                className="flex items-center justify-between rounded-lg border border-border bg-card/80 p-2.5 px-3 transition-colors hover:border-primary/40 hover:bg-accent/30 select-none"
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-500/15 text-blue-500 dark:text-blue-400 border border-blue-500/20">
                    <FileText className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Input
                        value={cand.name}
                        onChange={(e) => onUpdateCandidateName?.(idx, e.target.value)}
                        placeholder="Candidate Name (e.g. Ander Razvan)"
                        className="h-7 text-xs font-semibold px-2 py-0 bg-background/60 border-border/80 hover:border-primary/50 focus:border-primary focus:bg-background text-foreground rounded-md transition-colors max-w-[240px]"
                        title="Click to edit candidate name"
                      />
                      {cand.cvFileName && (
                        <span className="text-[10px] text-muted-foreground truncate hidden md:inline shrink-0">
                          ({cand.cvFileName})
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 px-0.5 text-[10px] text-muted-foreground truncate">
                      <CheckCircle2 className="h-2.5 w-2.5 text-emerald-500 shrink-0" />
                      <span className="truncate font-mono">
                        {cand.fileSizeFormatted ||
                          (cand.cvRawText
                            ? `${Math.round(cand.cvRawText.length / 100)} KB text`
                            : 'Ready')}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownload(cand);
                    }}
                    className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground hover:bg-accent cursor-pointer"
                    title="Download CV"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>

                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveCandidate(idx);
                    }}
                    className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                    title={t.cvUploader.remove}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
