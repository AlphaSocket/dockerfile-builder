# Alphasocket/dockerfile-builder

Dockerfile builder wrote in Python3

- Uses the "build > setup > config > test > push" pattern 
   + To automate and test builds with a few easy commands
- Permits inheritance between builds
   + Run all configuration scripts at container start
   + ( ex: if the service running in the container need configuration on the fly (at container start) all images that build on top will configure at same stage: before service run)
- Build scripts to deploy changes from master to other branches (git anti-pattern)

## Install
~~~
git clone https://github.com/AlphaSocket/dockerfile-builder ~/Projects/
ln -s ~/Projects/dockerfile-builder/build.py ~/bin/dockerfile-build
chmod +x ~/bin/dockerfile-build
~~~

## Add env vars in ~/.bashrc
~~~bash
#
# DOCKER
#
export DOCKER_USER='docker-prd-user'
export DOCKER_REGISTRY='docker-prd-registry'

export DOCKER_DEV_USER='docker-dev-user'
export DOCKER_DEV_REGISTRY='docker-prd-registry'
~~~

## Usage

### Build Files
- Place a `dockerfile-builder.yaml` file in the project folder
- init git repo
    + `git init`
- Create branches (latest branch is required)
    + `git branch {branch-name}`
- Edit `dockerfile-builder.yaml` adding all env vars and processes needed to
    + Build the docker image
    + Build the docker image
    + Run tests to verify on the image
- Run `dockerfile-build` on master
- Deploy changes and rebuild other branches running `bin/deploy-branches` on master

### Configure CI
- Go on your favourite CI and setup the build using files created
Ex:
~~~
# Move to the branch you want to build
- git checkout latest
# Build the docker image
- bin/build
# Test the image
- bin/test
# Push the image in the registry if test succeded
- bin/push
~~~


