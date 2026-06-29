#!/system/bin/sh
BASE=/data/adb/picoclaw
MODDIR=/data/adb/modules/picoclaw
CTL=$MODDIR/bin/picoclawctl
RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; NC='\033[0m'

printf "${BLUE}PicoClaw Health${NC}\n"
[ -x "$CTL" ] || { printf "${RED}module binary missing${NC}\n"; exit 1; }
"$CTL" status 2>&1 | while IFS= read -r line; do
  case "$line" in
    *'running'*|enabled*) printf "${GREEN}%s${NC}\n" "$line" ;;
    *'not running'*|disabled*) printf "${RED}%s${NC}\n" "$line" ;;
    *) printf "${YELLOW}%s${NC}\n" "$line" ;;
  esac
done
printf "${BLUE}Dashboard:${NC} http://127.0.0.1:18800\n"
printf "${BLUE}Logs:${NC} $BASE/logs/service.log\n"
