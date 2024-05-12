from fastapi import FastAPI, HTTPException, File, UploadFile
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Adjust the origin as needed
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


from query import PDFQuery, WebQuery


pdf_query_processor = PDFQuery(openai_api_key="sk-proj-3ohj0BPCEvr5dXZ71z5aT3BlbkFJJaXwHZUUgayFqTMKHVwi")
web_query_processor = WebQuery(openai_api_key="sk-proj-3ohj0BPCEvr5dXZ71z5aT3BlbkFJJaXwHZUUgayFqTMKHVwi")

ingested_files = []
ingested_urls = []

@app.post("/ingest")
async def ingest_content(urls: List[str], files: List[UploadFile] = File(...)):

    try:
        # Ingest PDF files
        for file in files:
            content = await file.read()
            with open("temp.pdf", "wb") as temp_file:
                temp_file.write(content)
            pdf_query_processor.ingest("temp.pdf")
            ingested_files.append(file.filename)

        # Ingest web content
        for url in urls:
            web_query_processor.ingest(url)
            ingested_urls.append(url)

        return {"message": f"PDF files {', '.join(ingested_files)} and website URLs {', '.join(ingested_urls)} successfully ingested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
async def ask_question(question: str):
    try:
        # Get answer from PDF query processor
        pdf_answer = pdf_query_processor.ask(question)
        
        # Get answer from web query processor
        web_answer = web_query_processor.ask(question)
        
        # Combine answers from both processors
        combined_answer = f"PDF Answer:\n{pdf_answer}\n\nWeb Answer:\n{web_answer}"
        
        return {"answer": combined_answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

