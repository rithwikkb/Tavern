import React from 'react';
import { getMarkdownText } from '../utils/getMarkdownText';
import '../styles/components/MarkdownEditor.css';

const MarkdownEditor = ({ markdown, setMarkdown }) => {
  const handleChange = (event) => {
    setMarkdown(event.target.value);
  };

  return (
    <div className="markdown-editor">
      <div className="markdown-pane">
        <label className="markdown-pane-label" htmlFor="markdown-textarea">Write</label>
        <textarea
          id="markdown-textarea"
          value={markdown}
          onChange={handleChange}
          placeholder={'**Bold**, _italic_, # headings, - lists, [links](https://...)'}
        />
      </div>
      <div className="markdown-pane">
        <span className="markdown-pane-label">Preview</span>
        <div
          className="markdown-preview post-markdown"
          dangerouslySetInnerHTML={getMarkdownText(markdown)}
        />
      </div>
    </div>
  );
};

export default MarkdownEditor;
