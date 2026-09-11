import DOMPurify from 'dompurify'
import { marked } from 'marked'

const HTML_CFG = {
  ALLOWED_TAGS: [
    'p', 'br', 'div', 'span', 'strong', 'b', 'em', 'i', 'u', 's',
    'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code', 'h1', 'h2', 'h3', 'h4',
  ],
  ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'target', 'rel', 'class'],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'svg'],
}

function afterSanitize(node) {
  if (node.tagName === 'A') {
    const href = (node.getAttribute('href') || '').trim()
    if (!/^(https?:|mailto:|\/uploads\/)/i.test(href)) node.removeAttribute('href')
    node.setAttribute('rel', 'noopener noreferrer nofollow')
    node.setAttribute('target', '_blank')
  }
  if (node.tagName === 'IMG') {
    const src = (node.getAttribute('src') || '').trim()
    if (!/^(https?:\/\/|\/uploads\/)/i.test(src)) node.removeAttribute('src')
  }
}

if (typeof window !== 'undefined') {
  DOMPurify.addHook('afterSanitizeAttributes', afterSanitize)
}

export function sanitizeHtml(html) {
  return DOMPurify.sanitize(html || '', HTML_CFG)
}

export function renderMarkdown(text) {
  return sanitizeHtml(marked.parse(text || '', { async: false }))
}
