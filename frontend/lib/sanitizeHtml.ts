import sanitize from 'sanitize-html'

const SEARCH_HIGHLIGHT_CLASS =
  'font-semibold text-sage-700 not-italic bg-sage-50 px-0.5 rounded'

export function sanitizeLegalHtml(
  html: string,
  options: { highlightSearchTerms?: boolean } = {},
): string {
  return sanitize(html, {
    allowedTags: [
      'a', 'abbr', 'b', 'blockquote', 'br', 'caption', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'div', 'dl', 'dt', 'em', 'figcaption', 'figure',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'mark',
      'ol', 'p', 'pre', 'q', 's', 'small', 'span', 'strong', 'sub', 'sup',
      'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul',
    ],
    allowedAttributes: {
      a: ['href', 'title', 'target', 'rel'],
      abbr: ['title'],
      col: ['span'],
      colgroup: ['span'],
      em: ['class'],
      img: ['src', 'alt', 'title', 'width', 'height'],
      ol: ['start', 'type'],
      td: ['colspan', 'rowspan', 'headers'],
      th: ['colspan', 'rowspan', 'headers', 'scope'],
    },
    allowedSchemes: ['http', 'https', 'mailto'],
    allowedSchemesByTag: { img: ['http', 'https'] },
    allowProtocolRelative: false,
    disallowedTagsMode: 'discard',
    transformTags: {
      a: (_tagName, attributes) => ({
        tagName: 'a',
        attribs: {
          ...attributes,
          ...(attributes.target === '_blank' ? { rel: 'noopener noreferrer' } : {}),
        },
      }),
      ...(options.highlightSearchTerms
        ? {
            em: (_tagName: string, attributes: Record<string, string>) => ({
              tagName: 'em',
              attribs: { ...attributes, class: SEARCH_HIGHLIGHT_CLASS },
            }),
          }
        : {}),
    },
  })
}
