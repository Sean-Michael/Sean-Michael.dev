# Personal Website as Code

This repositor *is* my website. From the infrastructure code that deploys the hosting setup in AWS, to the frontend and backend python code for the web content. Including the CI/CD in GitHub Actions to build, test, and deploy!

It's going to be so much fun. :)

## Phase 1: Website

I'm trying to do a 0% JS run and 100% server-side rendering with templating for simplicity since I'm not a web developer.

I'll be using a simple FastAPI and HTMX stack to power my site with dynamic templating with Jinja2.

### Development notes

Running the application with reload:

```bash
uvicorn main:app --reload
```
