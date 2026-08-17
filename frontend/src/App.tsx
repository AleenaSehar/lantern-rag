import { FormEvent, useEffect, useRef, useState } from "react";
import { AlertCircle, Check, ChevronDown, ChevronUp, FileText, LoaderCircle, Plus, Send, Upload } from "lucide-react";

import { AnswerResponse, Citation, DocumentRecord, askQuestion, listDocuments, uploadDocument } from "./api";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  text: string;
  status?: AnswerResponse["status"];
  citations?: Citation[];
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function CitationList({ citations }: { citations: Citation[] }) {
  const [openCitation, setOpenCitation] = useState<string | null>(null);

  return (
    <div className="citations" aria-label="Answer sources">
      <p className="citation-heading">Sources</p>
      {citations.map((citation, index) => {
        const isOpen = openCitation === citation.chunk_id;
        const location = citation.page_number ? `Page ${citation.page_number}` : `Chunk ${citation.chunk_index + 1}`;
        return (
          <div className="citation" key={citation.chunk_id}>
            <button className="citation-trigger" type="button" aria-expanded={isOpen} onClick={() => setOpenCitation(isOpen ? null : citation.chunk_id)}>
              <span className="citation-number">{index + 1}</span>
              <span className="citation-title"><strong>{citation.filename}</strong><small>{location}</small></span>
              {isOpen ? <ChevronUp size={17} /> : <ChevronDown size={17} />}
            </button>
            {isOpen && <blockquote>{citation.quote}</blockquote>}
          </div>
        );
      })}
    </div>
  );
}

function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const conversationEnd = useRef<HTMLDivElement>(null);
  const nextMessageId = useRef(1);

  useEffect(() => {
    const controller = new AbortController();
    listDocuments(controller.signal)
      .then((items) => {
        setDocuments(items);
        setSelectedIds(new Set(items.filter((item) => item.status === "ready").map((item) => item.id)));
      })
      .catch((error: Error) => { if (error.name !== "AbortError") setNotice(error.message); })
      .finally(() => setIsLoadingDocuments(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    conversationEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAnswering]);

  const readyDocuments = documents.filter((document) => document.status === "ready");

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    setIsUploading(true);
    setNotice(null);
    try {
      const uploaded = await uploadDocument(file);
      setDocuments((current) => [uploaded, ...current.filter((document) => document.id !== uploaded.id)]);
      if (uploaded.status === "ready") setSelectedIds((current) => new Set(current).add(uploaded.id));
      setNotice(uploaded.duplicate ? `${uploaded.filename} was already indexed.` : `${uploaded.filename} is ready.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setIsUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function toggleDocument(id: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function handleQuestion(event: FormEvent) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || isAnswering || selectedIds.size === 0) return;

    setMessages((current) => [...current, { id: nextMessageId.current++, role: "user", text: trimmedQuery }]);
    setQuery("");
    setIsAnswering(true);
    setNotice(null);
    try {
      const response = await askQuestion(trimmedQuery, [...selectedIds]);
      setMessages((current) => [...current, {
        id: nextMessageId.current++, role: "assistant", text: response.answer,
        status: response.status, citations: response.citations,
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: nextMessageId.current++, role: "assistant",
        text: error instanceof Error ? error.message : "The answer could not be generated.",
        status: "insufficient_evidence",
      }]);
    } finally {
      setIsAnswering(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div><a className="wordmark" href="/" aria-label="groundwork home">groundwork</a><span className="product-label">Grounded document Q&amp;A</span></div>
        <span className="connection-status"><span /> Local workspace</span>
      </header>

      <div className="workspace">
        <aside className="document-panel" aria-label="Document library">
          <div className="panel-heading">
            <div><p className="eyebrow">Evidence library</p><h1>Documents</h1></div>
            <button className="icon-button" type="button" title="Upload document" aria-label="Upload document" disabled={isUploading} onClick={() => fileInput.current?.click()}>
              {isUploading ? <LoaderCircle className="spin" size={19} /> : <Plus size={20} />}
            </button>
            <input ref={fileInput} className="visually-hidden" type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={(event) => void handleUpload(event.target.files?.[0])} />
          </div>

          {notice && <div className="notice" role="status"><AlertCircle size={16} /><span>{notice}</span><button type="button" aria-label="Dismiss message" onClick={() => setNotice(null)}>x</button></div>}

          <div className="document-list">
            {isLoadingDocuments && <div className="panel-state"><LoaderCircle className="spin" /> Loading documents</div>}
            {!isLoadingDocuments && documents.length === 0 && (
              <button className="upload-empty" type="button" onClick={() => fileInput.current?.click()}>
                <Upload size={22} /><strong>Upload your first document</strong><span>PDF or TXT, up to 10 MB</span>
              </button>
            )}
            {documents.map((document) => {
              const selected = selectedIds.has(document.id);
              return (
                <button className={`document-row${selected ? " selected" : ""}`} type="button" key={document.id} disabled={document.status !== "ready"} aria-pressed={selected} onClick={() => toggleDocument(document.id)}>
                  <span className="file-icon"><FileText size={18} /></span>
                  <span className="document-copy"><strong>{document.filename}</strong><small>{formatSize(document.size_bytes)} · {document.chunk_count} chunks</small></span>
                  <span className="selection-box">{selected && <Check size={14} />}</span>
                </button>
              );
            })}
          </div>
          {readyDocuments.length > 0 && <p className="selection-summary">{selectedIds.size} of {readyDocuments.length} included in answers</p>}
        </aside>

        <section className="chat-panel" aria-label="Question and answer conversation">
          <div className="chat-heading">
            <div><p className="eyebrow">Ask the evidence</p><h2>Conversation</h2></div>
            {messages.length > 0 && <button className="text-button" type="button" onClick={() => setMessages([])}>Clear</button>}
          </div>

          <div className="conversation" aria-live="polite">
            {messages.length === 0 && <div className="conversation-empty"><div className="evidence-mark"><FileText size={26} /></div><h3>Ask a question about your documents</h3><p>Answers use only the selected sources. Every supported answer includes an exact excerpt.</p></div>}
            {messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <p className="message-role">{message.role === "user" ? "You" : "groundwork"}</p>
                {message.status === "insufficient_evidence" && <span className="refusal-label"><AlertCircle size={14} /> Insufficient evidence</span>}
                <p className="message-text">{message.text}</p>
                {message.citations && message.citations.length > 0 && <CitationList citations={message.citations} />}
              </article>
            ))}
            {isAnswering && <div className="answering"><LoaderCircle className="spin" size={18} /> Checking the selected evidence...</div>}
            <div ref={conversationEnd} />
          </div>

          <form className="composer" onSubmit={(event) => void handleQuestion(event)}>
            <textarea aria-label="Question" placeholder={selectedIds.size ? "Ask a question about the selected documents..." : "Select at least one document to ask a question"} value={query} disabled={isAnswering || selectedIds.size === 0} rows={2} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} />
            <button className="send-button" type="submit" title="Send question" aria-label="Send question" disabled={!query.trim() || isAnswering || selectedIds.size === 0}><Send size={18} /></button>
          </form>
        </section>
      </div>
    </main>
  );
}

export default App;
