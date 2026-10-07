# Spreadsheet constraint coverage reconciliation

Audit date: 2026-10-05. Project read directly: `C:\Users\grego\projects\uad-3-6-validation`.

## Findings

- CSV: 731 distinct Message IDs; no duplicate Message IDs.
- Tracking TTL: 728 rule resources.
- Production loader: 521 rows.
- Loaded with collected row-specific tests: 521.
- Loaded without collected row-specific tests: 0.
- Not loaded by the production dispatcher: 210.
- Fixture existence/hash problems found in linked category evidence: 0.

These are implementation and evidence counts, not a claim of exhaustive semantic
correctness.
Dispatch binding identifies executable routing; collected tests identify actual
parametrized cases.
Neither alone proves every possible applicability condition is tested.

## Inventory difference

CSV-only IDs: UAD1438, UAD1443, UAD1625.
TTL-only IDs: none.
All three CSV-only rows are absent from the current production loader and have no
collected row-specific tests.
CSV record numbers below count parsed records starting at 2, not physical lines
(multiline CSV cells span lines), and are not asserted to be original workbook
row numbers.

## Category reconciliation

| Category | CSV rows | Loaded | With collected row tests |
| --- | ---: | ---: | ---: |
| aggregate_cross_record_consistency | 8 | 8 | 8 |
| alternative_mutually_exclusive | 13 | 0 | 0 |
| date_chronology | 14 | 14 | 14 |
| existing_context_required | 22 | 22 | 22 |
| format_precision_length | 22 | 22 | 22 |
| numeric_bounds | 24 | 24 | 24 |
| other_conditional_scoped | 228 | 34 | 34 |
| relationship_reference_integrity | 20 | 20 | 20 |
| required_structures | 98 | 98 | 98 |
| single_equality_conditional | 174 | 174 | 174 |
| unconditional_required | 62 | 62 | 62 |
| uniqueness_cardinality | 26 | 26 | 26 |
| value_cross_field_consistency | 17 | 17 | 17 |

## Evidence and limitations

The validation service calls `evaluate_required_data`; graph-store rule ingestion does not execute an alternate spreadsheet evaluator. Evaluator files and routing were traced from the current dispatcher in order. Original CSV rows were passed to the binding functions; loaded membership was checked against `load_required_rules()`.

Category Turtle manifests/test suites were parsed, associated through explicit ruleId values, and linked fixture existence and declared hashes were checked. The RDF artifact includes each case URI, inventory path, source metadata differences, and actual collected pytest node IDs. Legacy required-data inventories are included as supplementary evidence. UAD1025's embedded ground-lease test is represented by its collected node IDs even though it has no separate saved manifest.

The user confirmed the full acceptance selection: **2418 passed in 1230.02s (20:30)**. This audit did not re-run the full suite or assign independently observed per-row PASS results. Test collection was run without browser tests; only category tests and the two older acceptance suites were selected. Merely mentioning a Message ID in Python code was not treated as behavioral evidence. No fresh XSD validation was performed; existence/hash checks do not replace schema validation.

An absent production route is an implementation gap in the inspected validation path. A loaded row without a collected row-specific case is an evidence gap, not proof the evaluator is incorrect. Tracking status values are historical assertions and were not used to determine current completion.

## Remaining gaps

