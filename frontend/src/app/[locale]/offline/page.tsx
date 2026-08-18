'use client'

import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'

/**
 * Precached by the service worker and served when a navigation fails. It must
 * stay free of any data dependency — it renders precisely when the network is
 * gone. See ADR-010.
 */
export default function OfflinePage() {
  const t = useTranslations('offline')

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="max-w-md text-center">
        <h1 className="text-2xl font-bold text-slate-900">{t('title')}</h1>
        <p className="mt-3 text-slate-600">{t('body')}</p>
        <Button className="mt-6" onClick={() => window.location.reload()}>
          {t('retry')}
        </Button>
      </div>
    </main>
  )
}
