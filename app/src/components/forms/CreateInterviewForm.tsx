import React, { useState } from 'react';
import {
  Briefcase,
  Building2,
  User,
  FileSpreadsheet,
  ArrowRight,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CVUploader } from '@/components/forms/CVUploader';
import { useLanguage } from '@/hooks/use-language';
import { CreateInterviewInput, ExperienceLevel } from '@/types';

interface CreateInterviewFormProps {
  onSubmit: (data: CreateInterviewInput) => void;
  isLoading?: boolean;
}

export const CreateInterviewForm: React.FC<CreateInterviewFormProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const [jobTitle, setJobTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [candidateName, setCandidateName] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>('mid');
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const { t } = useLanguage();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim() || !jobDescription.trim()) {
      setFormError(t.form.validationError);
      return;
    }
    setFormError(null);

    onSubmit({
      jobTitle: jobTitle.trim(),
      companyName: companyName.trim() || undefined,
      candidateName: candidateName.trim() || 'Candidate',
      jobDescription: jobDescription.trim(),
      experienceLevel,
      cvFile,
      cvFileName: cvFile ? cvFile.name : undefined,
    });
  };

  const fillSampleData = () => {
    setFormError(null);
    setJobTitle('Senior Full Stack Engineer');
    setCompanyName('Google');
    setCandidateName('Alex Morgan');
    setExperienceLevel('senior');
    setJobDescription(
      'Requirements:\n- 5+ years building modern React and TypeScript web applications.\n- Strong experience with Next.js, Node.js or Python backend APIs.\n- Expertise in database optimization (PostgreSQL) and caching.\n- Deep understanding of distributed systems and developer tooling.\n- Excellent communication skills for remote pair programming.'
    );
  };

  return (
    <Card className="w-full border-border bg-card shadow-xs">
      <CardHeader className="p-4 sm:p-6 pb-2 sm:pb-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-7 w-7 sm:h-8 sm:w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Briefcase className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            </div>
            <CardTitle className="text-base sm:text-xl font-bold truncate">
              {t.form.title}
            </CardTitle>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={fillSampleData}
            className="h-8 text-xs text-muted-foreground hover:text-primary shrink-0 px-2 sm:px-3"
          >
            <Sparkles className="mr-1 sm:mr-1.5 h-3.5 w-3.5 text-amber-500" />
            <span>{t.form.loadSample}</span>
          </Button>
        </div>
        <CardDescription className="text-xs sm:text-sm mt-1">{t.form.description}</CardDescription>
      </CardHeader>

      <CardContent className="p-4 sm:p-6 pt-0 sm:pt-0">
        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
          {/* Validation Error Banner */}
          {formError && (
            <div className="flex items-center gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          {/* Job Title & Company */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="jobTitle" className="flex items-center gap-1.5 text-xs sm:text-sm">
                <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                {t.form.jobTitleLabel} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="jobTitle"
                placeholder={t.form.jobTitlePlaceholder}
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                required
                className="h-9 sm:h-10 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="companyName" className="flex items-center gap-1.5 text-xs sm:text-sm">
                <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                {t.form.companyLabel}
              </Label>
              <Input
                id="companyName"
                placeholder={t.form.companyPlaceholder}
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="h-9 sm:h-10 text-sm"
              />
            </div>
          </div>

          {/* Candidate Name & Seniority Level */}
          <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label
                htmlFor="candidateName"
                className="flex items-center gap-1.5 text-xs sm:text-sm"
              >
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                {t.form.candidateLabel}
              </Label>
              <Input
                id="candidateName"
                placeholder={t.form.candidatePlaceholder}
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                className="h-9 sm:h-10 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <Label
                htmlFor="experienceLevel"
                className="flex items-center gap-1.5 text-xs sm:text-sm"
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-muted-foreground" />
                {t.form.seniorityLabel}
              </Label>
              <Select
                value={experienceLevel}
                onValueChange={(val) => setExperienceLevel(val as ExperienceLevel)}
              >
                <SelectTrigger id="experienceLevel" className="h-9 sm:h-10 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="entry">{t.form.seniorityEntry}</SelectItem>
                  <SelectItem value="mid">{t.form.seniorityMid}</SelectItem>
                  <SelectItem value="senior">{t.form.senioritySenior}</SelectItem>
                  <SelectItem value="lead">{t.form.seniorityLead}</SelectItem>
                  <SelectItem value="executive">{t.form.seniorityExecutive}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Job Description / Requirements */}
          <div className="space-y-1.5">
            <Label
              htmlFor="jobDescription"
              className="flex items-center gap-1.5 text-xs sm:text-sm"
            >
              {t.form.jobDescLabel} <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="jobDescription"
              placeholder={t.form.jobDescPlaceholder}
              rows={5}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="min-h-[120px] sm:min-h-[160px] resize-y text-sm"
              required
            />
          </div>

          {/* CV Upload */}
          <div className="space-y-1.5">
            <Label className="flex items-center justify-between text-xs sm:text-sm">
              <span>{t.form.cvLabel}</span>
              <span className="text-[11px] sm:text-xs text-muted-foreground">
                {t.form.cvFormats}
              </span>
            </Label>
            <CVUploader onFileSelect={(file) => setCvFile(file)} selectedFileName={cvFile?.name} />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isLoading}
            size="lg"
            className="w-full gap-2 text-sm sm:text-base font-semibold h-11 sm:h-12"
          >
            {isLoading ? (
              <span>{t.form.generatingButton}</span>
            ) : (
              <>
                <span>{t.form.submitButton}</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
