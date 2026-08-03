'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { generateCommunication, sendCommunication } from '@/lib/api/cases'
import type { CommunicationSummary } from '@/types/case-detail'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'

interface CommunicationsGeneratorProps {
  scenarioId: string
  clientId: string
}

const CHANNELS = ['email', 'phone', 'whatsapp'] as const
const TONES = ['formal', 'firm', 'urgent'] as const

export default function CommunicationsGenerator({
  scenarioId,
  clientId,
}: CommunicationsGeneratorProps) {
  const t = useTranslations('communications')

  const [channel, setChannel] = useState<string>('email')
  const [tone, setTone] = useState<string>('formal')
  const [draft, setDraft] = useState<CommunicationSummary | null>(null)
  const [draftText, setDraftText] = useState('')
  const [generating, setGenerating] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function handleGenerate() {
    setGenerating(true)
    setError(null)
    setSuccess(false)

    try {
      const result = await generateCommunication(scenarioId, clientId, {
        channel,
        tone,
      })
      setDraft(result)
      setDraftText(result.draft_text)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('generateError'))
    } finally {
      setGenerating(false)
    }
  }

  async function handleSend() {
    if (!draft) return

    const confirmed = window.confirm(t('sendConfirm'))
    if (!confirmed) return

    setSending(true)
    setError(null)

    try {
      const result = await sendCommunication(scenarioId, clientId, draft.id)
      setDraft(result)
      setDraftText(result.draft_text)
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('sendError'))
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-900">{t('sectionTitle')}</h3>

      <div className="space-y-3">
        {/* Channel selector */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700">{t('channel')}</label>
          <Select
            value={channel}
            onValueChange={(value: string | null) => {
              if (value) setChannel(value)
            }}
            disabled={generating || sending}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CHANNELS.map((ch) => (
                <SelectItem key={ch} value={ch}>
                  {t(`channels.${ch}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Tone selector */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700">{t('tone')}</label>
          <Select
            value={tone}
            onValueChange={(value: string | null) => {
              if (value) setTone(value)
            }}
            disabled={generating || sending}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TONES.map((tn) => (
                <SelectItem key={tn} value={tn}>
                  {t(`tones.${tn}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Generate button */}
        <Button onClick={handleGenerate} disabled={generating || sending} className="w-full">
          {generating ? (
            <span className="flex items-center gap-2">
              <Spinner />
              {t('generating')}
            </span>
          ) : (
            t('generateButton')
          )}
        </Button>

        {/* Draft area */}
        {draft && (
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">{t('draftLabel')}</label>
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              <span className="rounded bg-slate-100 px-1.5 py-0.5">
                {t(`channels.${draft.channel}`)}
              </span>
              <span className="rounded bg-slate-100 px-1.5 py-0.5">{t(`tones.${draft.tone}`)}</span>
            </div>
            <textarea
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              disabled={sending}
              rows={6}
              className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 outline-none transition-colors focus:border-slate-400 focus:ring-2 focus:ring-slate-100 disabled:opacity-50"
            />
          </div>
        )}

        {/* Send button */}
        {draft && draft.status === 'draft' && (
          <Button
            onClick={handleSend}
            disabled={sending || generating}
            className="w-full"
            variant="default"
          >
            {sending ? (
              <span className="flex items-center gap-2">
                <Spinner />
                {t('sending')}
              </span>
            ) : (
              t('sendButton')
            )}
          </Button>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {t('sendSuccess')}
          </div>
        )}
      </div>
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
