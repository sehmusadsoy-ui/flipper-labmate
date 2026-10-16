#!/usr/bin/env bash
# LabMate v1.8 integrated feature acceptance: existing real portable C and
# firmware-interface stub regression tests in ONE fail-fast, no-flash gate.
# Not physical sensor, UART, PWM or SD-card acceptance.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

run_guard() {
  echo "::group::SOURCE GUARD: $1"
  python3 "scripts/$1"
  echo "::endgroup::"
}

run_model() {
  local name="$1"; shift
  echo "::group::NATIVE C: $name"
  cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc -x c \
    "$@" -o "$workdir/$name"
  "$workdir/$name"
  echo "::endgroup::"
}

run_guard check_repo_layout.py
run_guard check_v16_boundaries.py
run_guard check_v17_ui_layout.py
run_guard check_v18_coordinator.py
run_guard check_v18_exitfix_stage.py
run_guard check_v18_counter_resume.py
run_guard check_v18_button_resume.py
run_guard check_v18_uart.py
run_guard check_v18_i2c.py
run_guard check_v18_i2c_control_model.py
run_guard check_v18_i2c_present.py
run_guard check_v18_i2c_runtime.py
run_guard check_v18_onewire_codec.py
run_guard check_v18_e11_software_acceptance.py

# v1.5 CSV, History storage codecs, persistent Profiles, navigation.
run_model resource-policy src/labmate_resource_policy.c tests/test_resource_policy.c.inc
run_model navigation src/labmate_navigation.c tests/test_navigation.c.inc
run_model profiles src/labmate_profiles.c tests/test_profiles.c.inc
run_model csv-logger src/labmate_logger_codec.c tests/test_logger_codec.c.inc

# v1.6/v1.7 Frequency, Pulse, PWM, Counter, Button, Alerts.
run_model frequency-gate src/labmate_frequency_gate.c tests/test_frequency_gate.c.inc
run_model pulse-math src/labmate_pulse_math.c tests/test_pulse_math.c.inc
run_model pwm-settings src/labmate_pwm_settings.c tests/test_pwm_settings.c.inc
run_model counter-math src/labmate_counter_math.c tests/test_counter_math.c.inc
run_model button-logic src/labmate_button_logic.c tests/test_button_logic.c.inc
run_model threshold src/labmate_threshold.c tests/test_threshold.c.inc

# v1.8 UART: true firmware ownership, RX overflow simulated with HAL shim.
run_model uart-text src/labmate_uart_text.c tests/test_uart_text.c.inc
echo "::group::NATIVE C: UART genuine driver with host HAL shims"
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Itests/uart_host_stubs -Isrc \
  src/labmate_uart.c src/labmate_uart_text.c tests/test_uart_hal_host.c \
  -o "$workdir/uart-driver"
"$workdir/uart-driver"
echo "::endgroup::"

# v1.8 COMM: bounded I2C scan/cancel and real adapter, stock+matched SDK.
run_model comm-resource src/labmate_comm_resource.c tests/test_comm_resource.c.inc
run_model i2c-scan src/labmate_i2c_scan.c tests/test_i2c_scan.c.inc
run_model i2c-control src/labmate_i2c_scan.c src/labmate_i2c_control.c tests/test_i2c_control.c.inc
run_model i2c-present src/labmate_i2c_scan.c src/labmate_i2c_control.c src/labmate_i2c_present.c tests/test_i2c_present.c.inc
run_model i2c-session src/labmate_i2c_scan.c src/labmate_i2c_control.c src/labmate_i2c_session.c tests/test_i2c_session.c.inc
for target in stock patched; do
  echo "::group::NATIVE C: I2C $target HAL interface"
  defs=()
  if [[ "$target" == "patched" ]]; then
    defs=(-DLABMATE_MOMENTUM_TIMED_I2C_API=1 -DLABMATE_TEST_LEASE_API=1)
  fi
  cc -std=c11 -Wall -Wextra -Werror -pedantic -Isrc \
    -Itests/i2c_hal_stubs "${defs[@]}" \
    src/labmate_i2c_scan.c src/labmate_i2c_control.c \
    src/labmate_i2c_session.c src/labmate_i2c_momentum.c \
    tests/test_i2c_momentum_hal.c -o "$workdir/i2c-$target"
  "$workdir/i2c-$target"
  echo "::endgroup::"
done

# DS18B20: pure CRC/resolution + actual OneWire/PA4 owner under host HAL.
run_model onewire-codec src/labmate_onewire_ds18b20.c tests/test_onewire_ds18b20.c.inc
echo "::group::NATIVE C: OneWire 3.3V-safe PA4 hardware-interface shims"
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Itests/onewire_host_stubs -Isrc -x c \
  src/labmate_comm_resource.c src/labmate_onewire_ds18b20.c \
  src/labmate_onewire_hw.c tests/test_onewire_hw.c \
  -o "$workdir/onewire-hw"
"$workdir/onewire-hw"
echo "::endgroup::"

# The updater's pure parser/reject-path tests, not a device install.
python3 -m unittest discover -v -s tests -p test_v18_full_update_bundle.py
python3 -m unittest discover -v -s tests -p test_v18_full_review_pair.py
python3 -m unittest discover -v -s tests -p test_v18_e11_local_preflight.py
python3 -m unittest discover -v -s tests -p test_v18_e11_review_stage.py
python3 -m unittest discover -v -s tests -p test_v18_e11_resource_impact.py
python3 -m unittest discover -v -s tests -p test_v18_e11_split_review.py
python3 -m unittest discover -v -s tests -p test_v18_e11_live_labmate_sd.py
python3 -m unittest discover -v -s tests -p test_v18_e11_live_snapshot.py
python3 -m unittest discover -v -s tests -p test_v18_e11_external_sd_ro.py
python3 -m unittest discover -v -s tests -p test_v18_e11_full_sd_pc_copy.py
python3 -m unittest discover -v -s tests -p test_v18_e11_usb_sd_backup.py
python3 -m unittest discover -v -s tests -p test_v18_e11_recovery_readiness.py
python3 scripts/audit_v18_e11_recovery_readiness.py
python3 -m unittest discover -v -s tests -p test_v18_e11_installed_resource_manifest.py
python3 -m unittest discover -v -s tests -p test_v18_e11_updater_cleanup_semantics.py
python3 -m unittest discover -v -s tests -p test_v18_e11_split_trial_gate.py
python3 -m unittest discover -v -s tests -p test_v18_e11_packed_manifest_integrity.py
python3 scripts/check_v18_e11_split_trial_gate.py
echo "V1.8 FINAL INTEGRATED HOST SOFTWARE REGRESSION PASS"
echo "NOT PROVEN: live peripherals, actual microSD durability, Excel, firmware boot or rollback."
