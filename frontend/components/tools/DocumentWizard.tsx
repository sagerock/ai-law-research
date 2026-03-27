'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, ArrowRight, Check, AlertCircle, type LucideIcon } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import type { ToolProject, ToolDocument } from '@/types'

export interface WizardStep {
  id: number
  label: string
  icon: LucideIcon
  description: string
}

export interface StepProps {
  project: ToolProject
  onSave: (updates: Partial<ToolProject>) => Promise<void>
  onDocumentsChange: (docs: ToolDocument[]) => void
}

interface DocumentWizardProps {
  toolType: string
  project: ToolProject
  steps: WizardStep[]
  onUpdate: (project: ToolProject) => void
  backUrl: string
  disclaimer: string
  stepComplete: (stepId: number, project: ToolProject) => boolean
  renderStep: (stepId: number, props: StepProps) => React.ReactNode
}

export default function DocumentWizard({
  toolType,
  project,
  steps,
  onUpdate,
  backUrl,
  disclaimer,
  stepComplete,
  renderStep,
}: DocumentWizardProps) {
  const router = useRouter()
  const { session } = useAuth()
  const [activeStep, setActiveStep] = useState(1)
  const [saving, setSaving] = useState(false)

  const saveProject = useCallback(
    async (updates: Partial<ToolProject>) => {
      setSaving(true)
      try {
        const token = session?.access_token
        const body: Record<string, any> = {}
        if (updates.title !== undefined) body.title = updates.title
        if (updates.case_info !== undefined) body.case_info = updates.case_info
        if (updates.form_data !== undefined) body.form_data = updates.form_data

        await fetch(`${API_URL}/api/v1/tools/${toolType}/projects/${project.id}`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        })

        onUpdate({ ...project, ...updates })
      } catch (e) {
        console.error('Failed to save:', e)
      } finally {
        setSaving(false)
      }
    },
    [project, session, onUpdate, toolType]
  )

  const handleDocumentsChange = useCallback(
    (docs: ToolDocument[]) => {
      onUpdate({ ...project, documents: docs })
    },
    [project, onUpdate]
  )

  const lastStep = steps[steps.length - 1].id

  const stepProps: StepProps = {
    project,
    onSave: saveProject,
    onDocumentsChange: handleDocumentsChange,
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push(backUrl)}
          className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="font-display text-xl text-stone-900 truncate">
            {project.case_info?.plaintiff && project.case_info?.defendant
              ? `${project.case_info.plaintiff} v. ${project.case_info.defendant}`
              : project.title}
          </h1>
          <p className="text-xs text-stone-500">
            {saving ? 'Saving...' : 'Auto-saved'}
          </p>
        </div>
      </div>

      {/* Educational disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5 mb-6 flex items-center gap-2">
        <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0" />
        <p className="text-xs text-amber-700">{disclaimer}</p>
      </div>

      <div className="flex gap-6">
        {/* Step Sidebar */}
        <div className="w-56 flex-shrink-0 hidden lg:block">
          <nav className="space-y-1">
            {steps.map((step) => {
              const Icon = step.icon
              const isActive = activeStep === step.id
              const isComplete = stepComplete(step.id, project)
              return (
                <button
                  key={step.id}
                  onClick={() => setActiveStep(step.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                    isActive
                      ? 'bg-sage-50 border border-sage-200 text-sage-800'
                      : 'hover:bg-stone-50 text-stone-600'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isComplete
                        ? 'bg-sage-600 text-white'
                        : isActive
                        ? 'bg-sage-100 text-sage-700'
                        : 'bg-stone-100 text-stone-400'
                    }`}
                  >
                    {isComplete ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : (
                      <Icon className="h-3.5 w-3.5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{step.label}</div>
                    <div className="text-[11px] text-stone-400 truncate">{step.description}</div>
                  </div>
                </button>
              )
            })}
          </nav>
        </div>

        {/* Mobile step indicator */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-stone-200 z-40 px-4 py-2">
          <div className="flex gap-1 justify-center">
            {steps.map((step) => (
              <button
                key={step.id}
                onClick={() => setActiveStep(step.id)}
                className={`flex-1 py-2 text-center rounded-lg text-xs font-medium transition-colors ${
                  activeStep === step.id
                    ? 'bg-sage-100 text-sage-700'
                    : stepComplete(step.id, project)
                    ? 'text-sage-600'
                    : 'text-stone-400'
                }`}
              >
                {step.label}
              </button>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="flex-1 min-w-0 pb-20 lg:pb-0">
          {renderStep(activeStep, stepProps)}

          {/* Navigation buttons */}
          {activeStep < lastStep && (
            <div className="flex justify-between mt-6">
              <button
                onClick={() => setActiveStep(Math.max(1, activeStep - 1))}
                disabled={activeStep === 1}
                className="flex items-center gap-2 px-4 py-2 text-sm text-stone-600 hover:bg-stone-100
                           rounded-lg transition-colors disabled:opacity-30"
              >
                <ArrowLeft className="h-4 w-4" /> Previous
              </button>
              <button
                onClick={() => setActiveStep(Math.min(lastStep, activeStep + 1))}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-sage-700 text-white
                           rounded-lg hover:bg-sage-600 transition-colors"
              >
                Next <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