| CSV record | Message ID | Unique ID | Category | Production evaluator | Collected tests | Gap |
| --- | --- | --- | --- | --- | ---: | --- |
| 26 | UAD1026 | 0100.0030 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 39 | UAD1039 | 0100.0050 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 43 | UAD1043 | 0100.0067 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 55 | UAD1055 | 0300.0023 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 59 | UAD1059 | 0300.0029 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 60 | UAD1060 | 0300.0032 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 64 | UAD1064 | 0300.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 65 | UAD1065 | 0300.0055<br> | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 73 | UAD1073 | 0300.0048 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 74 | UAD1074 | 0300.0049 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 77 | UAD1077 | 0300.0052 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 78 | UAD1078 | 0300.0054 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 83 | UAD1083 | 0300.0060 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 84 | UAD1084 | 0300.0063 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 87 | UAD1087 | 0300.0064 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 88 | UAD1088 | 0300.0074 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 91 | UAD1091 | 0300.0101 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 95 | UAD1095 | 0300.0112 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 96 | UAD1096 | 0300.0113 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 97 | UAD1097 | 0300.0114 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 98 | UAD1098 | 0300.0116 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 99 | UAD1099 | 0300.0117 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 103 | UAD1103 | 0500.0007 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 104 | UAD1104 | 0500.0008 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 105 | UAD1105 | 0500.0009 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 106 | UAD1106 | 0500.0010 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 107 | UAD1107 | 0500.0011 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 108 | UAD1108 | 0500.0013 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 109 | UAD1109 | 0500.0014 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 110 | UAD1110 | 0500.0016 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 112 | UAD1113 | 0500.0020 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 113 | UAD1114 | 0500.0021 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 114 | UAD1115 | 0500.0022 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 115 | UAD1116 | 0500.0023 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 116 | UAD1117 | 0500.0028 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 117 | UAD1118 | 0500.0030 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 118 | UAD1119 | 0500.0031 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 119 | UAD1120 | 0500.0033 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 124 | UAD1125 | 0500.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 125 | UAD1126 | 0500.0044 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 137 | UAD1139 | 0700.0027 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 139 | UAD1141 | 0700.0029 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 143 | UAD1145 | 0700.0033 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 144 | UAD1146 | 0700.0036 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 146 | UAD1148 | 0700.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 147 | UAD1149 | 0700.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 150 | UAD1152 | 0700.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 155 | UAD1157 | 0700.0058 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 156 | UAD1158 | 0700.0060 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 157 | UAD1159 | 0700.0065 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 158 | UAD1160 | 0700.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 159 | UAD1161 | 0700.0067 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 160 | UAD1162 | 0700.0072 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 162 | UAD1164 | 0700.0089 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 167 | UAD1169 | 0700.0104 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 168 | UAD1170 | 0700.0114 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 171 | UAD1173 | 0700.0117 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 172 | UAD1174 | 0700.0118 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 173 | UAD1175 | 0700.0119 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 174 | UAD1176 | 0700.0120 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 175 | UAD1177 | 0700.0121 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 181 | UAD1184 | 0700.0137 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 182 | UAD1185 | 0700.0138 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 183 | UAD1186 | 0700.0140 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 184 | UAD1187 | 0700.0141 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 185 | UAD1188 | 0700.0142 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 186 | UAD1189 | 0700.0143 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 187 | UAD1190 | 0700.0144 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 190 | UAD1193 | 0800.0013 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 218 | UAD1221 | 1000.0119 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 225 | UAD1228 | 1100.0027 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 226 | UAD1229 | 1100.0030 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 228 | UAD1231 | 1100.0033 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 234 | UAD1237 |  | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 236 | UAD1239 | 1100.0065 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 237 | UAD1240 | 1100.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 238 | UAD1241 | 1100.0067 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 248 | UAD1251 | 1200.0034 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 263 | UAD1267 | 1300.0034 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 275 | UAD1282 | 1400.0905 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 292 | UAD1301 | 1500.0022 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 297 | UAD1306 | 1500.0031 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 298 | UAD1307 | 1500.0032 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 300 | UAD1309 | 1500.0036 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 321 | UAD1333 | 1500.0079 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 325 | UAD1337 | 1500.0197 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 327 | UAD1339 | 1500.0091 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 328 | UAD1340 | 1500.0092 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 331 | UAD1343 | 1500.0095 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 354 | UAD1367 | 1500.0122 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 355 | UAD1368 | 1500.0123 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 367 | UAD1382 | 1600.0004 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 368 | UAD1383 | 1600.0005 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 372 | UAD1387 | 1600.0008 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 378 | UAD1394 | 1800.0063 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 379 | UAD1395 | 1800.0064 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 381 | UAD1397 | 1800.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 383 | UAD1399 | 1800.0069 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 385 | UAD1401 | 1800.0071 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 390 | UAD1407 | 1800.0096 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 391 | UAD1408 | 1800.0094 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 392 | UAD1409 | 1800.0097 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 393 | UAD1410 | 1800.0098 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 394 | UAD1411 | 1800.0099 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 395 | UAD1412 | 1800.0100 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 396 | UAD1414 | 1800.0103 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 398 | UAD1416 | 1800.0128 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 400 | UAD1419 | 1800.0157 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 401 | UAD1420 | 1800.0158 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 403 | UAD1422 | 1800.0166 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 404 | UAD1423 | 1800.0169 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 405 | UAD1424 | 1800.0170 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 406 | UAD1425 | 1800.0184 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 407 | UAD1426 | 1800.0185 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 408 | UAD1427 | 1800.0186 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 418 | UAD1438 | 1800.0273 | not tracked | none in current dispatcher | 0 | not_loaded |
| 419 | UAD1439 | 1800.0208; 1800.0272 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 420 | UAD1440 | 1800.0206 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 422 | UAD1443 | 1800.0210 | not tracked | none in current dispatcher | 0 | not_loaded |
| 423 | UAD1444 | 1800.0211 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 425 | UAD1446 | 1800.0213 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 426 | UAD1447 | 1800.0215 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 427 | UAD1448 | 1800.0221 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 428 | UAD1449 | 1800.0239 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 430 | UAD1451 | 1800.0244 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 432 | UAD1453 | 1800.0287 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 435 | UAD1457 | 1800.0310 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 436 | UAD1458 | 1800.0311 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 440 | UAD1462 | 1800.0322 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 441 | UAD1463 | 1800.0330 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 442 | UAD1464 | 1800.0331 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 443 | UAD1465 | 1800.0332 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 444 | UAD1467 | 1800.0345 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 445 | UAD1468 | 1800.0347 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 446 | UAD1469 | 1800.0359 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 453 | UAD1476 | 1800.0367 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 455 | UAD1478 | 1800.0377 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 458 | UAD1481 | 1800.0385 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 459 | UAD1482 | 1800.0390 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 460 | UAD1483 | 1800.0393 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 461 | UAD1484 | 1800.0398 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 464 | UAD1487 | 2000.0021 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 465 | UAD1488 | 2000.0032 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 466 | UAD1489 | 2000.0035 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 467 | UAD1490 | 2000.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 468 | UAD1491 | 2000.0050 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 469 | UAD1492 | 2000.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 473 | UAD1496 | 2000.0088 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 474 | UAD1497 | 2000.0089 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 475 | UAD1498 | 2000.0092 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 476 | UAD1499 | 2000.0101 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 477 | UAD1500 | 2000.0102 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 478 | UAD1501 | 2000.0103 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 496 | UAD1521 | 1000.0132 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 497 | UAD1522 | 1000.0133 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 499 | UAD1524 | 2200.0075 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 500 | UAD1525 | 2200.0076 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 501 | UAD1526 | 2200.0080 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 503 | UAD1528 | 2200.0082 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 506 | UAD1531 | 2200.0083 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 507 | UAD1532 | 2200.0084 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 512 | UAD1537 | 2400.0001 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 513 | UAD1538 | 2400.0002 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 514 | UAD1539 | 2400.0003 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 515 | UAD1540 | 2400.0004 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 516 | UAD1541 | 2400.0013 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 519 | UAD1544 | 2400.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 520 | UAD1545 | 2400.0042 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 521 | UAD1546 | 2400.0051 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 522 | UAD1548 | 2400.0053 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 523 | UAD1551 | 2400.0054 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 524 | UAD1552 | 2400.0055 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 531 | UAD1560 | 2400.0295 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 547 | UAD1580 | 2500.0023 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 548 | UAD1581 | 2500.0024 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 555 | UAD1588 | 2500.0044 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 556 | UAD1589 | 2500.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 558 | UAD1591 | 2500.0049 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 560 | UAD1593 | 2500.0051 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 562 | UAD1595 | 2500.0057 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 568 | UAD1601 | 2500.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 569 | UAD1602 | 2500.0067 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 573 | UAD1606 | 2500.0074 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 574 | UAD1607 | 2500.0075 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 575 | UAD1608 | 2500.0076 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 577 | UAD1610 | 2500.0081 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 591 | UAD1625 | 1300.0010 | not tracked | none in current dispatcher | 0 | not_loaded |
| 618 | UAD1656 | 1400.0638 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 619 | UAD1657 | 3000.0051 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 635 | UAD1675 | 3200.0021 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 646 | UAD1688 | 3900.0107 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 653 | UAD1695 | 0300.0039 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 654 | UAD1696 | 0300.0039 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 655 | UAD1698 | 0800.0012 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 656 | UAD1699 | 1000.0019 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 657 | UAD1700 | 1000.0023 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 658 | UAD1701 | 1000.0102 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 670 | UAD1715 |  | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 675 | UAD1720 |  | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 684 | UAD1731 | 1800.0202 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 686 | UAD1733 | 1300.0013 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 699 | UAD1746 | 1300.0013 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 724 | UAD1771 | 1800.0274 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 725 | UAD1772 | 1800.0154 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 726 | UAD1773 | 1800.0337 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 728 | UAD1775 | 1800.0379 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 729 | UAD1776 | 1800.0394 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 730 | UAD1777 | 1800.0399 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 731 | UAD1778 | 1800.0392 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 732 | UAD1779 | 1800.0391 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |

## Source metadata differences

There are 23 rows with 27 differing fields. These require source-governance review. No source was rewritten. The table displays line endings as line breaks; coverage.ttl preserves exact literals, including CRLF versus LF.

