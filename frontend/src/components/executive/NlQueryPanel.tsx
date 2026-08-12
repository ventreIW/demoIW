'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { askQuestion, PortfolioNotScoredError } from '@/lib/api/executive'
import QueryResultChart from './QueryResultChart'
import type { NlQueryResponse } from '@/types/nlQuery'

interface NlQueryPanelProps {
  scenarioId: string
}

/** The supported vocabulary rendered as example questions, derived from the API
 *  response — never a hardcoded list that would drift from the backend.
 */
function renderExamples(t: (key: string) => string, supported: NlQueryResponse['supported']) {
  if (!supported) return null
  const groupers = supported.dimensions.length > 0 ? supported.dimensions.join(', ') : ''
  return (
    <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
      {supported.metrics.map((m) => (
        <li key={m}>{groupers ? `${m} — ${t('groupBy')}: ${groupers}` : m}</li>
      ))}
    </ul>
  )
}

export default function NlQueryPanel({ scenarioId }: NlQueryPanelProps) {
  const t = useTranslations('executivePage.query')
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<NlQueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isUnscored = error !== null && error.startsWith('PortfolioNotScored')

  async function handleSubmit() {
    const trimmed = question.trim()
    if (!trimmed || loading) return
    setLoading(true)
    setError(null)
    setResponse(null)
    try {
      const res = await askQuestion(scenarioId, trimmed)
      setResponse(res)
    } catch (e) {
      if (e instanceof PortfolioNotScoredError) {
        setError(`PortfolioNotScored:${e.message}`)
      } else {
        setError(e instanceof Error ? e.message : 'unknown')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <h2 className="mb-2 text-sm font-medium text-slate-700">{t('title')}</h2>
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSubmit()
          }}
          placeholder={t('placeholder')}
          className="h-9 flex-1 rounded-lg border border-slate-300 bg-white px-3 text-sm"
          aria-label="question"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={loading}
          className="h-9 rounded-lg bg-slate-900 px-4 text-sm font-medium text-white disabled:opacity-50"
        >
          {t('submit')}
        </button>
      </div>

      {loading && <p className="mt-3 text-sm text-slate-500">{t('loading')}</p>}

      {error && !isUnscored && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <p>{t('error')}</p>
          <p className="mt-1 text-xs text-red-500">{error}</p>
          <button
            type="button"
            onClick={handleSubmit}
            className="mt-2 rounded-lg border border-red-300 px-3 py-1 text-xs font-medium"
          >
            {t('retry')}
          </button>
        </div>
      )}

      {error && isUnscored && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
          <p>{error.replace('PortfolioNotScored:', '')}</p>
        </div>
      )}

      {response && response.answerable && response.result && (
        <div className="mt-3 space-y-3">
          <QueryResultChart result={response.result} />
          {response.narrative && (
            <p className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
              {response.narrative}
            </p>
          )}
          <p className="text-xs text-slate-500">
            {t('citation')}: {response.scenario.name} ({response.scenario.id})
          </p>
        </div>
      )}

      {response && !response.answerable && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
          <p className="text-sm font-medium text-slate-700">{t('cannotAnswer')}</p>
          {response.reason && (
            <p className="mt-1 text-sm text-slate-600">{t(`reason.${response.reason}`)}</p>
          )}
          {renderExamples(t, response.supported)}
          <p className="mt-2 text-xs text-slate-500">
            {t('citation')}: {response.scenario.name} ({response.scenario.id})
          </p>
        </div>
      )}
    </div>
  )
}
