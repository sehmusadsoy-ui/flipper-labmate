# Wiring Example

## Built-in loopback test

Use the LabMate Signal Generator to test the Frequency Meter or Pulse Analyzer.

```text
PA7 / physical pin 2  ->  PC1 / physical pin 15
```

No external supply is needed for this loopback test.

## Procedure

1. Open **Signal Generator**.
2. Select 1 Hz, 2 Hz, or 5 Hz.
3. Press OK to start the generator.
4. Return to the LabMate menu.
5. Open **Frequency Meter** or **Pulse Analyzer**.
6. Use PC1 as the measurement input.

## Expected frequency results

| Generator | Expected reading |
|---:|---:|
| 1 Hz | 1.00 Hz |
| 2 Hz | 2.00 Hz |
| 5 Hz | 5.00 Hz |

## Safety

- Use known **3.3 V-compatible** digital signals only.
- Do not connect 5 V or 12 V directly to Flipper GPIO.
- Do not connect vehicle electrical lines directly.
- Do not connect unknown-voltage sources.
- Use proper level shifting or isolation when interfacing with higher-voltage systems.
