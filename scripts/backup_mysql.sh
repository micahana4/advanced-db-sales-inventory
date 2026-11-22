
#!/bin/bash
set -euo pipefail
umask 077

if [[ $# -ne 1 || "$1" != /* ]]; then
    echo "Usage: $0 /absolute/path/to/backup-directory" >&2
    exit 2
fi

backup_dir="$1"
database="${MYSQL_DATABASE:-sales_inventory}"
login_path="${MYSQL_BACKUP_LOGIN_PATH:-sales_backup}"
dump="${MYSQLDUMP_BIN:-mysqldump}"

mkdir -p "$backup_dir"
temp=$(mktemp "$backup_dir/.backup.XXXXXX")
trap 'rm -f "$temp"' EXIT

"$dump" --login-path="$login_path" --single-transaction --quick --no-tablespaces \
    --set-gtid-purged=OFF -- "$database" | gzip > "$temp"

gzip -t "$temp"

destination="$backup_dir/$database-$(date -u +%Y%m%dT%H%M%SZ)-${temp##*.}.sql.gz"

mv "$temp" "$destination"
printf '%s\n' "$destination"
