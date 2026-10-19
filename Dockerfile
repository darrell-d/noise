FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --gid 10001 noise && useradd --uid 10001 --gid noise --create-home noise
COPY --chown=noise:noise . .
RUN mkdir -p /app/data /app/staticfiles && chown -R noise:noise /app/data /app/staticfiles
USER noise
EXPOSE 8000
CMD ["sh", "scripts/docker-entrypoint.sh"]
