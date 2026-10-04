import { useState } from "react";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);

  const askQuestion = async () => {
    if (!question.trim()) {
      return;
    }

    setLoading(true);
    setAnswer("");
    setSources([]);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      setAnswer(data.answer);
      setSources(data.sources || []);

    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        padding: "40px",
        maxWidth: "900px",
        margin: "auto",
      }}
    >
      <h1>EKIP</h1>

      <p>Enterprise Knowledge Intelligence Platform</p>

      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask a question about your documents..."
        rows="5"
        style={{
          width: "100%",
          padding: "12px",
          fontSize: "16px",
          boxSizing: "border-box",
        }}
      />

      <br />
      <br />

      <button
        onClick={askQuestion}
        disabled={loading}
        style={{
          padding: "12px 24px",
          fontSize: "16px",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Thinking..." : "Ask EKIP"}
      </button>

      {answer && (
        <div style={{ marginTop: "30px" }}>
          <h2>Answer</h2>

          <div
            style={{
              padding: "20px",
              background: "#f5f5f5",
              borderRadius: "8px",
              whiteSpace: "pre-wrap",
            }}
          >
            {answer}
          </div>
        </div>
      )}

      {sources.length > 0 && (
        <div style={{ marginTop: "30px" }}>
          <h2>Sources</h2>

          {sources.map((source, index) => (
            <div
              key={index}
              style={{
                padding: "15px",
                marginBottom: "10px",
                background: "#eeeeee",
                borderRadius: "8px",
              }}
            >
              <strong>📄 {source.filename}</strong>

              <div>
                Chunk: {source.chunk_index}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;