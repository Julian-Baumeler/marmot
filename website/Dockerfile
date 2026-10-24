FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Railway does not pull Git LFS, and media/*.mp4 is dockerignored so the
# pointer stubs cannot overwrite these downloads at COPY time.
COPY fetch_media.py .
ARG RAILWAY_GIT_COMMIT_SHA=master
RUN python3 fetch_media.py "$RAILWAY_GIT_COMMIT_SHA"
COPY . .
ENV PORT=8080
EXPOSE 8080
CMD ["python3", "server.py"]
