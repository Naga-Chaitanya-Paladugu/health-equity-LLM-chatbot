import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pathlib import Path
import os

from backend.db_utils import connect_db, get_schema, validate_sql_query
from backend.sql_chain import get_sql_chain
from backend.answer_generator import get_natural_language_response

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

load_dotenv()

app = FastAPI()
chat_history = []

frontend_path = Path(__file__).resolve().parent.parent / "frontend"
#app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")
templates = Jinja2Templates(directory=str(frontend_path / "templates"))

# Load API Key
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is missing. Please check your .env file.")

llm = ChatGroq(model_name="llama3-8b-8192", api_key=groq_api_key)

class QueryRequest(BaseModel):
    query: str

 # Predefined question-to-SQL mapping
predefined_sql_map = {
    "What are the demographic proportions (race and gender) of patients visiting the hospital?": "Q1",
    "What are the top 5 busiest hospital locations?": "Q2",
    "How does the average age of a patient visiting the hospital vary according to their race?": "Q3",
    "How does the average age of a patient visiting the hospital vary according to their gender?": "Q4",
    "How do the average healthcare expenses and coverage of patients belonging to different races compare with their average incomes?": "Q5",
    "Show me the list of counties recorded with more obese cases.": "Q6",
    "Show me the list of counties with more patients suffering from stress.": "Q7",
    "Show me the list of counties recorded with more cases of sepsis.": "Q8",
    "List the top 10 locations of patients diagnosed with chronic conditions. (use condition_duration_days)": "Q9",
    "Give me the list of patient encounter types and their respective percentages.": "Q10",
    "Which zip codes have the highest emergency visit rates?": "Q11",
    "What is the average duration for each encounter class?": "Q12",
    "Which providers have the longest average encounter durations?": "Q13",
    "Which department has the longest average encounter duration?": "Q14",
    "What is the average encounter duration and out-of-pocket cost for private, government, and uninsured patients?": "Q15",
    "What is the average out-of-pocket cost and insurance coverage ratio across different age groups?": "Q16",
    "Which encounter classes brought in higher average claim profit margins?": "Q17",
    "Which regions are bringing the higher claim profit margins?": "Q18",
    "Which regions are bringing the lower claim profit margins?": "Q19",
    "What is the average cost coverage ratio for each insurer, grouped by private and government ownership?": "Q20",
    "Which regions have the highest number of uninsured patients based on payer data?": "Q21",
    "Which departments have the highest average claim profit margin?": "Q22",
    "Which departments see the most uninsured patients?": "Q23"
}

@app.post("/generate_sql")
def generate_sql(request: QueryRequest):
    try:
        schema_response = get_schema()
        database_schema = schema_response.get("database_schema", {})

        schema_text = "\n".join(
            [f"Table: {table}, Columns: {', '.join([col['column'] for col in columns])}"
             for table, columns in database_schema.items()]
        )

        # Check predefined query map
        if request.query in predefined_sql_map:
            qid = predefined_sql_map[request.query]
            path = Path(fr"C:\Users\palad\PycharmProjects\health-equity-LLM-chatbot-2\backend\data\predefined_sql\{qid}.sql")
            with open(path, "r", encoding="utf-8") as f:
                sql_query = f.read().strip()
        else:
            # Fallback to LLM-based generation
            chain = get_sql_chain(lambda: schema_text)
            chat_text = "\n".join(chat_history[-5:])
            sql_query = chain.invoke({"question": request.query, "chat_history": chat_text})

        # Validate SQL
        is_valid, validation_message = validate_sql_query(sql_query, database_schema)
        if not is_valid:
            return {"error": f"Invalid SQL: {validation_message}"}

        # Execute SQL
        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute(sql_query)
            result = cursor.fetchall()
        except Exception as sql_err:
            return {"error": f"SQL Execution Error: {sql_err}"}

        if not result:
            return {"query": sql_query, "results": "No data found."}

        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        # Natural language explanation
        nl_response = get_natural_language_response(llm, schema_text, request.query, sql_query, data)

        chat_history.append(f"User: {request.query}")
        chat_history.append(f"Assistant: {nl_response}")

        return {
            "query": sql_query,
            "results": data,
            "answer": nl_response
        }

    except Exception as e:
        return {"error": f"Unhandled Server Error: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Run the FastAPI server
if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000)