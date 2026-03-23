FROM python:3.9-slim

WORKIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python3", "maxim4.py"]