FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 7860

CMD ["panel", "serve", "src/pywellsfmui/app.py", "--address=0.0.0.0", "--port=7860", "--allow-websocket-origin=*"]
