import MainLayout from '@/components/layout/MainLayout'

export default function HomePage() {
  return (
    <MainLayout>
      <h1 className="text-2xl font-bold text-slate-900">Bienvenido a demoIW</h1>
      <p className="mt-2 text-slate-600">
        Sistema de soporte para tratamiento de aguas residuales industriales.
      </p>
    </MainLayout>
  )
}
