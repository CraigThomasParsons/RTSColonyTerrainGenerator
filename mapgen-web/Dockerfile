FROM golang:1.21-alpine AS builder

WORKDIR /build

# Copy go.mod and source
COPY go.mod .
COPY cmd ./cmd
COPY internal ./internal
COPY web ./web

# Build
RUN go build -o server ./cmd/server

# Runtime stage
FROM alpine:latest

WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/server /app/server
COPY --from=builder /build/web /app/web

EXPOSE 5003

CMD ["/app/server"]
