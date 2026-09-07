"use client";

/**
 * src/components/ChatMessages.js
 * Renders chat messages + special Connect Zoho card + Live Transcript feedback
 */
import { motion, AnimatePresence } from "motion/react";
import { useEffect, useRef } from "react";

// Helper to render inline elements (bold, italic, code, links)
function renderInline(text, theme) {
  if (!text) return null;

  const parts = [];
  const inlineRegex = /(\[.*?\]\(.*?\))|(\*\*.*?\*\*)|(\*.*?\*)|(`.*?`)/g;
  
  let match;
  let lastIndex = 0;
  
  while ((match = inlineRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    
    const token = match[0];
    if (token.startsWith('[') && token.includes('](')) {
      const linkMatch = token.match(/\[(.*?)\]\((.*?)\)/);
      if (linkMatch) {
        parts.push(
          <a 
            key={match.index} 
            href={linkMatch[2]} 
            target="_blank" 
            rel="noopener noreferrer" 
            className={`underline font-semibold transition-colors duration-200 ${
              theme === "dark" ? "text-[#00d9ff] hover:text-[#0078D7]" : "text-[#0078D7] hover:text-[#0066bb]"
            }`}
          >
            {linkMatch[1]}
          </a>
        );
      }
    } else if (token.startsWith('**') && token.endsWith('**')) {
      const content = token.substring(2, token.length - 2);
      parts.push(
        <strong key={match.index} className={`font-extrabold ${theme === "dark" ? "text-white font-semibold" : "text-gray-950 font-bold"}`}>
          {content}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      const content = token.substring(1, token.length - 1);
      parts.push(
        <em key={match.index} className={`italic ${theme === "dark" ? "text-white/80" : "text-gray-700"}`}>
          {content}
        </em>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      const content = token.substring(1, token.length - 1);
      parts.push(
        <code 
          key={match.index} 
          className={`px-1.5 py-0.5 rounded text-xs font-mono border ${
            theme === "dark" 
              ? "bg-white/10 text-cyan-300 border-white/5" 
              : "bg-gray-100 text-cyan-700 border-gray-200"
          }`}
        >
          {content}
        </code>
      );
    }
    
    lastIndex = inlineRegex.lastIndex;
  }
  
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  
  return parts.length > 0 ? parts : text;
}

// Main Markdown block parser & renderer
function MarkdownRenderer({ content, theme }) {
  if (!content) return null;
  
  const lines = content.split('\n');
  const blocks = [];
  let currentBlock = null;

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (trimmed === '') {
      if (currentBlock) {
        blocks.push(currentBlock);
        currentBlock = null;
      }
      continue;
    }

    // Header check
    const headerMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headerMatch) {
      if (currentBlock) {
        blocks.push(currentBlock);
        currentBlock = null;
      }
      const level = headerMatch[1].length;
      const text = headerMatch[2];
      blocks.push({ type: 'header', level, text });
      continue;
    }

    // List item check: matches "- ", "* ", "• ", or "1. ", "2. ", etc.
    const listMatch = trimmed.match(/^([-*•]|\d+\.)\s+(.*)$/);
    if (listMatch) {
      const isNumbered = /^\d+\./.test(listMatch[1]);
      const text = listMatch[2];

      if (currentBlock && currentBlock.type === 'list' && currentBlock.numbered === isNumbered) {
        currentBlock.items.push(text);
      } else {
        if (currentBlock) {
          blocks.push(currentBlock);
        }
        currentBlock = { type: 'list', numbered: isNumbered, items: [text] };
      }
      continue;
    }

    // Table row check
    const isTable = trimmed.includes('|') || rawLine.includes('\t');
    if (isTable) {
      let cols = [];
      if (trimmed.includes('|')) {
        cols = trimmed.split('|').map(c => c.trim());
        if (cols[0] === '') cols.shift();
        if (cols[cols.length - 1] === '') cols.pop();
      } else {
        cols = rawLine.split('\t').map(c => c.trim());
      }

      const isSeparator = cols.every(col => /^-+$/.test(col));
      if (isSeparator) {
        if (currentBlock && currentBlock.type === 'table' && currentBlock.rows.length > 0) {
          currentBlock.hasHeader = true;
        }
        continue;
      }

      if (currentBlock && currentBlock.type === 'table') {
        currentBlock.rows.push(cols);
      } else {
        if (currentBlock) {
          blocks.push(currentBlock);
        }
        currentBlock = { type: 'table', hasHeader: false, rows: [cols] };
      }
      continue;
    }

    // Paragraph accumulation
    if (currentBlock && currentBlock.type === 'paragraph') {
      currentBlock.text += '\n' + trimmed;
    } else {
      if (currentBlock) {
        blocks.push(currentBlock);
      }
      currentBlock = { type: 'paragraph', text: trimmed };
    }
  }

  if (currentBlock) {
    blocks.push(currentBlock);
  }

  return (
    <div className="space-y-2">
      {blocks.map((block, bIdx) => {
        switch (block.type) {
          case 'header': {
            const hClass = block.level === 1 
              ? `text-lg font-extrabold tracking-tight mt-3 mb-1 font-['Sora'] ${theme === "dark" ? "text-white" : "text-gray-900"}`
              : block.level === 2
              ? `text-base font-bold tracking-tight mt-2.5 mb-1 font-['Sora'] ${theme === "dark" ? "text-white" : "text-gray-900"}`
              : `text-sm font-semibold mt-2 mb-0.5 font-['Sora'] ${theme === "dark" ? "text-white" : "text-gray-900"}`;
            const Tag = block.level <= 6 ? `h${block.level}` : 'h6';
            return <Tag key={bIdx} className={hClass}>{renderInline(block.text, theme)}</Tag>;
          }
          case 'list': {
            const ListTag = block.numbered ? 'ol' : 'ul';
            const listClass = block.numbered 
              ? "list-decimal pl-5 space-y-1 my-1" 
              : "list-disc pl-5 space-y-1 my-1";
            return (
              <ListTag key={bIdx} className={listClass}>
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className={`text-sm leading-relaxed ${theme === "dark" ? "text-white/90" : "text-gray-800"}`}>
                    {renderInline(item, theme)}
                  </li>
                ))}
              </ListTag>
            );
          }
          case 'table': {
            const tableBorder = theme === "dark" ? "border-white/10" : "border-gray-200";
            const tableText = theme === "dark" ? "text-white/80" : "text-gray-700";
            const tableHeaderBg = theme === "dark" ? "bg-white/5" : "bg-gray-50";
            const tableRowHover = theme === "dark" ? "hover:bg-white/5" : "hover:bg-gray-50/50";
            
            let headerRow = null;
            let bodyRows = block.rows;
            if (block.hasHeader && block.rows.length > 0) {
              headerRow = block.rows[0];
              bodyRows = block.rows.slice(1);
            }

            return (
              <div key={bIdx} className={`overflow-x-auto my-2 border ${tableBorder} rounded-xl shadow-sm max-w-full`}>
                <table className={`min-w-full divide-y ${tableBorder} text-xs text-left`}>
                  {headerRow && (
                    <thead className={tableHeaderBg}>
                      <tr>
                        {headerRow.map((col, cIdx) => (
                          <th key={cIdx} className={`px-4 py-2 font-bold tracking-wider ${theme === "dark" ? "text-white/90" : "text-gray-800"}`}>
                            {renderInline(col, theme)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                  )}
                  <tbody className={`divide-y ${tableBorder} ${tableText}`}>
                    {bodyRows.map((row, rIdx) => (
                      <tr key={rIdx} className={`${tableRowHover} transition-colors duration-150`}>
                        {row.map((col, cIdx) => (
                          <td key={cIdx} className="px-4 py-2 leading-relaxed">
                            {renderInline(col, theme)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }
          case 'paragraph':
          default:
            return (
              <p key={bIdx} className={`text-sm leading-relaxed ${theme === "dark" ? "text-white/90" : "text-gray-800"}`}>
                {renderInline(block.text, theme)}
              </p>
            );
        }
      })}
    </div>
  );
}

export function ChatMessages({ messages, theme, orbState, onConnectZoho, tempTranscript }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, tempTranscript]);

  return (
    <div className="w-full h-full overflow-y-auto px-4 py-4 space-y-6 max-w-3xl mx-auto">
      <AnimatePresence initial={false}>
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Bot orb avatar */}
            {msg.role === "assistant" && (
              <div className="flex-shrink-0 mt-1">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#0078D7] to-[#00d9ff] flex items-center justify-center">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                  </svg>
                </div>
              </div>
            )}

            {/* Message bubble, connect card, or disconnect banner */}
            {msg.content === "__DISCONNECT_BANNER__" ? (
              <motion.div
                className={`max-w-sm rounded-2xl overflow-hidden ${theme === "dark"
                    ? "bg-white/5 border border-white/10"
                    : "bg-white border border-gray-100"
                  }`}
                style={{ boxShadow: theme === "dark" ? "0 4px 24px rgba(0,0,0,0.3)" : "0 4px 24px rgba(0,0,0,0.08)" }}
              >
                {/* Coloured top strip */}
                <div className="h-1.5 w-full bg-gradient-to-r from-orange-400 to-red-400" />
                <div className="p-5">
                  <div className="flex items-center gap-3 mb-1">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-400 to-red-400 flex items-center justify-center flex-shrink-0 shadow-md">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M18.36 6.64A9 9 0 1 1 5.64 19.36" /><path d="M9 9l6 6m0-6l-6 6" />
                      </svg>
                    </div>
                    <div>
                      <p className={`font-['Sora'] font-bold text-base leading-tight ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
                        Zoho Projects Disconnected
                      </p>
                      <p className={`font-['Sora'] font-bold text-base leading-tight ${theme === "dark" ? "text-orange-300" : "text-orange-500"}`}>
                        Successfully
                      </p>
                    </div>
                  </div>
                  <p className={`text-xs font-['Plus_Jakarta_Sans'] mt-2 leading-relaxed ${theme === "dark" ? "text-white/50" : "text-gray-400"}`}>
                    Your Zoho session has ended. Reconnect anytime below.
                  </p>
                </div>
              </motion.div>
            ) : msg.content === "__CONNECT_CARD__" ? (
              <motion.div
                className={`max-w-sm rounded-2xl p-5 ${theme === "dark"
                    ? "bg-white/5 border border-white/10"
                    : "bg-white border border-gray-100"
                  }`}
                style={{ boxShadow: theme === "dark" ? "0 4px 24px rgba(0,0,0,0.3)" : "0 4px 24px rgba(0,0,0,0.08)" }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#0078D7] to-[#00d9ff] flex items-center justify-center">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                    </svg>
                  </div>
                  <span className={`font-['Sora'] font-semibold text-sm ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
                    Connect to Zoho Projects
                  </span>
                </div>
                <p className={`text-xs font-['Plus_Jakarta_Sans'] mb-4 leading-relaxed ${theme === "dark" ? "text-white/60" : "text-gray-500"}`}>
                  Connect your Zoho account to manage tasks, bugs, timelogs and more using natural language.
                </p>
                <motion.button
                  onClick={onConnectZoho}
                  className="w-full py-2.5 px-4 bg-gradient-to-r from-[#0078D7] to-[#00d9ff] text-white text-xs font-['Plus_Jakarta_Sans'] font-semibold rounded-xl"
                  whileHover={{ scale: 1.02, boxShadow: "0 4px 20px rgba(0,120,215,0.4)" }}
                  whileTap={{ scale: 0.98 }}
                >
                  🔑 Login to Zoho
                </motion.button>
              </motion.div>
            ) : msg.role === "user" ? (
              <div
                className="max-w-[75%] px-4 py-3 rounded-2xl rounded-tr-sm text-sm font-['Plus_Jakarta_Sans'] leading-relaxed whitespace-pre-wrap bg-gradient-to-br from-[#0078D7] to-[#0066bb] text-white"
                style={{ boxShadow: "0 2px 12px rgba(0,120,215,0.25)" }}
              >
                {msg.content}
              </div>
            ) : (
              <div className="max-w-[85%] w-full">
                <MarkdownRenderer content={msg.content} theme={theme} />
              </div>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}
