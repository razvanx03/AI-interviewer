import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { useLanguage } from '@/hooks/use-language';

interface NotFoundPageProps {
  onNewInterview?: () => void;
}

export const NotFoundPage: React.FC<NotFoundPageProps> = ({ onNewInterview }) => {
  const navigate = useNavigate();
  const { t } = useLanguage();

  const handleAction = () => {
    if (onNewInterview) {
      onNewInterview();
    } else {
      navigate('/');
    }
  };

  return (
    <div className="flex h-full items-center justify-center p-6 bg-background">
      <Card className="w-full max-w-md text-center border-border">
        <CardHeader className="pb-4">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <AlertCircle className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-bold">{t.notFound.title}</CardTitle>
          <CardDescription className="text-xs">{t.notFound.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleAction} className="w-full gap-2" size="sm">
            <Plus className="h-4 w-4" />
            {t.notFound.button}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
