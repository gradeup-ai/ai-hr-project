(
echo from fastapi import FastAPI
echo.
echo app = FastAPI()
echo.
echo @app.get("/")
echo def read_root():
echo     return {"message": "AI-HR API работает!"}
) > app.py
 
