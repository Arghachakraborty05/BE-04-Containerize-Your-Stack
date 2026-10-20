import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import psycopg
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
  """Helper function to connect to PostgreSQL and return a connection."""
  # psycopg connects directly using the DATABASE_URL string
  conn = psycopg.connect(DATABASE_URL)
  return conn

def init_db():
  """Stage 1: Create tasks table if missing, and seed 3 examples only if empty."""
  conn = get_db_connection()
  with conn.cursor() as cursor:
      # PostgreSQL syntax: SERIAL PRIMARY KEY and BOOLEAN
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT FALSE
          )
      """)

      cursor.execute("SELECT COUNT(*) FROM tasks")
      count = cursor.fetchone()[0]

      if count == 0:
          initial_tasks = [
              ("Learn FastAPI", False),
              ("Build CRUD API", False),
              ("Test the API", False),
          ]
          cursor.executemany(
              "INSERT INTO tasks (title, done) VALUES (%s, %s)", initial_tasks
          )
          conn.commit()

  conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
  init_db()
  yield

app = FastAPI(title="Task API (PostgreSQL)", version="3.0", lifespan=lifespan)

@app.get("/", description="Get API information and available endpoints.")
def root():
    return {
        "name": "Task API (PostgreSQL)",
        "version": "3.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health", description="Check whether the API is running.")
def health():
    return {"status": "ok"}

@app.get("/tasks", description="Get all tasks.")
def get_tasks():
    """Stage 2: Read all tasks from PostgreSQL database."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, title, done FROM tasks")
        rows = cursor.fetchall()
    conn.close()

    # Map raw rows into dictionaries
    return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]

@app.get("/tasks/{task_id}", description="Get a single task by ID.")
def get_task(task_id: int):
    """Stage 2: Read a single task by ID from PostgreSQL database."""
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Use %s parameterized query to prevent SQL injection
        cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
        row = cursor.fetchone()
    conn.close()

    if row is None:
        return JSONResponse(
            status_code=404, content={"error": "Task not found"}
        )

    return {"id": row[0], "title": row[1], "done": row[2]}

@app.post("/tasks", status_code=201, description="Create a new task.")
def create_task(task_data: dict):
    """Stage 2: Create a new task in the SQLite database with validation."""
    title = task_data.get("title")

    if not isinstance(title, str) or not title.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Title is required"}
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert task into SQLite database (done defaults to 0 / False)
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)", (title.strip(), 0)
    )
    conn.commit()

    new_id = cursor.lastrowid

    # Fetch the newly created record to return it
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (new_id,))
    new_task = cursor.fetchone()
    conn.close()

    return dict(new_task)

@app.put("/tasks/{task_id}", description="Update a task by ID.")
def update_task(task_id: int, task_data: dict):
    """Stage 3: Update a task in the SQLite database by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if task exists
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    
    if task is None:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    if not task_data:
        conn.close()
        return JSONResponse(
            status_code=400,
            content={"error": "Request body cannot be empty"}
        )

    # Current values from DB
    current_title = task["title"]
    current_done = task["done"]

    if "title" in task_data:
        title = task_data["title"]

        if not isinstance(title, str) or not title.strip():
            conn.close()
            return JSONResponse(
                status_code=400,
                content={"error": "Title must be a non-empty string"}
            )
        current_title = title.strip()

    if "done" in task_data:
        done = task_data["done"]

        if not isinstance(done, bool):
            conn.close()
            return JSONResponse(
                status_code=400,
                content={"error": "Done must be a boolean"}
            )

        current_done = 1 if done else 0

    if "title" not in task_data and "done" not in task_data:
        conn.close()
        return JSONResponse(
            status_code=400,
            content={"error": "At least one of title or done is required"}
        )

    # Update database
    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (current_title, current_done, task_id),
    )
    conn.commit()

    # Fetch updated task to return
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_task = cursor.fetchone()
    conn.close()

    return dict(updated_task)

@app.delete("/tasks/{task_id}", status_code=204, description="Delete a task by ID.")
def delete_task(task_id: int):
    """Stage 3: Delete a task from the SQLite database by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if task exists
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()

    if task is None:
        conn.close()
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"}
        )

    # Delete task
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    return