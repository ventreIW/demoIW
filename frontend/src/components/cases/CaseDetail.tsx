'use client'

import { useState } from 'react'
import { useTranslations, useFormatter, useLocale } from 'next-intl'
import type { CaseDetail, RecordContactResultResponse } from '@/types/case-detail'
import ContactResultForm from '@/components/cases/ContactResultForm'

interface CaseDetailViewProps {
  detail: CaseDetail
  scenarioId?: string
  clientId?: string
}

export default function CaseDetailView({ detail, scenarioId, clientId }: CaseDetailViewProps) {
  const t = useTranslations('caseDetail')
  const formatter = useFormatter()
  const locale = useLocale()
  const [updatedScore, setUpdatedScore] = useState<number | null>(null)

  const REGIONAL: Record<string, string> = { es: 'es-MX', en: 'en-US' }
  const currency = new Intl.NumberFormat(REGIONAL[locale] ?? locale, {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  })

  const scoreValue = updatedScore ?? detail.score?.score_value ?? null
  const scoreCategory = detail.score?.category ?? null
  const scoreExplanation = detail.score?.explanation ?? null

  function handleContactSuccess(response: RecordContactResultResponse) {
    const clientScore = response.portfolio.scores.find(
      (s) => s.client_id === clientId,
    )
    if (clientScore) {
      setUpdatedScore(clientScore.score_value)
    }
  }

  return (
    <div className="space-y-8">
      {/* Client Profile */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">
          {t('sectionProfile')}
        </h2>
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <dl className="grid grid-cols-2 gap-3">
            <div>
              <dt className="text-slate-500">{t('name')}</dt>
              <dd className="font-medium text-slate-900">{detail.client.name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('sector')}</dt>
              <dd className="text-slate-700">
                {detail.client.sector_description ?? '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">{t('paymentPattern')}</dt>
              <dd className="text-slate-700">
                {detail.client.payment_history_pattern}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      {/* Score */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">
          {t('sectionScore')}
        </h2>
        {scoreValue !== null ? (
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <dl className="grid grid-cols-3 gap-3">
              <div>
                <dt className="text-slate-500">{t('scoreValue')}</dt>
                <dd className="text-xl font-bold text-slate-900">
                  {Math.round(scoreValue)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">{t('category')}</dt>
                <dd className="text-slate-700">{scoreCategory}</dd>
              </div>
              <div>
                <dt className="text-slate-500">{t('explanation')}</dt>
                <dd className="text-slate-700">{scoreExplanation}</dd>
              </div>
            </dl>
          </div>
        ) : (
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noScore')}
          </p>
        )}
      </section>

      {/* Invoices */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">
          {t('sectionInvoices')}
        </h2>
        {detail.invoices.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">{t('folio')}</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">{t('amount')}</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">{t('dueDate')}</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">{t('daysOverdue')}</th>
                  <th scope="col" className="px-4 py-3 font-medium">{t('status')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {detail.invoices.map((inv, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{inv.folio}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {currency.format(inv.amount)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {formatter.dateTime(new Date(inv.due_date), { dateStyle: 'medium' })}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {inv.days_overdue}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noComms')}
          </p>
        )}
      </section>

      {/* Payments */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">
          {t('sectionPayments')}
        </h2>
        {detail.payments.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th scope="col" className="px-4 py-3 text-right font-medium">{t('amount')}</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">{t('paymentDate')}</th>
                  <th scope="col" className="px-4 py-3 font-medium">{t('method')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {detail.payments.map((pmt, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {currency.format(pmt.amount)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {formatter.dateTime(new Date(pmt.payment_date), { dateStyle: 'medium' })}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{pmt.method}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noComms')}
          </p>
        )}
      </section>

      {/* Communications */}
      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">
          {t('sectionCommunications')}
        </h2>
        {detail.communications.length > 0 ? (
          <div className="space-y-3">
            {detail.communications.map((comm, i) => (
              <div key={i} className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
                <div className="mb-2 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5">{comm.channel}</span>
                  <span className="rounded bg-slate-100 px-1.5 py-0.5">{comm.tone}</span>
                  <span className="rounded bg-slate-100 px-1.5 py-0.5">{comm.status}</span>
                  <span>
                    {formatter.dateTime(new Date(comm.created_at), { dateStyle: 'medium', timeStyle: 'short' })}
                  </span>
                </div>
                <p className="text-slate-700">{comm.draft_text}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noComms')}
          </p>
        )}
      </section>

      {/* Contact Result Form */}
      {scenarioId && clientId && (
        <section>
          <ContactResultForm
            scenarioId={scenarioId}
            clientId={clientId}
            onSuccess={handleContactSuccess}
          />
        </section>
      )}
    </div>
  )
}