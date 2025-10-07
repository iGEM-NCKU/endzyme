# Endzyme

[![Github All Releases](https://img.shields.io/github/downloads/iGEM-NCKU/endzyme/total.svg)]()

## Table of Contents

## How to use this software

- We Strongly recommand you to use **Endzyme software** on our Wiki website.

## Usage

> ⚠️ **Important:** To ensure proper functionality, the server stack must be started in the following order: **Gunicorn → Nginx**.  

### 1. Environment Setup

1. Create a Python environment (recommended: `conda` or `venv`):

```bash
conda create -n endzyme python=3.10
conda activate endzyme
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Ensure `nginx` and `gunicorn`are installed and accessible:
```bash
sudo apt install nginx
pip install gunicorn
```
### 2. Run Flask via Gunicorn

git clone our repo
```bash
git clone https://github.com/iGEM-NCKU/endzyme.git
``` 
Navigate to the project root:
```bash
cd /home/path/to/root
```
Start Gunicorn (example: 4 workers, listening on port 8001):
```bash
gunicorn -w 4 -b 127.0.0.1:8001 main:app
```
### 3. Configure and Start Nginx
```nginx
upstream endzyme {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name _;
    root /home/path/to/root;

    location /static/ {
        alias /home/path/to/root/static/;
    }

    location /api/ {
        proxy_pass http://endzyme;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```
Then restart Nginx:
```bash
sudo nginx -t        # test configuration
sudo systemctl restart nginx
```

Now the Endzyme frontend and API are available at `http://<server-ip>/`.

## Background

![image](https://hackmd.io/_uploads/H1zpGTXPle.png)

The design and optimization of enzymes for specific functions have always been a critical aspect of biotechnology. Traditional methods for enzyme engineering are often labor-intensive, requiring iterative rounds of mutation, expression, and screening. In recent years, the integration of artificial intelligence (AI) and computational biology has revolutionized this process, allowing for the in silico prediction of enzyme structures, stability, and functionality. By combining cutting-edge AI models, molecular modeling tools, and computational docking, this software provides an automated platform for novel enzyme sequence generation and efficiency analysis.

> Read more about background here:


