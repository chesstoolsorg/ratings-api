# Build with repository root as context:
#   docker build -t ratings-api .
FROM python:3.12-alpine3.20

WORKDIR /app

RUN apk add --no-cache build-base libffi-dev zip unzip wget

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p rating-lists && chmod +x initialize_rating_lists.sh

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
