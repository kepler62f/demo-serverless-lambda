Demo Serverless Lambda
======================

To set up and deploy:

- Clone this repo

- Run `npm install` to install serverless 
plugins. The serverless configuration uses
the docker option in `serverless-python-requirements`
plugin to package the lambda. It uses `serverless-pseudo-parameters`
to obtain the AWS account number from the deployment 
machine.   

- Ensure docker is installed and running: 

```https://docs.docker.com/install/linux/docker-ce/ubuntu/```

- Update the environment variables in `serverless.yml` for respective stages:
  - DOWNLOAD_URL: the url of the sql scripts zip file (custom.download_url.<stage>.url) 
  - DB_HOST: MySql database endpoint (custom.source_db.<stage>.host)
  - DB_USER: MySql database username (custom.source_db.<stage>.user)
  - DB_P: MySql database password (custom.source_db.<stage>.p)
  - DB_NAME: MySql database name (custom.source_db.<stage>.db)

- Run `sls deploy --stage <stage>`. 