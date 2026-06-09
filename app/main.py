from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(router)

@app.get("/", response_class=HTMLResponse)
def homepage() -> HTMLResponse:
    return HTMLResponse(content=HOME_PAGE_HTML)

HOME_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DecisionsRX RAG UI</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f8fafc; color: #111827; }
    .container { max-width: 900px; margin: 0 auto; padding: 32px; }
    h1 { margin-bottom: 0.25em; }
    .card { background: white; border-radius: 16px; box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08); padding: 24px; margin-bottom: 24px; }
    label { display: block; margin-bottom: 10px; font-weight: 600; }
    input, textarea { width: 100%; border: 1px solid #d1d5db; border-radius: 12px; padding: 14px; margin-bottom: 16px; font-size: 1rem; }
    textarea { min-height: 140px; resize: vertical; }
    button { background: #2563eb; color: white; border: none; border-radius: 12px; padding: 14px 20px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .row { display: grid; gap: 24px; }
    .hint { color: #6b7280; font-size: 0.95rem; margin-top: -12px; margin-bottom: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>DecisionsRX UI</h1>
      <p>Ingest a local document directory, ask a question, and view the answer below.</p>
    </div>

    <div class="card">
      <h2>1. Document ingestion</h2>
      <label for="directory">Local directory path</label>
      <input id="directory" type="text" placeholder="/absolute/path/to/local/docs" />
      <div class="hint">Enter the path to the folder containing your `.txt`, `.pdf`, or `.docx` documents.</div>
      <button id="ingestBtn">Ingest documents</button>
      <p id="ingestResult"></p>
    </div>

    <div class="card">
      <h2>2. Ask a question</h2>
      <label for="question">Question</label>
      <textarea id="question" placeholder="What evidence exists for adoption risk?"></textarea>
      <label for="topK">Top K results</label>
      <input id="topK" type="number" min="1" max="20" value="5" />
      <button id="askBtn">Ask question</button>
    </div>

    <div class="card">
      <h2>3. Answer output</h2>
      <textarea id="output" readonly placeholder="Answer will appear here..."></textarea>
    </div>
  </div>

  <script>
    const ingestBtn = document.getElementById('ingestBtn');
    const askBtn = document.getElementById('askBtn');
    const directoryInput = document.getElementById('directory');
    const questionInput = document.getElementById('question');
    const topKInput = document.getElementById('topK');
    const ingestResult = document.getElementById('ingestResult');
    const output = document.getElementById('output');

    ingestBtn.addEventListener('click', async () => {
      ingestResult.textContent = 'Ingesting...';
      output.value = '';
      try {
        const response = await fetch('/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ directory: directoryInput.value.trim() }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || JSON.stringify(data));
        ingestResult.textContent = `Ingested ${data.documents_ingested} documents, indexed ${data.chunks_indexed} chunks.`;
      } catch (error) {
        ingestResult.textContent = `Error: ${error.message}`;
      }
    });

    askBtn.addEventListener('click', async () => {
      output.value = 'Loading answer...';
      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: questionInput.value.trim(), top_k: Number(topKInput.value) || 5 }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || JSON.stringify(data));
        const evidenceText = data.supporting_evidence.map((item) => `- ${item.snippet}`).join('\n');
        const limitationsText = (data.limitations || []).map((item) => `- ${item}`).join('\n');
        output.value = `Answer Summary:\n${data.answer_summary}\n\nRationale Breakdown:\n${JSON.stringify(data.rationale_breakdown, null, 2)}\n\nSupporting Evidence:\n${evidenceText}\n\nConfidence: ${data.confidence}\n\nLimitations:\n${limitationsText}`;
      } catch (error) {
        output.value = `Error: ${error.message}`;
      }
    });
  </script>
</body>
</html>
"""
