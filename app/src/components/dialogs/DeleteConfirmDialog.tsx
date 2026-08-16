import React from 'react';
import { AlertTriangle, Trash2, StopCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/hooks/use-language';

interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title?: string;
  description?: string;
  confirmText?: string;
  confirmIcon?: 'trash' | 'stop';
  confirmVariant?: 'destructive' | 'default';
}

export const DeleteConfirmDialog: React.FC<DeleteConfirmDialogProps> = ({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmText,
  confirmIcon = 'trash',
  confirmVariant = 'destructive',
}) => {
  const { t } = useLanguage();

  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="items-center sm:items-start text-center sm:text-left gap-1.5 sm:gap-2">
          <div className="flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded-lg sm:rounded-xl bg-destructive/10 text-destructive shrink-0">
            <AlertTriangle className="h-4 w-4 sm:h-4.5 sm:w-4.5" />
          </div>
          <DialogTitle className="text-sm sm:text-base font-bold text-foreground">
            {title || t.sidebar.deleteModalTitle}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            {description || t.sidebar.deleteModalDesc}
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="flex-row justify-end gap-2 mt-2 sm:mt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="flex-1 sm:flex-none h-8 sm:h-9 text-xs"
          >
            {t.sidebar.cancel}
          </Button>
          <Button
            type="button"
            variant={confirmVariant}
            size="sm"
            onClick={handleConfirm}
            className="flex-1 sm:flex-none h-8 sm:h-9 gap-1.5 text-xs font-semibold"
          >
            {confirmIcon === 'stop' ? (
              <StopCircle className="h-3.5 w-3.5" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
            {confirmText || t.sidebar.delete}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
