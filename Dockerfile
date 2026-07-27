# Use Windows Server Core 2022 as base image
FROM mcr.microsoft.com/windows/servercore:ltsc2022

WORKDIR /app

# Copy Python installer and MT5 archive
COPY python-3.11.4-amd64.exe .
COPY meta.zip .

# Install Python and clean up installer
RUN .\python-3.11.4-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 && del .\python-3.11.4-amd64.exe

# Extract MT5 and clean up archive
RUN powershell -command "Expand-Archive -Path .\meta.zip -DestinationPath 'C:\Program Files'" && del .\meta.zip

# Copy dependencies list and install
COPY requirements.txt .
RUN pip install -r requirements.txt && pip cache purge

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
