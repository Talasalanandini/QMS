# QMS Project

## Environment Variables
Create a `.env` file in the root directory with the following content:

```
DATABASE_URL=postgresql://user:password@localhost/qms
```

## Running the Project
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Run migrations (if using Alembic):
   ```
   alembic upgrade head
   ```
3. Start the FastAPI server:
   ```
   uvicorn main:app --reload
   ```
