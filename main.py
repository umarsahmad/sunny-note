from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# The endpoint of your cloud GPU server
CLOUD_API_URL = "http://YOUR_CLOUD_IP:8000/v1/chat/completions"  # vLLM example
CLOUD_API_KEY = "YOUR_API_KEY"  # if using auth

@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/", response_class=HTMLResponse)
async def handle_form(request: Request, user_input: str = Form(...)):
    # Send the user input to the cloud LLaMA server
        

    async with httpx.AsyncClient() as client:
        payload = {
            "model": "your-llama3-model-name",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.7
        }
        headers = {"Authorization": f"Bearer {CLOUD_API_KEY}"}
        response = await client.post(CLOUD_API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            # For vLLM / OpenAI-compatible
            assistant_message = data["choices"][0]["message"]["content"]
        else:
            assistant_message = f"Error: {response.status_code} {response.text}"

    return templates.TemplateResponse("index.html", {"request": request, "result": assistant_message})
