# Use Windows Server Core 2022 as base image
FROM mcr.microsoft.com/windows/servercore:ltsc2022

WORKDIR /app

# Copy pre-built embedded Python (with all dependencies pre-installed) and MT5 archive
COPY python-embed.zip .
COPY meta.zip .

# Extract embedded Python to C:\Python and clean up
RUN powershell -command "Expand-Archive -Path .\python-embed.zip -DestinationPath 'C:\Python'" && del .\python-embed.zip

# Add Python to system PATH
RUN setx /M PATH "C:\Python;C:\Python\Scripts;%PATH%"

# Extract MT5 and clean up archive
RUN powershell -command "Expand-Archive -Path .\meta.zip -DestinationPath 'C:\Program Files'" && del .\meta.zip

# Copy application scripts
COPY src/streamer.py .
COPY src/api_gateway.py .
COPY src/start.ps1 .

# Define environment variable for the API Key
ENV API_KEY ""

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD ["powershell", "-Command", "try { $resp = Invoke-WebRequest -Uri 'http://localhost:8080/health' -UseBasicParsing; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"]

CMD ["powershell", "-File", "C:\\app\\start.ps1"]
