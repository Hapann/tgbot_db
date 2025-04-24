FROM python:latest
WORKDIR /app
COPY req.txt /app
RUN pip install -r req.txt