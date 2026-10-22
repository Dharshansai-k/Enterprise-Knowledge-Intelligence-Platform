import { useEffect, useRef, useState } from "react";
import "./App.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [token, setToken] = useState(
    () => localStorage.getItem("access_token") || ""
  );
  const [theme, setTheme] = useState(
    () => localStorage.getItem("ekip_theme") || "light"
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [showDocumentManager, setShowDocumentManager] = useState(false);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([]);
  const [deletingDocuments, setDeletingDocuments] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [renamingConversationId, setRenamingConversationId] = useState(null);
  const [renameTitle, setRenameTitle] = useState("");



  const fileInputRef = useRef(null);

  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("ekip_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [question]);

  const login = async (event) => {
    event.preventDefault();
    if (loginLoading) return;

    setLoginLoading(true);
    setLoginError("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      if (!data.access_token) {
        throw new Error("The server did not return an access token.");
      }

      localStorage.setItem("access_token", data.access_token);
      setToken(data.access_token);
      setPassword("");
      setMessages([]);
      setLoginError("");
    } catch (error) {
      setLoginError(error.message || "Unable to connect to the server.");
    } finally {
      setLoginLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setToken("");
    setEmail("");
    setPassword("");
    setQuestion("");
    setMessages([]);
    setSelectedDocument("");
    setLoginError("");
    setLoading(false);
  };


const fetchConversations = async () => {
  if (!token) return;

  setHistoryLoading(true);

  try {
    const response = await fetch(`${API_BASE_URL}/conversations`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.status === 401) {
      logout();
      return;
    }

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to load conversations.");
    }

    setConversations(data.conversations || []);
  } catch (error) {
    console.error("Conversation history error:", error);
  } finally {
    setHistoryLoading(false);
  }
};

const createConversation = async () => {
  const response = await fetch(`${API_BASE_URL}/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ title: "New conversation" }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to create conversation.");
  }

  const conversation = data;

  setConversations((previous) => [
    conversation,
    ...previous.filter((item) => item.id !== conversation.id),
  ]);

  setActiveConversationId(conversation.id);

  return conversation.id;
};

const openConversation = async (conversationId) => {
  setHistoryLoading(true);

  try {
    const response = await fetch(
      `${API_BASE_URL}/conversations/${conversationId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to open conversation.");
    }

    setActiveConversationId(data.conversation.id);
    setMessages(
      (data.messages || []).map((message) => ({
        role: message.role,
        content: message.content,
        sources: message.sources || [],
      }))
    );

    setQuestion("");
  } catch (error) {
    console.error("Open conversation error:", error);
    setUploadError(error.message || "Unable to open conversation.");
  } finally {
    setHistoryLoading(false);
  }
};


const renameConversation = async (conversationId) => {
  const title = renameTitle.trim();

  if (!title) {
    setUploadError("Conversation title cannot be empty.");
    return;
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/conversations/${conversationId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to rename conversation.");
    }

    setConversations((previous) =>
      previous.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, title: data.title }
          : conversation
      )
    );

    setRenamingConversationId(null);
    setRenameTitle("");
    setUploadError("");
  } catch (error) {
    setUploadError(error.message || "Unable to rename conversation.");
  }
};


const deleteConversation = async (conversationId) => {
  const conversation = conversations.find(
    (item) => item.id === conversationId
  );

  if (!conversation) return;

  const confirmed = window.confirm(
    `Delete "${conversation.title}"? This will permanently delete its messages.`
  );

  if (!confirmed) return;

  try {
    const response = await fetch(
      `${API_BASE_URL}/conversations/${conversationId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || "Failed to delete conversation.");
    }

    setConversations((previous) =>
      previous.filter((item) => item.id !== conversationId)
    );

    if (activeConversationId === conversationId) {
      setActiveConversationId(null);
      setMessages([]);
      setQuestion("");
    }

    setUploadError("");
  } catch (error) {
    setUploadError(error.message || "Unable to delete conversation.");
  }
};


const saveConversationMessage = async (
  conversationId,
  role,
  content,
  sources = []
) => {
  const response = await fetch(
    `${API_BASE_URL}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ role, content, sources }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to save chat message.");
  }

  return data.message;
};



