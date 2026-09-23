GITHUB PAGES SETUP

1. Copy index.html, style.css, script.js and .nojekyll into the root of your repository.
2. Commit and push to main.
3. GitHub -> Repository -> Settings -> Pages.
4. Source: Deploy from a branch.
5. Branch: main, Folder: / (root).
6. Save.
7. Your project site will be: https://sk-maaz243.github.io/NLP-Text-Summarization/

IMPORTANT
This static version calls the Gemini REST API directly from the visitor browser using the API key they enter. Never put a real API key in this repository.
The PDF button uses the browser Print dialog; choose Save as PDF.
The Python/Flask backend can remain in the repository for local/server deployment. GitHub Pages itself does not execute Python.
