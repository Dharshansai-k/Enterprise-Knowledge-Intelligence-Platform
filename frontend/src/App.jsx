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
  const [isRegistering, setIsRegistering] = useState(false);
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [authMessage, setAuthMessage] = useState("");

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
  const [conversationSearch, setConversationSearch] = useState("");
  const [issueModalOpen, setIssueModalOpen] = useState(false);
  const [issueQuestion, setIssueQuestion] = useState("");
  const [issueCategory, setIssueCategory] = useState("missing_information");
  const [issueDetails, setIssueDetails] = useState("");
  const [issueSubmitting, setIssueSubmitting] = useState(false);
  const [issueError, setIssueError] = useState("");
  const [issueSuccess, setIssueSuccess] = useState("");
  const [showMyIssues, setShowMyIssues] = useState(false);
  const [myIssues, setMyIssues] = useState([]);
  const [myIssuesLoading, setMyIssuesLoading] = useState(false);
  const [myIssuesError, setMyIssuesError] = useState("");

  const [currentUser, setCurrentUser] = useState(null);
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);
  const [adminIssues, setAdminIssues] = useState([]);
  const [adminIssuesLoading, setAdminIssuesLoading] = useState(false);
  const [adminIssuesError, setAdminIssuesError] = useState("");
  const [adminStatusFilter, setAdminStatusFilter] = useState("all");
  const [editingIssueId, setEditingIssueId] = useState(null);
  const [editIssueStatus, setEditIssueStatus] = useState("under_review");
  const [editIssueResponse, setEditIssueResponse] = useState("");
  const [issueUpdateLoading, setIssueUpdateLoading] = useState(false);

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
    setAuthMessage("");

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

  const register = async (event) => {
    event.preventDefault();
    if (registerLoading) return;

    setRegisterError("");
    setAuthMessage("");

    const cleanName = fullName.trim();
    if (cleanName.length < 2) {
      setRegisterError("Full name must contain at least 2 characters.");
      return;
    }
    if (password.length < 8) {
      setRegisterError("Password must contain at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setRegisterError("Passwords do not match.");
      return;
    }

    setRegisterLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: cleanName,
          email: email.trim(),
          password,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = typeof data.detail === "string"
          ? data.detail
          : "Registration failed. Please check your details and try again.";
        throw new Error(message);
      }

      setIsRegistering(false);
      setFullName("");
      setPassword("");
      setConfirmPassword("");
      setRegisterError("");
      setAuthMessage("Account created successfully. Please sign in.");
    } catch (error) {
      setRegisterError(
        error instanceof TypeError
          ? "Unable to connect to EKIP. Please try again."
          : error.message || "Registration failed. Please try again."
      );
    } finally {
      setRegisterLoading(false);
    }
  };

  const switchAuthMode = () => {
    setIsRegistering((current) => !current);
    setLoginError("");
    setRegisterError("");
    setAuthMessage("");
    setPassword("");
    setConfirmPassword("");
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

const fetchCurrentUser = async () => {
  if (!token) {
    setCurrentUser(null);
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.status === 401) {
      logout();
      return;
    }

    if (!response.ok) {
      throw new Error("Unable to load your account information.");
    }

    const data = await response.json();
    setCurrentUser(data);
  } catch (error) {
    console.error("Current user error:", error);
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


const filteredConversations = conversations.filter((conversation) =>
  (conversation.title || "New conversation")
    .toLowerCase()
    .includes(conversationSearch.trim().toLowerCase())
);

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


const submitKnowledgeIssue = async (event) => {
  event.preventDefault();

  if (issueSubmitting || !issueQuestion.trim() || !token) {
    return;
  }

  setIssueSubmitting(true);
  setIssueError("");
  setIssueSuccess("");

  try {
    const response = await fetch(`${API_BASE_URL}/issues`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        question: issueQuestion.trim(),
        category: issueCategory,
        details: issueDetails.trim() || null,
      }),
    });

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      setLoginError("Your session expired. Please log in again.");
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || "Unable to submit your issue.");
    }

    setIssueSuccess(
      `Issue #${data.issue.id} submitted successfully. You can track its status in My Issues once that page is available.`
    );
  } catch (error) {
    console.error("Issue submission error:", error);
    setIssueError(
      error instanceof TypeError
        ? "Unable to connect to EKIP. Please try again."
        : error.message || "Unable to submit your issue."
    );
  } finally {
    setIssueSubmitting(false);
  }
};


