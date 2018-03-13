# Dockerfile-builder

Dockerfile builder script wrote in Python3

- Uses the "build > setup > config > test > push" pattern
  + To automate and test builds with a few easy commands:
    * bin/build
    * bin/test
    * bin/push
  + To run faster tests
    * bin/cache_warm
  + To test manually the image
    * bin/test_container
  + to build different versions of an image
    * bin/deploy_branches (deploy changes from master to other branches (git anti-pattern) )

- Permits inheritance between builds
  + Run all configuration scripts at container start -> See `docker-config` script or `template/docker-config`
  + ( ex: if the service running in the container need configuration on the fly (at container start) all images that build on top will configure at same stage: before service run)

- Get rediness and liveness script kubernetes friendly Out-of-the-box
  + Check `imports/docker-rediness-test` in the image or `docker-rediness-test` inside the container
  + Check `imports/docker-liveness-test` in the image or `docker-liveness-test` inside the container

- Hardened alpine image out-of-the-box (in-progress)
  + Remove useless potentially dangerous script after container configuration
  + Let you specify user and groups used in the container

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
- Edit and configure `dockerfile-builder.yaml` adding all env vars and processes needed to
    + Build the docker image
    + Build the docker image
    + Run tests to verify on the image
- Run `dockerfile-build` on master
- Deploy changes and rebuild other branches running `bin/deploy-branches` on master

### Configuration CI 
Go on the CI and setup the build using files created ( automation in progress)
Ex:
~~~
# Move to the branch you want to build
- git checkout latest
# Build the docker image caching concurrenty
- bin/cache_warm & bin/build
# Test the image
- bin/test
# Push the image in the production registry if test succeded
- bin/push
~~~


