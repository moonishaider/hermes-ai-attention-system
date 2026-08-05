import {
  Button,
  Input,
  KEYBINDS_AREA,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  StatusDot,
  host,
  useQuery
} from '@hermes/plugin-sdk'
import { useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

let pluginContext

const CONTEXTS = [
  ['inside-success', 'Inside Success'],
  ['mitchell', 'Mitchell'],
  ['personal', 'Personal'],
  ['mixed', 'Mixed'],
  ['unknown', 'Unknown']
]

function ContextSelect({ value, onChange }) {
  return jsx('select', {
    'aria-label': 'Current context',
    className: 'rounded border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1 text-sm',
    onChange: event => onChange(event.target.value),
    value,
    children: CONTEXTS.map(([id, label]) => jsx('option', { value: id, children: label }, id))
  })
}

function StatusLine({ ok, children }) {
  return jsxs('div', {
    className: 'flex items-center gap-2 text-xs text-(--ui-text-secondary)',
    children: [jsx(StatusDot, { tone: ok ? 'good' : 'bad' }), children]
  })
}

function AttentionHome() {
  const [contextId, setContextId] = useState(pluginContext.storage.get('context', 'unknown'))
  const [title, setTitle] = useState('')
  const [screenReason, setScreenReason] = useState('Explain the selected area')
  const [notice, setNotice] = useState('')
  const query = useQuery({
    queryKey: ['hermes-attention', 'home', contextId],
    queryFn: () => pluginContext.rest(`/home?context_id=${encodeURIComponent(contextId)}`),
    refetchInterval: 15000
  })
  const learningQuery = useQuery({
    queryKey: ['hermes-attention', 'learning'],
    queryFn: () => host.learningGraph(),
    staleTime: 30000
  })
  const data = query.data
  const status = data?.status
  const learnedNodes = [...(learningQuery.data?.nodes || [])]
    .sort((left, right) => (right.timestamp || 0) - (left.timestamp || 0))
    .slice(0, 3)

  const changeContext = value => {
    pluginContext.storage.set('context', value)
    setContextId(value)
  }

  const addTask = async () => {
    const clean = title.trim()
    if (!clean) return
    try {
      await pluginContext.rest('/tasks', { method: 'POST', body: { title: clean, context_id: contextId, priority: 50 } })
      setTitle('')
      setNotice('Local task saved. Nothing was sent externally.')
      await query.refetch()
    } catch (error) {
      host.notifyError(error, 'Could not save the local task')
    }
  }

  const screen = async () => {
    if (!['inside-success', 'mitchell', 'personal'].includes(contextId)) {
      setNotice('Choose Inside Success, Mitchell, or Personal before screen viewing.')
      return
    }
    setNotice('Choose one area in the visible macOS selector. No pixels are retained.')
    try {
      const result = await pluginContext.rest('/screen', {
        method: 'POST',
        body: { reason: screenReason.trim(), context_id: contextId },
        timeoutMs: 180000
      })
      setNotice(result.description || 'Selected area understood; no pixels retained.')
    } catch (error) {
      host.notifyError(error, 'One-shot screen view did not complete')
    }
  }

  const cancel = async () => {
    const sid = host.state.activeSessionId.get()
    if (!sid) {
      setNotice('No active response to cancel.')
      return
    }
    try {
      await host.request('session.interrupt', { session_id: sid })
      setNotice('Active response cancelled.')
    } catch (error) {
      host.notifyError(error, 'Could not cancel the active response')
    }
  }

  const stopSpeaking = () => {
    host.stopSpeaking()
    setNotice('Hermes stopped speaking. The written response remains on screen.')
  }

  return jsxs('div', {
    className: 'flex h-full flex-col gap-5 overflow-auto p-6 text-sm',
    children: [
      jsxs('div', {
        className: 'flex flex-wrap items-center justify-between gap-3',
        children: [
          jsxs('div', { children: [
            jsx('h1', { className: 'text-xl font-semibold', children: 'Hermes Attention' }),
            jsx('p', { className: 'text-(--ui-text-tertiary)', children: 'One assistant, separated contexts, source-backed work.' })
          ] }),
          jsx(ContextSelect, { value: contextId, onChange: changeContext })
        ]
      }),
      jsxs('section', { className: 'space-y-2', children: [
        jsx(StatusLine, { ok: status?.kill_switch === true, children: 'External-action kill switch is on' }),
        jsx(StatusLine, { ok: status?.external_writes_enabled === false, children: 'Company and client writes are unavailable' }),
        jsx(StatusLine, { ok: status?.budget?.level === 'ok', children: `Monthly model budget: ${status?.budget?.level || 'checking'}` }),
        jsx('div', { className: 'text-xs text-(--ui-text-tertiary)', children: query.isLoading ? 'Checking local status…' : `Context: ${contextId}` })
      ] }),
      jsxs('section', { className: 'space-y-2', children: [
        jsx('h2', { className: 'font-medium', children: 'Tasks and open loops' }),
        data?.queue?.length
          ? jsx('ul', { className: 'space-y-1', children: data.queue.map(item => jsx('li', { className: 'text-(--ui-text-secondary)', children: `• ${item.title}` }, item.task_id)) })
          : jsx('p', { className: 'text-(--ui-text-tertiary)', children: 'No open items in this context.' }),
        jsxs('div', { className: 'flex gap-2', children: [
          jsx(Input, { 'aria-label': 'New local task', value: title, onChange: event => setTitle(event.target.value), placeholder: 'Add a local task' }),
          jsx(Button, { onClick: () => void addTask(), children: 'Add' })
        ] })
      ] }),
      jsxs('section', { className: 'space-y-2', children: [
        jsx('h2', { className: 'font-medium', children: 'Screen understanding' }),
        jsx(Input, { 'aria-label': 'Screen-view reason', value: screenReason, onChange: event => setScreenReason(event.target.value) }),
        jsx(Button, { onClick: () => void screen(), variant: 'secondary', children: 'Look at selected area' }),
        jsx('p', { className: 'text-xs text-(--ui-text-tertiary)', children: 'One visible selection only. No continuous capture, retained screenshot, or computer control.' })
      ] }),
      jsxs('section', { className: 'space-y-2', children: [
        jsx('h2', { className: 'font-medium', children: 'Conversation controls' }),
        jsxs('div', { className: 'flex flex-wrap gap-2', children: [
          jsx(Button, { onClick: () => void cancel(), variant: 'secondary', children: 'Cancel response' }),
          jsx(Button, { onClick: stopSpeaking, variant: 'secondary', children: 'Stop speaking' }),
          jsx(Button, { onClick: () => host.navigate('/starmap'), variant: 'secondary', children: 'Open Memory Graph' })
        ] }),
        jsx('p', { className: 'text-xs text-(--ui-text-tertiary)', children: 'Use the microphone beside the chat box for voice. Speak over Hermes to interrupt, use the native Mute control, or press Control+Shift+S to stop speech immediately.' })
      ] }),
      jsxs('section', { className: 'space-y-2', children: [
        jsx('h2', { className: 'font-medium', children: 'Learning status' }),
        jsx('p', {
          className: 'text-(--ui-text-secondary)',
          children: learningQuery.isLoading
            ? 'Checking learned preferences and workflows…'
            : `${learningQuery.data?.nodes?.length || 0} learned item${learningQuery.data?.nodes?.length === 1 ? '' : 's'}`
        }),
        learnedNodes.length
          ? jsx('ul', {
              className: 'space-y-1',
              children: learnedNodes.map(node => jsx('li', {
                className: 'text-xs text-(--ui-text-secondary)',
                children: `${node.kind === 'memory' ? 'Memory' : 'Skill'}: ${node.label}`
              }, node.id))
            })
          : null,
        jsx('p', { className: 'text-xs text-(--ui-text-tertiary)', children: 'The advanced graph uses orange diamonds for memories and blue dots for skills. Right-click a node there to inspect or edit it; skill removal is recoverable archival.' })
      ] }),
      data?.latest_action
        ? jsxs('section', { className: 'space-y-1', children: [
            jsx('h2', { className: 'font-medium', children: 'Latest action preview' }),
            jsx('p', { className: 'text-(--ui-text-secondary)', children: `${data.latest_action.action_type} · ${data.latest_action.state}` }),
            jsx('code', { className: 'text-xs text-(--ui-text-tertiary)', children: data.latest_action.preview_hash }),
            jsx('p', { className: 'text-xs text-(--ui-text-tertiary)', children: 'Execution is not available from this plugin.' })
          ] })
        : null,
      notice ? jsx('p', { role: 'status', className: 'text-xs text-(--ui-text-secondary)', children: notice }) : null
    ]
  })
}

export default {
  id: 'hermes-attention',
  name: 'Hermes Attention',
  defaultEnabled: true,
  register(ctx) {
    pluginContext = ctx
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/hermes-attention' }, render: () => jsx(AttentionHome, {}) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: '/hermes-attention', label: 'Attention', codicon: 'eye' } },
      { id: 'open', area: PALETTE_AREA, data: { id: 'hermes-attention.open', label: 'Open Hermes Attention', keywords: ['attention', 'tasks', 'context'], run: () => host.navigate('/hermes-attention') } },
      { id: 'open-key', area: KEYBINDS_AREA, data: { id: 'hermes-attention.open', label: 'Open Hermes Attention', category: 'Hermes Attention', defaults: ['mod+shift+a'], run: () => host.navigate('/hermes-attention') } },
      { id: 'stop-speaking', area: PALETTE_AREA, data: { id: 'hermes-attention.stop-speaking', action: 'hermes-attention.stop-speaking', label: 'Stop Hermes speaking', keywords: ['voice', 'audio', 'interrupt', 'quiet'], run: () => host.stopSpeaking() } },
      { id: 'stop-speaking-key', area: KEYBINDS_AREA, data: { id: 'hermes-attention.stop-speaking', label: 'Stop Hermes speaking', category: 'Hermes Attention', defaults: ['ctrl+shift+s'], run: () => host.stopSpeaking() } }
    ])
  }
}
