# Inventory of Tests

For a stable filename-only inventory, you could use:
```text
dir /b /o:n tests\test*.py > docs\testing\it-5-test-inventory.txt
```

That avoids timestamps and file sizes changing unnecessarily.