'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { recordContactResult } from '@/lib/api/cases'
import type { ContactResultType, RecordContactResultResponse } from '@/types/case-detail'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'

interface ContactResultFormProps {
  scenarioId: string
  clientId: string
  onSuccess: (response: RecordContactResultResponse) => void
}

const CONTACT_RESULT_TYPES: ContactResultType[] = [
  'promise_to_pay',
  'partial_payment',
  'no_answer',
  'disputed',
  'paid',
]

export default function ContactResultForm({
  scenarioId,
  clientId,
  onSuccess,
}: ContactResultFormProps) {
  const t = useTranslations('contactResult')

  const [contactResult, setContactResult] = useState<ContactResultType>('promise_to_pay')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      const response = await recordContactResult(scenarioId, clientId, {
        contact_result: contactResult,
        notes: notes || undefined,
      })
      setSuccess(true)
      onSuccess(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">{t('sectionTitle')}</h3>

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Contact result type */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700">{t('contactResult')}</label>
          <Select
            value={contactResult}
            onValueChange={(v) => setContactResult(v as ContactResultType)}
            disabled={loading}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CONTACT_RESULT_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {t(`types.${type}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Notes */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700" htmlFor="notes">
            {t('notes')}
          </label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={loading}
            rows={2}
            className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-slate-400 focus:ring-2 focus:ring-slate-100 disabled:opacity-50"
            placeholder={t('notes')}
          />
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {t('success')}
          </div>
        )}

        {/* Submit */}
        <Button type="submit" disabled={loading} className="w-full">
          {loading ? (
            <span className="flex items-center gap-2">
              <Spinner />
              {t('record')}
            </span>
          ) : (
            t('recordButton')
          )}
        </Button>
      </form>
    </section>
  )
}

function Spinner() {
  return (
    <svg
      className="size-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}