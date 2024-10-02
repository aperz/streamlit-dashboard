FROM python:3.12

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install requirements
COPY requirements.txt requirements.txt
RUN pip install -U pip
RUN pip install -r requirements.txt
RUN python -c 'import nltk; nltk.download("vader_lexicon")'

# Expose port you want your app on
EXPOSE 8080

# Copy app code and set working directory
COPY . .
WORKDIR .

# Run
ENTRYPOINT ["streamlit", "run", "dashboard_app.py", "–server.port=8501", "–server.address=0.0.0.0"]