useEffect(() => {
  if (!token) {
    setDocuments([]);
    setDocumentsLoading(false);
    return;
  }

  const controller = new AbortController();

  const fetchDocuments = async () => {
    setDocumentsLoading(true);
    setDocumentsError("");

    try {
      const response = await fetch(`${API_BASE_URL}/documents`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
      });

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        setToken("");
        setSelectedDocument("");
        return;
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load documents.");
      }

      const documentList = Array.isArray(data.documents)
        ? data.documents
        : [];

      setDocuments(documentList);

      setSelectedDocument((current) =>
        documentList.some((doc) => doc.filename === current)
          ? current
          : ""
      );
    } catch (error) {
      if (error.name !== "AbortError") {
        setDocumentsError(error.message || "Unable to load documents.");
      }
    } finally {
      if (!controller.signal.aborted) {
        setDocumentsLoading(false);
      }
    }
  };

  fetchDocuments();

  return () => controller.abort();
}, [token]);



const uploadDocument = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  setUploadError("");
  setUploadMessage("");

  const allowedTypes = [
    "application/pdf",
    "text/plain",
  ];

  const hasAllowedExtension = /\.(pdf|txt)$/i.test(file.name);

  if (!hasAllowedExtension) {
    setUploadError("Please select a PDF or TXT file.");
    event.target.value = "";
    return;
  }

  if (file.size === 0) {
    setUploadError("The selected file is empty.");
    event.target.value = "";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  setUploading(true);

  try {
    const response = await fetch(
      `${API_BASE_URL}/documents/upload`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      }
    );

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      setLoginError("Your session expired. Please log in again.");
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || "Document upload failed.");
    }

    setUploadMessage(`${file.name} uploaded successfully.`);

    // Refresh the document dropdown after upload.
    const listResponse = await fetch(`${API_BASE_URL}/documents`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const listData = await listResponse.json().catch(() => ({}));

    if (!listResponse.ok) {
      throw new Error("Uploaded, but could not refresh the document list.");
    }

    const documentList = Array.isArray(listData.documents)
      ? listData.documents
      : [];

    setDocuments(documentList);
    setSelectedDocument(file.name);
  } catch (error) {
    setUploadError(error.message || "Unable to upload the document.");
  } finally {
    setUploading(false);
    event.target.value = "";
  }
};


