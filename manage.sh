
#!/usr/bin/env sh

set -x 
set -euo pipefail

TEST_ARGS="-f docker-compose-test.yml"



manage() {
   docker compose -f docker-compose.yml -f docker-compose-inits.yml run --rm manage $@
}

language() {
    docker compose exec frontend sed -i 's/"defaultLanguage": "en"/"defaultLanguage": "ru"/' usr/share/nginx/html/conf.json
    docker compose restart frontend
}