const fetchMyIssues = async () => {
  if (!token || myIssuesLoading) return;

  setMyIssuesLoading(true);
  setMyIssuesError("");

  try {
    const response = await fetch(`${API_BASE_URL}/issues`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      setLoginError("Your session expired. Please log in again.");
      return;
    }

    if (!response.ok) {
      throw new Error(data.detail || "Unable to load your issues.");
    }

    setMyIssues(data.issues || []);
  } catch (error) {
    console.error("My issues error:", error);
    setMyIssuesError(
      error instanceof TypeError
        ? "Unable to connect to EKIP. Please try again."
        : error.message || "Unable to load your issues."
    );
  } finally {
    setMyIssuesLoading(false);
  }
};


const fetchAdminIssues = async () => {
  if (!token || adminIssuesLoading) return;

  setAdminIssuesLoading(true);
  setAdminIssuesError("");

  try {
    const response = await fetch(`${API_BASE_URL}/admin/issues`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      setLoginError("Your session expired. Please log in again.");
      return;
    }

    if (response.status === 403) {
      throw new Error("You don't have permission to view admin issues.");
    }

    if (!response.ok) {
      throw new Error(data.detail || "Unable to load admin issues.");
    }

    setAdminIssues(data.issues || []);
  } catch (error) {
    console.error("Admin issues error:", error);
    setAdminIssuesError(
      error instanceof TypeError
        ? "Unable to connect to EKIP. Please try again."
        : error.message || "Unable to load admin issues."
    );
  } finally {
    setAdminIssuesLoading(false);
  }
};


