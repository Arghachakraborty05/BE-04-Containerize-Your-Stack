# Task API (PostgreSQL & Docker Backend) - BE-04

Part 3 of the FlyRank Backend AI Engineering track. Containerizing the FastAPI CRUD backend stack with PostgreSQL running in Docker.

## Run Database

The course guideline suggests running:

```powershell
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres
```
### Note on PostgreSQL Version Pinning (`postgres:16`)

While the guideline uses the rolling `postgres` tag (which defaults to the latest version like PostgreSQL 18+), newer versions introduce strict data directory validation bugs and initialization errors when mounting named volumes (`taskdata`) on Windows environments. 

Pinning explicitly to **PostgreSQL 16** (`postgres:16`) bypasses these validation bugs, ensuring stable data persistence and successful local connectivity. 

**Production Run Command:**

```powershell
docker run --name taskdb -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tasks -p 5432:5432 -v taskdata:/var/lib/postgresql/data -d postgres:16
```