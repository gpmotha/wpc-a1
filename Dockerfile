FROM python:3.11-slim

WORKDIR /app

COPY wpc_admin/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY wpc_admin/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
