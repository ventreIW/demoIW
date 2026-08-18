import { getTranslations } from 'next-intl/server'
import MainLayout from '@/components/layout/MainLayout'

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params
  const t = await getTranslations({ locale, namespace: 'app' })

  return (
    <MainLayout>
      <h1 className="text-2xl font-bold text-slate-900">{t('homeTitle')}</h1>
      <p className="mt-2 text-slate-600">{t('homeSubtitle')}</p>
    </MainLayout>
  )
}
