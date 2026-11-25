# Project Setup and Installation

# 1. Clone the Repository

Now you can safely clone the course project:

```bash
git clone git@github.com:ps22373/assignment12.git
cd assignment12
```

---

# 2. Create and Activate a Virtual Environment

(Optional but recommended)

```bash
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate.bat  # Windows
```

### Install Required Packages

```bash
pip install -r requirements.txt
```

---

# 3. Run the Application Using Docker Compose

Make sure Docker Desktop is installed and running.

Build and start the application and its configured services:

``` bash
docker compose up --build
```

Once the containers are running, access the following:

| Service        | URL          |
| -------------- | ------------ |
| FastAPI Application          | http://localhost:8000 |
| Interactive API Documentation (Swagger)  | http://localhost:8000/docs |
| pgAdmin  | http://localhost:5050      |


To stop the application:
```bash
docker compose down
```

---

# 4. Run Tests Locally

Run the tests:
```bash
pytest
```

To generate a test coverage report (if pytest-cov is installed):

```bash
pytest --cov --cov-report=term-missing
```

---

# 5. Docker Hub

The project Docker image is available at:

https://hub.docker.com/r/ps223/assignment12

To pull the image:
```bash
docker pull ps223/assignment12:latest
```