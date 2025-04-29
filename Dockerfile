# 使用官方Python映像檔
FROM python:3.11-slim

# 安裝ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# 設定工作目錄
WORKDIR /app

# 複製專案檔案到容器中
COPY . .

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 啟動指令
CMD ["bash", "start.sh"]