| Message ID | Field | CSV value | Tracking TTL value |
| --- | --- | --- | --- |
| UAD1084 | Rule Logic | If ImprovementType = "Dwelling" or <br>(ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true"), and LivingUnitCount is not provided in a given instance of STRUCTURE_DETAIL | If ImprovementType = "Dwelling" or<br>(ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true"), and LivingUnitCount is not provided in a given instance of STRUCTURE_DETAIL |
| UAD1121 | Rule Logic | If ((ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured" and ManufacturedHomeModificationIndicator = "true") <br>or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome" and OutbuildingRealPropertyIndicator = "true" and LivingUnitCount > 0 and ManufacturedHomeModificationIndicator = "true")) and (at least one instance of MANUFACTURED_HOME_MODIFICATION is not provided or ManufacturedHomeModificationType is not provided in a given instance of MANUFACTURED_HOME_MODIFICATION) | If ((ImprovementType = "Dwelling" and ConstructionMethodType = "Manufactured" and ManufacturedHomeModificationIndicator = "true")<br>or (ImprovementType = "Outbuilding" and OutbuildingType = "ManufacturedHome" and OutbuildingRealPropertyIndicator = "true" and LivingUnitCount > 0 and ManufacturedHomeModificationIndicator = "true")) and (at least one instance of MANUFACTURED_HOME_MODIFICATION is not provided or ManufacturedHomeModificationType is not provided in a given instance of MANUFACTURED_HOME_MODIFICATION) |
| UAD1138 | Rule Logic | If ((ImprovementType = "Dwelling" ) or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and<br>If (at least one instance of ACCESSIBILITY_FEATURE is not provided or AccessibilityFeatureType is not provided in a given instance of ACCESSIBILITY_FEATURE) | If ((ImprovementType = "Dwelling" ) or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and<br>If (at least one instance of ACCESSIBILITY_FEATURE is not provided or AccessibilityFeatureType is not provided in a given instance of ACCESSIBILITY_FEATURE) |
| UAD1143 | Rule Logic | If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and (at least one instance of ROOM_DETAIL with RoomType = "Kitchen" is not provided)<br> | If (ImprovementType = "Dwelling" or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and (at least one instance of ROOM_DETAIL with RoomType = "Kitchen" is not provided)<br> |
| UAD1160 | Rule Logic | If (ImprovementType = "Dwelling") <br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and InteriorConditionRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL | If (ImprovementType = "Dwelling")<br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and InteriorConditionRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL |
| UAD1161 | Rule Logic | If (ImprovementType = "Dwelling") <br>OR (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and InteriorQualityRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL | If (ImprovementType = "Dwelling")<br>OR (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true"), and InteriorQualityRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL |
| UAD1183 | Rule Logic | If there is no instance of RELATIONSHIP with @xlink:arcrole = "urn:fdc:mismo.org:2009:residential/DATA_SOURCE_IsDataSourceFor_PROPERTY_UNIT_AREA" that links DATA_SOURCE to each PROPERTY_UNIT_AREA where @ValuationUseType = "SubjectProperty" <br><br> | If there is no instance of RELATIONSHIP with @xlink:arcrole = "urn:fdc:mismo.org:2009:residential/DATA_SOURCE_IsDataSourceFor_PROPERTY_UNIT_AREA" that links DATA_SOURCE to each PROPERTY_UNIT_AREA where @ValuationUseType = "SubjectProperty"<br><br> |
| UAD1229 | Rule Logic | If CostApproachIndicator = "true", or <br>(CostApproachIndicator = "false" and SiteValueIndicator = "true") and SiteEstimatedValueAmount is not provided | If CostApproachIndicator = "true", or<br>(CostApproachIndicator = "false" and SiteValueIndicator = "true") and SiteEstimatedValueAmount is not provided |
| UAD1231 | Rule Logic | If CostApproachIndicator = "true", or <br>(CostApproachIndicator = "false" and SiteValueIndicator = "true") and SiteValuationMethodType is not provided | If CostApproachIndicator = "true", or<br>(CostApproachIndicator = "false" and SiteValueIndicator = "true") and SiteValuationMethodType is not provided |
| UAD1239 | Severity | Fatal | Warning |
| UAD1279 | Rule Logic | If there is no instance of IMAGE in a given instance of ROOM with RoomType = "Kitchen" or "HalfBathroom" or "FullBathroom" | If PropertyValuationMethodType <> "ExteriorAppraisal" and (NewConstructionIndicator <> "true" or PropertyValuationConditionalConclusionType <> "SubjectToCompletionPerPlans") and there is no instance of IMAGE in a given instance of ROOM with RoomType = ("Kitchen" or "HalfBathroom" or "FullBathroom") |
| UAD1419 | Rule Logic | If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" <br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and InteriorConditionRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL | If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling"<br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and InteriorConditionRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL |
| UAD1420 | Rule Logic | If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling" <br>OR (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and InteriorQualityRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL | If @ValuationUseType = "SalesComparable" and (ImprovementType = "Dwelling"<br>OR (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")), and InteriorQualityRatingCode is not provided in a given instance of PROPERTY_UNIT_DETAIL |
| UAD1455 | Rule Logic | For each combination of ComparableAdjustmentType = ("SalesComparableAdditionalAdjustableComparisonItem" or "SalesComparableAdditionalNonAdjustableComparisonItem") and AdditionalComparisonLineItemIdentifier, if there are not matching occurrences of COMPARABLE_ADJUSTMENT across all instances of PROPERTY with @ValuationUseType = "SalesComparable", and the instance of PROPERTY with @ValuationUseType = "SubjectProperty". Example: In Appendix D-1: Sample Scenario SF1, an additional row was added with the Report Label "Basement Access". AdditionalComparisonLineItemIdentifier = "Basement Access" must be provided for the Subject and all Comps along with the associated data points. | For each combination of ComparableAdjustmentType = ("SalesComparableAdditionalAdjustableComparisonItem" or "SalesComparableAdditionalNonAdjustableComparisonItem") and AdditionalComparisonLineItemIdentifier, if there are not matching occurrences of COMPARABLE_ADJUSTMENT across all instances of PROPERTY with @ValuationUseType = "SalesComparable", and the instance of PROPERTY with @ValuationUseType = "SubjectProperty". Example: In Appendix D-1: Sample Scenario SF1, an additional row was added with the Report Label "Below Grade Exterior Access". AdditionalComparisonLineItemIdentifier = "Below Grade Exterior Access" must be provided for the Subject and all Comps along with the associated data points. |
| UAD1470 | Rule Logic | If (@ValuationUseType = "SubjectProperty" and (LivingUnitExcludingADUCount > 1 or AccessoryDwellingUnitTotalCount > 0)) and<br>(@ValuationUseType = "SalesComparable" and (LivingUnitExcludingADUCount > 1 or AccessoryDwellingUnitTotalCount > 0)), and there is not an instance of RELATIONSHIP with @xlink:arcrole = urn:fdc:mismo.org:2009:residential/PROPERTY_UNIT_IsComparableFor_PROPERTY_UNIT | If (@ValuationUseType = "SubjectProperty" and (LivingUnitExcludingADUCount > 1 or AccessoryDwellingUnitTotalCount > 0)) and<br>(@ValuationUseType = "SalesComparable" and (LivingUnitExcludingADUCount > 1 or AccessoryDwellingUnitTotalCount > 0)), and there is not an instance of RELATIONSHIP with @xlink:arcrole = urn:fdc:mismo.org:2009:residential/PROPERTY_UNIT_IsComparableFor_PROPERTY_UNIT |
| UAD1502 | Message Text | Provide the UAD Delivery Specification version. For assistance with this message, contact the appraisal software vendor.<br> | Provide the UAD Delivery Specification version. For assistance with this message, contact the appraisal software vendor.<br> |
| UAD1535 | Message Text | Provide the 'Date of Signature and Report'.<br>The 'Date of Signature and Report' must be provided for the Appraiser and the Supervisory Appraiser (if applicable), with only one instance allowed per party. | The 'Date of Signature and Report' must be provided for the Appraiser and the Supervisory Appraiser (if applicable), with only one instance allowed per party. |
| UAD1637 | Message Text | The market inventory type qualifier of 'ActiveListings' must be provided only once. For assistance with this message, contact the appraisal software vendor.<br> | The market inventory type qualifier of 'ActiveListings' must be provided only once. For assistance with this message, contact the appraisal software vendor.<br> |
| UAD1689 | Rule Logic | If @ValuationUseType = "SubjectProperty" and DwellingExteriorDefectsExistIndicator = "true", and there is no instance of RELATIONSHIP with @xlink:arcrole = "urn:fdc:mismo.org:2009:residential/DEFECT_ContainsDefectOf_IMPROVEMENT" that links DEFECT to the given instance of IMPROVEMENT with ImprovementType = 'Dwelling'<br> | If @ValuationUseType = "SubjectProperty" and DwellingExteriorDefectsExistIndicator = "true", and there is no instance of RELATIONSHIP with @xlink:arcrole = "urn:fdc:mismo.org:2009:residential/DEFECT_ContainsDefectOf_IMPROVEMENT" that links DEFECT to the given instance of IMPROVEMENT with ImprovementType = 'Dwelling'<br> |
| UAD1693 | Rule Logic | If AccessoryDwellingUnitTotalCount plus<br>LivingUnitExcludingADUCount does not equal the sum of LivingUnitCount across all instances of STRUCTURE_DETAIL | If AccessoryDwellingUnitTotalCount plus<br>LivingUnitExcludingADUCount does not equal the sum of LivingUnitCount across all instances of STRUCTURE_DETAIL |
| UAD1693 |  xPath | ../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/IMPROVEMENTS/IMPROVEMENT/STRUCTURE/STRUCTURE_DETAIL/<br><br> | ../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/IMPROVEMENTS/IMPROVEMENT/STRUCTURE/STRUCTURE_DETAIL/<br><br> |
| UAD1777 | Rule Logic | If @ValuationUseType = "SalesComparable" and ((ImprovementType = "Dwelling" and UnitNonStandardBelowGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") <br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true" and UnitNonStandardBelowGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty")), and UnitNonStandardBelowGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA  | If (@ValuationUseType  = "SalesComparable" or @ValuationUseType = "SubjectProperty") and (ImprovementType = "Dwelling" or  (ImprovementType = "Outbuilding" and  OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and  ((UnitNonStandardBelowGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") and UnitNonStandardBelowGradeFinishedAreaMeasure is not provided in the comparable instance of PROPERTY_UNIT_AREA that was compared with the subject unit) |
| UAD1777 | Severity | Fatal | Warning |
| UAD1778 | Rule Logic | IF @ValuationUseType = "SalesComparable" and ((ImprovementType = "Dwelling" and UnitAboveGradeUnfinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") <br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true" and UnitAboveGradeUnfinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty")), and UnitAboveGradeUnfinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA | If (@ValuationUseType  = "SalesComparable" or @ValuationUseType = "SubjectProperty") and (ImprovementType = "Dwelling" or  (ImprovementType = "Outbuilding" and  OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and  ((UnitAboveGradeUnfinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") and UnitAboveGradeUnfinishedAreaMeasure is not provided in the comparable instance of PROPERTY_UNIT_AREA that was compared with the subject unit) |
| UAD1778 | Severity | Fatal | Warning |
| UAD1779 | Rule Logic | IF @ValuationUseType = "SalesComparable" and ((ImprovementType = "Dwelling" and UnitNonStandardAboveGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") <br>or (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true" and UnitNonStandardAboveGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty")), and UnitNonStandardAboveGradeFinishedAreaMeasure is not provided in a given instance of PROPERTY_UNIT_AREA | If (@ValuationUseType  = "SalesComparable" or @ValuationUseType = "SubjectProperty") and (ImprovementType = "Dwelling" or  (ImprovementType = "Outbuilding" and OutbuildingRealPropertyIndicator = "true" and AccessoryDwellingUnitIndicator = "true")) and  ((UnitNonStandardAboveGradeFinishedAreaMeasure > 0 for @ValuationUseType = "SubjectProperty") and UnitNonStandardAboveGradeFinishedAreaMeasure is not provided in the comparable instance of PROPERTY_UNIT_AREA that was compared with the subject unit) |
| UAD1779 | Severity | Fatal | Warning |

## Complete row-by-row coverage

| CSV record | Message ID | Unique ID | Category | Production evaluator | Collected tests | Gap |
| --- | --- | --- | --- | --- | ---: | --- |
| 2 | UAD1001 | 0100.0007 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 3 | UAD1002 | 0100.0009 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 4 | UAD1003 | 0100.0010 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 5 | UAD1004 | 0100.0011 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 6 | UAD1005 | 0100.0011 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 7 | UAD1006 | 0100.0012 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 8 | UAD1007 | 0100.0012 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 9 | UAD1008 | 0100.0015 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 10 | UAD1009 | 0100.0016 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 11 | UAD1010 | 0100.0019 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 12 | UAD1011 | 0100.0019 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 3 | loaded_with_collected_tests |
| 13 | UAD1012 | 0100.0020 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 14 | UAD1013 | 0100.0021 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 15 | UAD1014 | 0100.0021 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 16 | UAD1015 | 0100.0021 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 17 | UAD1016 | 0100.0021 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 5 | loaded_with_collected_tests |
| 18 | UAD1017 | 0100.0022 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 19 | UAD1018 | 0100.0022 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 20 | UAD1019 | 0100.0022 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 3 | loaded_with_collected_tests |
| 21 | UAD1021 | 0100.0024 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 22 | UAD1022 | 0100.0053 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 12 | loaded_with_collected_tests |
| 23 | UAD1023 | 0100.0026 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 24 | UAD1024 | 0100.0028 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 5 | loaded_with_collected_tests |
| 25 | UAD1025 | 0100.0029 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 5 | loaded_with_collected_tests |
| 26 | UAD1026 | 0100.0030 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 27 | UAD1027 | 0100.0033 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 28 | UAD1028 | 0100.0034 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 29 | UAD1029 | 0100.0035 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 30 | UAD1030 | 0100.0036 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 31 | UAD1031 | 0100.0037 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 32 | UAD1032 | 0100.0043 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 33 | UAD1033 | 0100.0043 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 34 | UAD1034 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 35 | UAD1035 | 0100.0046 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 36 | UAD1036 | 0100.0047 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 37 | UAD1037 |  | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 38 | UAD1038 | 0100.0049 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 39 | UAD1039 | 0100.0050 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 40 | UAD1040 | 0100.0054 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 41 | UAD1041 | 0100.0059 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 42 | UAD1042 | 0100.0065 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 43 | UAD1043 | 0100.0067 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 44 | UAD1044 | 0100.0068 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 45 | UAD1045 | 0200.0015 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 46 | UAD1046 | 0200.0053 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 47 | UAD1047 | 0300.0009 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 48 | UAD1048 | 0300.0009 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 49 | UAD1049 | 0300.0010 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 50 | UAD1050 | 0300.0011 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 51 | UAD1051 | 0300.0010 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 5 | loaded_with_collected_tests |
| 52 | UAD1052 | 0300.0011 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 53 | UAD1053 | 0300.0011 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 3 | loaded_with_collected_tests |
| 54 | UAD1054 | 0300.0012 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 5 | loaded_with_collected_tests |
| 55 | UAD1055 | 0300.0023 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 56 | UAD1056 | 0300.0025 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 57 | UAD1057 | 0300.0026 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 58 | UAD1058 | 0300.0028 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 59 | UAD1059 | 0300.0029 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 60 | UAD1060 | 0300.0032 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 61 | UAD1061 | 0300.0033 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 62 | UAD1062 | 0300.0034 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 63 | UAD1063 | 0300.0035 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 64 | UAD1064 | 0300.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 65 | UAD1065 | 0300.0055<br> | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 66 | UAD1066 | 0300.0056 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 67 | UAD1067 | 0300.0055 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 68 | UAD1068 | 0300.0044 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 69 | UAD1069 | 0300.0045 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 70 | UAD1070 | 0300.0046 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 71 | UAD1071 | 0300.0047 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 72 | UAD1072 | 0300.0055 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 73 | UAD1073 | 0300.0048 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 74 | UAD1074 | 0300.0049 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 75 | UAD1075 | 0300.0050 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 76 | UAD1076 | 0300.0051 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 77 | UAD1077 | 0300.0052 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 78 | UAD1078 | 0300.0054 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 79 | UAD1079 | 0300.0055 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 80 | UAD1080 | 0300.0098 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 81 | UAD1081 | 0300.0099 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 82 | UAD1082 | 0300.0059 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 83 | UAD1083 | 0300.0060 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 84 | UAD1084 | 0300.0063 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 85 | UAD1085 | 0300.0063 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 86 | UAD1086 | 0300.0063 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 3 | loaded_with_collected_tests |
| 87 | UAD1087 | 0300.0064 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 88 | UAD1088 | 0300.0074 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 89 | UAD1089 | 0300.0088 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 90 | UAD1090 | 0300.0089 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 91 | UAD1091 | 0300.0101 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 92 | UAD1092 | 0300.0101 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 93 | UAD1093 | 0300.0065 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 94 | UAD1094 | 0300.0111 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 10 | loaded_with_collected_tests |
| 95 | UAD1095 | 0300.0112 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 96 | UAD1096 | 0300.0113 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 97 | UAD1097 | 0300.0114 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 98 | UAD1098 | 0300.0116 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 99 | UAD1099 | 0300.0117 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 100 | UAD1100 | 0500.0005 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 101 | UAD1101 | 0500.0004 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 11 | loaded_with_collected_tests |
| 102 | UAD1102 | 0500.0006 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 103 | UAD1103 | 0500.0007 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 104 | UAD1104 | 0500.0008 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 105 | UAD1105 | 0500.0009 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 106 | UAD1106 | 0500.0010 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 107 | UAD1107 | 0500.0011 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 108 | UAD1108 | 0500.0013 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 109 | UAD1109 | 0500.0014 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 110 | UAD1110 | 0500.0016 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 111 | UAD1111 | 0500.0016 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 112 | UAD1113 | 0500.0020 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 113 | UAD1114 | 0500.0021 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 114 | UAD1115 | 0500.0022 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 115 | UAD1116 | 0500.0023 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 116 | UAD1117 | 0500.0028 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 117 | UAD1118 | 0500.0030 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 118 | UAD1119 | 0500.0031 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 119 | UAD1120 | 0500.0033 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 120 | UAD1121 | 0500.0035 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 121 | UAD1122 | 0500.0036 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 122 | UAD1123 | 0500.0039 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 123 | UAD1124 | 0500.0040 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 124 | UAD1125 | 0500.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 125 | UAD1126 | 0500.0044 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 126 | UAD1127 | 0600.0005 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 127 | UAD1128 | 0600.0006 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 9 | loaded_with_collected_tests |
| 128 | UAD1129 | 0600.0008 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 12 | loaded_with_collected_tests |
| 129 | UAD1130 | 0600.0009 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 9 | loaded_with_collected_tests |
| 130 | UAD1131 | 0600.0009 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 2 | loaded_with_collected_tests |
| 131 | UAD1132 | 0600.0010 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 132 | UAD1133 | 0600.0011 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 133 | UAD1134 | 0600.0016 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 134 | UAD1135 | 0600.0017 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 9 | loaded_with_collected_tests |
| 135 | UAD1136 | 0600.0018 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 136 | UAD1138 | 0700.0005 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 137 | UAD1139 | 0700.0027 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 138 | UAD1140 | 0700.0028 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 139 | UAD1141 | 0700.0029 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 140 | UAD1142 | 0700.0030 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 141 | UAD1143 | 0700.0035 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 142 | UAD1144 | 0700.0087 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 143 | UAD1145 | 0700.0033 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 144 | UAD1146 | 0700.0036 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 145 | UAD1147 | 0700.0034 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 20 | loaded_with_collected_tests |
| 146 | UAD1148 | 0700.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 147 | UAD1149 | 0700.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 148 | UAD1150 | 0700.0041 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 149 | UAD1151 | 0700.0042 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 150 | UAD1152 | 0700.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 151 | UAD1153 | 0700.0047 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 152 | UAD1154 | 0700.0050 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 153 | UAD1155 | 0700.0043 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 154 | UAD1156 | 0700.0045 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 9 | loaded_with_collected_tests |
| 155 | UAD1157 | 0700.0058 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 156 | UAD1158 | 0700.0060 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 157 | UAD1159 | 0700.0065 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 158 | UAD1160 | 0700.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 159 | UAD1161 | 0700.0067 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 160 | UAD1162 | 0700.0072 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 161 | UAD1163 | 0700.0088 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 162 | UAD1164 | 0700.0089 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 163 | UAD1165 | 0700.0090 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 164 | UAD1166 | 0700.0091 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 165 | UAD1167 | 0700.0098 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 166 | UAD1168 | 0700.0100 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 167 | UAD1169 | 0700.0104 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 168 | UAD1170 | 0700.0114 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 169 | UAD1171 | 0700.0114 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 170 | UAD1172 | 1800.0159 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 171 | UAD1173 | 0700.0117 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 172 | UAD1174 | 0700.0118 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 173 | UAD1175 | 0700.0119 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 174 | UAD1176 | 0700.0120 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 175 | UAD1177 | 0700.0121 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 176 | UAD1178 | 0700.0122 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 177 | UAD1179 | 0700.0125 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 178 | UAD1181 | 0700.0126 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 179 | UAD1182 | 0700.0130 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 180 | UAD1183 | 0700.0131 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 181 | UAD1184 | 0700.0137 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 182 | UAD1185 | 0700.0138 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 183 | UAD1186 | 0700.0140 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 184 | UAD1187 | 0700.0141 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 185 | UAD1188 | 0700.0142 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 186 | UAD1189 | 0700.0143 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 187 | UAD1190 | 0700.0144 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 188 | UAD1191 | 0800.0005 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 189 | UAD1192 | 0800.0018 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 190 | UAD1193 | 0800.0013 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 191 | UAD1194 | 0800.0014 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 192 | UAD1195 | 0800.0011 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 193 | UAD1196 | 0800.0011 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 194 | UAD1197 | 0800.0012 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 195 | UAD1198 | 0800.0010 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 196 | UAD1199 | 0800.0031 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 197 | UAD1200 | 0800.0034 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 198 | UAD1201 | 0800.0039 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 199 | UAD1202 | 0800.0042 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 200 | UAD1203 | 0900.0004 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 201 | UAD1204 | 0900.0007 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 202 | UAD1205 | 0900.0008 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 203 | UAD1206 | 0900.0012 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 2 | loaded_with_collected_tests |
| 204 | UAD1207 | 0900.0013 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 205 | UAD1208 | 0900.0016 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 206 | UAD1209 | 0900.0033 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 207 | UAD1210 | 1000.0027 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 208 | UAD1211 | 1000.0028 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 209 | UAD1212 | 1000.0029 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 210 | UAD1213 | 1000.0030 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 211 | UAD1214 | 1000.0030 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 212 | UAD1215 | 1000.0031 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 213 | UAD1216 | 1000.0031 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 214 | UAD1217 | 1000.0031 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 215 | UAD1218 | 1000.0032 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 216 | UAD1219 | 1000.0034 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 217 | UAD1220 | 1000.0035 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 218 | UAD1221 | 1000.0119 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 219 | UAD1222 | 1000.0158 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 220 | UAD1223 | 1000.0198 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 221 | UAD1224 | 1000.0197 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 222 | UAD1225 | 1100.0015 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 223 | UAD1226 | 1100.0015 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 224 | UAD1227 | 1100.0026 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 225 | UAD1228 | 1100.0027 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 226 | UAD1229 | 1100.0030 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 227 | UAD1230 | 1100.0032 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 228 | UAD1231 | 1100.0033 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 229 | UAD1232 | 1100.0034 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 230 | UAD1233 |  | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 231 | UAD1234 |  | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 232 | UAD1235 |  | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 233 | UAD1236 |  | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 234 | UAD1237 |  | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 235 | UAD1238 | 1100.0033 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 236 | UAD1239 | 1100.0065 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 237 | UAD1240 | 1100.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 238 | UAD1241 | 1100.0067 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 239 | UAD1242 | 1200.0003 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 240 | UAD1243 | 1200.0004 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 241 | UAD1244 | 1200.0015 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 242 | UAD1245 | 1200.0016 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 243 | UAD1246 | 1200.0028 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 244 | UAD1247 | 1200.0028 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 245 | UAD1248 | 1200.0029 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 246 | UAD1249 | 1200.0030 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 247 | UAD1250 | 1200.0032 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 7 | loaded_with_collected_tests |
| 248 | UAD1251 | 1200.0034 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 249 | UAD1252 | 1300.0001 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 250 | UAD1253 | 1300.0006 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 251 | UAD1255 | 1300.0010 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 252 | UAD1256 | 1300.0010 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 253 | UAD1257 | 1300.0012 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 254 | UAD1258 | 1300.0012 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 255 | UAD1259 | 1300.0012 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 256 | UAD1260 | 1300.0012 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 257 | UAD1261 | 1300.0016 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 258 | UAD1262 | 1300.0017 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 259 | UAD1263 | 1300.0017 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 260 | UAD1264 | 1300.0017 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 261 | UAD1265 | 1300.0019 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 262 | UAD1266 | 1300.0021 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 263 | UAD1267 | 1300.0034 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 264 | UAD1268 |  | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 265 | UAD1270 | 1400.0383 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 266 | UAD1272 | 1400.0384 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 267 | UAD1273 | 1400.0408 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 268 | UAD1274 | 1400.0619 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 269 | UAD1275 | 1400.0628 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 270 | UAD1276 | 1400.0634 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 271 | UAD1278 | 1400.1013 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 272 | UAD1279 |  | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 273 | UAD1280 | 1400.0870 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 274 | UAD1281 | 1400.0876 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 275 | UAD1282 | 1400.0905 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 276 | UAD1283 | 1400.0915 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 277 | UAD1284 | 1400.0967 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 278 | UAD1285 | 1400.0975 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 279 | UAD1287 | 1500.0002 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 280 | UAD1288 | 1500.0003 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 281 | UAD1289 | 1500.0004 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 282 | UAD1290 | 1500.0005 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 283 | UAD1291 | 1500.0008 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 284 | UAD1292 | 1500.0009 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 285 | UAD1293 | 1500.0010 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 286 | UAD1294 | 1500.0015 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 287 | UAD1296 | 1500.0016 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 288 | UAD1297 | 1500.0017 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 289 | UAD1298 | 1500.0018 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 290 | UAD1299 | 1500.0020 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 291 | UAD1300 | 1500.0021 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 292 | UAD1301 | 1500.0022 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 293 | UAD1302 | 1500.0023 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 294 | UAD1303 | 1500.0024 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 295 | UAD1304 | 1500.0026 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 296 | UAD1305 | 1500.0027 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 297 | UAD1306 | 1500.0031 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 298 | UAD1307 | 1500.0032 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 299 | UAD1308 | 1500.0034 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 300 | UAD1309 | 1500.0036 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 301 | UAD1310 | 1500.0039 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 302 | UAD1311 | 1500.0040 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 303 | UAD1313 | 1500.0042 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 304 | UAD1314 | 1500.0043 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 305 | UAD1315 | 1500.0045 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 306 | UAD1316 | 1500.0052 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 307 | UAD1317 | 1500.0054 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 308 | UAD1318 | 1500.0055 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 309 | UAD1319 | 1500.0056 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 310 | UAD1320 | 1500.0060 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 311 | UAD1321 | 1500.0061 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 312 | UAD1323 | 1500.0062 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 313 | UAD1324 | 1500.0063 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 314 | UAD1325 | 1500.0065 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 315 | UAD1326 | 1500.0066 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 316 | UAD1328 | 1500.0087 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 317 | UAD1329 | 1500.0088 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 318 | UAD1330 | 1500.0086 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 319 | UAD1331 | 1500.0073 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 320 | UAD1332 | 1500.0074 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 321 | UAD1333 | 1500.0079 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 322 | UAD1334 | 1500.0080 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 323 | UAD1335 | 1500.0082 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 324 | UAD1336 | 1500.0083 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 325 | UAD1337 | 1500.0197 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 326 | UAD1338 | 1500.0198 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 327 | UAD1339 | 1500.0091 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 328 | UAD1340 | 1500.0092 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 329 | UAD1341 | 1500.0093 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 330 | UAD1342 | 1500.0094 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 331 | UAD1343 | 1500.0095 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 332 | UAD1344 | 1500.0104 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 333 | UAD1345 | 1500.0104 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 334 | UAD1346 | 1500.0104 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 335 | UAD1347 | 1500.0104 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 336 | UAD1348 | 1500.0105 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 337 | UAD1349 | 1500.0102 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 338 | UAD1350 | 1500.0103 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 339 | UAD1351 | 1500.0183 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 340 | UAD1352 | 1500.0106 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 341 | UAD1353 | 1500.0106 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 342 | UAD1354 | 1500.0107 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 343 | UAD1355 | 1500.0108 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 344 | UAD1356 | 1500.0109 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 345 | UAD1357 | 1500.0111 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 346 | UAD1358 | 1500.0112 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 347 | UAD1359 | 1500.0114 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 348 | UAD1361 | 1500.0120 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 349 | UAD1362 | 1500.0121 | single_equality_conditional | app/services/scoped_required_data.py :: evaluate_scoped_rule | 3 | loaded_with_collected_tests |
| 350 | UAD1363 | 1500.0117 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 351 | UAD1364 | 1500.0118 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 352 | UAD1365 | 1500.0119 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 353 | UAD1366 | 1500.0184 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 354 | UAD1367 | 1500.0122 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 355 | UAD1368 | 1500.0123 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 356 | UAD1369 | 1500.0125 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 357 | UAD1370 | 1500.0128 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 358 | UAD1371 | 1500.0129 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 359 | UAD1372 | 1500.0166 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 360 | UAD1373 | 1500.0178 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 361 | UAD1374 | 1500.0185 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 362 | UAD1375 | 1500.0187 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 363 | UAD1377 | 1500.0191 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 364 | UAD1378 | 1500.0193 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 365 | UAD1380 | 1500.0199 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 366 | UAD1381 | 1500.0200 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 367 | UAD1382 | 1600.0004 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 368 | UAD1383 | 1600.0005 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 369 | UAD1384 | 1600.0006 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 370 | UAD1385 | 1600.0007 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 371 | UAD1386 | 1600.0009 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 372 | UAD1387 | 1600.0008 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 373 | UAD1388 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 374 | UAD1390 | 1800.0001 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 375 | UAD1391 | 1800.0003 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 376 | UAD1392 | 1800.0004 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 377 | UAD1393 | 1800.0005 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 378 | UAD1394 | 1800.0063 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 379 | UAD1395 | 1800.0064 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 380 | UAD1396 | 1800.0065 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 381 | UAD1397 | 1800.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 382 | UAD1398 | 1800.0068 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 383 | UAD1399 | 1800.0069 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 384 | UAD1400 | 1800.0070 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 385 | UAD1401 | 1800.0071 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 386 | UAD1402 | 1800.0075 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 387 | UAD1403 | 1800.0075 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 388 | UAD1404 | 1000.0032 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 389 | UAD1405 | 1800.0095 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 390 | UAD1407 | 1800.0096 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 391 | UAD1408 | 1800.0094 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 392 | UAD1409 | 1800.0097 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 393 | UAD1410 | 1800.0098 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 394 | UAD1411 | 1800.0099 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 395 | UAD1412 | 1800.0100 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 396 | UAD1414 | 1800.0103 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 397 | UAD1415 | 1800.0125 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 398 | UAD1416 | 1800.0128 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 399 | UAD1418 | 1800.0128 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 400 | UAD1419 | 1800.0157 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 401 | UAD1420 | 1800.0158 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 402 | UAD1421 | 1800.0165 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 403 | UAD1422 | 1800.0166 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 404 | UAD1423 | 1800.0169 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 405 | UAD1424 | 1800.0170 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 406 | UAD1425 | 1800.0184 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 407 | UAD1426 | 1800.0185 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 408 | UAD1427 | 1800.0186 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 409 | UAD1428 | 1800.0189 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 410 | UAD1429 | 1800.0190 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 411 | UAD1430 | 1800.0191 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 412 | UAD1431 | 1800.0192 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 413 | UAD1432 | 1800.0192 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 414 | UAD1433 | 1800.0195 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 415 | UAD1434 | 1800.0196 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 416 | UAD1435 | 1800.0197 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 417 | UAD1436 | 1800.0198 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 418 | UAD1438 | 1800.0273 | not tracked | none in current dispatcher | 0 | not_loaded |
| 419 | UAD1439 | 1800.0208; 1800.0272 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 420 | UAD1440 | 1800.0206 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 421 | UAD1442 | 1800.0208; 1800.0272 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 422 | UAD1443 | 1800.0210 | not tracked | none in current dispatcher | 0 | not_loaded |
| 423 | UAD1444 | 1800.0211 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 424 | UAD1445 | 1800.0212 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 425 | UAD1446 | 1800.0213 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 426 | UAD1447 | 1800.0215 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 427 | UAD1448 | 1800.0221 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 428 | UAD1449 | 1800.0239 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 429 | UAD1450 | 1800.0243 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 430 | UAD1451 | 1800.0244 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 431 | UAD1452 | 1800.0277 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 432 | UAD1453 | 1800.0287 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 433 | UAD1455 | 1800.0319 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 8 | loaded_with_collected_tests |
| 434 | UAD1456 | 1800.0309 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 435 | UAD1457 | 1800.0310 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 436 | UAD1458 | 1800.0311 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 437 | UAD1459 | 1800.0312 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 438 | UAD1460 | 1800.0313 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 439 | UAD1461 | 1800.0313 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 4 | loaded_with_collected_tests |
| 440 | UAD1462 | 1800.0322 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 441 | UAD1463 | 1800.0330 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 442 | UAD1464 | 1800.0331 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 443 | UAD1465 | 1800.0332 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 444 | UAD1467 | 1800.0345 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 445 | UAD1468 | 1800.0347 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 446 | UAD1469 | 1800.0359 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 447 | UAD1470 | 1800.0360 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 448 | UAD1471 | 1800.0363 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 449 | UAD1472 | 1800.0363 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 450 | UAD1473 | 1800.0364 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 451 | UAD1474 | 1800.0365 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 452 | UAD1475 | 1800.0365 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 453 | UAD1476 | 1800.0367 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 454 | UAD1477 | 1800.0374 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 455 | UAD1478 | 1800.0377 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 456 | UAD1479 | 1800.0378 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 457 | UAD1480 | 1800.0383 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 458 | UAD1481 | 1800.0385 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 459 | UAD1482 | 1800.0390 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 460 | UAD1483 | 1800.0393 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 461 | UAD1484 | 1800.0398 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 462 | UAD1485 | 1900.0017 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 463 | UAD1486 | 2000.0012 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 464 | UAD1487 | 2000.0021 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 465 | UAD1488 | 2000.0032 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 466 | UAD1489 | 2000.0035 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 467 | UAD1490 | 2000.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 468 | UAD1491 | 2000.0050 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 469 | UAD1492 | 2000.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 470 | UAD1493 | 2000.0067 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 471 | UAD1494 | 2000.0078 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 472 | UAD1495 | 2000.0078 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 473 | UAD1496 | 2000.0088 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 474 | UAD1497 | 2000.0089 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 475 | UAD1498 | 2000.0092 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 476 | UAD1499 | 2000.0101 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 477 | UAD1500 | 2000.0102 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 478 | UAD1501 | 2000.0103 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 479 | UAD1502 | 2100.0045 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 480 | UAD1505 | 2200.0154; 2200.0002 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 481 | UAD1506 | 2200.0154; 2200.0002 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 482 | UAD1507 | 2200.0154; 2200.0002 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 483 | UAD1508 | 2200.0017 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 484 | UAD1509 | 2200.0034 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 485 | UAD1510 | 2200.0037 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 486 | UAD1511 | 2200.0038 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 487 | UAD1512 | 1000.0158 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 488 | UAD1513 | 1000.0158 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 489 | UAD1514 | 1000.0158 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 490 | UAD1515 | 1000.0158 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 491 | UAD1516 | 2200.0038 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 492 | UAD1517 | 2200.0038 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 493 | UAD1518 | 2200.0038 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 494 | UAD1519 | 1000.0043 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 495 | UAD1520 | 2400.0513 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 496 | UAD1521 | 1000.0132 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 497 | UAD1522 | 1000.0133 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 498 | UAD1523 | 2200.0062 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 1 | loaded_with_collected_tests |
| 499 | UAD1524 | 2200.0075 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 500 | UAD1525 | 2200.0076 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 501 | UAD1526 | 2200.0080 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 502 | UAD1527 | 2200.0081; 2400.0052 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 503 | UAD1528 | 2200.0082 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 504 | UAD1529 | 2200.0082 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 3 | loaded_with_collected_tests |
| 505 | UAD1530 | 2400.0053; 2200.0082 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 506 | UAD1531 | 2200.0083 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 507 | UAD1532 | 2200.0084 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 508 | UAD1533 | 2200.0084; 2400.0055 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 509 | UAD1534 | 2200.0085 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 510 | UAD1535 | 2200.0154; 2200.0002 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 511 | UAD1536 | 2200.0154; 2200.0002 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 512 | UAD1537 | 2400.0001 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 513 | UAD1538 | 2400.0002 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 514 | UAD1539 | 2400.0003 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 515 | UAD1540 | 2400.0004 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 516 | UAD1541 | 2400.0013 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 517 | UAD1542 | 2400.0018 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 518 | UAD1543 | 2400.0017 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 519 | UAD1544 | 2400.0041 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 520 | UAD1545 | 2400.0042 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 521 | UAD1546 | 2400.0051 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 522 | UAD1548 | 2400.0053 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 523 | UAD1551 | 2400.0054 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 524 | UAD1552 | 2400.0055 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 525 | UAD1554 | 2400.0056 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 526 | UAD1555 |  | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 527 | UAD1556 | 2400.0080; 2400.0502 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 21 | loaded_with_collected_tests |
| 528 | UAD1557 | 2400.0080; 2400.0502 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 529 | UAD1558 | 2400.0081; 2400.0503 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 530 | UAD1559 | 2400.0082; 2400.0504 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 531 | UAD1560 | 2400.0295 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 532 | UAD1561 | 2400.0405 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 533 | UAD1562 | 2400.0406 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 534 | UAD1563 | 2400.0413 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 535 | UAD1568 | 2500.0002 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 9 | loaded_with_collected_tests |
| 536 | UAD1569 | 2500.0003 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 537 | UAD1570 |  | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 538 | UAD1571 | 2500.0005 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 539 | UAD1572 | 2500.0006 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 540 | UAD1573 | 2500.0007 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 541 | UAD1574 | 2500.0008 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 542 | UAD1575 | 2500.0009 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 543 | UAD1576 | 2500.0010 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 544 | UAD1577 | 2500.0012 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 545 | UAD1578 | 2500.0013 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 10 | loaded_with_collected_tests |
| 546 | UAD1579 | 2500.0019 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 547 | UAD1580 | 2500.0023 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 548 | UAD1581 | 2500.0024 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 549 | UAD1582 | 2500.0025 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 550 | UAD1583 | 2500.0031 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 551 | UAD1584 | 2500.0032 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 552 | UAD1585 | 2500.0033 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 553 | UAD1586 | 2500.0036 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 554 | UAD1587 | 2500.0041 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 555 | UAD1588 | 2500.0044 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 556 | UAD1589 | 2500.0046 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 557 | UAD1590 | 2500.0048 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 558 | UAD1591 | 2500.0049 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 559 | UAD1592 | 2500.0050 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 560 | UAD1593 | 2500.0051 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 561 | UAD1594 | 2500.0055 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 562 | UAD1595 | 2500.0057 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 563 | UAD1596 | 2500.0058 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 564 | UAD1597 | 2500.0060 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 565 | UAD1598 | 2500.0061 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 566 | UAD1599 | 2500.0062 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 567 | UAD1600 | 2500.0064 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 568 | UAD1601 | 2500.0066 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 569 | UAD1602 | 2500.0067 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 570 | UAD1603 | 2500.0071 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 571 | UAD1604 | 2500.0072 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 572 | UAD1605 | 2500.0073 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 573 | UAD1606 | 2500.0074 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 574 | UAD1607 | 2500.0075 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 575 | UAD1608 | 2500.0076 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 576 | UAD1609 | 2500.0078 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 577 | UAD1610 | 2500.0081 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 578 | UAD1611 | 2500.0084 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 2 | loaded_with_collected_tests |
| 579 | UAD1612 | 2500.0151 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 580 | UAD1613 | 2500.0163 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 581 | UAD1614 | 2500.0165 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 582 | UAD1615 | 2500.0168 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 583 | UAD1616 | 2600.0003 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 584 | UAD1617 | 2600.0004 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 585 | UAD1618 | 2600.0005 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 586 | UAD1619 | 2600.0016 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 587 | UAD1620 | 2600.0018 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 588 | UAD1622 | 2600.0019 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 589 | UAD1623 | 2600.0020 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 590 | UAD1624 | 1300.0010 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 591 | UAD1625 | 1300.0010 | not tracked | none in current dispatcher | 0 | not_loaded |
| 592 | UAD1626 | 3000.0008 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 593 | UAD1627 | 3000.0009 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 594 | UAD1629 | 3000.0018 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 595 | UAD1630 | 3000.0019 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 596 | UAD1631 | 3000.0019 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 597 | UAD1632 | 3000.0020 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 598 | UAD1633 | 3000.0020 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 599 | UAD1634 | 3000.0021 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 600 | UAD1635 | 3000.0022 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 601 | UAD1636 | 3000.0022 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 602 | UAD1637 | 3000.0023 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 603 | UAD1638 | 3000.0023 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 604 | UAD1639 | 3000.0024 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 605 | UAD1640 | 3000.0025 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 606 | UAD1641 | 3000.0025 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 607 | UAD1642 | 3000.0026 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 608 | UAD1643 | 3000.0027 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 609 | UAD1644 | 3000.0027 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 610 | UAD1645 | 3000.0028 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 611 | UAD1646 | 3000.0028 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 612 | UAD1647 | 3000.0029 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 12 | loaded_with_collected_tests |
| 613 | UAD1648 | 3000.0029 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 614 | UAD1649 | 3000.0030 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 615 | UAD1650 | 3000.0030 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 616 | UAD1652 | 3000.0033 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 617 | UAD1653 | 3000.0034 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 618 | UAD1656 | 1400.0638 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 619 | UAD1657 | 3000.0051 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 620 | UAD1658 | 3000.0053 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 621 | UAD1659 | 3100.0003 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 622 | UAD1660 | 3100.0004 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 623 | UAD1661 | 3100.0005 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 624 | UAD1662 | 3100.0006 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 625 | UAD1663 | 3100.0007 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 626 | UAD1664 | 3200.0004 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 9 | loaded_with_collected_tests |
| 627 | UAD1665 | 3200.0005 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 9 | loaded_with_collected_tests |
| 628 | UAD1667 | 3200.0006 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 629 | UAD1668 | 3200.0007 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 630 | UAD1669 | 3200.0008 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 9 | loaded_with_collected_tests |
| 631 | UAD1670 | 3200.0009 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 632 | UAD1671 | 3200.0010 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 37 | loaded_with_collected_tests |
| 633 | UAD1672 | 3200.0011 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 9 | loaded_with_collected_tests |
| 634 | UAD1673 | 3200.0012 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 11 | loaded_with_collected_tests |
| 635 | UAD1675 | 3200.0021 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 636 | UAD1676 | 3300.0002 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 637 | UAD1677 | 3300.0007 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 638 | UAD1678 | 3300.0008 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 639 | UAD1680 | 3600.0002 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 640 | UAD1681 | 3600.0003 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 641 | UAD1683 | 3700.0002 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 642 | UAD1684 | 3700.0003 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 643 | UAD1685 | 3900.0033 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 644 | UAD1686 | 3900.0091 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 645 | UAD1687 | 3900.0097 | other_conditional_scoped | app/services/scoped_required_data.py :: evaluate_scoped_rule | 7 | loaded_with_collected_tests |
| 646 | UAD1688 | 3900.0107 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 647 | UAD1689 | 3900.0145 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 648 | UAD1690 | 3900.0148 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 649 | UAD1691 | 3900.0154 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 650 | UAD1692 | 3900.0192 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 651 | UAD1693 | 0300.0063 | aggregate_cross_record_consistency | app/services/aggregate_cross_record_required_data.py :: evaluate_aggregate_cross_record | 3 | loaded_with_collected_tests |
| 652 | UAD1694 | 0700.0089 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 653 | UAD1695 | 0300.0039 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 654 | UAD1696 | 0300.0039 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 655 | UAD1698 | 0800.0012 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 656 | UAD1699 | 1000.0019 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 657 | UAD1700 | 1000.0023 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 658 | UAD1701 | 1000.0102 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 659 | UAD1702 |  | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 660 | UAD1703 |  | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 661 | UAD1704 |  | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 662 | UAD1705 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 663 | UAD1707 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 664 | UAD1708 | 1400.0901 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 665 | UAD1710 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 666 | UAD1711 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 667 | UAD1712 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 668 | UAD1713 |  | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 669 | UAD1714 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 670 | UAD1715 |  | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 671 | UAD1716 |  | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 672 | UAD1717 |  | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 673 | UAD1718 |  | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 674 | UAD1719 |  | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 675 | UAD1720 |  | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 676 | UAD1721 | 0500.0016 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 677 | UAD1722 | 2400.0056 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 678 | UAD1723 | 2400.0080; 2400.0502 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 679 | UAD1725 | 0900.0012 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 680 | UAD1726 | 0900.0010 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 681 | UAD1727 | 2500.0084 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 682 | UAD1728 | 0600.0009 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 683 | UAD1730 | 0700.0089 | value_cross_field_consistency | app/services/value_consistency_required_data.py :: evaluate_value_consistency | 1 | loaded_with_collected_tests |
| 684 | UAD1731 | 1800.0202 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 685 | UAD1732 | 1300.0010 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 686 | UAD1733 | 1300.0013 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 687 | UAD1734 | 1800.0209 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 688 | UAD1735 | 1800.0207; 1800.0342 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 689 | UAD1736 | 1400.0742 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 690 | UAD1737 | 1400.0778 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 691 | UAD1738 | 1400.0784 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 692 | UAD1739 | 1400.0748 | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 693 | UAD1740 |  | existing_context_required | app/services/existing_context_required_data.py :: evaluate_existing_context_required | 1 | loaded_with_collected_tests |
| 694 | UAD1741 | 2500.0023 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 695 | UAD1742 | 0100.0015 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 696 | UAD1743 | 0100.0016 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 697 | UAD1744 | 1800.0342; 1800.0207 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 698 | UAD1745 | 1200.0034 | numeric_bounds | app/services/numeric_bound_required_data.py :: evaluate_numeric_bound | 1 | loaded_with_collected_tests |
| 699 | UAD1746 | 1300.0013 | alternative_mutually_exclusive | none in current dispatcher | 0 | not_loaded |
| 700 | UAD1747 | 2400.0492; 1400.0348 | relationship_reference_integrity | app/services/relationship_reference_required_data.py :: evaluate_relationship_reference | 1 | loaded_with_collected_tests |
| 701 | UAD1748 | 1800.0190 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 702 | UAD1749 | 1800.0191 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 703 | UAD1750 | 4000.0004 | unconditional_required | app/services/required_data.py :: evaluate_required_data (unconditional presence) | 3 | loaded_with_collected_tests |
| 704 | UAD1751 | 4000.0005 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 705 | UAD1752 | 4000.0006 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 706 | UAD1753 | 4000.0008 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 707 | UAD1754 | 4000.0007 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 708 | UAD1755 | 4000.0007 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 709 | UAD1756 | 4000.0007 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 710 | UAD1757 | 4000.0007 | date_chronology | app/services/date_chronology_required_data.py :: evaluate_date_chronology | 1 | loaded_with_collected_tests |
| 711 | UAD1758 | 1800.0318 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 712 | UAD1759 | 2200.0085 | uniqueness_cardinality | app/services/uniqueness_cardinality_required_data.py :: evaluate_uniqueness_cardinality | 1 | loaded_with_collected_tests |
| 713 | UAD1760 | 1800.0278 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 714 | UAD1761 | 1100.0023 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 715 | UAD1762 | 1200.0007 | single_equality_conditional | app/services/required_data.py :: evaluate_required_data (ConditionalRule) | 3 | loaded_with_collected_tests |
| 716 | UAD1763 | 2000.0048; 2000.0047 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 717 | UAD1764 |  | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 718 | UAD1765 | 1500.0186; 1500.0189 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 719 | UAD1766 |  | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 720 | UAD1767 | 0100.0050 | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 721 | UAD1768 |  | format_precision_length | app/services/representation_restriction_required_data.py :: evaluate_representation_restriction | 1 | loaded_with_collected_tests |
| 722 | UAD1769 | 1800.0233 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 723 | UAD1770 | 1800.0234 | single_equality_conditional | app/services/single_equality_required_data.py :: evaluate_single_equality | 3 | loaded_with_collected_tests |
| 724 | UAD1771 | 1800.0274 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 725 | UAD1772 | 1800.0154 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 726 | UAD1773 | 1800.0337 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 727 | UAD1774 | 1800.0171 | required_structures | app/services/required_structure_required_data.py :: evaluate_required_structure | 1 | loaded_with_collected_tests |
| 728 | UAD1775 | 1800.0379 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 729 | UAD1776 | 1800.0394 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 730 | UAD1777 | 1800.0399 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 731 | UAD1778 | 1800.0392 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
| 732 | UAD1779 | 1800.0391 | other_conditional_scoped | none in current dispatcher | 0 | not_loaded |
