#!/usr/bin/env sh
# Запуск тестов по этапам. Этапы идут по порядку файлов tests/test_*.py.
# Если этап упал, следующие не запускаются.
set -eu

PYTHON="${PYTHON:-.venv/bin/python}"
mkdir -p results
: > results/summary.txt

for test_file in tests/test_*.py; do
    stage="$(basename "$test_file" .py)"
    echo
    echo "========== ЭТАП: $stage =========="
    if "$PYTHON" -m pytest "$test_file" -v -rx --tb=short -p no:cacheprovider 2>&1 | tee "results/$stage.txt"; then :; fi
    result="$(tail -n 1 "results/$stage.txt" | tr -d '=' | sed 's/^ *//; s/ *$//')"
    case "$result" in
        *[0-9]" failed"*|*error*) status=FAILED ;;
        *) status=ok ;;
    esac
    echo "$stage: $status — $result" >> results/summary.txt
    if [ "$status" = FAILED ]; then
        echo "Этап $stage не прошёл, следующие этапы не запускаются."
        exit 1
    fi
done

echo
echo "========== ИТОГ ПО ЭТАПАМ =========="
cat results/summary.txt
