/**
 * Utility functions for formatting content in the chat interface.
 */

import { marked, Renderer } from 'marked'
import DOMPurify from 'isomorphic-dompurify'
import hljs from 'highlight.js'

// Create custom renderer
const renderer = new Renderer()

// Override table rendering to add wrapper div and custom class
const originalTable = renderer.table.bind(renderer)
renderer.table = function(header: string, body: string): string {
  const table = originalTable(header, body)
  return `<div class="table-wrapper">${table.replace('<table>', '<table class="markdown-table">')}</div>`
}

// Override code rendering for syntax highlighting
const originalCode = renderer.code.bind(renderer)
renderer.code = function(code: string, language: string | undefined): string {
  if (language && hljs.getLanguage(language)) {
    try {
      const highlighted = hljs.highlight(code, { language }).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    } catch (err) {
      console.error('Syntax highlighting error:', err)
    }
  }
  return originalCode(code, language)
}

// Configure marked options
marked.setOptions({
  renderer: renderer,
  gfm: true, // GitHub Flavored Markdown
  breaks: true, // Convert \n to <br>
  pedantic: false
})

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
 * Convert markdown to HTML with syntax highlighting and table support.
 * Uses marked.js for markdown parsing and highlight.js for code syntax highlighting.
 */
export const formatMarkdown = (text: string): string => {
  try {
    // Parse markdown to HTML
    const rawHtml = marked.parse(text) as string

    // Sanitize HTML to prevent XSS attacks
    const sanitizedHtml = DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'a', 'ul', 'ol', 'li', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'div', 'span'
      ],
      ALLOWED_ATTR: ['href', 'target', 'class', 'rel'],
      ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
    })

    return sanitizedHtml
  } catch (error) {
    console.error('Error formatting markdown:', error)
    // Fallback to plain text if markdown parsing fails
    return text.replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
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