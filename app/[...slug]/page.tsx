import AppShell from '../app-shell'

export default async function WorkspacePage({ params }: { params: Promise<{ slug: string[] }> }) {
  const { slug } = await params
  return <AppShell route={slug.join('/')} />
}
