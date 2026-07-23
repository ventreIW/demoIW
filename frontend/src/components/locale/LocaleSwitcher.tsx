'use client'

import { useLocale } from 'next-intl'
import { useRouter, usePathname } from '@/i18n/routing'

export default function LocaleSwitcher() {
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const next = locale === 'es' ? 'en' : 'es'

  return (
    <button
      onClick={() => router.replace(pathname, { locale: next })}
      className="text-xs font-medium text-slate-500 hover:text-slate-800"
      aria-label={`Switch to ${next === 'en' ? 'English' : 'Spanish'}`}
    >
      {locale === 'es' ? 'EN' : 'ES'}
    </button>
  )
}
