#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
COURSE = ROOT / "course"
LESSONS = COURSE / "lessons"
REQUIRED = [
    "work-order.yaml", "lesson.md", "video-script.md", "prompts.md",
    "assignment.md", "quiz.yaml", "qa-report.md"
]
MIN_BYTES = {
    "work-order.yaml": 1500,
    "lesson.md": 4500,
    "video-script.md": 7000,
    "prompts.md": 9000,
    "assignment.md": 3500,
    "quiz.yaml": 150,
    "qa-report.md": 1000,
}
errors = []
warnings = []

for top in ["course-map.md", "glossary.md", "orchestra-assignments.md", "final-bank.yaml"]:
    p = COURSE / top
    if not p.exists() or p.stat().st_size < 500:
        errors.append(f"Нет или слишком мал: course/{top}")

expected_ids = [f"L{i:02d}" for i in range(1, 37)]
actual_ids = sorted(p.name for p in LESSONS.iterdir() if p.is_dir()) if LESSONS.exists() else []
if actual_ids != expected_ids:
    errors.append(f"Набор уроков не совпадает с L01-L36: {actual_ids}")

for lesson_id in expected_ids:
    folder = LESSONS / lesson_id
    for filename in REQUIRED:
        path = folder / filename
        if not path.exists():
            errors.append(f"{lesson_id}: отсутствует {filename}")
            continue
        if path.stat().st_size < MIN_BYTES[filename]:
            errors.append(f"{lesson_id}/{filename}: слишком мал ({path.stat().st_size} байт)")

    lesson = (folder / "lesson.md").read_text(encoding="utf-8") if (folder / "lesson.md").exists() else ""
    if "## Русская версия" not in lesson or "## Қазақша нұсқа" not in lesson:
        errors.append(f"{lesson_id}: lesson.md не содержит обе языковые версии")
    if len(re.findall(r"^\d+\. ", lesson, flags=re.M)) < 12:
        errors.append(f"{lesson_id}: менее 6 шагов на каждый язык в lesson.md")

    video = (folder / "video-script.md").read_text(encoding="utf-8") if (folder / "video-script.md").exists() else ""
    if video.count("| 00:00") != 2:
        errors.append(f"{lesson_id}: видео не содержит два сценария с 00:00")
    counts = [int(x) for x in re.findall(r"^\s{4}words:\s*(\d+)", video, flags=re.M)]
    if len(counts) < 2 or any(x < 260 or x > 380 for x in counts[:2]):
        errors.append(f"{lesson_id}: объём дикторского текста вне 260–380 слов: {counts[:2]}")
    seconds = [int(x) for x in re.findall(r"^\s{4}estimated_seconds:\s*(\d+)", video, flags=re.M)]
    if len(seconds) < 2 or any(x < 120 or x > 180 for x in seconds[:2]):
        errors.append(f"{lesson_id}: расчётная длительность вне 120–180 секунд: {seconds[:2]}")

    prompts = (folder / "prompts.md").read_text(encoding="utf-8") if (folder / "prompts.md").exists() else ""
    prompt_ids = re.findall(r"^### (P-L\d{2}-\d{2})", prompts, flags=re.M)
    if len(set(prompt_ids)) < 12:
        errors.append(f"{lesson_id}: найдено менее 12 двуязычных промптов/ID")
    for slot in ["{{ПРЕДМЕТ}}", "{{КЛАСС}}", "{{ТЕМА}}", "{{ЦЕЛЬ}}", "{{ЯЗЫК}}"]:
        if slot not in prompts:
            warnings.append(f"{lesson_id}: отсутствует слот {slot}")

    assignment = (folder / "assignment.md").read_text(encoding="utf-8") if (folder / "assignment.md").exists() else ""
    if "рубри" not in assignment.lower() and "бағалау" not in assignment.lower():
        errors.append(f"{lesson_id}: не найдена рубрика assignment.md")

bank = (COURSE / "final-bank.yaml").read_text(encoding="utf-8") if (COURSE / "final-bank.yaml").exists() else ""
match = re.search(r"bank_size:\s*(\d+)", bank)
if not match or int(match.group(1)) < 60:
    errors.append("final-bank.yaml: банк меньше 60 вопросов")
for lesson_id in expected_ids:
    if lesson_id not in bank:
        errors.append(f"final-bank.yaml: нет покрытия {lesson_id}")

report = [
    "# Автоматическая проверка / Автоматты тексеру",
    "",
    f"- Уроков / Сабақтар: {len(actual_ids)}/36",
    f"- Обязательных файлов уроков / Міндетті сабақ файлдары: {len(actual_ids) * len(REQUIRED)}/252",
    f"- Ошибок / Қателер: {len(errors)}",
    f"- Предупреждений / Ескертулер: {len(warnings)}",
    "",
]
if errors:
    report += ["## Ошибки / Қателер", ""] + [f"- {e}" for e in errors] + [""]
if warnings:
    report += ["## Предупреждения / Ескертулер", ""] + [f"- {w}" for w in warnings] + [""]
if not errors:
    report += [
        "## Результат / Нәтиже", "",
        "PASS: структура и автоматические ограничения соблюдены.",
        "",
        "Құрылым мен автоматты шектеулер сақталды.",
        "",
        "Перед публикацией всё равно требуется ручная проверка актуального интерфейса и казахской терминологии.",
        "",
        "Жариялау алдында өзекті интерфейс пен қазақша терминологияны қолмен тексеру қажет.",
    ]

(ROOT / "VALIDATION_REPORT.md").write_text("\n".join(report), encoding="utf-8")
print("\n".join(report))
sys.exit(1 if errors else 0)
