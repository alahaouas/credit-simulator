import SimulatorForm from '@/components/SimulatorForm'

export default function SimulatePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-lg">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Run a simulation</h1>
        <p className="text-gray-500 mb-8">Enter your financial details to find the optimal loan plan.</p>
        <SimulatorForm />
      </div>
    </main>
  )
}
