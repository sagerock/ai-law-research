'use client'

import { Scale, Upload, User, List, Sparkles } from 'lucide-react'
import DocumentWizard, { type StepProps } from '@/components/tools/DocumentWizard'
import SharedCaseInfo from '@/components/tools/SharedCaseInfo'
import SharedDocumentUpload from '@/components/tools/SharedDocumentUpload'
import SharedChat from '@/components/tools/SharedChat'
import AffiantInfo from './AffiantInfo'
import AffidavitFacts from './AffidavitFacts'
import type { ToolProject, AffidavitFormData } from '@/types'

interface AffidavitWizardProps {
  project: ToolProject
  onUpdate: (project: ToolProject) => void
}

const STEPS = [
  { id: 1, label: 'Case Info', icon: Scale, description: 'Parties, court, jurisdiction' },
  { id: 2, label: 'Documents', icon: Upload, description: 'Depositions, discovery, exhibits' },
  { id: 3, label: 'Affiant', icon: User, description: 'Who is making this affidavit' },
  { id: 4, label: 'Facts', icon: List, description: 'Facts affiant can attest to' },
  { id: 5, label: 'Generate', icon: Sparkles, description: 'AI drafting & export' },
]

const PRESET_PROMPTS = [
  { label: 'Review my facts', prompt: 'Review my attestable facts. Are they properly based on personal knowledge? Are any too conclusory or argumentative?' },
  { label: 'Suggest additional facts', prompt: 'Based on the uploaded documents, what additional facts could this affiant attest to from personal knowledge?' },
  { label: 'Check for hearsay', prompt: 'Review my draft for any hearsay issues. Flag any statements that may not be based on personal knowledge.' },
  { label: 'Improve specificity', prompt: 'Review my facts for specificity. Suggest where I need more precise dates, times, locations, or names.' },
]

function stepComplete(stepId: number, project: ToolProject): boolean {
  const formData = project.form_data as AffidavitFormData | undefined
  switch (stepId) {
    case 1:
      return !!(project.case_info?.plaintiff && project.case_info?.defendant)
    case 2:
      return (project.documents?.length ?? 0) > 0
    case 3:
      return !!(formData?.affiant_info?.name)
    case 4:
      return (formData?.attestable_facts?.length ?? 0) > 0
    case 5:
      return project.status === 'complete'
    default:
      return false
  }
}

function renderStep(stepId: number, { project, onSave, onDocumentsChange }: StepProps) {
  const formData = (project.form_data || {}) as AffidavitFormData

  switch (stepId) {
    case 1:
      return (
        <SharedCaseInfo
          caseInfo={project.case_info || {}}
          onChange={(info) => onSave({ case_info: info })}
        />
      )
    case 2:
      return (
        <SharedDocumentUpload
          toolType="affidavit"
          projectId={project.id}
          title="Upload Supporting Documents"
          description="Upload depositions, discovery responses, exhibits, and other documents that contain facts the affiant can attest to."
          docTypes={['deposition', 'discovery', 'exhibit', 'pleading', 'evidence']}
          documents={project.documents || []}
          onDocumentsChange={onDocumentsChange}
        />
      )
    case 3:
      return (
        <AffiantInfo
          affiantInfo={formData.affiant_info || {}}
          onChange={(info) => onSave({ form_data: { ...formData, affiant_info: info } })}
        />
      )
    case 4:
      return (
        <AffidavitFacts
          facts={formData.attestable_facts || []}
          documents={project.documents || []}
          onChange={(facts) => onSave({ form_data: { ...formData, attestable_facts: facts } })}
        />
      )
    case 5:
      return (
        <SharedChat
          toolType="affidavit"
          project={project}
          onProjectUpdate={(p) => onSave(p)}
          generateLabel="Generate Affidavit"
          regenerateLabel="Regenerate Affidavit"
          documentLabel="Generated Affidavit"
          chatPlaceholder="Ask about your affidavit, request revisions, or get suggestions..."
          presetPrompts={PRESET_PROMPTS}
        />
      )
    default:
      return null
  }
}

export default function AffidavitWizard({ project, onUpdate }: AffidavitWizardProps) {
  return (
    <DocumentWizard
      toolType="affidavit"
      project={project}
      steps={STEPS}
      onUpdate={onUpdate}
      backUrl="/tools/affidavit"
      disclaimer="Educational tool only. Generated affidavits should not be filed with any court."
      stepComplete={stepComplete}
      renderStep={renderStep}
    />
  )
}
