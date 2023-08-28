#!/usr/bin/env sh

set -x 
set -euo pipefail

TEST_ARGS="-f docker-compose-test.yml"
export $(cat .env.test | xargs)

docker pull $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy_test() {
    
    docker compose $TEST_ARGS down
    docker compose $TEST_ARGS up -d postgres-test
    sleep 5
    docker compose $TEST_ARGS cp .gitlab/init.sql postgres-test:/tmp
    docker compose $TEST_ARGS exec -it postgres-test ash -c "dropdb -U taiga taiga && createdb -U taiga -O taiga taiga && psql -U taiga taiga < /tmp/init.sql"
    docker compose $TEST_ARGS up -d
    docker compose $TEST_ARGS cp taiga/taiga.conf taiga:/etc/nginx/conf.d/default.conf
    docker compose $TEST_ARGS restart

}

deploy_stage() {

    deploy_test
    docker compose $TEST_ARGS up -d  

}

case "$1" in
    test)
        deploy_test
        ;;
    stage)
        deploy_stage
        ;;
    *)
        exit 1
        ;;
esac