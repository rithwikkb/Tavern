import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Post content is user-supplied, so strip scripts, event handlers and
// javascript: links from the generated HTML before it is rendered.
export const getMarkdownText = (markdown) => {
  return { __html: DOMPurify.sanitize(marked(markdown ?? '')) };
};
