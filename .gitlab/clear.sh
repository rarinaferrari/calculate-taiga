#!/usr/bin/env sh

docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
docker image prune -a -f
docker volume prune -f
rm -rf /builds
rm -rf /var/lib/docker
reboot

