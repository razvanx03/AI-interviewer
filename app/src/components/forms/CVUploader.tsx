import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, CheckCircle2, X, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/hooks/use-language';

interface CVUploaderProps {
  onFileSelect: (file: File | null) => void;
  selectedFileName?: string;
}

export const CVUploader: React.FC<CVUploaderProps> = ({ onFileSelect, selectedFileName }) => {
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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      validateAndSelectFile(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSelectFile(e.target.files[0]);
    }
  };

  const validateAndSelectFile = (file: File) => {
    setUploadError(null);
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
    ];
    const isExtensionValid = /\.(pdf|docx|doc|txt)$/i.test(file.name);

    if (validTypes.includes(file.type) || isExtensionValid) {
      if (file.size > 10 * 1024 * 1024) {
        setUploadError(t.cvUploader.sizeError);
        return;
      }
      onFileSelect(file);
    } else {
      setUploadError(t.cvUploader.invalidType);
    }
  };

  const handleRemove = () => {
    onFileSelect(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-2">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf,.docx,.doc,.txt"
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

      {selectedFileName ? (
        <div className="flex items-center justify-between rounded-lg border border-primary/30 bg-primary/5 p-3 sm:p-3.5 transition-all">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
              <FileText className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs sm:text-sm font-medium text-foreground truncate">
                {selectedFileName}
              </p>
              <div className="flex items-center gap-1.5 text-[11px] sm:text-xs text-muted-foreground">
                <CheckCircle2 className="h-3 w-3 sm:h-3.5 sm:w-3.5 text-emerald-500 shrink-0" />
                <span className="truncate">{t.cvUploader.fileAttached}</span>
              </div>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleRemove}
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
            title={t.cvUploader.remove}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-4 sm:p-6 text-center transition-all ${
            isDragging
              ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
              : 'border-border/80 hover:border-primary/50 hover:bg-muted/30'
          }`}
        >
          <div className="mb-2 sm:mb-3 flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <UploadCloud className="h-5 w-5 sm:h-6 sm:w-6" />
          </div>
          <p className="text-xs sm:text-sm font-medium text-foreground">
            {t.cvUploader.dragPrompt}{' '}
            <span className="text-primary underline">{t.cvUploader.browse}</span>
          </p>
          <p className="mt-0.5 sm:mt-1 text-[11px] sm:text-xs text-muted-foreground">
            {t.cvUploader.supportedTypes}
          </p>
        </div>
      )}
    </div>
  );
};
