# ===============================
# Stage 1: Builder
# ===============================
FROM python:3.12-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装ffmpeg（用于音频处理）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 安装yt-dlp（用于B站视频下载）
RUN pip install --no-cache-dir yt-dlp

# ===============================
# Stage 2: Final
# ===============================
FROM python:3.12-slim AS final

# 设置工作目录
WORKDIR /app

# 安装ffmpeg（用于音频处理），并清理apt缓存
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖和yt-dlp可执行文件
# 1. 复制site-packages（Python依赖）
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# 2. 复制yt-dlp可执行文件（通常在 /usr/local/bin/yt-dlp）
COPY --from=builder /usr/local/bin/yt-dlp /usr/local/bin/yt-dlp

# 复制后端应用代码
COPY app ./app

# 暴露FastAPI默认端口
EXPOSE 8000

# 启动命令：打印所有环境变量
CMD ["env"] 