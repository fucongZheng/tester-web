import DOMPurify from 'dompurify'
import { marked } from 'marked'

const HTML_CFG = {
  ALLOWED_TAGS: [
    'p', 'br', 'hr', 'div', 'span', 'strong', 'b', 'em', 'i', 'u', 's',
    'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'pre', 'code', 'h1', 'h2', 'h3', 'h4',
    // markdown 表格（测试报告/AI 回答都大量用表格，缺了会被整段剥成纯文本）
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
  ],
  ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'target', 'rel', 'class', 'loading'],
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
    node.setAttribute('loading', 'lazy') // 富文本里截图多，进视口才加载
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
