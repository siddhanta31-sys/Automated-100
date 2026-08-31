FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STREAMLIT_SERVER_FILE_WATCHER_TYPE=none
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD sh -c "python -u supervisor.py & exec streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT:-10000} --server.headless true --server.fileWatcherType none"
