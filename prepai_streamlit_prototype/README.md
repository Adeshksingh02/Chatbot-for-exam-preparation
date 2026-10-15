# PrepAI — AI-powered study workspace

A Streamlit hackathon prototype for **Education Technologies and Future Learning**.

## Features
- Upload a text-based PDF and extract page text.
- Ask questions grounded in relevant document chunks.
- Generate exam-revision summaries.
- Generate multiple-choice practice quizzes and score answers.
- Generate interactive revision flashcards.
- Dark navy/cyan responsive-style Streamlit interface.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (optional but recommended).
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Create `.streamlit/secrets.toml` with:
   ```toml
   GEMINI_API_KEY = "your_actual_gemini_api_key"
   GEMINI_MODEL = "gemini-3.8-flash"
   ```
6. Start the app:
   ```bash
   streamlit run app.py
   ```

If that model is unavailable to your API account, replace `GEMINI_MODEL` with a model ID available in your Google AI Studio account.

## Deploy on Streamlit Community Cloud
1. Push these project files to a GitHub repository.
2. Go to https://share.streamlit.io/ and sign in with GitHub.
3. Select the repository, branch, and `app.py` as the main file.
4. In app settings / Advanced settings, add these secrets:
   ```toml
   GEMINI_API_KEY = "your_actual_gemini_api_key"
   GEMINI_MODEL = "gemini-3.8-flash"
   ```
5. Deploy. Never put the real API key in GitHub or in `app.py`.

## Important limitations
- Keyword-based retrieval is used rather than vector embeddings.
- Text-based PDFs work best; scanned PDFs may not contain extractable text.
- Uploaded files are processed in the app session and are not persisted to a database.
- AI-generated answers, summaries, and quizzes can contain errors. Verify important information against the original document.
- This is a student prototype, not a certified education or assessment system.
