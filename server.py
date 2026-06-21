import uvicorn


if __name__ == "__main__":
    uvicorn.run("sage_research.api.app:app", host="0.0.0.0", port=8000, reload=True)