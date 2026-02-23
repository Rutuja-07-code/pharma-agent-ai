# pharma-agent-ai

## Run frontend + backend together

cd frontend
python3 -m http.server 5501


cd backend/app
uvicorn main:app --reload --host 127.0.0.1 --port 8000