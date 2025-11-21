from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.auth.login import router as auth_router
from src.users.users import router as users_router
from src.documents.document import router as documents_router, category_router as categories_router, public_router as public_documents_router
from fastapi_mcp import FastApiMCP

from datetime import datetime

app = FastAPI(
    title="Smart Documents API",
    description="API for Smart Documents Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# log.add_log(app)


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(categories_router, prefix="/categories", tags=["Categories"])
app.include_router(public_documents_router, prefix="/public-documents", tags=["Public Documents"])

mcp = FastApiMCP(app)
mcp.mount()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002,reload=True)


