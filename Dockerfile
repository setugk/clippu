FROM python:3.12-alpine
WORKDIR /app
RUN pip install flask --no-cache-dir
COPY app.py db.py ./
COPY templates/ templates/
COPY static/ static/
EXPOSE 5000
CMD ["python", "app.py"]
