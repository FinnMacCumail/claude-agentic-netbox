/**
 * Utility functions for formatting content in the chat interface.
 */

/**
 * Format a timestamp into a human-readable time string.
 */
export const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()

  // Check if same day
  const isToday = date.toDateString() === now.toDateString()

  // Format time
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const time = `${hours}:${minutes}`

  if (isToday) {
    return time
  }

  // Check if yesterday
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = date.toDateString() === yesterday.toDateString()

  if (isYesterday) {
    return `Yesterday ${time}`
  }

  // Format as date and time
  const day = date.getDate()
  const month = date.toLocaleString('default', { month: 'short' })
  return `${month} ${day}, ${time}`
}

/**
 * Basic markdown to HTML conversion for chat messages.
 * This is a simplified version - for production, consider using a library like marked.js
 */
export const formatMarkdown = (text: string): string => {
  let html = text

  // Escape HTML first
  html = html.replace(/&/g, '&amp;')
  html = html.replace(/</g, '&lt;')
  html = html.replace(/>/g, '&gt;')

  // Headers (h3, h2, h1)
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')

  // Bold text
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>')

  // Italic text
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  // Code blocks
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`
  })

  // Unordered lists
  html = html.replace(/^\* (.+)$/gm, '<li>$1</li>')
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    return `<ul>${match}</ul>`
  })

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    // Check if this is already wrapped in ul
    if (match.includes('<ul>')) return match
    // Check if this looks like an ordered list
    return `<ol>${match}</ol>`
  })

  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')

  // Line breaks
  html = html.replace(/\n\n/g, '</p><p>')
  html = `<p>${html}</p>`

  // Clean up empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, '')
  html = html.replace(/<p>(<h[1-6]>)/g, '$1')
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1')
  html = html.replace(/<p>(<ul>|<ol>|<blockquote>|<pre>)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')

  return html
}

/**
 * Truncate text to a maximum length with ellipsis.
 */
export const truncateText = (text: string, maxLength: number = 100): string => {
  if (text.length <= maxLength) {
    return text
  }
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Format bytes into human-readable format.
 */
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * Format a duration in milliseconds to human-readable format.
 */
export const formatDuration = (ms: number): string => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  }
  return `${seconds}s`
}