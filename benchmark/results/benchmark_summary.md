# IEEE-like synthetic benchmark results

**Limitations:** All three fixtures are generated, not real IEEE publications; formula OCR was not benchmarked. The mock Chinese does not measure translation quality. Each reported score uses only annotated observable tasks.

| Fixture | MD observed-task macro | Header F1 | Reading-order pairs | Table cell recall | Figure recall | Mock overlay SSIM | Coarse layout IoU | Overflow blocks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ieee_crosspage_table.pdf | 1.000 | 1.000 | 1.000 | 1.000 | N/A | 0.977 | 0.962 | 1 |
| ieee_two_column.pdf | 1.000 | 1.000 | 1.000 | N/A | N/A | 0.973 | 0.929 | 1 |
| ieee_vectors_equations.pdf | 1.000 | 1.000 | 1.000 | N/A | 1.000 | 0.968 | 0.940 | 2 |

Do not interpret high macro values as structural correctness on arbitrary real IEEE manuscripts.
