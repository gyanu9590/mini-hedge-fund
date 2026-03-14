from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.route import router

app = FastAPI(
    title="Mini Hedge Fund API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Mini Hedge Fund API Running"}