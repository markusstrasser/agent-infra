## Results — overall (500 pairs, 250 equivalent / 250 not)

| arm | coverage | FN rate | FP rate | acc(covered) | ms/pair |
|-----|----------|---------|---------|--------------|---------|
| regex | 100.0% | 89.6% | 0.0% | 55.2% | 0.01 |
| sympy | 65.2% | 66.0% | 0.6% | 66.9% | 18.38 |
| symbolica | 49.4% | 55.6% | 2.4% | 70.9% | 0.10 |
| llm(gpt-5.5) | 100.0% | 6.8% | 1.2% | 96.0% | 144.91 |

## Algebraic slice only (expression+numeric, the CAS home turf)

| arm | coverage | FN rate | FP rate | acc(covered) |
|-----|----------|---------|---------|--------------|
| regex | 100.0% | 94.7% | 0.0% | 52.6% |
| sympy | 58.3% | 86.4% | 0.0% | 57.1% |
| symbolica | 35.1% | 80.5% | 2.6% | 57.5% |
| llm(gpt-5.5) | 100.0% | 7.0% | 0.9% | 96.1% |

## sympy vs symbolica by answer-kind (coverage | FN | FP)

| kind | n | sympy cov | sympy FN | sympy FP | symbolica cov | symbolica FN | symbolica FP |
|------|---|-----------|----------|----------|---------------|--------------|--------------|
| equation_or_function | 82 | 75.6% | 41.9% | 3.2% | 61.0% | 28.0% | 8.0% |
| expression | 150 | 56.7% | 81.0% | 0.0% | 25.3% | 65.0% | 5.6% |
| interval | 8 | 25.0% | 100.0% | 0.0% | 0.0% | — | — |
| matrix | 6 | 0.0% | — | — | 16.7% | 0.0% | — |
| numeric | 78 | 61.5% | 95.8% | 0.0% | 53.8% | 95.2% | 0.0% |
| set_or_list | 112 | 74.1% | 56.1% | 0.0% | 66.1% | 50.0% | 0.0% |
| set_or_tuple | 64 | 71.9% | 56.5% | 0.0% | 65.6% | 52.4% | 0.0% |
