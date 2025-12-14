# Running list of TODOS

Broken up by category. 


## App & Infra

- [x] Create Dockerfile for fastAPI app.
- [ ] Setup block storage for `content/`



## Automation

- [ ] Automate build and push to ECR and private harbor registry with gha
- [ ] Tests and linting with github actions
- [ ] Automated deployment with terraform 
- [ ] Automated server restart with new image on build and push
- [ ] Local deployments with ArgoCD for testing, then push to 'prod' in AWS