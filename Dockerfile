# -- Python Intelligence Swarm --
FROM python:3.12-slim as python-agents
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
CMD ["python", "agents_service/api/main.py"]

# -- Go Gateway --
FROM golang:1.22-alpine as go-gateway
WORKDIR /app
COPY gateway/go.mod gateway/go.sum ./
RUN cd gateway && go mod download
COPY . .
RUN cd gateway && go build -o /sarang-gateway ./cmd/gateway/main.go
CMD ["/sarang-gateway"]

# -- Next.js Dashboard --
FROM node:20-alpine as dashboard
WORKDIR /app
COPY dashboard/package.json dashboard/package-lock.json ./
RUN cd dashboard && npm install
COPY . .
RUN cd dashboard && npm run build
CMD ["cd", "dashboard", "&&", "npm", "run", "start"]
