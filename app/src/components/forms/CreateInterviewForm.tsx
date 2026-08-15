import React, { useState } from 'react';
import { Briefcase, Building2, User, FileSpreadsheet, ArrowRight, Sparkles } from 'lucide-react';
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobTitle.trim() || !jobDescription.trim()) {
      alert('Please provide both a Job Title and Job Requirements.');
      return;
    }

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
    setJobTitle('Senior Full Stack Engineer');
    setCompanyName('Vercel');
    setCandidateName('Alex Morgan');
    setExperienceLevel('senior');
    setJobDescription(
      'Requirements:\n- 5+ years building modern React and TypeScript web applications.\n- Strong experience with Next.js, Node.js or Python backend APIs.\n- Expertise in database optimization (PostgreSQL) and caching.\n- Deep understanding of distributed systems and developer tooling.\n- Excellent communication skills for remote pair programming.'
    );
  };

  return (
    <Card className="w-full border-border/80 bg-card shadow-sm">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Briefcase className="h-4 w-4" />
            </div>
            <CardTitle className="text-xl font-bold">Configure Interview</CardTitle>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={fillSampleData}
            className="text-xs text-muted-foreground hover:text-primary"
          >
            <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
            Load Sample Data
          </Button>
        </div>
        <CardDescription>
          Provide the job specifics and upload the candidate's CV. The AI interviewer will tailor
          every question dynamically.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Job Title & Company */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="jobTitle" className="flex items-center gap-1.5">
                <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                Job Title / Role <span className="text-destructive">*</span>
              </Label>
              <Input
                id="jobTitle"
                placeholder="e.g. Senior Backend Engineer"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="companyName" className="flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                Company Name (Optional)
              </Label>
              <Input
                id="companyName"
                placeholder="e.g. Stripe, Acme Corp"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </div>
          </div>

          {/* Candidate Name & Seniority Level */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="candidateName" className="flex items-center gap-1.5">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                Candidate Name
              </Label>
              <Input
                id="candidateName"
                placeholder="e.g. Alex Morgan"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="experienceLevel" className="flex items-center gap-1.5">
                <FileSpreadsheet className="h-3.5 w-3.5 text-muted-foreground" />
                Seniority Level
              </Label>
              <Select
                value={experienceLevel}
                onValueChange={(val) => setExperienceLevel(val as ExperienceLevel)}
              >
                <SelectTrigger id="experienceLevel" className="w-full">
                  <SelectValue placeholder="Select seniority level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="entry">Entry Level (0-2 years)</SelectItem>
                  <SelectItem value="mid">Mid Level (2-5 years)</SelectItem>
                  <SelectItem value="senior">Senior Level (5+ years)</SelectItem>
                  <SelectItem value="lead">Lead / Principal (8+ years)</SelectItem>
                  <SelectItem value="executive">Executive / Management</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Job Description / Requirements */}
          <div className="space-y-1.5">
            <Label htmlFor="jobDescription" className="flex items-center gap-1.5">
              Job Description & Key Requirements <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="jobDescription"
              placeholder="Paste job description, required technical stack, responsibilities, or evaluation rubrics..."
              rows={4}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              required
            />
          </div>

          {/* CV Upload */}
          <div className="space-y-1.5">
            <Label className="flex items-center justify-between">
              <span>Candidate CV / Resume</span>
              <span className="text-xs text-muted-foreground">(PDF, DOCX, TXT)</span>
            </Label>
            <CVUploader onFileSelect={(file) => setCvFile(file)} selectedFileName={cvFile?.name} />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isLoading}
            size="lg"
            className="w-full gap-2 text-base font-semibold"
          >
            {isLoading ? (
              <span>Generating Interview Session...</span>
            ) : (
              <>
                <span>Launch AI Interview</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