const updateAdminIssue = async (issueId) => {
  if (issueUpdateLoading) return;

  setIssueUpdateLoading(true);
  setAdminIssuesError("");

  try {
    const response = await fetch(
      `${API_BASE_URL}/admin/issues/${issueId}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          status: editIssueStatus,
          admin_response: editIssueResponse.trim() || null,
        }),
      }
    );

    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
      logout();
      setLoginError("Your session expired. Please log in again.");
      return;
    }

    if (response.status === 403) {
      throw new Error("You don't have permission to update issues.");
    }

    if (!response.ok) {
      throw new Error(data.detail || "Unable to update the issue.");
    }

    await fetchAdminIssues();
    setEditingIssueId(null);
  } catch (error) {
    console.error("Update issue error:", error);
    setAdminIssuesError(error.message || "Unable to update the issue.");
  } finally {
    setIssueUpdateLoading(false);
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
    setSelectedDocument(String(data.document_id));
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
  setDeletingDocuments(true);

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
      previous.filter((item) => String(item.id) !== String(doc.id))
    );

    setSelectedDocument((current) =>
      String(current) === String(doc.id) ? "" : current
    );
    setSelectedDocumentIds((previous) =>
      previous.filter((id) => String(id) !== String(doc.id))
    );

    setUploadMessage(`${doc.filename} deleted successfully.`);
  } catch (error) {
    setUploadError(error.message || "Unable to delete document.");
  } finally {
    setDeletingDocuments(false);
  }
};


useEffect(() => {
  if (token) {
    fetchConversations();
    fetchCurrentUser();
  } else {
    setConversations([]);
    setActiveConversationId(null);
    setCurrentUser(null);
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
        document_id: selectedDocument
          ? Number(selectedDocument)
          : null,
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
    setMessages(previous => [
  ...previous,
  {
    role: "assistant",
    content: answer,
    sources,
    hasSufficientEvidence: data.has_sufficient_evidence,
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

  const errorMessage =
    error instanceof TypeError
      ? "Unable to connect to EKIP. Please check your connection and try again."
      : error.message || "Something went wrong. Please try again.";

  setMessages((previous) => {
    const lastMessage = previous[previous.length - 1];

    // Don't add a duplicate error if the answer is already displayed.
    if (
      lastMessage?.role === "assistant" &&
      !lastMessage.error
    ) {
      return previous;
    }

    return [
      ...previous,
      {
        role: "assistant",
        content: errorMessage,
        sources: [],
        error: true,
      },
    ];
  });
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
  setActiveConversationId(null);
  setMessages([]);
  setQuestion("");
  setUploadError("");
};;

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
          <form className="login-form" onSubmit={isRegistering ? register : login}>
            <div className="login-icon" aria-hidden="true">✦</div>
            <h2>{isRegistering ? "Create your account" : "Welcome back"}</h2>
            <p>
              {isRegistering
                ? "Create an EKIP account to access your enterprise knowledge."
                : "Sign in to explore your enterprise knowledge."}
            </p>

            {isRegistering && (
              <>
                <label htmlFor="fullName">Full name</label>
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Enter your full name"
                  autoComplete="name"
                  minLength={2}
                  maxLength={100}
                  required
                />
              </>
            )}

            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />

            <label htmlFor="password">Password</label>
            <div className="password-input-wrap">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={isRegistering ? "At least 8 characters" : "Enter your password"}
                autoComplete={isRegistering ? "new-password" : "current-password"}
                minLength={isRegistering ? 8 : 1}
                maxLength={128}
                required
              />
              <button
                className="password-toggle"
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "🙈" : "👁️"}
              </button>
            </div>

            {isRegistering && (
              <>
                <label htmlFor="confirmPassword">Confirm password</label>
                <div className="password-input-wrap">
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Re-enter your password"
                    autoComplete="new-password"
                    minLength={8}
                    maxLength={128}
                    required
                  />
                  <button
                    className="password-toggle"
                    type="button"
                    onClick={() => setShowConfirmPassword((visible) => !visible)}
                    aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                    title={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? "🙈" : "👁️"}
                  </button>
                </div>
              </>
            )}

            {authMessage && (
              <p className="auth-success" role="status">{authMessage}</p>
            )}
            {(isRegistering ? registerError : loginError) && (
              <p className="login-error" role="alert">
                {isRegistering ? registerError : loginError}
              </p>
            )}

            <button
              className="login-button"
              type="submit"
              disabled={isRegistering
                ? registerLoading || !fullName.trim() || !email.trim() || !password || !confirmPassword
                : loginLoading || !email.trim() || !password}
            >
              {isRegistering
                ? (registerLoading ? "Creating account..." : "Create account")
                : (loginLoading ? "Signing in..." : "Sign in")}
            </button>

            <p className="auth-switch">
              {isRegistering ? "Already have an account?" : "New to EKIP?"}
              <button type="button" onClick={switchAuthMode}>
                {isRegistering ? "Sign in" : "Create an account"}
              </button>
            </p>
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
        <input
            type="search"
            className="conversation-search"
            placeholder="Search conversations..."
            value={conversationSearch}
            onChange={(event) => setConversationSearch(event.target.value)}
            aria-label="Search conversations"
          />


      <div className="conversation-sidebar-heading">
        Recent conversations
      </div>

      <div className="conversation-list">
        {historyLoading && filteredConversations.length === 0 ? (
          <p className="conversation-empty">Loading chats...</p>
        ) : filteredConversations.length === 0 ? (
          <p className="conversation-empty">No conversations yet</p>
        ) : (
          
filteredConversations.map((conversation) => (
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

          <button
          className="header-button"
          type="button"
          onClick={() => {
            setShowMyIssues(true);
            fetchMyIssues();
          }}
        >
          My Issues
        </button>

        {currentUser?.role === "admin" && (
        <button
          className="header-button"
          type="button"
          onClick={() => {
              setShowAdminDashboard(true);
              fetchAdminIssues();
            }}
        >
          Admin Dashboard
        </button>
)}

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

{showAdminDashboard && (
  <div
    className="document-modal-overlay"
    onClick={(event) => {
      if (event.target === event.currentTarget) {
        setShowAdminDashboard(false);
      }
    }}
  >
    <section
      className="document-modal my-issues-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-dashboard-title"
    >
      <div className="document-modal-header">
        <div>
          <h2 id="admin-dashboard-title">Admin Dashboard</h2>
          <p>{adminIssues.length} reported issue(s)</p>
        </div>

        <button
          type="button"
          className="header-button"
          onClick={() => setShowAdminDashboard(false)}
          aria-label="Close admin dashboard"
        >
          ✕
        </button>
      </div>

      <div className="admin-issues-toolbar">
  <label htmlFor="admin-status-filter">Filter by status</label>

  <select
    id="admin-status-filter"
    value={adminStatusFilter}
    onChange={(event) => setAdminStatusFilter(event.target.value)}
  >
    <option value="all">All issues</option>
    <option value="open">Open</option>
    <option value="under_review">Under Review</option>
    <option value="resolved">Resolved</option>
    <option value="rejected">Rejected</option>
  </select>

  <button
    type="button"
    className="header-button"
    onClick={fetchAdminIssues}
    disabled={adminIssuesLoading}
  >
    {adminIssuesLoading ? "Refreshing..." : "Refresh"}
  </button>
</div>


      {adminIssuesError && (
        <p role="alert">{adminIssuesError}</p>
      )}

      {adminIssuesLoading ? (
        <p role="status">Loading reported issues...</p>
      ) : adminIssues.length === 0 ? (
        <p>No issues have been reported yet.</p>
      ) : adminIssues.filter(
          (issue) =>
            adminStatusFilter === "all" ||
            issue.status === adminStatusFilter
        ).length === 0 ? (
        <p>No issues match the selected status.</p>
      ) : (
        <div className="document-modal-list">
          {adminIssues
  .filter(
    (issue) =>
      adminStatusFilter === "all" ||
      issue.status === adminStatusFilter
  )
  .map((issue) => (
            <article className="my-issue-card" key={issue.id}>
              <div className="my-issue-heading">
                <strong>Issue #{issue.id}</strong>
                <span className={`issue-status status-${issue.status}`}>
                  {issue.status.replaceAll("_", " ")}
                </span>
              </div>

                <button
                  type="button"
                  className="header-button"
                  onClick={() => {
                    setEditingIssueId(issue.id);
                    setEditIssueStatus(issue.status);
                    setEditIssueResponse(issue.admin_response || "");
                    setAdminIssuesError("");
                  }}
                >
                  Edit issue
                </button>

{editingIssueId === issue.id && (
  <div className="admin-issue-editor">
    <label htmlFor={`issue-status-${issue.id}`}>
      Status
    </label>

    <select
      id={`issue-status-${issue.id}`}
      value={editIssueStatus}
      onChange={(event) => setEditIssueStatus(event.target.value)}
    >
      <option value="open">Open</option>
      <option value="under_review">Under Review</option>
      <option value="resolved">Resolved</option>
      <option value="rejected">Rejected</option>
    </select>

    <label htmlFor={`issue-response-${issue.id}`}>
      Admin response
    </label>

    <textarea
      id={`issue-response-${issue.id}`}
      value={editIssueResponse}
      onChange={(event) => setEditIssueResponse(event.target.value)}
      maxLength={5000}
      rows={3}
      placeholder="Explain what you found or what action was taken..."
    />

    <div className="admin-issues-toolbar">
      <button
        type="button"
        className="header-button"
        disabled={issueUpdateLoading}
        onClick={() => setEditingIssueId(null)}
      >
        Cancel
      </button>

      <button
        type="button"
        className="header-button"
        disabled={issueUpdateLoading}
        onClick={() => updateAdminIssue(issue.id)}
      >
        {issueUpdateLoading ? "Saving..." : "Save changes"}
      </button>
    </div>
  </div>
)}


              <p className="my-issue-question">{issue.question}</p>
              <p className="my-issue-category">
                Category: {issue.category.replaceAll("_", " ")}
              </p>

              {issue.details && <p>{issue.details}</p>}

              <p className="my-issue-category">
                Reported by: {issue.reported_by}
              </p>

              {issue.admin_response && (
                <div className="my-issue-response">
                  <strong>Current admin response</strong>
                  <p>{issue.admin_response}</p>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  </div>
)}

{showMyIssues && (
  <div
    className="document-modal-overlay"
    onClick={(event) => {
      if (event.target === event.currentTarget) {
        setShowMyIssues(false);
      }
    }}
  >
    <section
      className="document-modal my-issues-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="my-issues-title"
    >
      <div className="document-modal-header">
        <div>
          <h2 id="my-issues-title">My Issues</h2>
          <p>Track your knowledge gap reports</p>
        </div>

        <button
          type="button"
          className="header-button"
          onClick={() => setShowMyIssues(false)}
          aria-label="Close My Issues"
        >
          ✕
        </button>
      </div>

      {myIssuesLoading ? (
        <p role="status">Loading your issues...</p>
      ) : myIssuesError ? (
        <div>
          <p role="alert">{myIssuesError}</p>
          <button
            type="button"
            className="header-button"
            onClick={fetchMyIssues}
          >
            Try again
          </button>
        </div>
      ) : myIssues.length === 0 ? (
        <p>You haven't reported any issues yet.</p>
      ) : (
        <div className="document-modal-list">
          {myIssues.map((issue) => (
            <article className="my-issue-card" key={issue.id}>
              <div className="my-issue-heading">
                <strong>Issue #{issue.id}</strong>
                <span className={`issue-status status-${issue.status}`}>
                  {issue.status.replace("_", " ")}
                </span>
              </div>

              <p className="my-issue-question">{issue.question}</p>

              <p className="my-issue-category">
                Category: {issue.category.replaceAll("_", " ")}
              </p>

              {issue.details && (
                <p className="my-issue-details">{issue.details}</p>
              )}

              <div className="my-issue-response">
                <strong>Admin response</strong>
                <p>
                  {issue.admin_response ||
                    "No response yet. The administrator may still be reviewing this issue."}
                </p>
              </div>

              <small>
                Submitted:{" "}
                {new Date(issue.created_at).toLocaleString()}
              </small>
            </article>
          ))}
        </div>
      )}
    </section>
  </div>
)}


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
            <div className="document-modal-item" key={doc.id}>
              <input
                id={`document-select-${doc.id}`}
                type="checkbox"
                checked={selectedDocumentIds.some(
                  (id) => String(id) === String(doc.id)
                )}
                onChange={(event) => {
                  setSelectedDocumentIds((previous) =>
                    event.target.checked
                      ? [...previous, doc.id]
                      : previous.filter((id) => String(id) !== String(doc.id))
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
                <small>
                  {doc.owner_id == null
                    ? "Legacy document · Uploader unknown"
                    : `Uploaded by: ${doc.uploaded_by || "Unknown"}`}
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
            </div>
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
              {message.role === "assistant" &&
                !message.error &&
                message.hasSufficientEvidence === false &&
                  messages
                    .slice(0, index)
                    .some((item) => item.role === "user") && (
                    <button
                      type="button"
                      className="report-issue-button"
                      onClick={() => {
                        const previousUserMessage = messages
                          .slice(0, index)
                          .reverse()
                          .find((item) => item.role === "user");

                        if (previousUserMessage) {
                          setIssueQuestion(previousUserMessage.content);
                          setIssueDetails("");
                          setIssueCategory("missing_information");
                          setIssueModalOpen(true);
                        }
                      }}
                    >
                      <span aria-hidden="true">⚑</span> Report an issue
                    </button>
                )}

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

        {issueModalOpen && (
                <div
                  className="issue-modal-backdrop"
                  onClick={(event) => {
                    if (event.target === event.currentTarget && !issueSubmitting) {
                      setIssueModalOpen(false);
                      setIssueError("");
                      setIssueSuccess("");
                    }
                  }}
                >
                  <section
                    className="issue-modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="issue-modal-title"
                  >
                    <h2 id="issue-modal-title">Report a knowledge issue</h2>

                    {issueSuccess ? (
                      <>
                        <p role="status">{issueSuccess}</p>
                        <button
                          type="button"
                          onClick={() => {
                            setIssueModalOpen(false);
                            setIssueSuccess("");
                            setIssueError("");
                          }}
                        >
                          Done
                        </button>
                      </>
                    ) : (
                      <form onSubmit={submitKnowledgeIssue}>
                        <label htmlFor="issue-question">Your question</label>
                        <textarea
                          id="issue-question"
                          value={issueQuestion}
                          onChange={(event) => setIssueQuestion(event.target.value)}
                          maxLength={5000}
                          required
                          rows={3}
                        />

                        <label htmlFor="issue-category">Reason for reporting</label>
                        <select
                          id="issue-category"
                          value={issueCategory}
                          onChange={(event) => setIssueCategory(event.target.value)}
                        >
                          <option value="missing_information">
                            Information is missing
                          </option>
                          <option value="access_problem">
                            I cannot access the information
                          </option>
                          <option value="incorrect_answer">
                            The answer may be incorrect
                          </option>
                        </select>

                        <label htmlFor="issue-details">
                          Additional details (optional)
                        </label>
                        <textarea
                          id="issue-details"
                          value={issueDetails}
                          onChange={(event) => setIssueDetails(event.target.value)}
                          maxLength={2000}
                          rows={3}
                          placeholder="Tell the administrator what you expected to find..."
                        />

                        {issueError && (
                          <p className="login-error" role="alert">
                            {issueError}
                          </p>
                        )}

                        <div className="issue-modal-actions">
                          <button
                            type="button"
                            disabled={issueSubmitting}
                            onClick={() => {
                              setIssueModalOpen(false);
                              setIssueError("");
                            }}
                          >
                            Cancel
                          </button>

                          <button
                            type="submit"
                            disabled={issueSubmitting || !issueQuestion.trim()}
                          >
                            {issueSubmitting ? "Submitting..." : "Submit issue"}
                          </button>
                        </div>
                      </form>
                    )}
                  </section>
                </div>
                )}

        {loading && (
  <div
    className="message-row assistant"
    role="status"
    aria-live="polite"
    aria-label="EKIP is generating an answer"
  >
    <div
      className="avatar assistant-avatar"
      aria-hidden="true"
    >
      ✦
    </div>

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

            if (loading) return;

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
    <option key={doc.id} value={doc.id}>
      {doc.filename} (ID: {doc.id})
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
