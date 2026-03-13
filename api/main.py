from fastapi import FastAPI
from api.route import router

app = FastAPI(
    title="Mini Hedge Fund API",
    version="1.0"
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Mini Hedge Fund API Running"}