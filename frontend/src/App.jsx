import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  const askQuestion = async () => {
    if (!question.trim() || loading) {
      return;
    }

    const userQuestion = question.trim();

    setQuestion("");

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userQuestion,
      },
    ]);

    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: userQuestion,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
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
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askQuestion();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className="app">

      {/* Header */}
      <header className="header">
        <div>
          <h1>EKIP</h1>
          <p>Enterprise Knowledge Intelligence Platform</p>
        </div>

        {messages.length > 0 && (
          <button
            className="clear-button"
            onClick={clearChat}
          >
            Clear Chat
          </button>
        )}
      </header>

      {/* Chat Area */}
      <main className="chat-container">

        {messages.length === 0 && (
          <div className="welcome">
            <h2>Welcome to EKIP 👋</h2>

            <p>
              Ask questions about your enterprise documents
              and get AI-powered answers with source citations.
            </p>

            <div className="example-questions">
              <button
                onClick={() =>
                  setQuestion(
                    "What are the education details of the author?"
                  )
                }
              >
                Education details
              </button>

              <button
                onClick={() =>
                  setQuestion(
                    "What programming languages are mentioned?"
                  )
                }
              >
                Programming languages
              </button>

              <button
                onClick={() =>
                  setQuestion(
                    "What technologies are mentioned in the document?"
                  )
                }
              >
                Technologies
              </button>
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message-row ${message.role}`}
          >

            <div className="avatar">
              {message.role === "user" ? "You" : "AI"}
            </div>

            <div
              className={`message ${
                message.error ? "error-message" : ""
              }`}
            >
              <div className="message-content">
                {message.content}
              </div>

              {/* Sources */}
              {message.role === "assistant" &&
                message.sources?.length > 0 && (
                  <div className="sources">

                    <h4>📚 Sources</h4>

                    {message.sources.map(
                      (source, sourceIndex) => (
                        <div
                          className="source-card"
                          key={sourceIndex}
                        >
                          <strong>
                            📄 {source.filename}
                          </strong>

                          <span>
                            Chunk {source.chunk_index}
                          </span>
                        </div>
                      )
                    )}

                  </div>
                )}
            </div>

          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="message-row assistant">
            <div className="avatar">AI</div>

            <div className="message">
              <div className="thinking">
                EKIP is thinking
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />

      </main>

      {/* Input */}
      <div className="input-area">

        <textarea
          value={question}
          onChange={(event) =>
            setQuestion(event.target.value)
          }
          onKeyDown={handleKeyDown}
          placeholder="Ask EKIP about your documents..."
          rows="2"
          disabled={loading}
        />

        <button
          className="send-button"
          onClick={askQuestion}
          disabled={loading || !question.trim()}
        >
          {loading ? "..." : "➤"}
        </button>

      </div>

      <div className="input-hint">
        Press Enter to send • Shift + Enter for a new line
      </div>

    </div>
  );
}

export default App;