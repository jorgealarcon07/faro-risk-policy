FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
RUN pip install --no-deps --no-build-isolation . && useradd --create-home faro && mkdir -p local && chown -R faro:faro /app/local
USER faro
ENTRYPOINT ["faro-risk"]
CMD ["demo"]
