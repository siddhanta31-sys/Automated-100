FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["sh","-c","python worker.py & streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-10000} --server.fileWatcherType=none --server.runOnSave=false"]
