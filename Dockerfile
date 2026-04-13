# --- مرحله ۱: Builder ---
FROM mcr.microsoft.com/windows/servercore:ltsc2022 AS builder
WORKDIR /source

COPY python-3.11.4-amd64.exe .
COPY meta.zip .
# --- Persian: کپی کردن اسکریپت‌های جدید ---
# --- English: Copying the new scripts ---
COPY src/api_gateway.py .
COPY src/streamer.py .
COPY src/start.ps1 .

# --- مرحله ۲: Final Image ---
FROM mcr.microsoft.com/windows/servercore:ltsc2022
WORKDIR /app

COPY --from=builder /source/python-3.11.4-amd64.exe .
RUN .\python-3.11.4-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 && del .\python-3.11.4-amd64.exe

COPY --from=builder /source/meta.zip .
RUN powershell -command "Expand-Archive -Path .\meta.zip -DestinationPath 'C:\Program Files'" && del .\meta.zip
RUN pip install "numpy<2.0.0" MetaTrader5 pandas websockets Flask waitress && pip cache purge

COPY --from=builder /source/streamer.py .
COPY --from=builder /source/api_gateway.py . 
COPY --from=builder /source/start.ps1 .

# --- Persian: تعریف متغیر محیطی برای کلید API ---
# --- English: Define environment variable for the API Key ---
ENV API_KEY ""

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD ["powershell", "-Command", "try { $resp = Invoke-WebRequest -Uri 'http://localhost:8080/health' -UseBasicParsing; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"]

CMD ["powershell", "-File", "C:\\app\\start.ps1"]