const deleteDocument = async (doc) => {
  const confirmed = window.confirm(
    `Are you sure you want to delete "${doc.filename}"? This cannot be undone.`
  );

  if (!confirmed) return;

  setUploadError("");
  setUploadMessage("");

  try {
    const response = await fetch(
      `${API_BASE_URL}/documents/${doc.id}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || "Failed to delete document.");
    }

    setDocuments((previous) =>
      previous.filter((item) => item.id !== doc.id)
    );

    setSelectedDocument((current) =>
      current === doc.filename ? "" : current
    );

    setUploadMessage(`${doc.filename} deleted successfully.`);
  } catch (error) {
    setUploadError(error.message || "Unable to delete document.");
  }
};


useEffect(() => {
  if (token) {
    fetchConversations();
  } else {
    setConversations([]);
    setActiveConversationId(null);
  }
}, [token]);



const askQuestion = async (overrideQuestion) => {
  const userQuestion = (overrideQuestion ?? question).trim();
  if (!userQuestion || loading) return;

  if (!token) {
    logout();
    return;
  }

  setQuestion("");
  setMessages((previous) => [
    ...previous,
    { role: "user", content: userQuestion },
  ]);
  setLoading(true);

  let conversationId = activeConversationId;

  try {
    // Create a conversation for the first question.
    if (!conversationId) {
      conversationId = await createConversation();
    }

    // Save the user's question.
    await saveConversationMessage(
      conversationId,
      "user",
      userQuestion
    );

    // Ask EKIP.
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        question: userQuestion,
        filename: selectedDocument || null,
      }),
    });

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      setLoginError("Your session expired. Please log in again.");
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || "Unable to answer your question.");
    }

    const answer = data.answer || "No answer was returned.";
    const sources = data.sources || [];

    // Display the answer and sources.
    setMessages((previous) => [
      ...previous,
      {
        role: "assistant",
        content: answer,
        sources,
      },
    ]);

    // Save the assistant's answer.
    await saveConversationMessage(
      conversationId,
      "assistant",
      answer,
      sources
    );

    // Refresh the conversation list.
    await fetchConversations();
  } catch (error) {
    console.error("Chat error:", error);

    setMessages((previous) => [
      ...previous,
      {
        role: "assistant",
        content: `Error: ${error.message}`,
        sources: [],
        error: true,
      },
    ]);
  } finally {
    setLoading(false);
  }
};

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      askQuestion();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setQuestion("");
  };

  if (!token) {
    return (
      <div className="app login-app">
        <header className="header">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">✦</div>
            <div>
              <h1>EKIP</h1>
              <p>Enterprise Knowledge Intelligence Platform</p>
            </div>
          </div>
          <button className="theme-toggle" type="button" onClick={toggleTheme}>
            {theme === "light" ? "☾ Dark" : "☀ Light"}
          </button>
        </header>

        <main className="login-container">
          <form className="login-form" onSubmit={login}>
            <div className="login-icon" aria-hidden="true">✦</div>
            <h2>Welcome back</h2>
            <p>Sign in to explore your enterprise knowledge.</p>

            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="username"
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              required
            />

            {loginError && (
              <p className="login-error" role="alert">{loginError}</p>
            )}

            <button
              className="login-button"
              type="submit"
              disabled={loginLoading || !email.trim() || !password}
            >
              {loginLoading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </main>
      </div>
    );
  }

  return (
  <div className="app">
    <aside className="conversation-sidebar">
      <button
        type="button"
        className="new-chat-button"
        onClick={() => {
          setActiveConversationId(null);
          setMessages([]);
          setQuestion("");
          setUploadError("");
        }}
      >
        + New chat
      </button>

      <div className="conversation-sidebar-heading">
        Recent conversations
      </div>

      <div className="conversation-list">
        {historyLoading && conversations.length === 0 ? (
          <p className="conversation-empty">Loading chats...</p>
        ) : conversations.length === 0 ? (
          <p className="conversation-empty">No conversations yet</p>
        ) : (
          
conversations.map((conversation) => (
  <div
    key={conversation.id}
    className={`conversation-entry ${
      activeConversationId === conversation.id ? "active" : ""
    }`}
  >
    {renamingConversationId === conversation.id ? (
      <form
        className="conversation-rename-form"
        onSubmit={(event) => {
          event.preventDefault();
          renameConversation(conversation.id);
        }}
      >
        <input
          autoFocus
          value={renameTitle}
          maxLength={200}
          onChange={(event) => setRenameTitle(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setRenamingConversationId(null);
              setRenameTitle("");
            }
          }}
          aria-label="Conversation title"
        />
        <button type="submit" title="Save title">✓</button>
        <button
          type="button"
          title="Cancel"
          onClick={() => {
            setRenamingConversationId(null);
            setRenameTitle("");
          }}
        >
          ✕
        </button>
      </form>
    ) : (
      <>
        <button
          type="button"
          className={`conversation-item ${
            activeConversationId === conversation.id ? "active" : ""
          }`}
          onClick={() => openConversation(conversation.id)}
          disabled={historyLoading}
          title={conversation.title}
        >
          <span className="conversation-item-icon">▤</span>
          <span className="conversation-item-title">
            {conversation.title || "New conversation"}
          </span>
        </button>

        <button
          type="button"
          className="conversation-rename-button"
          title="Rename conversation"
          aria-label={`Rename ${conversation.title}`}
          onClick={() => {
            setRenamingConversationId(conversation.id);
            setRenameTitle(conversation.title || "");
          }}
        >
          ✎
        </button>

<button
  type="button"
  className="conversation-delete-button"
  title="Delete conversation"
  aria-label={`Delete ${conversation.title}`}
  onClick={() => deleteConversation(conversation.id)}
>
  🗑
</button>

      </>
    )}
  </div>
))
)
}
      </div>
    </aside>
      <header className="header">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">✦</div>
          <div>
            <h1>EKIP</h1>
            <p>Enterprise Knowledge Intelligence Platform</p>
          </div>
        </div>

        <div className="header-actions">

              <button
                className="header-button"
                type="button"
                onClick={() => setShowDocumentManager(true)}
              >
                Manage Documents
              </button>

          <button className="theme-toggle" type="button" onClick={toggleTheme}>
            {theme === "light" ? "☾ Dark" : "☀ Light"}
          </button>
          {messages.length > 0 && (
            <button className="header-button" onClick={clearChat} type="button">
              Clear chat
            </button>
          )}
          
<button
  className="header-button"
  type="button"
  onClick={() => fileInputRef.current?.click()}
  disabled={uploading}
>
  {uploading ? "Uploading..." : "Upload document"}
</button>

<input
  ref={fileInputRef}
  type="file"
  accept=".pdf,.txt"
  onChange={uploadDocument}
  hidden
/>

<button className="header-button" onClick={logout} type="button">
  Log out
</button>

        </div>
      </header>

          {uploadMessage && <p role="status">{uploadMessage}</p>}
{uploadError && <p role="alert">{uploadError}</p>}
      <main className="chat-container" ref={chatContainerRef}>

{showDocumentManager && (
  <div
    className="document-modal-overlay"
    onClick={(event) => {
      if (event.target === event.currentTarget) {
        setShowDocumentManager(false);
      }
    }}
  >
    <section
      className="document-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-modal-title"
    >
      <div className="document-modal-header">
        <div>
          <h2 id="document-modal-title">Manage Documents</h2>
          <p>{documents.length} documents uploaded</p>
        </div>

        <button
          type="button"
          className="header-button"
          onClick={() => setShowDocumentManager(false)}
          aria-label="Close document manager"
        >
          ✕
        </button>
      </div>

      <div className="document-modal-list">
        {documents.length === 0 ? (
          <p>No documents uploaded yet.</p>
        ) : (
          documents.map((doc) => (
            <label className="document-modal-item" key={doc.id}>
              <input
                type="checkbox"
                checked={selectedDocumentIds.includes(doc.id)}
                onChange={(event) => {
                  setSelectedDocumentIds((previous) =>
                    event.target.checked
                      ? [...previous, doc.id]
                      : previous.filter((id) => id !== doc.id)
                  );
                }}
              />

              <span className="document-modal-file-icon">▤</span>

              <span className="document-modal-filename">
                <strong>{doc.filename}</strong>
                <small>
                  {doc.file_type || "Document"}
                  {doc.uploaded_at
                    ? ` · ${new Date(doc.uploaded_at).toLocaleDateString()}`
                    : ""}
                </small>
              </span>

              <button
                type="button"
                className="header-button document-delete-button"
                disabled={deletingDocuments}
                onClick={() => deleteDocument(doc)}
              >
                Delete
              </button>
            </label>
          ))
        )}
      </div>

      <div className="document-modal-footer">
        <button
          type="button"
          className="header-button"
          onClick={() => {
            setSelectedDocumentIds(
              selectedDocumentIds.length === documents.length
                ? []
                : documents.map((doc) => doc.id)
            );
          }}
        >
          {selectedDocumentIds.length === documents.length &&
          documents.length > 0
            ? "Deselect all"
            : "Select all"}
        </button>

        <span>{selectedDocumentIds.length} selected</span>

        <button
          type="button"
          className="header-button"
          disabled={selectedDocumentIds.length === 0 || deletingDocuments}
          onClick={async () => {
            const selected = documents.filter((doc) =>
              selectedDocumentIds.includes(doc.id)
            );

            if (
              !window.confirm(
                `Delete ${selected.length} selected document(s)? This cannot be undone.`
              )
            ) {
              return;
            }

            setDeletingDocuments(true);

            try {
              const failed = [];

              for (const doc of selected) {
                try {
                  const response = await fetch(
                    `${API_BASE_URL}/documents/${doc.id}`,
                    {
                      method: "DELETE",
                      headers: {
                        Authorization: `Bearer ${token}`,
                      },
                    }
                  );

                  if (response.status === 401) {
                    logout();
                    return;
                  }

                  if (!response.ok) {
                    failed.push(doc.filename);
                  }
                } catch {
                  failed.push(doc.filename);
                }
              }

              const listResponse = await fetch(
                `${API_BASE_URL}/documents`,
                {
                  headers: {
                    Authorization: `Bearer ${token}`,
                  },
                }
              );

              if (!listResponse.ok) {
                throw new Error("Unable to refresh the document list.");
              }

              const listData = await listResponse.json();
              const updatedDocuments = listData.documents || [];

              setDocuments(updatedDocuments);
              setSelectedDocumentIds([]);
              setSelectedDocument((current) =>
                updatedDocuments.some((doc) => doc.filename === current)
                  ? current
                  : ""
              );

              setUploadMessage(
                failed.length
                  ? `Could not delete: ${failed.join(", ")}`
                  : "Selected documents deleted successfully."
              );

              setUploadError("");
            } catch (error) {
              setUploadError(error.message);
            } finally {
              setDeletingDocuments(false);
            }
          }}
        >
          {deletingDocuments ? "Deleting..." : "Delete selected"}
        </button>
      </div>
    </section>
  </div>
)}

        {messages.length === 0 && (
          <section className="welcome">
            <div className="welcome-icon" aria-hidden="true">✦</div>
            <h2>Knowledge at your fingertips.</h2>
            <p>
              Ask questions about your enterprise documents and get
              AI-powered answers grounded in your sources.
            </p>

            <div className="example-questions">
              <button
                type="button"
                onClick={() => setQuestion("What are the education details of the author?")}
              >
                <span aria-hidden="true">▤</span> Education details
              </button>
              <button
                type="button"
                onClick={() => setQuestion("What programming languages are mentioned?")}
              >
                <span aria-hidden="true">⌘</span> Programming languages
              </button>
              <button
                type="button"
                onClick={() => setQuestion("What technologies are mentioned in the document?")}
              >
                <span aria-hidden="true">✧</span> Technologies
              </button>
            </div>
          </section>
        )}

        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`message-row ${message.role}`}
          >
            {message.role === "assistant" && (
              <div className="avatar assistant-avatar" aria-label="EKIP assistant">
                ✦
              </div>
            )}

            <div className={`message ${message.error ? "error-message" : ""}`}>
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>

              {message.role === "assistant" && message.sources?.length > 0 && (
                <div className="sources">
                  <h4><span aria-hidden="true">▤</span> Sources</h4>
                  {message.sources.map((source, sourceIndex) => (
                    <div
                      className="source-card"
                      key={`${source.document_id}-${source.chunk_index}-${sourceIndex}`}
                    >
                      <span className="source-file-icon" aria-hidden="true">▧</span>
                      <strong>{source.filename}</strong>
                      <span className="source-chunk">Chunk {source.chunk_index}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {message.role === "user" && (
              <div className="avatar user-avatar" aria-label="You">You</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message-row assistant">
            <div className="avatar assistant-avatar" aria-label="EKIP assistant">✦</div>
            <div className="message thinking-message">
              <div className="thinking">
                EKIP is thinking
                <span>.</span><span>.</span><span>.</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      <footer className="composer-section">



        <form
          className="input-area"
          onSubmit={(event) => {
            event.preventDefault();
            askQuestion();
          }}
        >
          <div className="document-selector">
            <label htmlFor="document-select">Search in</label>
            
<select
  id="document-select"
  value={selectedDocument}
  onChange={(event) => setSelectedDocument(event.target.value)}
  disabled={loading || documentsLoading}
>
  <option value="">
    {documentsLoading ? "Loading documents..." : "All documents"}
  </option>

  {documents.map((doc) => (
    <option key={doc.id} value={doc.filename}>
      {doc.filename}
    </option>
  ))}
</select>

{documentsError && (
  <p className="login-error" role="alert">
    {documentsError}
  </p>
)}

          </div>

          <textarea
            ref={textareaRef}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message EKIP..."
            rows={1}
            disabled={loading}
            aria-label="Ask EKIP a question"
          />

          <button
            className="send-button"
            type="submit"
            disabled={loading || !question.trim()}
            aria-label="Send question"
            title="Send message"
          >
            {loading ? "…" : "➤"}
          </button>
        </form>

        <p className="input-hint">
          Enter to send · Shift + Enter for a new line
        </p>
      </footer>
    </div>
  );
}

export default App;
