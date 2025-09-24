'use client'

import { useState } from 'react'
import { Upload, FileText, Loader2, AlertCircle, CheckCircle, TrendingUp, XCircle, DollarSign } from 'lucide-react'

interface BriefAnalysisResult {
  filename: string
  total_citations: number
  extracted_citations: any[]
  validated_citations: any[]
  missing_authorities: any[]
  problematic_citations: any[]
  suggested_cases: any[]
  key_arguments: string[]
  ai_summary?: string
  analysis_cost: number
  status: string
}

export default function BriefUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [useAI, setUseAI] = useState(false)
  const [result, setResult] = useState<BriefAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFile = (file: File) => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if (validTypes.includes(file.type) || file.name.endsWith('.pdf') || file.name.endsWith('.docx') || file.name.endsWith('.txt')) {
      setFile(file)
      setError(null)
    } else {
      setError('Please upload a PDF, DOCX, or TXT file')
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const analyzeBrief = async () => {
    if (!file) return

    setIsAnalyzing(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`http://localhost:8000/api/v1/briefcheck?use_ai=${useAI}`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Analysis failed')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError('Failed to analyze brief. Please try again.')
      console.error(err)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const getCitationBadge = (status: string) => {
    switch (status) {
      case 'valid':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />
      default:
        return <XCircle className="h-4 w-4 text-red-600" />
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-neutral-900 mb-2">Brief Check</h2>
        <p className="text-neutral-600">
          Upload your legal brief to extract citations, validate authorities, and get AI-powered suggestions.
        </p>
      </div>

      {/* Upload Area */}
      {!result && (
        <div className="bg-white rounded-lg border-2 border-dashed border-neutral-300 p-8">
          <div
            className={`relative ${dragActive ? 'bg-blue-50' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={handleFileInput}
              accept=".pdf,.docx,.txt"
            />

            <label
              htmlFor="file-upload"
              className="flex flex-col items-center cursor-pointer"
            >
              <Upload className="h-12 w-12 text-neutral-400 mb-4" />
              <p className="text-lg font-medium text-neutral-700">
                Drop your brief here or click to browse
              </p>
              <p className="text-sm text-neutral-500 mt-2">
                Supports PDF, DOCX, and TXT files
              </p>
            </label>
          </div>

          {file && (
            <div className="mt-6 flex items-center justify-between bg-neutral-50 p-4 rounded-lg">
              <div className="flex items-center">
                <FileText className="h-5 w-5 text-neutral-600 mr-3" />
                <span className="text-neutral-700">{file.name}</span>
              </div>
              <button
                onClick={() => setFile(null)}
                className="text-red-600 hover:text-red-700"
              >
                Remove
              </button>
            </div>
          )}

          {/* AI Toggle */}
          <div className="mt-6 flex items-center justify-between p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="use-ai"
                checked={useAI}
                onChange={(e) => setUseAI(e.target.checked)}
                className="mr-3 h-4 w-4 text-blue-600 rounded"
              />
              <label htmlFor="use-ai" className="flex items-center">
                <span className="text-neutral-700 font-medium">Enable AI Analysis</span>
                <span className="ml-2 text-sm text-neutral-600">
                  (~$0.002 per brief with GPT-5-mini)
                </span>
                <DollarSign className="h-3 w-3 text-green-600 ml-1" />
              </label>
            </div>
            <div className="text-xs text-neutral-500">
              Adds case suggestions & summary
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center">
              <AlertCircle className="h-5 w-5 mr-2" />
              {error}
            </div>
          )}

          {file && (
            <button
              onClick={analyzeBrief}
              disabled={isAnalyzing}
              className="mt-6 w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-neutral-400 flex items-center justify-center"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  Analyzing Brief...
                </>
              ) : (
                <>
                  <TrendingUp className="h-5 w-5 mr-2" />
                  Analyze Brief
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary Stats */}
          <div className="bg-white rounded-lg border p-6">
            <h3 className="text-lg font-semibold text-neutral-900 mb-4">Analysis Summary</h3>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{result.total_citations}</div>
                <div className="text-sm text-neutral-600">Citations Found</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{result.validated_citations.length}</div>
                <div className="text-sm text-neutral-600">Valid Citations</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{result.problematic_citations.length}</div>
                <div className="text-sm text-neutral-600">Issues Found</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{result.missing_authorities.length}</div>
                <div className="text-sm text-neutral-600">Missing Cases</div>
              </div>
            </div>
            {result.analysis_cost > 0 && (
              <div className="mt-4 text-sm text-neutral-600 text-center">
                Analysis cost: ${result.analysis_cost.toFixed(4)}
              </div>
            )}
          </div>

          {/* Validated Citations */}
          {result.validated_citations.length > 0 && (
            <div className="bg-green-50 rounded-lg border border-green-200 p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center">
                <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                Valid Citations Found in Database
              </h3>
              <div className="space-y-3">
                {result.validated_citations.map((cite, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-lg flex items-start justify-between">
                    <div className="flex items-start">
                      <CheckCircle className="h-4 w-4 text-green-600 mt-1 mr-3 flex-shrink-0" />
                      <div>
                        <div className="font-medium text-neutral-700">
                          {cite.citation.text || cite.citation.case_name ||
                           `${cite.citation.volume} ${cite.citation.reporter} ${cite.citation.page}`}
                        </div>
                        {cite.found_case && (
                          <div className="text-sm text-neutral-600 mt-1">
                            Database: {cite.found_case.case_name}
                            {cite.found_case.date_filed && (
                              <span className="ml-2">
                                ({new Date(cite.found_case.date_filed).getFullYear()})
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                      Good Law
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Summary */}
          {result.ai_summary && (
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200 p-6">
              <h3 className="text-xl font-bold text-neutral-900 mb-4 flex items-center">
                <span className="mr-2">🤖</span> AI Case Analysis
              </h3>
              <div className="prose prose-sm max-w-none text-neutral-700">
                {result.ai_summary.split('\n').map((line, idx) => {
                  // Style headers differently
                  if (line.includes('📋') || line.includes('⚖️') || line.includes('📚') ||
                      line.includes('💡') || line.includes('🎯')) {
                    return (
                      <h4 key={idx} className="font-bold text-neutral-800 mt-4 mb-2">
                        {line}
                      </h4>
                    )
                  }
                  // Style bullet points
                  else if (line.trim().startsWith('-')) {
                    return (
                      <p key={idx} className="ml-4 text-neutral-700 mb-1">
                        {line}
                      </p>
                    )
                  }
                  // Regular paragraphs
                  else if (line.trim()) {
                    return (
                      <p key={idx} className="text-neutral-700 mb-2">
                        {line}
                      </p>
                    )
                  }
                  return null
                })}
              </div>
              <div className="mt-4 pt-4 border-t border-blue-100 flex justify-between items-center">
                <span className="text-xs text-neutral-600">
                  Powered by GPT-5-mini
                </span>
                <span className="text-xs text-neutral-600">
                  Analysis cost: ${result.analysis_cost.toFixed(4)}
                </span>
              </div>
            </div>
          )}

          {/* Key Arguments */}
          {result.key_arguments.length > 0 && (
            <div className="bg-white rounded-lg border p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">Key Arguments Identified</h3>
              <ul className="space-y-3">
                {result.key_arguments.map((arg, idx) => (
                  <li key={idx} className="flex items-start">
                    <span className="text-blue-600 mr-2">•</span>
                    <span className="text-neutral-700">{arg}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Problematic Citations */}
          {result.problematic_citations.length > 0 && (
            <div className="bg-yellow-50 rounded-lg border border-yellow-200 p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center">
                <AlertCircle className="h-5 w-5 text-yellow-600 mr-2" />
                Citations Needing Attention
              </h3>
              <div className="space-y-3">
                {result.problematic_citations.map((cite, idx) => (
                  <div key={idx} className="flex items-start">
                    {getCitationBadge(cite.status)}
                    <div className="ml-3">
                      <div className="font-medium text-neutral-700">
                        {typeof cite.citation.text === 'string' && cite.citation.text.trim()
                          ? cite.citation.text
                          : cite.citation.case_name ||
                            (cite.citation.volume && cite.citation.reporter && cite.citation.page
                              ? `${cite.citation.volume} ${cite.citation.reporter} ${cite.citation.page}`
                              : 'Unknown Citation')}
                      </div>
                      <div className="text-sm text-neutral-600">{cite.problem}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Missing Authorities */}
          {result.missing_authorities.length > 0 && (
            <div className="bg-purple-50 rounded-lg border border-purple-200 p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4">
                Suggested Foundation Cases
              </h3>
              <div className="space-y-3">
                {result.missing_authorities.map((auth, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-lg">
                    <div className="font-medium text-neutral-700">
                      {auth.case?.case_name || 'Unknown Case'}
                    </div>
                    <div className="text-sm text-neutral-600 mt-1">
                      {auth.reason} • Importance: {auth.importance}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Suggested Cases */}
          {result.suggested_cases.length > 0 && (
            <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
              <h3 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center">
                <span className="mr-2">✨</span> AI-Suggested Similar Cases
              </h3>
              <div className="space-y-3">
                {result.suggested_cases.map((sugg, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-lg">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium text-neutral-700">
                          {sugg.case?.case_name || 'Unknown Case'}
                        </div>
                        <div className="text-sm text-neutral-600 mt-1">
                          Matched: "{sugg.argument_matched || ''}"
                        </div>
                      </div>
                      <div className="text-sm bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        {((sugg.similarity || 0) * 100).toFixed(0)}% match
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => {
              setResult(null)
              setFile(null)
            }}
            className="w-full bg-neutral-600 text-white py-3 px-6 rounded-lg hover:bg-neutral-700"
          >
            Analyze Another Brief
          </button>
        </div>
      )}
    </div>
  )
}