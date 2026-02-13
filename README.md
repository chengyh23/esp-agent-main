# Quick Start

```bash
# Arduino (default)
python create_and_build-arduino.py

# ESP-IDF
python create_and_build-arduino.py --platform ESP-IDF
```

## Batch Evaluation

```bash
# Run all tasks from design_list-arduino.txt
python batch_eval.py

# Run specific tasks
python batch_eval.py --tasks lab1_task1 lab2_task2

# ESP-IDF platform
python batch_eval.py --platform ESP-IDF --input design_list.txt

# Custom output directory
python batch_eval.py --output results/
```
