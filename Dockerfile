FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY paperstudio /app/paperstudio
COPY studio_web.py /app/studio_web.py
ENV ACADEMICPDF_HOME=/data
EXPOSE 8765
# Default localhost-only behavior is deliberately overridden for Docker routing.
# Do not publish this unauthenticated app directly to the Internet.
ENV ACADEMICPDF_ALLOW_REMOTE=1
CMD ["python", "studio_web.py", "--host", "0.0.0.0", "--port", "8765", "--no-browser"]
