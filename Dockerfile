FROM python:3.11.9
WORKDIR /app
COPY requirements.txt /app
RUN pip install -r requirements.txt