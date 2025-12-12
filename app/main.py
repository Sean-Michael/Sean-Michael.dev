from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

items = ["Rock Climbing", "Skiing"]

@app.get("/", response_class=HTMLResponse)
async def get_items(request: Request):
    return templates.TemplateResponse("items.html", {"request": request, "items": items})

@app.post("/add-item")
def add_item(request: Request, item: str = Form(...)):
    items.append(item)
    return templates.TemplateResponse("partials/item.html",  {"request": request, "item": item})


